"""Citas de evidencia `[E00x]` — la unidad de trazabilidad del sistema.

Toda afirmación factual del Discovery debe poder rastrearse hasta el insumo del que salió. Esa
trazabilidad se codifica como una marca en línea dentro del propio texto:

    "La tabla se factura a diario [E002]"          → evidencia E002
    "El corte es a las 23:00 [E003 seg-014]"       → evidencia E003, segmento 14
    "Se procesa por lotes [inferencia de E003]"    → inferencia declarada sobre E003

El patrón vive aquí y en ningún otro sitio. Duplicarlo en cada módulo que lo necesita —ensamblador,
tablas, exportador Word, exportador HTML, verificador de fidelidad— sería multiplicar por cinco las
oportunidades de que una copia se quede atrás.

Dos decisiones del patrón, ambas nacidas de fallos reales:

- Usa `E\\d+` y **no** `E\\d{3}`. El pipeline numera con `f"E{n:03d}"`, así que un caso con más de
  999 insumos produce `E1000`, que el patrón de ancho fijo dejaba de reconocer en silencio: la cita
  se volvía invisible para el verificador y el documento perdía trazabilidad sin avisar.
- Acepta la cita **en cualquier posición del corchete**, no solo al principio. El prompt del
  Constructor manda marcar las deducciones como `[inferencia de E003]`, y un patrón anclado al
  inicio no las reconocía: el sistema pedía una forma de citar que después contaba como no citada,
  y penalizaba justamente al que seguía la regla.
"""
from __future__ import annotations

import re
from typing import List, Optional

# Cita completa dentro de corchetes: captura el contenido sin los corchetes.
# Reconoce `[E003]`, `[E003 seg-006]` y `[inferencia de E003]`.
CITA = re.compile(r"\[([^\]]*\bE\d+[^\]]*)\]")

# Identificador de evidencia dentro de una cita ("E003 seg-006" → "E003"). También reconoce las
# inferencias declaradas ("inferencia de E003"), que citan evidencia real aunque no sean un hecho.
_ID = re.compile(r"E\d+")


def tiene_cita(texto: object) -> bool:
    """True si el texto contiene al menos una cita de evidencia."""
    return bool(CITA.search(str(texto or "")))


def extraer_citas(texto: object) -> List[str]:
    """Devuelve el contenido de cada cita del texto, en orden de aparición.

    >>> extraer_citas("Diario [E002] y por lotes [E003 seg-014]")
    ['E002', 'E003 seg-014']
    """
    return CITA.findall(str(texto or ""))


def id_evidencia(cita: object) -> Optional[str]:
    """Normaliza una cita a su ID de evidencia ('E003 seg-006' → 'E003'); None si no lo tiene."""
    m = _ID.search(str(cita or ""))
    return m.group(0) if m else None


def ids_citados(texto: object) -> List[str]:
    """IDs de evidencia únicos citados en el texto, en orden de aparición (sin duplicados)."""
    vistos: List[str] = []
    for cita in extraer_citas(texto):
        eid = id_evidencia(cita)
        if eid and eid not in vistos:
            vistos.append(eid)
    return vistos


def sin_citas(texto: object) -> str:
    """Texto legible con las marcas `[E00x]` retiradas.

    Lo usa el Resumen Ejecutivo HTML: un líder lee la conclusión, no el aparato de trazabilidad
    (que sigue disponible, íntegro, en el documento Word y en la matriz de trazabilidad).
    """
    limpio = CITA.sub("", str(texto or ""))
    limpio = re.sub(r"\s{2,}", " ", limpio)
    return limpio.strip(" .;,")
