"""Router/Ingestor determinista.

Escanea la carpeta de insumos del caso de uso, clasifica cada archivo por (subcarpeta + extensión)
y produce un manifiesto JSON. NO lee el contenido de los archivos: solo metadatos baratos, para
que el orquestador pueda proponer su estrategia sin gastar un solo token.

La tabla de extensiones vive en `registry.py`, no aquí: clasificar y procesar deben mirar la misma
lista o acabarán discrepando (clasificando algo que nadie sabe procesar, o al revés).
"""
from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List

from .registry import EQUIVALENTE_MODERNO, es_ignorable, extractor_de, soffice_ruta


def _iso(epoch: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(epoch))

# Subcarpetas convenidas → categoría semántica del insumo.
CATEGORIA_POR_CARPETA: Dict[str, str] = {
    "caso_de_uso": "caso_de_uso",
    "discovery_inicial": "discovery_inicial",
    "discovery_tecnico": "discovery_tecnico",
    "transcripciones": "transcripcion",
    "hallazgos": "hallazgo",
    "fuentes": "fuente",
    "imagenes": "imagen",
}



@dataclass
class ItemInsumo:
    ruta: str
    nombre: str
    categoria: str          # de qué subcarpeta proviene
    extractor: str          # qué extractor aplicarle
    extension: str
    tamano_bytes: int
    modificado: str = ""    # mtime ISO — metadato para trazabilidad e incrementalidad


@dataclass
class Manifiesto:
    raiz: str
    caso_de_uso: str
    total_items: int
    por_categoria: Dict[str, int] = field(default_factory=dict)
    por_extractor: Dict[str, int] = field(default_factory=dict)
    items: List[ItemInsumo] = field(default_factory=list)
    advertencias: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


def build_manifest(folder: str) -> dict:
    """Construye el manifiesto de la carpeta de insumos. Determinista, 0 tokens.

    Args:
        folder: ruta a inputs/<caso_de_uso>/
    Returns:
        dict serializable con el inventario clasificado de insumos.
    """
    raiz = os.path.abspath(folder)
    caso = os.path.basename(raiz.rstrip(os.sep))
    items: List[ItemInsumo] = []
    advertencias: List[str] = []

    if not os.path.isdir(raiz):
        return Manifiesto(
            raiz=raiz, caso_de_uso=caso, total_items=0,
            advertencias=[f"La carpeta no existe: {raiz}"],
        ).to_dict()

    # LibreOffice se consulta una sola vez por manifiesto: decide si los binarios legacy son
    # insumos procesables o solo un aviso.
    hay_soffice = bool(soffice_ruta())

    for dirpath, _dirnames, filenames in os.walk(raiz):
        # categoría = primera subcarpeta bajo la raíz
        rel = os.path.relpath(dirpath, raiz)
        top = rel.split(os.sep)[0] if rel != "." else ""
        categoria = CATEGORIA_POR_CARPETA.get(top, "sin_clasificar")
        for nombre in filenames:
            if es_ignorable(nombre):
                continue
            ruta = os.path.join(dirpath, nombre)
            ext = os.path.splitext(nombre)[1].lower()
            extractor = extractor_de(ext)
            if not extractor:
                advertencias.append(f"Extensión no soportada, se ignora: {nombre}")
                continue
            if extractor == "legacy" and not hay_soffice:
                # Sin LibreOffice el binario no se puede abrir. Se avisa en vez de fingir que se
                # procesó: un insumo perdido en silencio es peor que un insumo declarado ausente.
                advertencias.append(
                    f"Formato binario legacy no legible, se omite: {nombre} "
                    f"({EQUIVALENTE_MODERNO.get(ext, ext)}). Instala LibreOffice para convertirlo "
                    f"automáticamente.")
                continue
            # Un .docx o .txt dentro de transcripciones/ es una transcripción, no un documento:
            # la carpeta declara la intención mejor que la extensión.
            if categoria == "transcripcion" and extractor == "documento":
                extractor = "transcripcion"
            try:
                st = os.stat(ruta)
                tam, mod = st.st_size, _iso(st.st_mtime)
            except OSError:
                tam, mod = 0, ""
            items.append(ItemInsumo(
                ruta=ruta, nombre=nombre, categoria=categoria,
                extractor=extractor, extension=ext, tamano_bytes=tam, modificado=mod,
            ))

    por_categoria: Dict[str, int] = {}
    por_extractor: Dict[str, int] = {}
    for it in items:
        por_categoria[it.categoria] = por_categoria.get(it.categoria, 0) + 1
        por_extractor[it.extractor] = por_extractor.get(it.extractor, 0) + 1

    if not items:
        advertencias.append("No se encontraron insumos procesables en la carpeta.")

    return Manifiesto(
        raiz=raiz, caso_de_uso=caso, total_items=len(items),
        por_categoria=por_categoria, por_extractor=por_extractor,
        items=items, advertencias=advertencias,
    ).to_dict()
