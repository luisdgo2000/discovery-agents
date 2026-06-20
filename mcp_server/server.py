"""Servidor MCP del ecosistema Discovery Agents — v2 (workspace persistente).

Principio (revisión H3/H5): el contexto del chat NO es memoria. Toda la información pesada vive
en `work/<caso>/` y las tools devuelven índices/resúmenes compactos. El contenido se pide bajo
demanda por ID y chunk. Los entregables se escriben server-side: nunca viajan por el contexto.

Requiere el SDK `mcp` (Python >= 3.10). El núcleo determinista NO depende de mcp y puede usarse
vía `python -m mcp_server.cli` en Python 3.9.
"""
from __future__ import annotations

import json
import os

from . import consolidator, workspace
from .artefactos.mermaid import generar_diagramas
from .artefactos.tablas import generar_tablas
from .discovery.assembler import ensamblar_discovery
from .discovery.rubric import rubrica_serializable
from .discovery.scorer import score_discovery
from .discovery.template import schema_vacio
from .extractors.manifest import build_manifest
from .pipeline import construir_evidencia
from .prompts import cargar_prompt

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - solo en entornos sin el SDK
    raise SystemExit(
        "El SDK 'mcp' no está instalado o requiere Python >= 3.10.\n"
        "Instala con:  pip install 'mcp[cli]'\n"
        "Para probar el núcleo determinista sin MCP usa:  python -m mcp_server.cli ...\n"
        f"(detalle: {exc})"
    )

mcp = FastMCP("discovery-agents")


# ---------------------------------------------------------------------------
# FASE 0-1: manifiesto y extracción (persistente, devuelve solo índices)
# ---------------------------------------------------------------------------
@mcp.tool()
def build_manifest_tool(folder: str) -> str:
    """Escanea la carpeta de insumos y devuelve el manifiesto clasificado (JSON compacto).

    Úsalo en el PASO 0 para proponer la estrategia sin leer contenido (no gasta tokens)."""
    return _json(build_manifest(folder))


@mcp.tool()
def extract_evidence(folder: str, caso: str = "") -> str:
    """Extrae TODOS los insumos a work/<caso>/10_evidence/ y devuelve SOLO el índice compacto.

    El índice trae: id de cada evidencia, resumen de 1 línea, fuentes_detectadas del Excel y
    métricas. El contenido NO viaja por el contexto: pídelo con get_evidence(caso, id, chunk)."""
    return _json(construir_evidencia(folder, caso=caso))


@mcp.tool()
def get_evidence(caso: str, evidence_id: str, chunk: int = 0) -> str:
    """Devuelve un fragmento (~3k tokens) de la vista de texto de una evidencia, bajo demanda.

    Úsalo SOLO para lo que vas a razonar ahora (p. ej. la transcripción que estás destilando)."""
    return _json(workspace.get_evidence_chunk(caso, evidence_id, chunk))


@mcp.tool()
def pending_distillation(caso: str) -> str:
    """IDs de transcripciones SIN destilado (incremental: solo destila lo nuevo)."""
    return _json({"pendientes": workspace.evidencias_sin_destilar(caso)})


# ---------------------------------------------------------------------------
# Estado compartido: los agentes escriben sus resultados aquí (no por el chat)
# ---------------------------------------------------------------------------
@mcp.tool()
def save_state(caso: str, archivo: str, contenido: str) -> str:
    """Guarda el resultado de una fase en el workspace (memoria compartida en disco).

    Archivos permitidos: 20_destilado/D<EID>.json, 30_discovery.json, 40_hipotesis.json,
    50_critica.json, 60_redaccion.md, 60_inconsistencias.json."""
    path = workspace.save_state(caso, archivo, contenido)
    return _json({"guardado": archivo, "ruta": path})


@mcp.tool()
def load_state(caso: str, archivo: str) -> str:
    """Lee un archivo de estado del workspace (p. ej. 30_discovery.json para el Crítico)."""
    if archivo.endswith(".md"):
        contenido = workspace.load_text(caso, archivo)
        return contenido if contenido is not None else _json({"error": f"No existe {archivo}"})
    data = workspace.load_json(caso, archivo)
    return _json(data if data is not None else {"error": f"No existe {archivo}"})


