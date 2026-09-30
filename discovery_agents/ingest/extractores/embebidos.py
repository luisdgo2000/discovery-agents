"""Imágenes incrustadas dentro de documentos: el hueco de información más grande que había.

Un `.pptx` de arquitectura son ocho diapositivas cuyo contenido real es **una imagen por
diapositiva**. El extractor de PowerPoint las contaba (`imagenes_embebidas: 8`) y ahí terminaba
todo: nadie las abría, nadie las leía, y el diagrama de arquitectura —muchas veces el insumo más
denso del Discovery— no llegaba al documento final. Lo mismo con los pantallazos pegados en un
acta de Word.

Aquí se sacan y se enrutan por el mismo camino que cualquier imagen suelta: OCR local si se puede,
y bandera `requiere_vision_llm` solo para las que el OCR no resolvió. La regla de economía se
mantiene intacta —al modelo de visión van las imágenes que hacen falta, no todas— pero ahora
también alcanza a las que estaban escondidas.

`.pptx` y `.docx` son archivos ZIP con las imágenes en `ppt/media/` y `word/media/`, así que esto
no necesita ninguna librería: `zipfile` de la stdlib basta.
"""
from __future__ import annotations

import os
import tempfile
import zipfile
from typing import Dict, List

# Dónde guarda cada formato OOXML sus medios incrustados.
_CARPETAS_MEDIA = ("ppt/media/", "word/media/", "xl/media/")

# Extensiones de imagen que vale la pena pasar por OCR. Los `.emf`/`.wmf` son vectoriales de
# Windows y ninguna librería del entorno los rasteriza, así que se omiten a propósito.
_IMAGENES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff"}

# Los iconos de plantilla y las viñetas producen ruido de OCR sin aportar nada.
_MINIMO_BYTES = 12_000


def listar_incrustadas(path: str) -> List[str]:
    """Nombres de las imágenes incrustadas relevantes dentro de un documento OOXML."""
    if not zipfile.is_zipfile(path):
        return []
    try:
        with zipfile.ZipFile(path) as z:
            return [
                info.filename for info in z.infolist()
                if info.filename.startswith(_CARPETAS_MEDIA)
                and os.path.splitext(info.filename)[1].lower() in _IMAGENES
                and info.file_size >= _MINIMO_BYTES
            ]
    except (zipfile.BadZipFile, OSError):
        return []


def ocr_de_incrustadas(path: str) -> Dict[str, object]:
    """Extrae y aplica OCR a las imágenes incrustadas de un documento.

    Returns:
        {texto, n_imagenes, n_con_texto, requieren_vision: [nombres]}
        `requieren_vision` nombra las imágenes que el OCR no resolvió, para que el orquestador
        decida si mandarlas al modelo de visión: son las únicas que costarían tokens.
    """
    from .imagenes import ocr_de_archivo

    nombres = listar_incrustadas(path)
    if not nombres:
        return {"texto": "", "n_imagenes": 0, "n_con_texto": 0, "requieren_vision": []}

    trozos: List[str] = []
    requieren_vision: List[str] = []
    con_texto = 0
    temporal = tempfile.mkdtemp(prefix="discovery_media_")
    try:
        with zipfile.ZipFile(path) as z:
            for nombre in nombres:
                destino = os.path.join(temporal, os.path.basename(nombre))
                try:
                    with z.open(nombre) as origen, open(destino, "wb") as salida:
                        salida.write(origen.read())
                except (KeyError, OSError):
                    continue
                texto = ocr_de_archivo(destino)
                etiqueta = os.path.basename(nombre)
                if texto and len(texto.strip()) >= 20:
                    con_texto += 1
                    trozos.append(f"[Imagen incrustada: {etiqueta}]\n{texto.strip()}")
                else:
                    requieren_vision.append(etiqueta)
    finally:
        import shutil
        shutil.rmtree(temporal, ignore_errors=True)

    return {
        "texto": "\n\n".join(trozos),
        "n_imagenes": len(nombres),
        "n_con_texto": con_texto,
        "requieren_vision": requieren_vision,
    }
