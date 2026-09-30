"""Validación de forma de `30_discovery.json` (0 tokens).

`save_state` comprueba que el archivo sea JSON válido, y hasta ahí llegaba la garantía. Pero un
JSON perfectamente válido puede violar el contrato del schema de la peor manera posible: si el
Constructor aplana `fuentes` a un párrafo de texto en vez de dejarlo como lista de objetos, el
documento no falla — **degrada en silencio**. La tabla de fuentes sale vacía, el diagrama de flujo
sale vacío, la matriz de trazabilidad sale vacía, y nadie se entera hasta que alguien lee el Word y
se pregunta dónde están las tablas.

Ese es exactamente el modo de fallo que este módulo convierte en un error visible. El principio:
**una pérdida de información entre subagentes tiene que doler de inmediato, no al final.**

Se distinguen dos severidades:
  errores → el ensamblado se detiene. La estructura está rota y el entregable saldría mutilado.
  avisos  → el ensamblado sigue. Es contenido mejorable, no estructura rota.
"""
from __future__ import annotations

from typing import Dict, List

from ..common.citas import tiene_cita
from ..common.marcas import es_ausente
from .schema import _SCHEMA_BASE

# Claves de cada lista de objetos cuya ausencia deja el ítem inservible para el render.
CLAVE_OBLIGATORIA: Dict[str, str] = {
    "casos_uso": "nombre",
    "fuentes": "tabla",
    "entidades": "nombre",
    "productos_relacionados": "nombre",
    "hallazgos_tecnicos": "hallazgo",
    "dependencias": "descripcion",
    "impedimentos": "descripcion",
    "accesos": "recurso",
    "riesgos": "descripcion",
    "supuestos": "descripcion",
    "restricciones": "descripcion",
    "hipotesis": "enunciado",
    "arquetipos_datamesh": "nombre",
    "temas_faltantes": "punto",
    "equipo_desarrollador": "nombre",
    "expertos_datos": "nombre",
    "expertos_por_pais": "nombre",
    "certificadores": "nombre",
}

# Listas de texto suelto: sus elementos son cadenas, no objetos.
_LISTAS_DE_TEXTO = {"mensajes_clave"}


def validar_discovery(discovery: object) -> dict:
    """Comprueba que el Discovery respete el contrato tipado del schema.

    Returns:
        {"valido": bool, "errores": [...], "avisos": [...], "claves_desconocidas": [...]}
    """
    errores: List[str] = []
    avisos: List[str] = []
    desconocidas: List[str] = []

    if not isinstance(discovery, dict):
        return {"valido": False, "errores": [f"El Discovery debe ser un objeto JSON, no "
                                             f"{type(discovery).__name__}."],
                "avisos": [], "claves_desconocidas": []}

    for clave in discovery:
        if clave not in _SCHEMA_BASE:
            desconocidas.append(clave)

    for clave, esperado in _SCHEMA_BASE.items():
        if clave not in discovery:
            avisos.append(f"Falta la clave '{clave}' del schema; se asumirá vacía.")
            continue
        valor = discovery[clave]

        if isinstance(esperado, str):
            if not isinstance(valor, str):
                errores.append(
                    f"'{clave}' debe ser texto y llegó como {type(valor).__name__}. "
                    f"El Constructor debe respetar los tipos del schema.")
        elif isinstance(esperado, dict):
            _validar_persona(clave, valor, errores)
        elif isinstance(esperado, list):
            _validar_lista(clave, valor, errores, avisos)

    _avisos_de_contenido(discovery, avisos)

    return {
        "valido": not errores,
        "errores": errores,
        "avisos": avisos,
        "claves_desconocidas": desconocidas,
    }


def _validar_persona(clave: str, valor: object, errores: List[str]) -> None:
    if not isinstance(valor, dict):
        errores.append(
            f"'{clave}' debe ser un objeto {{nombre, rol, contacto}} y llegó como "
            f"{type(valor).__name__}. Aplanar un rol a texto pierde el contacto y el cargo.")


def _validar_lista(clave: str, valor: object, errores: List[str], avisos: List[str]) -> None:
    if not isinstance(valor, list):
        errores.append(
            f"'{clave}' debe ser una LISTA y llegó como {type(valor).__name__}. "
            f"Aplanarla a texto rompe la tabla, el diagrama y la trazabilidad que la usan.")
        return

    if clave in _LISTAS_DE_TEXTO:
        for i, item in enumerate(valor):
            if not isinstance(item, str):
                errores.append(f"'{clave}[{i}]' debe ser texto y llegó como "
                               f"{type(item).__name__}.")
        return

    obligatoria = CLAVE_OBLIGATORIA.get(clave)
    for i, item in enumerate(valor):
        if not isinstance(item, dict):
            errores.append(
                f"'{clave}[{i}]' debe ser un objeto con las claves del schema y llegó como "
                f"{type(item).__name__}.")
            continue
        if obligatoria and es_ausente(item.get(obligatoria)):
            avisos.append(
                f"'{clave}[{i}]' no tiene '{obligatoria}': el ítem no se podrá renderizar ni citar.")


def _avisos_de_contenido(discovery: dict, avisos: List[str]) -> None:
    """Señales de calidad que no rompen la estructura pero degradan el entregable."""
    # El veredicto lo calcula el scorer; que venga escrito indica que un modelo intentó decidirlo.
    for calculada in ("brechas", "veredicto"):
        if str(discovery.get(calculada, "")).strip():
            avisos.append(
                f"'{calculada}' viene rellenada, pero la calcula el scorer determinista. "
                f"Se sobrescribirá al ensamblar.")

    # El beneficio económico sin cifra citada es la afirmación más peligrosa de un Discovery.
    beneficio = discovery.get("beneficio_economico", "")
    if not es_ausente(beneficio) and not tiene_cita(beneficio):
        avisos.append(
            "'beneficio_economico' afirma un beneficio sin evidencia [E00x]: el documento lo "
            "marcará como no cuantificado en lugar de afirmarlo.")

    fuentes = discovery.get("fuentes")
    if isinstance(fuentes, list):
        sin_servidor = [f.get("tabla") for f in fuentes
                        if isinstance(f, dict) and es_ausente(f.get("servidor"))]
        if sin_servidor:
            avisos.append(
                "Fuentes sin servidor de origen: " + ", ".join(str(t) for t in sin_servidor[:5])
                + ". El diagrama de flujo las agrupará como 'Servidor por definir'.")
