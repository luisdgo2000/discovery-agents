"""Pipeline determinista de extracción (0 tokens de LLM).

Regla central: la evidencia NUNCA viaja por el contexto del modelo. Cada insumo se extrae a un registro con ID (`E001`, `E002`, ...) persistido en
`work/<caso>/10_evidence/`, y lo único que se devuelve (y que el LLM ve) es el ÍNDICE compacto
con resúmenes de una línea. El contenido se pide bajo demanda con `workspace.get_evidence_chunk`.

Las funciones aquí NO usan el SDK de MCP: corren en cualquier Python 3.9+.
"""
from __future__ import annotations

import os
from typing import List

from .. import workspace
from ..common.texto import slug
from .manifest import build_manifest
from .registry import adaptador


def construir_evidencia(folder: str, caso: str = "") -> dict:
    """Extrae todos los insumos, persiste la evidencia por ID y devuelve el índice compacto.

    Args:
        folder: ruta a inputs/<caso_de_uso>/
        caso: nombre del caso en el workspace (default: nombre de la carpeta).
    Returns:
        Índice compacto (~500 tokens): items con id/tipo/resumen, fuentes_detectadas agregadas
        (pequeñas y de alto valor), métricas de eficiencia y advertencias.
    """
    manifiesto = build_manifest(folder)
    caso = caso or manifiesto["caso_de_uso"]
    workspace.save_json(caso, "00_manifest.json", manifiesto)

    items_index: List[dict] = []
    fuentes_detectadas: List[dict] = []
    advertencias: List[str] = list(manifiesto["advertencias"])
    car_orig = car_limpio = 0
    n_vision = n_imagenes = 0

    for n, item in enumerate(manifiesto["items"], start=1):
        eid = f"E{n:03d}"
        try:
            registro, resumen, extra = adaptador(item["extractor"])(item["ruta"])
        except Exception as exc:  # noqa: BLE001 — un archivo malo no tumba el pipeline
            advertencias.append(f"Error procesando {item['nombre']}: {exc}")
            continue

        registro.update({
            "id": eid,
            "tipo": item["extractor"],
            "categoria": item["categoria"],
            "archivo_origen": item["ruta"],
            "modificado": item.get("modificado", ""),
        })
        archivo_evidencia = f"{eid}_{slug(item['nombre'])}.json"
        workspace.save_json(caso, os.path.join("10_evidence", archivo_evidencia), registro)

        items_index.append({
            "id": eid,
            "tipo": item["extractor"],
            "categoria": item["categoria"],
            "origen": item["nombre"],
            "archivo_evidencia": archivo_evidencia,
            "resumen": resumen,
            "chars_vista": len(registro.get("vista_texto", "")),
        })

        fuentes_detectadas.extend(extra.get("fuentes", []))
        car_orig += extra.get("car_orig", 0)
        car_limpio += extra.get("car_limpio", 0)
        n_imagenes += extra.get("es_imagen", 0)
        n_vision += extra.get("requiere_vision", 0)

    metricas = {
        "transcripciones_caracteres_original": car_orig,
        "transcripciones_caracteres_limpio": car_limpio,
        "transcripciones_reduccion_pct": round(100 * (1 - car_limpio / car_orig), 1) if car_orig else 0.0,
        "imagenes_que_requieren_vision_llm": n_vision,
        "imagenes_resueltas_por_ocr": n_imagenes - n_vision,
    }

    index = {
        "caso": caso,
        "total_items": len(items_index),
        "items": items_index,
        "fuentes_detectadas": fuentes_detectadas,   # pequeñas y de alto valor: van en el índice
        "metricas_eficiencia": metricas,
        "advertencias": advertencias,
        "nota": "Contenido bajo demanda con get_evidence(caso, id, chunk). No releer archivos crudos.",
    }
    workspace.save_json(caso, os.path.join("10_evidence", "index.json"), index)
    workspace.append_metric(caso, "extraccion", {
        "items": len(items_index), **metricas,
    })
    return index
