"""Limpieza NO DESTRUCTIVA de transcripciones (determinista, 0 tokens).

Principios (ver docs/REVISION_INTEGRAL.md, hallazgos H1/H2):
1. **Nunca dañar contenido.** Solo se eliminan interjecciones inequívocas ("eh", "mmm", "ajá").
   Las muletillas ambiguas que también son palabras con significado ("este", "tipo", "ya",
   "cierto", "bueno", "pues", "verdad", "o sea") SOLO se quitan al inicio de la intervención,
   jamás dentro de la frase: "este servidor", "tipo de datos" y "no es cierto" quedan intactos.
2. **El original siempre queda accesible**: cada segmento conserva `original` y un `id` estable
   para auditoría y para que el destilador pida el texto crudo ante ambigüedad.
3. **Dedupe solo adyacente**: únicamente glitches de la transcripción automática (misma línea
   repetida consecutiva). Nunca deduplicación global ni semántica.
4. **Formatos reales de Teams soportados**: VTT con tags `<v Hablante>`, transcripción .docx de
   Teams ("Nombre Apellido   0:15" en línea propia) y texto genérico "Hablante: texto".
"""
from __future__ import annotations

import re
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

# --- Líneas que se descartan completas (metadatos de la herramienta, no habla humana) ---------
_DESCARTAR = [
    re.compile(r"^\s*WEBVTT", re.I),
    re.compile(r"^\s*NOTE\b", re.I),
    re.compile(r"^\s*\d+\s*$"),                                   # índice de cue (.srt)
    re.compile(r"^\s*[\d:.,]+\s*-->\s*[\d:.,]+"),                 # 00:00:01.000 --> 00:00:03.000
    re.compile(r"se (unió|unio|ha unido|salió|salio) a la reunión", re.I),
    re.compile(r"(joined|left) the meeting", re.I),
    re.compile(r"comenzó la transcripción|grabación (iniciada|detenida)", re.I),
]

# --- Interjecciones INEQUÍVOCAS: seguras de eliminar en cualquier posición -------------------
# (Solo sonidos sin significado léxico en español. NO incluir: este, tipo, ya, cierto, bueno,
#  pues, verdad, o sea, digamos, como que — son palabras con significado; ver H1.)
_INTERJECCIONES = re.compile(r"\b(eh+|ehm+|em+|mmm+|umm+|uh+|ajá|aja)\b[,]?\s*", re.I)

# --- Muletillas ambiguas: SOLO al inicio de la intervención Y seguidas de coma ----------------
# La coma es lo que distingue la muletilla ("Este, la idea es...") del uso con significado
# ("Este servidor es...", "Bueno saber que..."). Sin coma, NO se toca.
# Nunca incluir afirmaciones (sí, ok, vale, correcto): son respuestas, no relleno.
_MULETILLAS_INICIO = re.compile(
    r"^(?:(?:eh|em|este|bueno|pues|o sea|digamos|a ver)\s*,\s*)+",
    re.I,
)

# --- Timestamp inline tipo "[00:01:23]" o "(0:12)" al inicio de línea -------------------------
_TS_INLINE = re.compile(r"^\s*[\[(]?\d{1,2}:\d{2}(:\d{2})?([.,]\d+)?[\])]?\s*")

# --- Hablante en formato genérico: "Nombre Apellido:" ------------------------------------------
_HABLANTE_GENERICO = re.compile(r"^\s*([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ.'\- ]{1,40})\s*[:：]\s*")

# --- Formato VTT de Teams: <v Carlos Vega>texto</v> -------------------------------------------
_VTT_TEAMS = re.compile(r"<v\s+([^>]+)>(.*?)(?:</v>|$)", re.S)

# --- Formato .docx de Teams: línea "Nombre Apellido   0:15" (nombre + timestamp, sin texto) ----
_DOCX_TEAMS_CABECERA = re.compile(
    r"^\s*([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ.'\- ]{1,50}?)\s{1,}\(?(\d{1,2}:\d{2}(?::\d{2})?)\)?\s*$"
)


