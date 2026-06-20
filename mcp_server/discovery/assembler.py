"""Ensamblado determinista del documento final (0 tokens) — v2 tipado + narrativa.

Estructura del documento final:
  - Si existe la narrativa del Redactor Experto (60_redaccion.md): el cuerpo del documento es
    la narrativa, y la información estructurada (tablas tipadas) va como anexos referenciables.
  - Si no existe: documento estructurado por secciones (modo v1, útil antes del Redactor).
El LLM no interviene aquí: solo se formatea.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ..artefactos.tablas import render_clave
from .scorer import score_discovery
from .template import ETIQUETAS, SECCIONES


def ensamblar_discovery(discovery: Dict[str, object], caso_de_uso: str = "",
                        redaccion_md: Optional[str] = None) -> dict:
    """Devuelve {markdown, brechas_markdown, veredicto, score} listos para persistir."""
    score = score_discovery(discovery)
    titulo = caso_de_uso or "Producto de datos"

    md: List[str] = [f"# Discovery — {titulo}\n", _badge_veredicto(score) + "\n"]

    if redaccion_md and redaccion_md.strip():
        md.append(redaccion_md.strip())
        md.append("\n---\n")
        md.append("# Anexos — Información estructurada\n")
        encabezado = "##"
    else:
        encabezado = "##"

    for sec in SECCIONES:
        sec_id = sec["id"]
        if redaccion_md and sec_id == "resumen_ejecutivo":
            continue  # la narrativa ya cubre el resumen; no duplicar
        md.append(f"{encabezado} {sec['titulo']}\n")
        if sec_id == "brechas":
            md.append(_brechas_inline(score))
            continue
        if sec_id == "veredicto":
            md.append(_veredicto_inline(score))
            continue
        for clave in sec["claves"]:  # type: ignore[union-attr]
            etiqueta = ETIQUETAS.get(clave, clave)
            valor = render_clave(clave, discovery.get(clave))
            if "\n" in valor:  # tabla o bullets: etiqueta como subtítulo
                md.append(f"**{etiqueta}:**\n\n{valor}\n")
            else:
                md.append(f"**{etiqueta}:** {valor}\n")
        md.append("")

    return {
        "markdown": "\n".join(md).strip() + "\n",
        "brechas_markdown": _reporte_brechas(score, titulo),
        "veredicto": {
            "caso_de_uso": titulo,
            "veredicto": score["veredicto"],
            "completitud_total": score["completitud_total"],
            "condiciones_para_avanzar": score["condiciones_para_avanzar"],
            "n_brechas": score["n_brechas"],
            "bloques": [
                {"titulo": b["titulo"], "completitud": b["completitud"], "critico": b["critico"]}
                for b in score["bloques"]
            ],
        },
        "score": score,
    }


def _badge_veredicto(score: dict) -> str:
    v = score["veredicto"]
    icono = {"Go": "✅", "Condicional": "🟡", "No-Go": "⛔"}.get(v, "•")
    return (f"> {icono} **Veredicto: {v}** · Completitud: {score['completitud_total']}% · "
            f"Brechas: {score['n_brechas']}")


def _veredicto_inline(score: dict) -> str:
    out = [_badge_veredicto(score), ""]
    cond = score["condiciones_para_avanzar"]
    if cond:
        out.append("**Condiciones para avanzar:**")
        out.extend(f"- {c}" for c in cond)
    else:
        out.append("_Sin condiciones bloqueantes pendientes._")
    out.append("")
    out.append("**Completitud por bloque:**")
    for b in score["bloques"]:
        marca = "crítico" if b["critico"] else "opcional"
        out.append(f"- {b['titulo']} ({marca}): {b['completitud']}%")
    return "\n".join(out) + "\n"


def _brechas_inline(score: dict) -> str:
    if not score["brechas"]:
        return "_Sin brechas: el discovery responde todas las preguntas de la rúbrica._\n"
    out: List[str] = []
    for br in score["brechas"]:
        sev = "🔴" if (br["critico"] and br["obligatoria"]) else "🟠" if br["obligatoria"] else "⚪"
        out.append(f"- {sev} [{br['bloque']}] {br['pregunta']}")
    return "\n".join(out) + "\n"


def _reporte_brechas(score: dict, titulo: str) -> str:
    out = [f"# Brechas y preguntas poderosas pendientes — {titulo}\n",
           _badge_veredicto(score), ""]
    if not score["brechas"]:
        out.append("_Sin brechas pendientes._")
        return "\n".join(out) + "\n"
    criticas = [b for b in score["brechas"] if b["critico"] and b["obligatoria"]]
    otras = [b for b in score["brechas"] if not (b["critico"] and b["obligatoria"])]
    if criticas:
        out.append("## 🔴 Bloqueantes (responder antes de avanzar)\n")
        out.extend(f"- [{b['bloque']}] {b['pregunta']}" for b in criticas)
        out.append("")
    if otras:
        out.append("## 🟠 Recomendadas\n")
        out.extend(f"- [{b['bloque']}] {b['pregunta']}" for b in otras)
    return "\n".join(out) + "\n"
