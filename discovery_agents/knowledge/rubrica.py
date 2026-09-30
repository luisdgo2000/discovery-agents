"""Rúbrica de 'preguntas poderosas' para un Discovery sólido de producto de datos.

Es la fuente de verdad que usan: (1) el subagente Crítico para detectar brechas y generar
preguntas pendientes, y (2) el scorer determinista para calcular completitud y veredicto.

Cada bloque tiene un peso y un flag `critico`: un bloque crítico incompleto fuerza veredicto
distinto de "Go". Cada pregunta mapea a una `clave` del schema del Discovery (template.py) para
poder evaluar automáticamente si fue respondida.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Pregunta:
    clave: str          # campo del schema que la responde
    texto: str
    obligatoria: bool = True


@dataclass
class Bloque:
    id: str
    titulo: str
    peso: int
    critico: bool
    preguntas: List[Pregunta] = field(default_factory=list)


RUBRICA: List[Bloque] = [
    Bloque(
        id="negocio", titulo="Negocio / Caso de uso", peso=20, critico=True,
        preguntas=[
            Pregunta("nombre_caso_uso", "¿Cuál es el nombre del caso de uso?"),
            Pregunta("contexto", "¿En qué contexto de negocio surge el caso?", obligatoria=False),
            Pregunta("problematica_actual", "¿Cuál es la problemática actual que se vive hoy?", obligatoria=False),
            Pregunta("casos_uso", "¿Cuáles y cuántos casos de uso cubre el Discovery?", obligatoria=False),
            Pregunta("necesidad_negocio", "¿Cuál es el problema de negocio concreto que resuelve?"),
            Pregunta("objetivo", "¿Cuál es el objetivo del caso de uso?"),
            Pregunta("valor_esperado", "¿Cuál es el beneficio de atender el caso / valor esperado y su prioridad?"),
            Pregunta("alcance_in", "¿Cuál es el alcance incluido?"),
            Pregunta("alcance_out", "¿Qué queda explícitamente fuera del alcance?"),
            Pregunta("metricas_exito", "¿Cuáles son las métricas de éxito / KPIs y cómo se medirán?"),
            Pregunta("consumidores", "¿Quiénes son los consumidores y cómo consumirán el producto?"),
        ],
    ),
    Bloque(
        id="roles", titulo="Gobierno / Roles", peso=15, critico=True,
        preguntas=[
            Pregunta("solicitante", "¿Quién es el solicitante del caso de uso?"),
            Pregunta("dueno_producto", "¿Quién es el dueño final del producto de datos?"),
            Pregunta("product_owner", "¿Quién es el Product Owner (PO) del producto de datos?"),
            Pregunta("lider_tecnico", "¿Quién es el líder técnico de la solución?", obligatoria=False),
            Pregunta("equipo_desarrollador", "¿Quiénes conforman el equipo desarrollador y sus roles?"),
            Pregunta("expertos_datos", "¿Quiénes son los expertos técnicos / del dato y sus contactos?"),
            Pregunta("expertos_por_pais", "¿Quiénes son los expertos por país?", obligatoria=False),
            Pregunta("certificadores", "¿Quiénes certifican el producto de datos (regional y por país)?", obligatoria=False),
        ],
    ),
    Bloque(
        id="fuentes", titulo="Fuentes y datos", peso=22, critico=True,
        preguntas=[
            Pregunta("fuentes", "¿Cuáles son las fuentes / tablas a llevar a la nube?"),
            Pregunta("servidor_origen", "¿En qué servidor/origen están (on-premise/cloud)?"),
            Pregunta("columnas_fuentes", "¿Cuáles son las columnas necesarias por fuente?"),
            Pregunta("librerias_fuentes", "¿Qué librerías / drivers se requieren para las fuentes origen?", obligatoria=False),
            Pregunta("volumetria", "¿Cuál es la volumetría de cada tabla/insumo (al menos 1 año)?"),
            Pregunta("frecuencia_latencia", "¿Cuál es la frecuencia de actualización / latencia requerida?"),
            Pregunta("logica_negocio", "¿Cuál es la lógica de negocio a nivel de queries (cómo se construye el dato)?"),
            Pregunta("calidad_datos", "¿Qué se sabe de la calidad de los datos y sus limitaciones?", obligatoria=False),
            Pregunta("datos_sensibles", "¿Existen datos sensibles/privados/regulados?"),
        ],
    ),
    Bloque(
        id="habilitacion", titulo="Técnico / Habilitación", peso=18, critico=True,
        preguntas=[
            Pregunta("habilitacion_tecnica", "¿Qué se debe habilitar para poner el producto en línea (replicación anti-bloqueo, Data Factory, accesos, mancomunación, códigos)?"),
            Pregunta("dependencias", "¿Cuáles son las dependencias internas/externas y los accesos requeridos?"),
            Pregunta("hallazgos_tecnicos", "¿Qué hallazgos técnicos relevantes surgieron en el Discovery?", obligatoria=False),
            Pregunta("costos_finops", "¿Hay estimación de costos (FinOps)?", obligatoria=False),
        ],
    ),
    Bloque(
        id="hipotesis", titulo="Hipótesis y valor", peso=15, critico=False,
        preguntas=[
            Pregunta("hipotesis", "¿Cuáles son las hipótesis del producto y sus criterios de validación?"),
            Pregunta("arquetipos_datamesh", "¿Qué arquetipos DataMesh adicionales podría habilitar (facturación, plazos, etc.)?"),
            Pregunta("productos_relacionados", "¿Qué productos de datos relacionados o dependientes existen?", obligatoria=False),
        ],
    ),
    Bloque(
        id="riesgos", titulo="Riesgos y factibilidad", peso=10, critico=True,
        preguntas=[
            Pregunta("impedimentos", "¿Cuáles son los impedimentos abiertos y su plan/responsable?"),
            Pregunta("riesgos", "¿Cuáles son los riesgos abiertos?", obligatoria=False),
            Pregunta("supuestos", "¿Qué supuestos se están asumiendo y quién los validará?", obligatoria=False),
            Pregunta("restricciones", "¿Qué restricciones (técnicas, regulatorias, de negocio) limitan la solución?", obligatoria=False),
        ],
    ),
]


def rubrica_serializable() -> dict:
    """Devuelve la rúbrica como dict (para exponerla como recurso MCP cacheable)."""
    return {
        "bloques": [
            {
                "id": b.id, "titulo": b.titulo, "peso": b.peso, "critico": b.critico,
                "preguntas": [
                    {"clave": p.clave, "texto": p.texto, "obligatoria": p.obligatoria}
                    for p in b.preguntas
                ],
            }
            for b in RUBRICA
        ],
        "peso_total": sum(b.peso for b in RUBRICA),
    }
