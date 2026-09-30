"""Registro de formatos: el único lugar donde una extensión se asocia a su extractor.

Existe una sola tabla y la leen tanto la clasificación (`manifest.py`) como el despacho
(`pipeline.py`). Si cada uno tuviera la suya, añadir un formato exigiría tocar ambas y bastaría un
descuido para que una clasificara algo que la otra no sabe procesar.

**Cómo añadir un formato nuevo** (el contrato de extensibilidad del sistema):

1. Escribe el extractor en `extractores/` con una función `extraer(ruta) -> (registro, resumen, extras)`.
2. Añade una línea a `FORMATOS`.
3. Escribe la prueba, incluida la degradación cuando falte su dependencia.

No hay paso 4: ni `manifest.py` ni `pipeline.py` necesitan enterarse.

**Contrato del adaptador** — toda función `extraer` devuelve la misma tripleta:
    registro  dict que se persiste en `10_evidence/E00x_*.json`. DEBE traer `vista_texto`:
              es lo único que se le sirve al modelo, por trozos y bajo demanda.
    resumen   una línea para el índice. Es lo que el orquestador ve del insumo.
    extras    señales para las métricas agregadas (`fuentes`, `car_orig`, `es_imagen`, …).

Las dependencias opcionales se resuelven dentro de cada extractor, nunca aquí: importar este
módulo nunca debe fallar por una librería ausente.
"""
from __future__ import annotations

import os
import shutil
from typing import Callable, Dict, List, NamedTuple, Optional, Tuple

# Firma del adaptador: ruta del archivo → (registro, resumen, extras)
Adaptador = Callable[[str], Tuple[dict, str, dict]]


class Formato(NamedTuple):
    """Una extensión soportada y cómo se procesa."""
    extension: str
    extractor: str        # categoría semántica; también el `tipo` de la evidencia resultante
    descripcion: str
    requiere: str = ""    # dependencia opcional; "" si es stdlib pura


# ---------------------------------------------------------------------------------------------
# Tabla de formatos. El orden importa solo para la legibilidad del informe `formatos`.
# ---------------------------------------------------------------------------------------------
FORMATOS: List[Formato] = [
    # — hojas de cálculo: la fuente estructurada por excelencia del Discovery —
    Formato(".xlsx", "excel", "Libro de Excel", "openpyxl"),
    Formato(".xlsm", "excel", "Libro de Excel con macros", "openpyxl"),

    # — presentaciones —
    Formato(".pptx", "powerpoint", "Presentación de PowerPoint", "python-pptx"),
    Formato(".pptm", "powerpoint", "Presentación de PowerPoint con macros", "python-pptx"),

    # — documentos de texto —
    Formato(".docx", "documento", "Documento de Word", "python-docx"),
    Formato(".docm", "documento", "Documento de Word con macros", "python-docx"),
    Formato(".pdf", "documento", "PDF", "pypdf"),
    Formato(".txt", "documento", "Texto plano"),
    Formato(".md", "documento", "Markdown"),
    Formato(".markdown", "documento", "Markdown"),
    Formato(".csv", "documento", "CSV"),
    Formato(".tsv", "documento", "Valores separados por tabulador"),
    Formato(".rtf", "documento", "Texto enriquecido"),
    Formato(".html", "documento", "Página web / export de Confluence o SharePoint"),
    Formato(".htm", "documento", "Página web"),

    # — transcripciones de reunión —
    Formato(".vtt", "transcripcion", "Subtítulos WebVTT (Teams)"),
    Formato(".srt", "transcripcion", "Subtítulos SubRip"),

    # — imágenes y diagramas —
    Formato(".png", "imagen", "Imagen PNG", "pytesseract"),
    Formato(".jpg", "imagen", "Imagen JPEG", "pytesseract"),
    Formato(".jpeg", "imagen", "Imagen JPEG", "pytesseract"),
    Formato(".gif", "imagen", "Imagen GIF", "pytesseract"),
    Formato(".bmp", "imagen", "Imagen BMP", "pytesseract"),
    Formato(".webp", "imagen", "Imagen WebP", "pytesseract"),
    Formato(".tif", "imagen", "Imagen TIFF", "pytesseract"),
    Formato(".tiff", "imagen", "Imagen TIFF", "pytesseract"),
    Formato(".heic", "imagen", "Foto HEIC (iPhone)", "pillow-heif"),
    Formato(".heif", "imagen", "Foto HEIF", "pillow-heif"),
    Formato(".svg", "imagen", "Diagrama SVG (Visio/draw.io exportado)"),

    # — archivos técnicos: se resumen por su ESTRUCTURA, no se vuelcan crudos —
    Formato(".json", "estructurado", "JSON"),
    Formato(".yaml", "estructurado", "YAML"),
    Formato(".yml", "estructurado", "YAML"),
    Formato(".xml", "estructurado", "XML"),
    Formato(".drawio", "estructurado", "Diagrama de draw.io"),
    Formato(".sql", "estructurado", "Script SQL — aporta tablas y esquemas al inventario"),
    Formato(".ddl", "estructurado", "DDL — aporta tablas y esquemas al inventario"),
    Formato(".toml", "estructurado", "Configuración TOML"),
    Formato(".ini", "estructurado", "Configuración INI"),
    Formato(".cfg", "estructurado", "Configuración"),
    Formato(".log", "estructurado", "Bitácora / log"),
    Formato(".ipynb", "estructurado", "Notebook Jupyter"),

    # — correo: donde suelen quedar los acuerdos del Discovery —
    Formato(".eml", "correo", "Correo electrónico (RFC 822)"),
    Formato(".msg", "correo", "Correo de Outlook", "extract-msg"),

    # — binarios legacy: se convierten al vuelo si hay LibreOffice —
    Formato(".xls", "legacy", "Excel 97-2003", "LibreOffice (soffice)"),
    Formato(".doc", "legacy", "Word 97-2003", "LibreOffice (soffice)"),
    Formato(".ppt", "legacy", "PowerPoint 97-2003", "LibreOffice (soffice)"),
]

