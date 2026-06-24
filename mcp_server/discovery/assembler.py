"""Ensamblado determinista del documento final (0 tokens) — v3: dos vistas + temas faltantes.

El documento se entrega como una SUMA de dos vistas del mismo discovery:
  - Parte I — Discovery inicial (general): negocio, roles, riesgos, evaluación.
  - Parte II — Discovery técnico (profundo): fuentes a la nube (columnas, librerías, servidor),
    habilitación, dependencias, expertos, etc.
Más un cierre con Temas faltantes / deuda técnica (recolectado automáticamente), Cobertura de
evidencia (validador de fidelidad) y Brechas. Si existe la narrativa del Redactor Experto
(60_redaccion.md), se incluye arriba y la información estructurada va como anexos.
El LLM no interviene aquí: solo se formatea y se cruzan datos ya producidos.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ..artefactos.tablas import render_clave
from .fidelidad import seccion_cobertura_md
from .scorer import score_discovery
from .template import ETIQUETAS, PARTES, SECCIONES, es_ausente

_ORDEN_PARTES = ["general", "tecnico", "cierre"]


def ensamblar_discovery(discovery: Dict[str, object], caso_de_uso: str = "",
                        redaccion_md: Optional[str] = None,
                        inconsistencias: Optional[dict] = None,
                        fidelidad: Optional[dict] = None) -> dict:
    """Devuelve {markdown, brechas_markdown, veredicto, score, temas_faltantes} para persistir."""
    score = score_discovery(discovery)
    titulo = caso_de_uso or "Producto de datos"

    # Temas faltantes: lo que el Constructor aportó + lo que el sistema detecta determinista.
    temas = list(discovery.get("temas_faltantes") or [])
    temas = _dedup_temas(temas + recolectar_temas_faltantes(score, discovery, inconsistencias))
    discovery = dict(discovery)
    discovery["temas_faltantes"] = temas

    md: List[str] = [f"# Discovery — {titulo}\n", _badge_veredicto(score) + "\n"]

    hay_narrativa = bool(redaccion_md and redaccion_md.strip())
    if hay_narrativa:
        md.append(redaccion_md.strip())
        md.append("\n---\n")
        md.append("# Anexos — Información estructurada\n")

    for nivel in _ORDEN_PARTES:
        secs = [s for s in SECCIONES if s.get("nivel") == nivel]
        if not secs:
            continue
        md.append(f"# {PARTES[nivel]}\n")
        for sec in secs:
            sec_id = sec["id"]
            if hay_narrativa and sec_id == "resumen_ejecutivo":
                continue  # la narrativa ya cubre el resumen; no duplicar
            md.append(f"## {sec['titulo']}\n")
            if sec_id == "brechas":
                md.append(_brechas_inline(score)); continue
            if sec_id == "veredicto":
                md.append(_veredicto_inline(score)); continue
            if sec_id == "cobertura":
                md.append(seccion_cobertura_md(fidelidad) if fidelidad
                          else "_Sin verificación de fidelidad disponible._\n")
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
            "n_temas_faltantes": len(temas),
            "bloques": [
                {"titulo": b["titulo"], "completitud": b["completitud"], "critico": b["critico"]}
                for b in score["bloques"]
            ],
        },
        "score": score,
        "temas_faltantes": temas,
    }


# ---------------------------------------------------------------------------------------------
# Recolector determinista de "Temas faltantes / deuda técnica"
# ---------------------------------------------------------------------------------------------
def recolectar_temas_faltantes(score: dict, discovery: dict,
                               inconsistencias: Optional[dict]) -> List[dict]:
    """Reúne todo lo que NO se conoció: brechas de rúbrica + vacíos del redactor + supuestos
    sin validar + decisiones pendientes. Así, si falta cualquier punto (incl. alcance u objetivo),
    aparece aquí automáticamente."""
    temas: List[dict] = []

    for br in score.get("brechas", []):
        if br["obligatoria"]:
            tipo = "falta_dato"
            impacto = "Bloqueante" if br["critico"] else "Recomendado"
        else:
            tipo = "desconocido"
            impacto = "Opcional"
        temas.append({
            "punto": br["pregunta"], "tipo": tipo, "impacto": impacto,
            "detalle": f"Bloque: {br['bloque']}", "origen": "rúbrica",
            "accion_sugerida": "Responder en la próxima sesión de discovery",
        })

    inc = inconsistencias or {}
    for v in inc.get("vacios_no_capturados_por_rubrica", []):
        temas.append({"punto": str(v), "tipo": "desconocido", "impacto": "",
                      "detalle": "No capturado por la rúbrica", "origen": "redactor",
                      "accion_sugerida": ""})
    for q in inc.get("preguntas_criticas_adicionales", []):
        temas.append({"punto": str(q), "tipo": "desconocido", "impacto": "",
                      "detalle": "Pregunta crítica adicional del experto", "origen": "redactor",
                      "accion_sugerida": ""})
    for d in inc.get("decisiones_pendientes", []):
        if isinstance(d, dict):
            temas.append({"punto": d.get("decision", ""), "tipo": "decision_pendiente",
                          "impacto": d.get("urgencia", ""), "detalle": "Decisión pendiente",
                          "origen": "redactor",
                          "accion_sugerida": f"Decisor sugerido: {d.get('decisor_sugerido', '')}"})

    for s in discovery.get("supuestos", []):
        if isinstance(s, dict) and es_ausente(s.get("validado_por")):
            temas.append({"punto": s.get("descripcion", ""), "tipo": "supuesto_no_validado",
                          "impacto": "", "detalle": "Supuesto asumido sin validar",
                          "origen": "discovery", "accion_sugerida": "Validar con el responsable"})

    return [t for t in temas if str(t.get("punto", "")).strip()]


def _dedup_temas(temas: List[dict]) -> List[dict]:
    vistos = set()
    out: List[dict] = []
    for t in temas:
        clave = str(t.get("punto", "")).strip().lower()
        if clave and clave not in vistos:
            vistos.add(clave)
            out.append(t)
    return out


# ---------------------------------------------------------------------------------------------
# Render de badges/bloques (sin cambios de comportamiento)
# ---------------------------------------------------------------------------------------------
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
