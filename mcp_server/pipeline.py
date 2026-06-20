"""Pipeline determinista de extracción (0 tokens de LLM) — versión persistente (v2).

Corrige el hallazgo H3 de la revisión: la evidencia YA NO viaja por el contexto del modelo.
Cada insumo se extrae a un registro con ID (`E001`, `E002`, ...) persistido en
`work/<caso>/10_evidence/`, y lo único que se devuelve (y que el LLM ve) es el ÍNDICE compacto
con resúmenes de una línea. El contenido se pide bajo demanda con `workspace.get_evidence_chunk`.

Las funciones aquí NO usan el SDK de MCP: corren en cualquier Python 3.9+.
"""
from __future__ import annotations

import os
import re
from typing import Dict, List, Tuple

from . import workspace
from .extractors.documents import extract_document
from .extractors.excel import extract_excel
from .extractors.images import extract_image
from .extractors.manifest import build_manifest
from .extractors.powerpoint import extract_pptx
from .transcripts.cleaner import clean_transcript


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
            registro, resumen, extra = _extraer(item)
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
        slug = _slug(item["nombre"])
        archivo_evidencia = f"{eid}_{slug}.json"
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


def _extraer(item: dict) -> Tuple[dict, str, dict]:
    """Devuelve (registro_a_persistir, resumen_1_linea, extras_para_metricas)."""
    ruta, extractor = item["ruta"], item["extractor"]

    if extractor == "excel":
        data = extract_excel(ruta)
        fuentes = data["fuentes_detectadas"]
        registro = {
            "hojas": [{"nombre": h["nombre"], "n_celdas": len(h["celdas"])} for h in data["hojas"]],
            "celdas_por_hoja": {h["nombre"]: h["celdas"] for h in data["hojas"]},
            "fuentes_detectadas": fuentes,
            "vista_texto": _vista_excel(data),
        }
        resumen = f"Excel: {len(fuentes)} fuentes detectadas en {len(data['hojas'])} hoja(s)"
        return registro, resumen, {"fuentes": fuentes}

    if extractor == "transcripcion":
        doc = extract_document(ruta)
        limpio = clean_transcript(doc["texto"])
        registro = {
            "formato_detectado": limpio["formato_detectado"],
            "hablantes": limpio["hablantes"],
            "segmentos": limpio["segmentos"],           # incluye id + original (no destructivo)
            "reduccion_pct": limpio["reduccion_pct"],
            "vista_texto": limpio["texto_limpio"],
        }
        resumen = (f"Transcripción ({limpio['formato_detectado']}): {limpio['n_segmentos']} segmentos, "
                   f"hablantes: {', '.join(limpio['hablantes'][:4])}, reducción {limpio['reduccion_pct']}%")
        return registro, resumen, {
            "car_orig": limpio["caracteres_original"], "car_limpio": limpio["caracteres_limpio"],
        }

    if extractor == "powerpoint":
        data = extract_pptx(ruta)
        registro = {
            "n_diapositivas": data["n_diapositivas"],
            "diapositivas": data["diapositivas"],
            "imagenes_embebidas": data["imagenes_embebidas"],
            "vista_texto": data["texto"],
        }
        resumen = (f"PowerPoint: {data['n_diapositivas']} diapositivas, "
                   f"{data['imagenes_embebidas']} imágenes embebidas")
        return registro, resumen, {}

    if extractor == "documento":
        doc = extract_document(ruta)
        registro = {"n_parrafos": doc["n_parrafos"], "vista_texto": doc["texto"]}
        resumen = f"Documento: {doc['n_parrafos']} párrafos, {doc['n_caracteres']} chars"
        return registro, resumen, {}

    if extractor == "imagen":
        data = extract_image(ruta)
        registro = {
            "ocr_disponible": data["ocr_disponible"],
            "requiere_vision_llm": data["requiere_vision_llm"],
            "vista_texto": data["texto_ocr"],
        }
        resumen = ("Imagen: OCR suficiente" if not data["requiere_vision_llm"]
                   else "Imagen: REQUIERE visión LLM (OCR insuficiente)")
        return registro, resumen, {"es_imagen": 1, "requiere_vision": int(data["requiere_vision_llm"])}

    raise ValueError(f"Extractor desconocido: {extractor}")


def _vista_excel(data: dict) -> str:
    """Vista de texto compacta del Excel para chunking bajo demanda."""
    lineas: List[str] = []
    for hoja in data["hojas"]:
        lineas.append(f"== Hoja: {hoja['nombre']} ==")
        lineas.extend(f"{c['coord']}={c['valor']}" for c in hoja["celdas"])
    return "\n".join(lineas)


def _slug(nombre: str) -> str:
    base = os.path.splitext(nombre)[0].lower()
    return re.sub(r"[^a-z0-9]+", "_", base).strip("_")[:40]
