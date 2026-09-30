"""Extractor de correo (0 tokens): .eml con la stdlib, .msg de Outlook si hay librería.

En un Discovery real, buena parte de los acuerdos no está en la transcripción de la reunión sino
en el correo posterior que los confirma: quién aprueba el acceso, qué servidor quedó, cuál es la
fecha de corte. Ese hilo es evidencia citable como cualquier otra.

Del correo interesa su **cabecera** tanto como su cuerpo: `De`, `Para` y `Fecha` son precisamente
los datos de gobierno que la rúbrica pregunta (quién es el dueño, quién certifica), y llegan aquí
ya estructurados, sin que nadie tenga que inferirlos.
"""
from __future__ import annotations

import os
import re
from email import policy
from email.parser import BytesParser
from typing import List, Tuple

_CITA_PREVIA = re.compile(r"^\s*>+")                 # línea del hilo citado
_SEPARADOR_HILO = re.compile(
    r"^\s*(-{3,}\s*(mensaje original|original message|forwarded message)|"
    r"de:\s|from:\s|el .{5,60} escribió:|on .{5,60} wrote:)",
    re.I | re.M,
)


def extract_email(path: str) -> dict:
    """Extrae cabeceras y cuerpo en texto plano de un correo."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".msg":
        return _msg(path)
    return _eml(path)


def _eml(path: str) -> dict:
    with open(path, "rb") as fh:
        mensaje = BytesParser(policy=policy.default).parse(fh)

    cuerpo = ""
    if mensaje.is_multipart():
        parte = mensaje.get_body(preferencelist=("plain", "html"))
        if parte is not None:
            cuerpo = parte.get_content()
            if parte.get_content_subtype() == "html":
                cuerpo = _texto_de_html(cuerpo)
    else:
        cuerpo = mensaje.get_content()

    adjuntos = [p.get_filename() for p in mensaje.iter_attachments() if p.get_filename()]
    return _componer(
        path,
        de=str(mensaje.get("From", "")),
        para=str(mensaje.get("To", "")),
        cc=str(mensaje.get("Cc", "")),
        fecha=str(mensaje.get("Date", "")),
        asunto=str(mensaje.get("Subject", "")),
        cuerpo=cuerpo,
        adjuntos=adjuntos,
    )


def _msg(path: str) -> dict:
    try:
        import extract_msg  # dependencia opcional
    except ImportError:
        nombre = os.path.basename(path)
        return _componer(
            path, de="", para="", cc="", fecha="", asunto=nombre,
            cuerpo=f"[.msg no extraído: instala 'extract-msg' para leer {nombre}]",
            adjuntos=[],
        )
    with extract_msg.Message(path) as m:
        return _componer(
            path,
            de=str(m.sender or ""), para=str(m.to or ""), cc=str(m.cc or ""),
            fecha=str(m.date or ""), asunto=str(m.subject or ""),
            cuerpo=str(m.body or ""),
            adjuntos=[a.longFilename or a.shortFilename or "" for a in (m.attachments or [])],
        )


def _componer(path: str, de: str, para: str, cc: str, fecha: str, asunto: str,
              cuerpo: str, adjuntos: List[str]) -> dict:
    limpio = _cuerpo_util(cuerpo)
    cabecera = [f"Asunto: {asunto}", f"De: {de}", f"Para: {para}"]
    if cc.strip():
        cabecera.append(f"CC: {cc}")
    cabecera.append(f"Fecha: {fecha}")
    if adjuntos:
        cabecera.append("Adjuntos: " + ", ".join(a for a in adjuntos if a))
    return {
        "archivo": path,
        "de": de, "para": para, "cc": cc, "fecha": fecha, "asunto": asunto,
        "adjuntos": [a for a in adjuntos if a],
        "cuerpo": limpio,
        "texto": "\n".join(cabecera) + "\n\n" + limpio,
    }


def _cuerpo_util(cuerpo: str) -> str:
    """Se queda con el mensaje nuevo y descarta el hilo citado.

    Un hilo de diez respuestas repite el mismo texto diez veces. Conservarlo entero no añade
    información y sí multiplica lo que después hay que deduplicar.
    """
    texto = str(cuerpo or "").replace("\r\n", "\n")
    corte = _SEPARADOR_HILO.search(texto)
    if corte and corte.start() > 0:
        texto = texto[:corte.start()]
    # Las líneas citadas con `>` son el mensaje de otro, ya recogido en su propio correo. Se
    # descartan enteras: desmarcarlas las convertiría en texto propio y duplicaría el contenido,
    # que es exactamente lo que este recorte existe para evitar.
    lineas = [ln.rstrip() for ln in texto.splitlines() if not _CITA_PREVIA.match(ln)]
    return "\n".join(ln for ln in lineas if ln.strip())


def _texto_de_html(html_crudo: str) -> str:
    from .documentos import _TextoDeHtml

    parser = _TextoDeHtml()
    parser.feed(html_crudo)
    crudo = " ".join(parser.trozos)
    return "\n".join(ln.strip() for ln in crudo.split("\n") if ln.strip())


def extraer(ruta: str) -> Tuple[dict, str, dict]:
    """Adaptador del registro."""
    data = extract_email(ruta)
    registro = {
        "de": data["de"], "para": data["para"], "cc": data["cc"],
        "fecha_correo": data["fecha"], "asunto": data["asunto"],
        "adjuntos": data["adjuntos"],
        "vista_texto": data["texto"],
    }
    remitente = data["de"] or "remitente desconocido"
    asunto = data["asunto"] or "(sin asunto)"
    resumen = f"Correo de {remitente}: {asunto}"
    if data["adjuntos"]:
        resumen += f" ({len(data['adjuntos'])} adjunto(s))"
    return registro, resumen, {}
