"""Extractor de binarios Office 97-2003 (.xls/.doc/.ppt) por conversión con LibreOffice.

`openpyxl`, `python-docx` y `python-pptx` solo entienden los formatos OOXML modernos. Un `.xls` de
2011 con la volumetría histórica de las tablas es un insumo perfectamente válido de un Discovery, y
hasta ahora se rechazaba con un aviso pidiéndole al usuario que lo reguardara a mano.

Si LibreOffice está instalado, aquí se convierte al vuelo a un directorio temporal y se procesa con
el extractor moderno que corresponda. Si no está, se conserva el aviso de antes: **degradar con
gracia es preferible a fallar**, y el aviso viaja en el índice para que el orquestador lo declare
en la estrategia en vez de que el dato desaparezca en silencio.

La conversión es a un temporal, nunca junto al original: los insumos del usuario no se tocan.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Tuple

from ..registry import EQUIVALENTE_MODERNO, soffice_ruta

# A qué formato moderno convierte cada legacy, y qué extractor lo procesa después.
_DESTINO = {
    ".xls": ("xlsx", "excel"),
    ".doc": ("docx", "documento"),
    ".ppt": ("pptx", "powerpoint"),
}

# LibreOffice arranca una JVM en frío; 120 s cubre un arranque lento sin colgar el pipeline.
_TIMEOUT_S = 120


class ConversionNoDisponible(RuntimeError):
    """LibreOffice no está instalado: el insumo no puede leerse en este entorno."""


def convertir(ruta: str) -> str:
    """Convierte un binario legacy a su equivalente moderno y devuelve la ruta temporal.

    Raises:
        ConversionNoDisponible: si no hay LibreOffice.
        RuntimeError: si la conversión falla o no produce archivo.
    """
    ext = os.path.splitext(ruta)[1].lower()
    if ext not in _DESTINO:
        raise ValueError(f"No es un formato legacy conocido: {ext}")

    soffice = soffice_ruta()
    if not soffice:
        raise ConversionNoDisponible(
            f"{EQUIVALENTE_MODERNO.get(ext, ext)}. Instala LibreOffice para convertirlo "
            f"automáticamente, o vuelve a guardar el archivo en formato moderno."
        )

    destino_ext, _ = _DESTINO[ext]
    temporal = tempfile.mkdtemp(prefix="discovery_legacy_")
    try:
        resultado = subprocess.run(
            [soffice, "--headless", "--norestore", "--convert-to", destino_ext,
             "--outdir", temporal, os.path.abspath(ruta)],
            capture_output=True, timeout=_TIMEOUT_S, check=False,
        )
        esperado = os.path.join(
            temporal, os.path.splitext(os.path.basename(ruta))[0] + "." + destino_ext)
        if not os.path.exists(esperado):
            detalle = (resultado.stderr or resultado.stdout or b"").decode("utf-8", "replace")
            raise RuntimeError(f"LibreOffice no produjo la conversión de {os.path.basename(ruta)}. "
                               f"{detalle.strip()[:200]}")
        return esperado
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(temporal, ignore_errors=True)
        raise RuntimeError(
            f"La conversión de {os.path.basename(ruta)} superó {_TIMEOUT_S}s.") from exc
    except Exception:
        shutil.rmtree(temporal, ignore_errors=True)
        raise


def extraer(ruta: str) -> Tuple[dict, str, dict]:
    """Adaptador del registro: convierte y delega en el extractor moderno."""
    from ..registry import adaptador

    ext = os.path.splitext(ruta)[1].lower()
    _, extractor_destino = _DESTINO[ext]
    convertido = convertir(ruta)
    temporal = os.path.dirname(convertido)
    try:
        registro, resumen, extras = adaptador(extractor_destino)(convertido)
    finally:
        shutil.rmtree(temporal, ignore_errors=True)

    # Se deja constancia de que este registro nació de una conversión: si algo se ve raro más
    # adelante, la explicación está aquí y no hay que adivinarla.
    registro["convertido_desde"] = ext
    registro["tipo_efectivo"] = extractor_destino
    return registro, f"{resumen} (convertido desde {ext} con LibreOffice)", extras
