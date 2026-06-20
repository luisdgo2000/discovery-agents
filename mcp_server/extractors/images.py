"""Extractor de imágenes (diagramas, capturas, fotos de pizarra).

Estrategia de eficiencia de tokens:
  1. Intenta OCR local con pytesseract (0 tokens de LLM) si está disponible.
  2. Si no hay OCR o el texto es pobre, marca la imagen para que el subagente de VISIÓN de Copilot
     la lea — pero SOLO esas imágenes, no todas, para no malgastar tokens.
"""
from __future__ import annotations

import os
from typing import Optional


def extract_image(path: str) -> dict:
    nombre = os.path.basename(path)
    texto_ocr = _ocr(path)
    requiere_vision = texto_ocr is None or len(texto_ocr.strip()) < 20
    return {
        "archivo": path,
        "nombre": nombre,
        "texto_ocr": texto_ocr or "",
        "ocr_disponible": texto_ocr is not None,
        # Bandera para el orquestador: solo estas imágenes pasan al modelo de visión (caras en tokens).
        "requiere_vision_llm": requiere_vision,
        "nota": (
            "OCR insuficiente: enviar al subagente de visión de Copilot."
            if requiere_vision else
            "OCR suficiente: no requiere modelo de visión (ahorra tokens)."
        ),
    }


def _ocr(path: str) -> Optional[str]:
    try:
        import pytesseract  # dependencia opcional
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(path) as img:
            return pytesseract.image_to_string(img, lang="spa+eng")
    except Exception:
        return None
