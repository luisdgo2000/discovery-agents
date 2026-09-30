"""Marcas de ausencia — el vocabulario con el que el sistema dice "no lo sé".

Se distinguen a propósito y NO son intercambiables:
  PENDIENTE   → la rúbrica lo pide y el equipo aún debe definirlo (acción pendiente del negocio).
  DESCONOCIDO → no surgió en los insumos, nadie lo mencionó (deuda de información / riesgo futuro).

Ambas cuentan como "sin dato" en el scoring —un Discovery lleno de DESCONOCIDO no puede alcanzar
Go— pero el documento las presenta distinto y el recolector de "Temas faltantes" las clasifica por
tipo, porque la acción correctiva es diferente: PENDIENTE se decide, DESCONOCIDO se investiga.

Vive en `common/` porque la pregunta "¿este valor está vacío?" la hacen todas las capas: el scorer,
el verificador de fidelidad, el ensamblador, el exportador Word y el HTML ejecutivo.
"""
from __future__ import annotations

PENDIENTE = "PENDIENTE"
DESCONOCIDO = "DESCONOCIDO"
MARCAS_AUSENCIA = {PENDIENTE, DESCONOCIDO}


def es_ausente(texto: object) -> bool:
    """True si un valor string está vacío o es una marca de ausencia (PENDIENTE/DESCONOCIDO)."""
    v = str(texto or "").strip()
    return (not v) or v.upper() in MARCAS_AUSENCIA


def marca_de(texto: object) -> str:
    """Devuelve la marca de ausencia del valor ('PENDIENTE'/'DESCONOCIDO') o '' si tiene dato."""
    v = str(texto or "").strip().upper()
    return v if v in MARCAS_AUSENCIA else ""
