"""Schema/plantilla TIPADA del Discovery final (v2 — corrige H4 de la revisión).

La estructura extraída viaja como datos hasta el render final: fuentes, roles, riesgos,
dependencias e hipótesis son listas/objetos, no texto plano. Esto habilita tablas, diagramas,
matrices y validación automática. El Constructor rellena exactamente estas claves; lo no
encontrado queda vacío o "PENDIENTE" — nunca se inventa.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Dict, List

PENDIENTE = "PENDIENTE"

# ---------------------------------------------------------------------------------------------
# Schema tipado: claves → valor por defecto (str | dict | list).
# Nota: `servidor_origen` y `volumetria` de la rúbrica YA NO son campos propios: se evalúan
# desde fuentes[] (cada fuente trae servidor y volumetría). Ver scorer.VALIDADORES.
# ---------------------------------------------------------------------------------------------
_SCHEMA_BASE: Dict[str, object] = {
    # — narrativa (strings) —
    "resumen_ejecutivo": "",
    "necesidad_negocio": "",
    "valor_esperado": "",
    "alcance_in": "",
    "alcance_out": "",
    "metricas_exito": "",
    "consumidores": "",
    "frecuencia_latencia": "",
    "logica_negocio": "",
    "calidad_datos": "",
    "datos_sensibles": "",
    "controles_seguridad": "",
    "habilitacion_tecnica": "",
    "costos_finops": "",
    # — personas (objetos / listas de objetos) —
    "solicitante": {"nombre": "", "rol": "", "contacto": ""},
    "dueno_producto": {"nombre": "", "rol": "", "contacto": ""},
    "expertos_datos": [],     # [{nombre, especialidad, contacto}]
    "certificadores": [],     # [{nombre, ambito}]  ambito: REG|CRI|SAL|PAN|GTM|HND|NIC
    # — datos (listas de objetos) —
    "fuentes": [],            # [{tabla, esquema, servidor, volumetria, frecuencia, sensible, evidencia}]
    "entidades": [],          # [{nombre, descripcion, relaciones}]  (boceto preliminar, no diseño)
    # — gestión (listas de objetos) —
    "dependencias": [],       # [{descripcion, tipo, responsable, estado}]
    "impedimentos": [],       # [{descripcion, responsable, plan, estado}]
    "accesos": [],            # [{recurso, solicitado_a, estado}]
    "riesgos": [],            # [{descripcion, severidad, responsable}]
    "supuestos": [],          # [{descripcion, validado_por}]
    "restricciones": [],      # [{descripcion, origen}]
    # — estrategia (listas de objetos) —
    "hipotesis": [],          # [{enunciado, criterio_validacion, experimento}]
    "arquetipos_datamesh": [],  # [{nombre, dominio, valor_de_negocio, reutiliza_fuentes}]
    # — calculadas por el sistema (el Constructor las deja vacías) —
    "brechas": "",
    "veredicto": "",
}

# Columnas preferidas al renderizar tablas (orden estable y legible).
COLUMNAS_PREFERIDAS: Dict[str, List[str]] = {
    "fuentes": ["tabla", "esquema", "servidor", "volumetria", "frecuencia", "sensible", "evidencia"],
    "expertos_datos": ["nombre", "especialidad", "contacto"],
    "certificadores": ["nombre", "ambito"],
    "entidades": ["nombre", "descripcion", "relaciones"],
    "dependencias": ["descripcion", "tipo", "responsable", "estado"],
    "impedimentos": ["descripcion", "responsable", "plan", "estado"],
    "accesos": ["recurso", "solicitado_a", "estado"],
    "riesgos": ["descripcion", "severidad", "responsable"],
    "supuestos": ["descripcion", "validado_por"],
    "restricciones": ["descripcion", "origen"],
    "hipotesis": ["enunciado", "criterio_validacion", "experimento"],
    "arquetipos_datamesh": ["nombre", "dominio", "valor_de_negocio", "reutiliza_fuentes"],
}

# Orden y títulos de las secciones del documento final.
SECCIONES: List[Dict[str, object]] = [
    {"id": "resumen_ejecutivo", "titulo": "1. Resumen ejecutivo", "claves": ["resumen_ejecutivo"]},
    {"id": "negocio", "titulo": "2. Caso de uso y negocio",
     "claves": ["necesidad_negocio", "valor_esperado", "alcance_in", "alcance_out",
                "metricas_exito", "consumidores"]},
    {"id": "roles", "titulo": "3. Roles y contactos",
     "claves": ["solicitante", "dueno_producto", "expertos_datos", "certificadores"]},
    {"id": "fuentes", "titulo": "4. Fuentes de datos",
     "claves": ["fuentes", "frecuencia_latencia", "logica_negocio", "calidad_datos", "entidades"]},
    {"id": "sensibles", "titulo": "5. Datos sensibles / privados / regulados",
     "claves": ["datos_sensibles", "controles_seguridad"]},
    {"id": "habilitacion", "titulo": "6. Habilitación técnica", "claves": ["habilitacion_tecnica"]},
    {"id": "dependencias", "titulo": "7. Dependencias, impedimentos y accesos",
     "claves": ["dependencias", "impedimentos", "accesos"]},
    {"id": "hipotesis", "titulo": "8. Hipótesis de valor y arquetipos DataMesh",
     "claves": ["hipotesis", "arquetipos_datamesh"]},
    {"id": "costos", "titulo": "9. Costos preliminares (FinOps)", "claves": ["costos_finops"]},
    {"id": "riesgos", "titulo": "10. Riesgos, supuestos y restricciones",
     "claves": ["riesgos", "supuestos", "restricciones"]},
    {"id": "brechas", "titulo": "11. Brechas y preguntas poderosas pendientes", "claves": ["brechas"]},
    {"id": "veredicto", "titulo": "12. Veredicto de factibilidad", "claves": ["veredicto"]},
]

ETIQUETAS: Dict[str, str] = {
    "resumen_ejecutivo": "Resumen ejecutivo",
    "necesidad_negocio": "Necesidad de negocio / problema",
    "valor_esperado": "Valor esperado / caso de negocio y prioridad",
    "alcance_in": "Alcance incluido",
    "alcance_out": "Alcance excluido",
    "metricas_exito": "Métricas de éxito / KPIs",
    "consumidores": "Consumidores y forma de consumo",
    "solicitante": "Solicitante del caso de uso",
    "dueno_producto": "Dueño final del producto de datos",
    "expertos_datos": "Expertos técnicos / del dato",
    "certificadores": "Certificadores (regional y por país)",
    "fuentes": "Inventario de fuentes de datos",
    "servidor_origen": "Servidor / origen (on-premise/cloud)",
    "volumetria": "Volumetría por tabla (≥1 año)",
    "frecuencia_latencia": "Frecuencia de actualización / latencia",
    "logica_negocio": "Lógica de negocio a nivel de queries",
    "calidad_datos": "Calidad de datos y limitaciones",
    "entidades": "Entidades preliminares (boceto, no diseño)",
    "datos_sensibles": "Datos sensibles / privados / regulados",
    "controles_seguridad": "Controles de seguridad requeridos",
    "habilitacion_tecnica": "Habilitación para estar en línea",
    "dependencias": "Dependencias internas/externas",
    "impedimentos": "Impedimentos abiertos",
    "accesos": "Accesos requeridos",
    "hipotesis": "Hipótesis del producto",
    "arquetipos_datamesh": "Arquetipos DataMesh adicionales",
    "costos_finops": "Estimación de costos (FinOps)",
    "riesgos": "Riesgos iniciales",
    "supuestos": "Supuestos",
    "restricciones": "Restricciones",
    "brechas": "Brechas y preguntas pendientes",
    "veredicto": "Veredicto de factibilidad",
}


def schema_vacio() -> Dict[str, object]:
    """Devuelve el schema tipado con valores por defecto (contrato para el Constructor)."""
    return deepcopy(_SCHEMA_BASE)
