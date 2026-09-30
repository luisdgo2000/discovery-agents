"""Extractor de imágenes: diagramas, capturas, fotos de pizarra y SVG exportados.

Estrategia de eficiencia de tokens, en dos escalones:
  1. OCR local con pytesseract (0 tokens). Resuelve la mayoría de capturas y diagramas.
  2. Solo si el OCR no dio texto útil, la imagen se marca `requiere_vision_llm` para que el
     orquestador la mande al modelo de visión — que es caro, y por eso no lo recibe todo.

El SVG es un caso aparte y afortunado: es XML, así que su texto se lee directamente sin OCR ni
dependencias. Un diagrama de Visio o draw.io exportado a SVG entrega sus etiquetas íntegras y
exactas, sin el margen de error que siempre tiene reconocer caracteres en un mapa de bits.
"""
from __future__ import annotations

import os
from typing import Optional, Tuple

# Por debajo de este umbral el OCR no encontró texto aprovechable y hace falta el modelo de visión.
_MINIMO_TEXTO_UTIL = 20


def extract_image(path: str) -> dict:
    nombre = os.path.basename(path)
    ext = os.path.splitext(path)[1].lower()

    if ext == ".svg":
        texto = _texto_svg(path)
        return {
            "archivo": path, "nombre": nombre, "texto_ocr": texto,
            "ocr_disponible": True, "requiere_vision_llm": False,
            "nota": "SVG: texto leído del XML, sin OCR ni pérdida de exactitud.",
        }

    texto_ocr = ocr_de_archivo(path)
    requiere_vision = texto_ocr is None or len(texto_ocr.strip()) < _MINIMO_TEXTO_UTIL
    return {
        "archivo": path,
        "nombre": nombre,
        "texto_ocr": texto_ocr or "",
        "ocr_disponible": texto_ocr is not None,
        # Bandera para el orquestador: solo estas imágenes pasan al modelo de visión.
        "requiere_vision_llm": requiere_vision,
        "nota": (
            "OCR insuficiente: enviar al subagente de visión."
            if requiere_vision else
            "OCR suficiente: no requiere modelo de visión (ahorra tokens)."
        ),
    }


def ocr_de_archivo(path: str) -> Optional[str]:
    """Texto reconocido en una imagen, o None si el OCR no está disponible o falló.

    Es pública porque el extractor de imágenes incrustadas (`embebidos.py`) la reutiliza: el OCR
    debe comportarse igual venga la imagen de un archivo suelto o de dentro de un .pptx.
    """
    try:
        import pytesseract  # dependencia opcional
        from PIL import Image
    except ImportError:
        return None

    try:
        _habilitar_heic()
        with Image.open(path) as img:
            return pytesseract.image_to_string(img, lang="spa+eng")
    except Exception:  # noqa: BLE001 — falta el binario de tesseract, formato corrupto, etc.
        return None


def _habilitar_heic() -> None:
    """Registra el decodificador HEIC en Pillow si `pillow-heif` está instalado."""
    try:
        import pillow_heif  # dependencia opcional (fotos de iPhone)
    except ImportError:
        return
    try:
        pillow_heif.register_heif_opener()
    except Exception:  # noqa: BLE001 — ya registrado o versión incompatible
        pass


def _texto_svg(path: str) -> str:
    """Etiquetas de texto de un SVG, leídas de su XML."""
    from .estructurados import _textos_xml

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return "\n".join(_textos_xml(fh.read()))


def extraer(ruta: str) -> Tuple[dict, str, dict]:
    """Adaptador del registro."""
    data = extract_image(ruta)
    registro = {
        "ocr_disponible": data["ocr_disponible"],
        "requiere_vision_llm": data["requiere_vision_llm"],
        "nota": data["nota"],
        "vista_texto": data["texto_ocr"],
    }
    resumen = ("Imagen: REQUIERE visión LLM (OCR insuficiente)" if data["requiere_vision_llm"]
               else "Imagen: texto extraído sin costo de tokens")
    return registro, resumen, {
        "es_imagen": 1, "requiere_vision": int(data["requiere_vision_llm"]),
    }
