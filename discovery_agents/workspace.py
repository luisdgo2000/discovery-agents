"""Workspace de estado en disco — la memoria compartida del ecosistema.

El contexto del chat NO es memoria: cada fase lee/escribe archivos en `work/<caso>/` a través
del MCP, y el LLM solo ve índices y resúmenes. Esto hace al proceso reanudable, incremental,
trazable (IDs de evidencia citables) y barato en tokens.

Estructura:
    work/<caso>/
    ├─ 00_manifest.json        # inventario clasificado + metadatos
    ├─ 10_evidence/
    │  ├─ index.json           # lo ÚNICO que ve el orquestador (~500 tokens)
    │  └─ E001_<slug>.json     # evidencia completa por insumo, direccionable por ID
    ├─ 20_destilado/           # D<EID>.json por transcripción + consolidado.json
    ├─ 30_discovery.json       # schema tipado rellenado (Constructor)
    ├─ 40_hipotesis.json       # Generador
    ├─ 50_critica.json         # Crítico
    ├─ 55_score.json           # scorer determinista
    ├─ 60_redaccion.md         # narrativa del Redactor Experto
    ├─ 60_inconsistencias.json
    ├─ _metrics.json           # telemetría por fase
    └─ outputs/                # entregables finales (doc, brechas, veredicto, diagramas/, tablas/)
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import List, Optional

# Archivos de estado que los agentes pueden escribir vía MCP (lista blanca).
#
# Es una lista blanca y no una lista negra a propósito: un agente solo puede escribir en los
# casilleros que le corresponden por fase, y cualquier otra ruta —incluida `../fuera.json`— se
# rechaza. Los entregables de `outputs/` no están aquí porque los escribe Python, no el modelo.
#
# `60_redaccion.json` es el contrato actual del Redactor (prosa indexada por sección);
# `60_redaccion.md` se mantiene permitido para no invalidar el trabajo hecho con el contrato
# anterior, que el ensamblador sigue sabiendo leer.
ARCHIVOS_ESTADO_PERMITIDOS = re.compile(
    r"^(20_destilado/D[\w\-]+\.json|20_destilado/consolidado\.json|30_discovery\.json|"
    r"40_hipotesis\.json|50_critica\.json|55_score\.json|"
    r"60_redaccion\.(json|md)|60_inconsistencias\.json)$"
)

CHUNK_CHARS = 12_000  # ~3k tokens por chunk de evidencia


def work_root() -> str:
    return os.environ.get("DISCOVERY_WORK_ROOT", os.path.join(os.getcwd(), "work"))


def work_dir(caso: str) -> str:
    d = os.path.join(work_root(), caso)
    os.makedirs(os.path.join(d, "10_evidence"), exist_ok=True)
    os.makedirs(os.path.join(d, "20_destilado"), exist_ok=True)
    os.makedirs(os.path.join(d, "outputs"), exist_ok=True)
    return d


def save_json(caso: str, relpath: str, obj: object) -> str:
    path = os.path.join(work_dir(caso), relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
    return path


def load_json(caso: str, relpath: str) -> Optional[dict]:
    path = os.path.join(work_dir(caso), relpath)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_text(caso: str, relpath: str, texto: str) -> str:
    path = os.path.join(work_dir(caso), relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(texto)
    return path


def load_text(caso: str, relpath: str) -> Optional[str]:
    path = os.path.join(work_dir(caso), relpath)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def save_state(caso: str, relpath: str, contenido: str) -> str:
    """Escritura de estado por agentes IA: solo archivos de la lista blanca."""
    relpath = relpath.replace("\\", "/").lstrip("/")
    if not ARCHIVOS_ESTADO_PERMITIDOS.match(relpath):
        raise ValueError(
            f"Archivo de estado no permitido: {relpath}. "
            "Permitidos: 20_destilado/D*.json, 20_destilado/consolidado.json, 30_discovery.json, "
            "40_hipotesis.json, 50_critica.json, 55_score.json, 60_redaccion.md, 60_inconsistencias.json"
        )
    if relpath.endswith(".json"):
        # valida que sea JSON antes de persistir
        return save_json(caso, relpath, json.loads(contenido))
    return save_text(caso, relpath, contenido)


def get_evidence_chunk(caso: str, evidence_id: str, chunk: int = 0) -> dict:
    """Devuelve un fragmento de la vista de texto de una evidencia (contenido bajo demanda)."""
    index = load_json(caso, os.path.join("10_evidence", "index.json")) or {}
    item = next((i for i in index.get("items", []) if i["id"] == evidence_id), None)
    if item is None:
        return {"error": f"Evidencia {evidence_id} no existe. IDs: "
                         f"{[i['id'] for i in index.get('items', [])]}"}
    registro = load_json(caso, os.path.join("10_evidence", item["archivo_evidencia"]))
    vista = registro.get("vista_texto", "") if registro else ""
    total = max(1, (len(vista) + CHUNK_CHARS - 1) // CHUNK_CHARS)
    chunk = max(0, min(chunk, total - 1))
    return {
        "id": evidence_id,
        "chunk": chunk,
        "total_chunks": total,
        "contenido": vista[chunk * CHUNK_CHARS:(chunk + 1) * CHUNK_CHARS],
    }


def evidencias_sin_destilar(caso: str) -> List[str]:
    """IDs de transcripciones que aún no tienen destilado D<ID>.json (procesamiento incremental)."""
    index = load_json(caso, os.path.join("10_evidence", "index.json")) or {}
    pendientes = []
    for item in index.get("items", []):
        if item.get("tipo") != "transcripcion":
            continue
        if load_json(caso, os.path.join("20_destilado", f"D{item['id']}.json")) is None:
            pendientes.append(item["id"])
    return pendientes


def append_metric(caso: str, fase: str, datos: dict) -> None:
    """Telemetría ligera por fase (para medir el ahorro real de tokens)."""
    path = os.path.join(work_dir(caso), "_metrics.json")
    metricas = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            metricas = json.load(fh)
    metricas.append({"fase": fase, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **datos})
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(metricas, fh, ensure_ascii=False, indent=2)
