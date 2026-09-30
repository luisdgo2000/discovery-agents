"""Extractores deterministas: leen insumos y devuelven JSON estructurado sin gastar tokens de LLM.

Cada módulo expone `extraer(ruta) -> (registro, resumen, extras)` — el contrato que documenta
`ingest/registry.py`— además de su función de extracción cruda, útil por separado y en pruebas.

Todas las dependencias de terceros son **opcionales**: se importan dentro de la función que las
usa, no en la cabecera del módulo. Un entorno sin `python-pptx` debe poder procesar Excel, y un
archivo que no se puede leer debe producir un aviso en el índice, no tumbar la extracción entera.
"""
from __future__ import annotations

from typing import Dict

# Dependencia opcional → para qué sirve cuando está.
_OPCIONALES = {
    "openpyxl": "leer .xlsx/.xlsm",
    "docx": "leer .docx (python-docx)",
    "pptx": "leer .pptx (python-pptx)",
    "pypdf": "leer .pdf",
    "pytesseract": "OCR de imágenes (requiere además el binario tesseract)",
    "PIL": "abrir imágenes para OCR (Pillow)",
    "pillow_heif": "abrir fotos .heic/.heif",
    "yaml": "leer .yaml/.yml (PyYAML)",
    "extract_msg": "leer correos .msg de Outlook",
}


def disponibilidad() -> Dict[str, dict]:
    """Qué dependencias opcionales están instaladas ahora mismo, y para qué sirve cada una.

    Se consulta en tiempo de ejecución para que el informe refleje el entorno real y no una lista
    escrita a mano que envejece.
    """
    from importlib import import_module

    informe: Dict[str, dict] = {}
    for modulo, proposito in _OPCIONALES.items():
        try:
            import_module(modulo)
            instalado = True
        except ImportError:
            instalado = False
        informe[modulo] = {"instalado": instalado, "habilita": proposito}

    from ..registry import soffice_ruta
    informe["libreoffice"] = {
        "instalado": bool(soffice_ruta()),
        "habilita": "convertir .xls/.doc/.ppt legacy al vuelo",
    }
    return informe
