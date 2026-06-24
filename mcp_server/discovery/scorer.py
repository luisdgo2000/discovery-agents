"""Scoring determinista de completitud + veredicto de factibilidad (0 tokens) — v2 tipado.

Mejoras de la revisión (H4): además de "no vacío", cada clave crítica tiene un VALIDADOR por
tipo que verifica calidad mínima verificable:
  - `volumetria`: TODAS las fuentes deben traer volumetría con números (no "mucho").
  - `servidor_origen`: todas las fuentes deben indicar servidor/origen.
  - personas: deben traer nombre real, no solo un string cualquiera.
Así el score no se puede "engañar" rellenando texto. El veredicto sigue siendo reproducible
y auditable: no depende del criterio variable de un LLM.
"""
from __future__ import annotations

import re
from typing import Callable, Dict, List

from .rubric import RUBRICA, Bloque
from .template import PENDIENTE

# Umbrales de completitud total.
UMBRAL_GO = 85
UMBRAL_CONDICIONAL = 60


# ---------------------------------------------------------------------------------------------
# Evaluación genérica por tipo + validadores específicos por clave
# ---------------------------------------------------------------------------------------------
def _no_vacio(valor: object) -> bool:
    """Regla genérica: string con contenido ≠ PENDIENTE; lista con ítems; dict con algún valor."""
    if valor is None:
        return False
    if isinstance(valor, str):
        v = valor.strip()
        return bool(v) and v.upper() != PENDIENTE
    if isinstance(valor, list):
        return any(_no_vacio(x) for x in valor)
    if isinstance(valor, dict):
        return any(_no_vacio(x) for x in valor.values())
    return bool(valor)


def _fuentes_validas(d: dict) -> List[dict]:
    f = d.get("fuentes")
    if not isinstance(f, list):
        return []
    return [x for x in f if isinstance(x, dict) and str(x.get("tabla", "")).strip()]


def _v_fuentes(d: dict) -> bool:
    return len(_fuentes_validas(d)) > 0


def _v_servidor_origen(d: dict) -> bool:
    fuentes = _fuentes_validas(d)
    return bool(fuentes) and all(str(f.get("servidor", "")).strip() for f in fuentes)


def _v_volumetria(d: dict) -> bool:
    """Volumetría real: cada fuente debe traerla y debe contener números."""
    fuentes = _fuentes_validas(d)
    return bool(fuentes) and all(
        re.search(r"\d", str(f.get("volumetria", ""))) for f in fuentes
    )


def _campo_fuente_no_vacio(campo: str) -> Callable[[dict], bool]:
    """Validador derivado de fuentes[]: TODAS las fuentes deben traer `campo` con contenido."""
    def chequear(d: dict) -> bool:
        fuentes = _fuentes_validas(d)
        return bool(fuentes) and all(_no_vacio(f.get(campo)) for f in fuentes)
    return chequear


def _v_persona(clave: str) -> Callable[[dict], bool]:
    def chequear(d: dict) -> bool:
        p = d.get(clave)
        if isinstance(p, dict):
            return bool(str(p.get("nombre", "")).strip()) and \
                str(p.get("nombre", "")).strip().upper() != PENDIENTE
        return _no_vacio(p)  # tolera string legado
    return chequear


def _v_lista_personas(clave: str) -> Callable[[dict], bool]:
    def chequear(d: dict) -> bool:
        lst = d.get(clave)
        if isinstance(lst, list):
            return any(isinstance(x, dict) and str(x.get("nombre", "")).strip() for x in lst)
        return _no_vacio(lst)
    return chequear


# clave de la rúbrica → validador específico (default: _no_vacio sobre discovery[clave])
VALIDADORES: Dict[str, Callable[[dict], bool]] = {
    "fuentes": _v_fuentes,
    "servidor_origen": _v_servidor_origen,           # derivada de fuentes[] — no es campo propio
    "volumetria": _v_volumetria,                     # derivada de fuentes[] — no es campo propio
    "columnas_fuentes": _campo_fuente_no_vacio("columnas"),   # columnas necesarias por fuente
    "librerias_fuentes": _campo_fuente_no_vacio("librerias"), # librerías/drivers por fuente
    "solicitante": _v_persona("solicitante"),
    "dueno_producto": _v_persona("dueno_producto"),
    "equipo_desarrollador": _v_lista_personas("equipo_desarrollador"),
    "expertos_datos": _v_lista_personas("expertos_datos"),
    "expertos_por_pais": _v_lista_personas("expertos_por_pais"),
    "certificadores": _v_lista_personas("certificadores"),
}


def _respondida(clave: str, discovery: dict) -> bool:
    validador = VALIDADORES.get(clave)
    if validador is not None:
        return validador(discovery)
    return _no_vacio(discovery.get(clave))


# ---------------------------------------------------------------------------------------------
# Score y veredicto
# ---------------------------------------------------------------------------------------------
def _evaluar_bloque(b: Bloque, discovery: dict) -> dict:
    obligatorias = [p for p in b.preguntas if p.obligatoria]
    base = obligatorias or b.preguntas
    respondidas_oblig = [p for p in base if _respondida(p.clave, discovery)]
    todas_resp = [p for p in b.preguntas if _respondida(p.clave, discovery)]
    completitud = round(100 * len(respondidas_oblig) / len(base), 1) if base else 100.0
    pendientes = [
        {"clave": p.clave, "pregunta": p.texto, "obligatoria": p.obligatoria}
        for p in b.preguntas if not _respondida(p.clave, discovery)
    ]
    return {
        "id": b.id,
        "titulo": b.titulo,
        "peso": b.peso,
        "critico": b.critico,
        "completitud": completitud,
        "respondidas": len(todas_resp),
        "total_preguntas": len(b.preguntas),
        "pendientes": pendientes,
    }


def score_discovery(discovery: dict) -> dict:
    """Calcula completitud, brechas y veredicto a partir del discovery tipado rellenado."""
    bloques = [_evaluar_bloque(b, discovery) for b in RUBRICA]
    peso_total = sum(b["peso"] for b in bloques) or 1
    completitud_total = round(
        sum(b["completitud"] * b["peso"] for b in bloques) / peso_total, 1
    )

    criticos_incompletos = [b for b in bloques if b["critico"] and b["completitud"] < 100]
    brechas: List[dict] = []
    for b in bloques:
        for p in b["pendientes"]:
            brechas.append({
                "bloque": b["titulo"],
                "critico": b["critico"],
                "obligatoria": p["obligatoria"],
                "pregunta": p["pregunta"],
                "clave": p["clave"],
            })

    veredicto, condiciones = _veredicto(completitud_total, criticos_incompletos, brechas)

    return {
        "completitud_total": completitud_total,
        "veredicto": veredicto,
        "condiciones_para_avanzar": condiciones,
        "bloques": bloques,
        "n_brechas": len(brechas),
        "brechas": brechas,
        "umbral_go": UMBRAL_GO,
        "umbral_condicional": UMBRAL_CONDICIONAL,
    }


def _veredicto(total: float, criticos_incompletos: List[dict], brechas: List[dict]):
    condiciones: List[str] = []
    for br in brechas:
        if br["critico"] and br["obligatoria"]:
            condiciones.append(f"[{br['bloque']}] {br['pregunta']}")

    if not criticos_incompletos and total >= UMBRAL_GO:
        return "Go", []
    if total < UMBRAL_CONDICIONAL or len(condiciones) > 4:
        return "No-Go", condiciones
    return "Condicional", condiciones
