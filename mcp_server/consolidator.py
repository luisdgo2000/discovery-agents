"""Consolidador de destilados + detector determinista de conflictos (0 tokens).

Une los destilados por transcripción (20_destilado/D*.json) en un consolidado único y detecta
CONTRADICCIONES NUMÉRICAS entre fuentes de evidencia: p. ej. el Excel dice que TRX_ADQUIRENCIA
tiene 400M registros/año pero en la reunión se dijo "300 millones". Python localiza el conflicto
y se lo entrega al Redactor Experto ya identificado — el LLM solo razona sobre los conflictos,
no busca agujas en el pajar.
"""
from __future__ import annotations

import os
import re
from typing import Dict, List, Optional

from . import workspace

# Umbral relativo para considerar dos volúmenes "en conflicto".
TOLERANCIA = 0.10  # 10%

_MULT = {
    "k": 1e3, "mil": 1e3, "miles": 1e3,
    "m": 1e6, "mm": 1e6, "millon": 1e6, "millón": 1e6, "millones": 1e6,
    "b": 1e9, "billon": 1e9, "billón": 1e9, "billones": 1e9,  # escala corta usada en datos
}

_NUM = re.compile(
    r"(\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s*"
    r"(k|m|mm|b|mil(?:es)?|millon(?:es)?|millón|billon(?:es)?|billón)?\b",
    re.I,
)


def parse_volumen(texto: object) -> Optional[float]:
    """Convierte expresiones de volumetría a número: '400,000,000', '400M', '300 millones', '18M/año'."""
    if texto is None:
        return None
    s = str(texto).strip().lower()
    m = _NUM.search(s)
    if not m:
        return None
    bruto, sufijo = m.group(1), (m.group(2) or "").lower()
    # separadores de miles: si hay grupos de 3, los separadores son miles; si no, decimal
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", bruto):
        valor = float(re.sub(r"[.,]", "", bruto))
    else:
        valor = float(bruto.replace(",", "."))
    return valor * _MULT.get(sufijo, 1.0)


def _norm_tabla(nombre: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(nombre or "").upper())


def detectar_conflictos(fuentes_excel: List[dict], datos_reunion: List[dict]) -> List[dict]:
    """Cruza volumetrías del Excel contra lo dicho en reuniones (destilado `datos_fuente`).

    Args:
        fuentes_excel: [{tabla, volumetria, ...}] del extractor de Excel.
        datos_reunion: [{tabla_o_fuente, volumetria, evidencia?}] de los destilados.
    Returns:
        [{tabla, valor_excel, valor_reunion, diferencia_pct, detalle}]
    """
    conflictos: List[dict] = []
    excel_por_tabla: Dict[str, dict] = {_norm_tabla(f.get("tabla")): f for f in fuentes_excel}

    for dato in datos_reunion:
        clave = _norm_tabla(dato.get("tabla_o_fuente"))
        if not clave or clave not in excel_por_tabla:
            continue
        v_excel = parse_volumen(excel_por_tabla[clave].get("volumetria"))
        v_reunion = parse_volumen(dato.get("volumetria"))
        if v_excel is None or v_reunion is None or v_excel == 0:
            continue
        diff = abs(v_excel - v_reunion) / v_excel
        if diff > TOLERANCIA:
            conflictos.append({
                "tabla": excel_por_tabla[clave].get("tabla"),
                "valor_excel": excel_por_tabla[clave].get("volumetria"),
                "valor_reunion": dato.get("volumetria"),
                "evidencia_reunion": dato.get("evidencia", ""),
                "diferencia_pct": round(diff * 100, 1),
                "detalle": "La volumetría del Excel y la mencionada en reunión difieren; "
                           "confirmar con el experto de datos cuál es la vigente.",
            })
    return conflictos


def consolidar(caso: str) -> dict:
    """Une todos los destilados D*.json + detecta conflictos contra fuentes del índice.

    Escribe 20_destilado/consolidado.json y devuelve un resumen compacto.
    """
    destilado_dir = os.path.join(workspace.work_dir(caso), "20_destilado")
    consolidado: Dict[str, list] = {
        "decisiones": [], "hallazgos": [], "datos_fuente": [],
        "preguntas_abiertas": [], "acciones": [], "procesos": [], "reglas": [],
    }
    archivos = sorted(
        f for f in os.listdir(destilado_dir)
        if f.startswith("D") and f.endswith(".json") and f != "consolidado.json"
    )
    for nombre in archivos:
        d = workspace.load_json(caso, os.path.join("20_destilado", nombre)) or {}
        origen = nombre[1:].replace(".json", "")  # DE003.json → E003
        for clave in consolidado:
            for item in d.get(clave, []):
                if isinstance(item, dict):
                    item.setdefault("evidencia", origen)
                consolidado[clave].append(item)

    index = workspace.load_json(caso, os.path.join("10_evidence", "index.json")) or {}
    conflictos = detectar_conflictos(
        index.get("fuentes_detectadas", []), consolidado["datos_fuente"]
    )
    consolidado["conflictos"] = conflictos
    workspace.save_json(caso, os.path.join("20_destilado", "consolidado.json"), consolidado)
    workspace.append_metric(caso, "consolidacion", {
        "destilados": len(archivos), "conflictos": len(conflictos),
    })
    return {
        "destilados_unidos": len(archivos),
        "totales": {k: len(v) for k, v in consolidado.items()},
        "conflictos": conflictos,
    }
