"""Tabulador determinista: matrices e inventarios en markdown desde el schema tipado (0 tokens).

La IA decide el contenido (listas de objetos en 30_discovery.json); Python decide el render.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from ..discovery.template import COLUMNAS_PREFERIDAS, ETIQUETAS, PENDIENTE

_CITA = re.compile(r"\[(E\d{3}[^\]]*)\]")


def tabla_md(filas: List[dict], columnas: Optional[List[str]] = None) -> str:
    """Render genérico de lista de dicts → tabla markdown."""
    filas = [f for f in filas if isinstance(f, dict) and any(str(v).strip() for v in f.values())]
    if not filas:
        return f"_{PENDIENTE}_"
    if not columnas:
        columnas = []
        for f in filas:
            for k in f:
                if k not in columnas:
                    columnas.append(k)
    cab = "| " + " | ".join(c.replace("_", " ").capitalize() for c in columnas) + " |"
    sep = "|" + "|".join("---" for _ in columnas) + "|"
    cuerpo = []
    for f in filas:
        celdas = []
        for c in columnas:
            v = f.get(c, "")
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v)
            celdas.append(str(v).replace("\n", " ").replace("|", "\\|").strip() or "—")
        cuerpo.append("| " + " | ".join(celdas) + " |")
    return "\n".join([cab, sep] + cuerpo)


def render_clave(clave: str, valor: object) -> str:
    """Render por tipo de una clave del schema: tabla, persona, bullets o texto."""
    if isinstance(valor, list):
        if valor and isinstance(valor[0], dict):
            return tabla_md(valor, COLUMNAS_PREFERIDAS.get(clave))
        if valor:
            return "\n".join(f"- {v}" for v in valor)
        return f"_{PENDIENTE}_"
    if isinstance(valor, dict):
        partes = [str(valor.get("nombre", "")).strip()]
        if str(valor.get("rol", "")).strip():
            partes.append(f"({valor['rol']})")
        if str(valor.get("contacto", "")).strip():
            partes.append(f"— {valor['contacto']}")
        texto = " ".join(p for p in partes if p)
        if texto:
            return texto
        otros = ", ".join(f"{k}: {v}" for k, v in valor.items() if str(v).strip())
        return otros or f"_{PENDIENTE}_"
    v = str(valor or "").strip()
    return v if v and v.upper() != PENDIENTE else f"_{PENDIENTE}_"


# ---------------------------------------------------------------------------------------------
# Matrices derivadas
# ---------------------------------------------------------------------------------------------
def matriz_trazabilidad(discovery: dict) -> str:
    """Clave del Discovery → evidencias citadas [E00x] en sus valores. Gratis con los IDs."""
    filas: List[dict] = []
    for clave, valor in discovery.items():
        citas = sorted(set(_CITA.findall(_aplanar(valor))))
        if citas:
            filas.append({"campo": ETIQUETAS.get(clave, clave), "evidencias": ", ".join(citas)})
    if not filas:
        return ("_Sin citas de evidencia [E00x] en el discovery — pedir al Constructor que cite "
                "el origen de cada dato._")
    return tabla_md(filas, ["campo", "evidencias"])


def matriz_decisiones(inconsistencias: Optional[dict]) -> str:
    """Matriz de decisiones pendientes desde 60_inconsistencias.json del Redactor."""
    decisiones = (inconsistencias or {}).get("decisiones_pendientes", [])
    return tabla_md(decisiones, ["decision", "decisor_sugerido", "urgencia"])


def generar_tablas(discovery: dict, inconsistencias: Optional[dict] = None) -> Dict[str, str]:
    """Genera todas las matrices como markdown. Devuelve {nombre_archivo: contenido}."""
    return {
        "inventario_fuentes.md": "# Inventario de fuentes\n\n" + render_clave("fuentes", discovery.get("fuentes", [])),
        "matriz_riesgos.md": "# Matriz de riesgos\n\n" + render_clave("riesgos", discovery.get("riesgos", [])),
        "matriz_dependencias.md": "# Catálogo de dependencias e impedimentos\n\n## Dependencias\n\n"
            + render_clave("dependencias", discovery.get("dependencias", []))
            + "\n\n## Impedimentos\n\n" + render_clave("impedimentos", discovery.get("impedimentos", []))
            + "\n\n## Accesos\n\n" + render_clave("accesos", discovery.get("accesos", [])),
        "matriz_supuestos_restricciones.md": "# Supuestos y restricciones\n\n## Supuestos\n\n"
            + render_clave("supuestos", discovery.get("supuestos", []))
            + "\n\n## Restricciones\n\n" + render_clave("restricciones", discovery.get("restricciones", [])),
        "matriz_trazabilidad.md": "# Matriz de trazabilidad (campo → evidencia)\n\n"
            + matriz_trazabilidad(discovery),
        "matriz_decisiones.md": "# Matriz de decisiones pendientes\n\n"
            + matriz_decisiones(inconsistencias),
        "matriz_temas_faltantes.md": "# Temas faltantes y deuda técnica\n\n"
            + render_clave("temas_faltantes", discovery.get("temas_faltantes", [])),
    }


def _aplanar(valor: object) -> str:
    if isinstance(valor, str):
        return valor
    if isinstance(valor, list):
        return " ".join(_aplanar(v) for v in valor)
    if isinstance(valor, dict):
        return " ".join(_aplanar(v) for v in valor.values())
    return str(valor or "")
