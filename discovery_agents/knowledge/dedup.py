"""Deduplicación semántica del destilado (0 tokens).

El problema, en concreto: un Discovery recorre cinco reuniones y en tres de ellas alguien dice que
hay que replicar la base para no bloquear producción. El destilador, haciendo bien su trabajo,
extrae el hallazgo las tres veces. Sin este módulo, el documento final lo afirma tres veces con
distintas palabras, y el lector no sabe si son tres hallazgos o uno.

**Fusionar no es descartar.** Cuando dos ítems dicen lo mismo, se conserva el enunciado más
informativo y se **unen** sus procedencias: el resultado cita las tres reuniones. La trazabilidad
no se pierde en la deduplicación, se concentra — y un hallazgo respaldado por tres sesiones es una
señal más fuerte que el mismo hallazgo repetido tres veces.

Todo es determinista: mismos ítems, mismo resultado. Comparar frases es un problema resoluble con
código, y lo que se puede calcular no se prompea.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from ..common.texto import similitud

# Por encima de este parecido, dos ítems se consideran el mismo hecho.
#
# El valor sale de calibrar contra los dos errores posibles. Más bajo funde hechos distintos que
# comparten vocabulario ("la tabla TRX tiene 400M" y "la tabla LIQ tiene 400M"), que es el error
# grave: pierde información y nadie lo nota. Más alto deja pasar reformulaciones evidentes, que es
# el error leve: se ve en el documento y se corrige. Ante la duda, el sistema prefiere repetir a
# perder.
UMBRAL = 0.82

# Campos que acumulan procedencia y por tanto se unen en vez de sobrescribirse al fusionar.
_CAMPOS_PROCEDENCIA = ("segmentos", "evidencia", "evidencias", "origen", "fuentes")

# Por dónde buscar el enunciado de un ítem, en orden de preferencia.
_CAMPOS_TEXTO = ("descripcion", "hallazgo", "decision", "texto", "punto", "regla", "proceso",
                 "pregunta", "accion", "enunciado", "detalle", "nombre")


def texto_de(item: object) -> str:
    """Enunciado comparable de un ítem del destilado, venga con la forma que venga."""
    if isinstance(item, str):
        return item
    if not isinstance(item, dict):
        return str(item or "")
    for campo in _CAMPOS_TEXTO:
        valor = item.get(campo)
        if isinstance(valor, str) and valor.strip():
            return valor
    # Sin campo conocido: se compara por todos sus valores de texto.
    return " ".join(str(v) for v in item.values() if isinstance(v, str))


def deduplicar(items: Sequence[object], umbral: float = UMBRAL) -> Dict[str, object]:
    """Funde los ítems que dicen lo mismo, uniendo sus procedencias.

    Returns:
        {"items": [...], "fusionados": int, "grupos": [[texto, ...], ...]}
        `grupos` deja por escrito qué se fundió con qué: una fusión que no se puede auditar es
        indistinguible de una pérdida de datos.
    """
    resultado: List[object] = []
    textos: List[str] = []
    grupos: List[List[str]] = []
    fusionados = 0

    for item in items:
        texto = texto_de(item).strip()
        if not texto:
            resultado.append(item)
            textos.append("")
            grupos.append([])
            continue

        indice = _indice_equivalente(texto, textos, umbral)
        if indice is None:
            resultado.append(item)
            textos.append(texto)
            grupos.append([texto])
            continue

        resultado[indice] = _fusionar(resultado[indice], item)
        textos[indice] = texto_de(resultado[indice])
        grupos[indice].append(texto)
        fusionados += 1

    return {
        "items": resultado,
        "fusionados": fusionados,
        "grupos": [g for g in grupos if len(g) > 1],
    }


def _indice_equivalente(texto: str, previos: List[str], umbral: float) -> Optional[int]:
    """Índice del ítem previo más parecido por encima del umbral, o None."""
    mejor_idx, mejor_puntaje = None, umbral
    for i, previo in enumerate(previos):
        if not previo:
            continue
        puntaje = similitud(texto, previo)
        if puntaje >= mejor_puntaje:
            mejor_idx, mejor_puntaje = i, puntaje
    return mejor_idx


def _fusionar(base: object, otro: object) -> object:
    """Funde dos ítems equivalentes conservando la mayor cantidad de información de ambos."""
    if not isinstance(base, dict) or not isinstance(otro, dict):
        # Ítems de texto suelto: gana el más largo, que es el más específico.
        return base if len(texto_de(base)) >= len(texto_de(otro)) else otro

    # El enunciado más largo suele ser el más preciso ("réplica" vs "réplica no transaccional").
    principal, secundario = ((base, otro) if len(texto_de(base)) >= len(texto_de(otro))
                             else (otro, base))
    fundido = dict(principal)

    for clave, valor in secundario.items():
        if clave in _CAMPOS_PROCEDENCIA:
            fundido[clave] = _unir(fundido.get(clave), valor)
        elif not str(fundido.get(clave, "")).strip():
            # El secundario rellena lo que al principal le faltaba.
            fundido[clave] = valor
    return fundido


def _unir(a: object, b: object) -> object:
    """Une dos procedencias sin duplicar y preservando el orden de aparición."""
    def como_lista(v: object) -> List[object]:
        if v is None or v == "":
            return []
        return list(v) if isinstance(v, (list, tuple)) else [v]

    salida: List[object] = []
    for elemento in como_lista(a) + como_lista(b):
        if elemento not in salida:
            salida.append(elemento)
    # Si ambos venían como cadena suelta, se devuelve cadena para no cambiarle el tipo al campo.
    if isinstance(a, str) and isinstance(b, str):
        return ", ".join(str(e) for e in salida)
    return salida