@mcp.tool()
def consolidate(caso: str) -> str:
    """Une los destilados y DETECTA CONFLICTOS numéricos entre Excel y reuniones (0 tokens).

    Ejecutar tras destilar todas las transcripciones. Los conflictos van al Constructor/Redactor."""
    return _json(consolidator.consolidar(caso))


# ---------------------------------------------------------------------------
# Contratos y prompts
# ---------------------------------------------------------------------------
@mcp.tool()
def get_schema() -> str:
    """Schema TIPADO del Discovery (contrato exacto que debe rellenar el Constructor)."""
    return _json(schema_vacio())


@mcp.tool()
def get_rubrica() -> str:
    """Rúbrica de preguntas poderosas (bloques, preguntas, pesos) para el Crítico."""
    return _json(rubrica_serializable())


@mcp.tool()
def get_subagent_prompt(nombre: str) -> str:
    """System prompt de un subagente: destilador-transcripciones, constructor-discovery,
    generador-hipotesis, critico-brechas, redactor-experto."""
    return cargar_prompt(nombre)


# ---------------------------------------------------------------------------
# FASES FINALES: scoring y ensamblado server-side (los entregables no viajan por el chat)
# ---------------------------------------------------------------------------
@mcp.tool()
def score_state(caso: str) -> str:
    """Calcula el score/veredicto determinista de work/<caso>/30_discovery.json.

    Persiste 55_score.json y devuelve solo el resumen (veredicto, completitud, condiciones)."""
    discovery = workspace.load_json(caso, "30_discovery.json")
    if discovery is None:
        return _json({"error": "No existe 30_discovery.json: el Constructor debe correr primero."})
    score = score_discovery(discovery)
    workspace.save_json(caso, "55_score.json", score)
    workspace.append_metric(caso, "scoring", {
        "veredicto": score["veredicto"], "completitud": score["completitud_total"],
    })
    return _json({
        "veredicto": score["veredicto"],
        "completitud_total": score["completitud_total"],
        "condiciones_para_avanzar": score["condiciones_para_avanzar"],
        "n_brechas": score["n_brechas"],
    })


@mcp.tool()
def assemble(caso: str, caso_de_uso: str = "") -> str:
    """Ensambla TODO server-side en work/<caso>/outputs/: discovery_final.md (con la narrativa
    del Redactor si existe), brechas.md, veredicto.json, diagramas/ y tablas/.

    Devuelve solo el veredicto y la lista de archivos generados: el contenido NO viaja por el chat."""
    discovery = workspace.load_json(caso, "30_discovery.json")
    if discovery is None:
        return _json({"error": "No existe 30_discovery.json: el Constructor debe correr primero."})
    redaccion = workspace.load_text(caso, "60_redaccion.md")
    inconsistencias = workspace.load_json(caso, "60_inconsistencias.json")
    resultado = ensamblar_discovery(discovery, caso_de_uso=caso_de_uso or caso,
                                    redaccion_md=redaccion)

    generados = []
    generados.append(workspace.save_text(caso, "outputs/discovery_final.md", resultado["markdown"]))
    generados.append(workspace.save_text(caso, "outputs/brechas.md", resultado["brechas_markdown"]))
    generados.append(workspace.save_json(caso, "outputs/veredicto.json", resultado["veredicto"]))
    workspace.save_json(caso, "55_score.json", resultado["score"])
    for nombre, contenido in generar_diagramas(discovery, caso_de_uso or caso).items():
        generados.append(workspace.save_text(caso, os.path.join("outputs", "diagramas", nombre), contenido))
    for nombre, contenido in generar_tablas(discovery, inconsistencias).items():
        generados.append(workspace.save_text(caso, os.path.join("outputs", "tablas", nombre), contenido))
    workspace.append_metric(caso, "ensamblado", {"archivos": len(generados)})

    return _json({
        "veredicto": resultado["veredicto"],
        "narrativa_incluida": bool(redaccion),
        "archivos_generados": generados,
    })


def _json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