# Cómo se llamaba el formato moderno equivalente, para el aviso cuando no hay LibreOffice.
EQUIVALENTE_MODERNO: Dict[str, str] = {
    ".xls": "Excel 97-2003 → guardar como .xlsx",
    ".doc": "Word 97-2003 → guardar como .docx",
    ".ppt": "PowerPoint 97-2003 → guardar como .pptx",
}

EXTENSION_A_EXTRACTOR: Dict[str, str] = {f.extension: f.extractor for f in FORMATOS}

# Archivos que nunca son insumos: metadatos del sistema operativo y bloqueos de Office.
IGNORAR = {".ds_store", "thumbs.db", "desktop.ini", ".gitkeep"}
PREFIJOS_IGNORADOS = ("~$",)


def extractor_de(extension: str) -> str:
    """Categoría de extractor para una extensión ('.docx' → 'documento'); '' si no se soporta."""
    return EXTENSION_A_EXTRACTOR.get(str(extension or "").lower(), "")


def es_ignorable(nombre: str) -> bool:
    """True si el archivo es ruido del sistema y no un insumo del Discovery."""
    bajo = str(nombre or "").lower()
    return bajo in IGNORAR or bajo.startswith(PREFIJOS_IGNORADOS)


def soffice_ruta() -> Optional[str]:
    """Ruta al binario de LibreOffice si está disponible; None si no.

    Se consulta en tiempo de ejecución, no de importación: instalar LibreOffice no debería
    obligar a reiniciar nada, y su ausencia no debe romper el arranque.
    """
    for candidato in ("soffice", "libreoffice"):
        ruta = shutil.which(candidato)
        if ruta:
            return ruta
    # Instalación estándar de macOS, que no queda en el PATH.
    mac = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    return mac if os.path.exists(mac) else None


def adaptador(extractor: str) -> Adaptador:
    """Resuelve el adaptador de una categoría de extractor.

    La importación es perezosa a propósito: cada extractor arrastra sus dependencias opcionales, y
    un entorno sin `python-pptx` debe poder procesar Excel sin tropezar al importar el registro.
    """
    if extractor == "excel":
        from .extractores.excel import extraer
    elif extractor == "powerpoint":
        from .extractores.presentaciones import extraer
    elif extractor == "documento":
        from .extractores.documentos import extraer
    elif extractor == "transcripcion":
        from .extractores.transcripcion import extraer
    elif extractor == "imagen":
        from .extractores.imagenes import extraer
    elif extractor == "estructurado":
        from .extractores.estructurados import extraer
    elif extractor == "correo":
        from .extractores.correo import extraer
    elif extractor == "legacy":
        from .extractores.legacy import extraer
    else:
        raise ValueError(
            f"Extractor desconocido: {extractor!r}. "
            f"Categorías registradas: {sorted({f.extractor for f in FORMATOS})}"
        )
    return extraer


def formatos_soportados() -> dict:
    """Informe legible de qué se puede ingerir hoy y con qué dependencias. 0 tokens."""
    from .extractores import disponibilidad

    por_extractor: Dict[str, dict] = {}
    for f in FORMATOS:
        entrada = por_extractor.setdefault(f.extractor, {"extensiones": [], "requiere": []})
        entrada["extensiones"].append(f.extension)
        if f.requiere and f.requiere not in entrada["requiere"]:
            entrada["requiere"].append(f.requiere)
    return {
        "total_extensiones": len(FORMATOS),
        "por_extractor": por_extractor,
        "dependencias_opcionales": disponibilidad(),
        "nota": ("Las dependencias ausentes degradan con gracia: el insumo se registra con un aviso "
                 "en vez de romper la extracción."),
    }