def clean_transcript(text: str) -> dict:
    """Limpia una transcripción preservando el original por segmento.

    Returns dict con:
      - formato_detectado: vtt_teams | docx_teams | generico
      - segmentos: [{id, hablante, texto, original}]
      - hablantes, texto_limpio, n_segmentos
      - caracteres_original / caracteres_limpio / reduccion_pct (métrica de ahorro)
    """
    original_len = len(text)
    formato, crudos = _parsear(text)
    segmentos: List[Dict[str, str]] = []

    for hablante, bruto in crudos:
        limpio = _limpiar_texto(bruto)
        if not limpio:
            continue
        # Consolida con el segmento previo si es el mismo hablante.
        if segmentos and segmentos[-1]["hablante"] == hablante:
            # Dedupe SOLO adyacente: glitch típico de la transcripción automática.
            if limpio.lower() == segmentos[-1]["_ultimo"].lower():
                continue
            segmentos[-1]["texto"] = (segmentos[-1]["texto"] + " " + limpio).strip()
            segmentos[-1]["original"] = (segmentos[-1]["original"] + " " + bruto.strip()).strip()
            segmentos[-1]["_ultimo"] = limpio
        else:
            segmentos.append({
                "id": f"seg-{len(segmentos) + 1:03d}",
                "hablante": hablante,
                "texto": limpio,
                "original": bruto.strip(),
                "_ultimo": limpio,
            })

    for s in segmentos:
        s.pop("_ultimo", None)

    hablantes = list(OrderedDict((s["hablante"], None) for s in segmentos).keys())
    texto_limpio = "\n".join(f"[{s['id']}] {s['hablante']}: {s['texto']}" for s in segmentos)
    reduccion = 0.0 if original_len == 0 else round(100 * (1 - len(texto_limpio) / original_len), 1)

    return {
        "formato_detectado": formato,
        "segmentos": segmentos,
        "hablantes": hablantes,
        "texto_limpio": texto_limpio,
        "n_segmentos": len(segmentos),
        "caracteres_original": original_len,
        "caracteres_limpio": len(texto_limpio),
        "reduccion_pct": reduccion,
    }


# ---------------------------------------------------------------------------------------------
# Parsers por formato → lista de (hablante, texto_bruto)
# ---------------------------------------------------------------------------------------------
def _parsear(text: str) -> Tuple[str, List[Tuple[str, str]]]:
    if "<v " in text:
        return "vtt_teams", _parse_vtt_teams(text)
    if _parece_docx_teams(text):
        return "docx_teams", _parse_docx_teams(text)
    return "generico", _parse_generico(text)


def _parse_vtt_teams(text: str) -> List[Tuple[str, str]]:
    """VTT de Teams: el hablante viene en tags <v Nombre>texto</v> dentro de cada cue."""
    pares: List[Tuple[str, str]] = []
    for linea in text.splitlines():
        if any(p.search(linea) for p in _DESCARTAR):
            continue
        for m in _VTT_TEAMS.finditer(linea):
            hablante = _norm_hablante(m.group(1))
            contenido = m.group(2).strip()
            if contenido:
                pares.append((hablante, contenido))
    return pares


def _parece_docx_teams(text: str) -> bool:
    """Heurística: ≥2 líneas con formato 'Nombre Apellido   0:15' delatan el .docx de Teams."""
    hits = sum(1 for ln in text.splitlines()[:60] if _DOCX_TEAMS_CABECERA.match(ln))
    return hits >= 2


def _parse_docx_teams(text: str) -> List[Tuple[str, str]]:
    """Transcripción .docx de Teams: cabecera 'Nombre   0:15' y el texto en las líneas siguientes."""
    pares: List[Tuple[str, str]] = []
    hablante_actual = "Desconocido"
    for linea in text.splitlines():
        if not linea.strip() or any(p.search(linea) for p in _DESCARTAR):
            continue
        m = _DOCX_TEAMS_CABECERA.match(linea)
        if m:
            hablante_actual = _norm_hablante(m.group(1))
            continue  # la cabecera no lleva texto: el timestamp NO se filtra al contenido
        pares.append((hablante_actual, linea.strip()))
    return pares


def _parse_generico(text: str) -> List[Tuple[str, str]]:
    """Texto plano genérico: 'Hablante: texto' por línea, con timestamps inline opcionales."""
    pares: List[Tuple[str, str]] = []
    hablante_actual = "Desconocido"
    for linea in text.splitlines():
        if not linea.strip() or any(p.search(linea) for p in _DESCARTAR):
            continue
        linea = _TS_INLINE.sub("", linea)
        m = _HABLANTE_GENERICO.match(linea)
        if m:
            hablante_actual = _norm_hablante(m.group(1))
            linea = linea[m.end():]
        if linea.strip():
            pares.append((hablante_actual, linea.strip()))
    return pares


# ---------------------------------------------------------------------------------------------
# Limpieza de texto (conservadora)
# ---------------------------------------------------------------------------------------------
def _limpiar_texto(s: str) -> str:
    s = _INTERJECCIONES.sub("", s)          # interjecciones inequívocas: en cualquier posición
    s = _MULETILLAS_INICIO.sub("", s)       # muletillas ambiguas: SOLO al inicio de intervención
    s = re.sub(r"\b(\w{3,})( \1\b)+", r"\1", s, flags=re.I)  # palabra (≥3 letras) repetida adyacente
    s = re.sub(r"\s{2,}", " ", s)
    s = re.sub(r"\s+([,.;:])", r"\1", s)
    s = re.sub(r"[,;]\s*([.!?])", r"\1", s)  # ",." residual tras quitar una interjección final
    return s.strip(" ,-")


def _norm_hablante(nombre: str) -> str:
    return re.sub(r"\s+", " ", nombre).strip().title()
