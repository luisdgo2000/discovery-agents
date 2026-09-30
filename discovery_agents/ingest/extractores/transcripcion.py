"""Adaptador de transcripciones: extraer el texto y limpiarlo sin destruirlo.

Une los dos pasos que una transcripción necesita —sacarla de su envoltorio (.vtt, .docx, .txt) y
limpiarla— porque para el resto del sistema son uno solo: un insumo de tipo `transcripcion` es
siempre texto ya segmentado y atribuido a su hablante.

La limpieza vive en `transcripciones/cleaner.py` y es deliberadamente conservadora: cada segmento
conserva su texto original junto al limpio, de modo que ninguna decisión de limpieza sea
irreversible. Ver la nota de diseño de ese módulo.
"""
from __future__ import annotations

from typing import Tuple

from ..transcripciones.cleaner import clean_transcript
from .documentos import extract_document


def extraer(ruta: str) -> Tuple[dict, str, dict]:
    """Adaptador del registro."""
    doc = extract_document(ruta)
    limpio = clean_transcript(doc["texto"])
    registro = {
        "formato_detectado": limpio["formato_detectado"],
        "hablantes": limpio["hablantes"],
        "segmentos": limpio["segmentos"],       # incluye id + original: la limpieza es reversible
        "reduccion_pct": limpio["reduccion_pct"],
        "vista_texto": limpio["texto_limpio"],
    }
    resumen = (f"Transcripción ({limpio['formato_detectado']}): {limpio['n_segmentos']} segmentos, "
               f"hablantes: {', '.join(limpio['hablantes'][:4])}, "
               f"reducción {limpio['reduccion_pct']}%")
    return registro, resumen, {
        "car_orig": limpio["caracteres_original"],
        "car_limpio": limpio["caracteres_limpio"],
    }
