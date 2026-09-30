"""Verificador determinista de FIDELIDAD a las fuentes (0 tokens).

El agente documentador no debe inventar: todo dato del discovery y toda afirmación de la
narrativa deben poder rastrearse a una evidencia `[E00x]` realmente existente. Este módulo NO
usa LLM — comprueba con regex y los IDs del índice de evidencia:

  - Campos de texto con contenido pero SIN cita de evidencia.
  - Citas a evidencias que no existen (IDs inválidos).
  - Fuentes sin `evidencia` declarada.
  - Párrafos de la narrativa que afirman hechos sin citar.

Produce un reporte (`65_fidelidad.json`) y una sección "Cobertura de evidencia" para el
documento, de modo que el lector sepa exactamente qué está respaldado y qué no.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Set

from ..common.citas import CITA, id_evidencia
from ..common.marcas import es_ausente
from ..common.texto import aplanar
from .schema import ETIQUETAS, _SCHEMA_BASE

# Campos de texto que NO requieren cita (identificadores/computados por el sistema).
_EXENTOS = {"brechas", "veredicto", "nombre_caso_uso", "fecha_discovery"}
# Longitud mínima para considerar que un párrafo de la narrativa "afirma" algo verificable.
_MIN_PARRAFO = 80


def _id_evidencia(cita: str) -> str:
    """Normaliza 'E003 seg-006' → 'E003' para validar contra el índice."""
    m = re.match(r"(E\d{3})", cita.strip())
    return m.group(1) if m else cita.strip()


def _ids_validos(index: Optional[dict]) -> Optional[Set[str]]:
    if not index:
        return None
    return {str(i.get("id", "")).strip() for i in index.get("items", []) if i.get("id")}


def verificar_fidelidad(discovery: dict, redaccion_md: Optional[str] = None,
                        index: Optional[dict] = None) -> dict:
    """Devuelve el reporte de fidelidad del discovery + narrativa frente a la evidencia."""
    ids = _ids_validos(index)
    campos_sin_cita: List[str] = []
    citas_invalidas: List[dict] = []
    con_contenido = con_cita = 0

    for clave, defecto in _SCHEMA_BASE.items():
        if clave in _EXENTOS or not isinstance(defecto, str):
            continue
        valor = str(discovery.get(clave, "") or "")
        if es_ausente(valor):
            continue
        con_contenido += 1
        citas = CITA.findall(valor)
        if citas:
            con_cita += 1
            if ids is not None:
                for c in citas:
                    if _id_evidencia(c) not in ids:
                        citas_invalidas.append({"campo": ETIQUETAS.get(clave, clave), "cita": c})
        else:
            campos_sin_cita.append(ETIQUETAS.get(clave, clave))

    # Fuentes sin evidencia declarada (cada tabla a la nube debe citar su origen).
    fuentes_sin_evidencia: List[str] = []
    for f in discovery.get("fuentes", []):
        if isinstance(f, dict) and str(f.get("tabla", "")).strip() and not CITA.findall(
                aplanar(f.get("evidencia", "")) + " " + str(f.get("evidencia", ""))):
            if es_ausente(f.get("evidencia", "")):
                fuentes_sin_evidencia.append(str(f.get("tabla")).strip())

    # Validar también IDs citados en las fuentes contra el índice.
    if ids is not None:
        for f in discovery.get("fuentes", []):
            if not isinstance(f, dict):
                continue
            for c in CITA.findall(aplanar(f)):
                if _id_evidencia(c) not in ids:
                    citas_invalidas.append({"campo": f"Fuente {f.get('tabla', '?')}", "cita": c})

    parrafos_sin_cita = _parrafos_sin_cita(redaccion_md)
    parrafos_redundantes = _parrafos_redundantes(redaccion_md)

    cobertura_pct = round(100 * con_cita / con_contenido, 1) if con_contenido else 100.0
    return {
        "cobertura_pct": cobertura_pct,
        "campos_con_contenido": con_contenido,
        "campos_con_cita": con_cita,
        "campos_sin_cita": campos_sin_cita,
        "fuentes_sin_evidencia": fuentes_sin_evidencia,
        "citas_invalidas": citas_invalidas,
        "parrafos_sin_cita": parrafos_sin_cita,
        "parrafos_redundantes": parrafos_redundantes,
        "ids_evidencia": sorted(ids) if ids is not None else [],
    }


def _parrafos_sin_cita(redaccion_md: Optional[str]) -> List[str]:
    """Párrafos de la narrativa que afirman hechos (texto largo) sin citar evidencia."""
    if not redaccion_md:
        return []
    fuera: List[str] = []
    en_codigo = False
    for linea in redaccion_md.splitlines():
        s = linea.strip()
        if s.startswith("```"):
            en_codigo = not en_codigo
            continue
        if en_codigo or not s:
            continue
        if s[0] in "#->|*" or s.startswith(("- ", "* ")):
            continue
        if len(s) >= _MIN_PARRAFO and not CITA.findall(s):
            fuera.append(s[:120] + ("…" if len(s) > 120 else ""))
    return fuera


def _parrafos_redundantes(redaccion_md: Optional[str]) -> List[dict]:
    """Párrafos que repiten lo que ya dijo otro párrafo de la narrativa.

    La estructura fusionada del documento evita que un mismo DATO aparezca dos veces, pero no
    puede evitar que el Redactor cuente dos veces la misma HISTORIA —el riesgo de bloqueos
    explicado en «Riesgos» y otra vez en «Habilitación técnica»—. Eso solo se ve leyendo, y leer
    es justo lo que un verificador determinista puede hacer sin cansarse.

    No se corrige automáticamente: se reporta. Decidir cuál de las dos versiones sobra es una
    decisión editorial, y el sistema no toma decisiones editoriales sobre el texto de otro.
    """
    if not redaccion_md:
        return []
    from ..common.texto import similitud

    candidatos: List[str] = []
    en_codigo = False
    for linea in redaccion_md.splitlines():
        s = linea.strip()
        if s.startswith("```"):
            en_codigo = not en_codigo
            continue
        if en_codigo or not s or s[0] in "#->|*":
            continue
        if len(s) >= _MIN_PARRAFO:
            candidatos.append(s)

    repetidos: List[dict] = []
    for i, actual in enumerate(candidatos):
        for previo in candidatos[:i]:
            if similitud(actual, previo) >= 0.85:
                repetidos.append({
                    "parrafo": actual[:120] + ("…" if len(actual) > 120 else ""),
                    "repite": previo[:120] + ("…" if len(previo) > 120 else ""),
                })
                break
    return repetidos


def _icono(pct: float) -> str:
    return "🟢" if pct >= 90 else "🟡" if pct >= 70 else "🔴"


def seccion_cobertura_md(fid: dict) -> str:
    """Render markdown de la sección 'Cobertura de evidencia' para el documento."""
    pct = fid.get("cobertura_pct", 0.0)
    out: List[str] = [
        f"> {_icono(pct)} **Cobertura de evidencia: {pct}%** "
        f"({fid.get('campos_con_cita', 0)}/{fid.get('campos_con_contenido', 0)} campos con cita "
        f"`[E00x]`).", ""]
    sin = fid.get("campos_sin_cita", [])
    if sin:
        out.append("**Campos con contenido pero sin cita de evidencia:**")
        out.extend(f"- {c}" for c in sin)
        out.append("")
    if fid.get("fuentes_sin_evidencia"):
        out.append("**Fuentes sin evidencia declarada:** "
                   + ", ".join(fid["fuentes_sin_evidencia"]))
        out.append("")
    if fid.get("citas_invalidas"):
        out.append("**Citas a evidencias inexistentes (revisar):**")
        out.extend(f"- {c['campo']}: `[{c['cita']}]`" for c in fid["citas_invalidas"])
        out.append("")
    n_parr = len(fid.get("parrafos_sin_cita", []))
    if n_parr:
        out.append(f"**Párrafos de la narrativa sin cita:** {n_parr} "
                   "(afirmaciones que deberían anclarse a evidencia).")
    if not sin and not fid.get("citas_invalidas") and not fid.get("fuentes_sin_evidencia") and not n_parr:
        out.append("_Todo el contenido con datos está respaldado por evidencia citada._")
    return "\n".join(out).strip() + "\n"
