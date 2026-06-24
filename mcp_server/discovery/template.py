"""Schema/plantilla TIPADA del Discovery final (v2 — corrige H4 de la revisión).

La estructura extraída viaja como datos hasta el render final: fuentes, roles, riesgos,
dependencias e hipótesis son listas/objetos, no texto plano. Esto habilita tablas, diagramas,
matrices y validación automática. El Constructor rellena exactamente estas claves; lo no
encontrado queda vacío o "PENDIENTE" — nunca se inventa.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Dict, List

# Marcas de ausencia (se distinguen a propósito):
#   PENDIENTE  → la rúbrica lo pide y aún falta llenarlo (acción del equipo).
#   DESCONOCIDO → no surgió en los insumos / no se conoció en el discovery (deuda/riesgo a futuro).
# Ambas se tratan como "sin dato" en el scoring, pero el documento las muestra distinto y el
# recolector de "Temas faltantes" las clasifica por tipo.
PENDIENTE = "PENDIENTE"
DESCONOCIDO = "DESCONOCIDO"
MARCAS_AUSENCIA = {PENDIENTE, DESCONOCIDO}


def es_ausente(texto: object) -> bool:
    """True si un valor string está vacío o es una marca de ausencia (PENDIENTE/DESCONOCIDO)."""
    v = str(texto or "").strip()
    return (not v) or v.upper() in MARCAS_AUSENCIA

# ---------------------------------------------------------------------------------------------
# Schema tipado: claves → valor por defecto (str | dict | list).
# Nota: `servidor_origen` y `volumetria` de la rúbrica YA NO son campos propios: se evalúan
# desde fuentes[] (cada fuente trae servidor y volumetría). Ver scorer.VALIDADORES.
# ---------------------------------------------------------------------------------------------
_SCHEMA_BASE: Dict[str, object] = {
    # — identidad del caso (strings) —
    "nombre_caso_uso": "",
    # — narrativa (strings) —
    "resumen_ejecutivo": "",
    "necesidad_negocio": "",
    "objetivo": "",
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
    "equipo_desarrollador": [],  # [{nombre, rol, contacto}] — equipo que construye el producto
    "expertos_datos": [],     # [{nombre, especialidad, contacto}]
    "expertos_por_pais": [],  # [{nombre, pais, especialidad, contacto}]
    "certificadores": [],     # [{nombre, ambito}]  ambito: REG|CRI|SAL|PAN|GTM|HND|NIC
    # — datos (listas de objetos) —
    # fuentes: cada tabla a llevar a la nube, con servidor origen, columnas necesarias y librerías.
    "fuentes": [],            # [{tabla, esquema, servidor, columnas, librerias, volumetria, frecuencia, sensible, evidencia}]
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
    # — temas faltantes / deuda técnica (el Constructor puede aportar; el sistema los completa) —
    "temas_faltantes": [],    # [{punto, tipo, detalle, impacto, origen, accion_sugerida}]
    # — calculadas por el sistema (el Constructor las deja vacías) —
    "brechas": "",
    "veredicto": "",
}

# Columnas preferidas al renderizar tablas (orden estable y legible).
COLUMNAS_PREFERIDAS: Dict[str, List[str]] = {
    "fuentes": ["tabla", "esquema", "servidor", "columnas", "librerias", "volumetria",
                "frecuencia", "sensible", "evidencia"],
    "equipo_desarrollador": ["nombre", "rol", "contacto"],
    "expertos_datos": ["nombre", "especialidad", "contacto"],
    "expertos_por_pais": ["nombre", "pais", "especialidad", "contacto"],
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
    "temas_faltantes": ["punto", "tipo", "impacto", "detalle", "accion_sugerida"],
}

# Orden, títulos y NIVEL de cada sección. El documento se arma en dos vistas + cierre:
#   nivel="general" → Parte I · Discovery inicial (negocio/estratégico)
#   nivel="tecnico" → Parte II · Discovery técnico (datos + habilitación)
#   nivel="cierre"  → Evaluación, temas faltantes y trazabilidad (transversal)
SECCIONES: List[Dict[str, object]] = [
    # ----- Parte I · Discovery inicial (general) -----
    {"id": "resumen_ejecutivo", "titulo": "Resumen ejecutivo", "nivel": "general",
     "claves": ["resumen_ejecutivo"]},
    {"id": "negocio", "titulo": "Caso de uso y negocio", "nivel": "general",
     "claves": ["nombre_caso_uso", "necesidad_negocio", "objetivo", "valor_esperado",
                "alcance_in", "alcance_out", "metricas_exito", "consumidores"]},
    {"id": "roles_negocio", "titulo": "Roles del caso de uso y equipo", "nivel": "general",
     "claves": ["solicitante", "dueno_producto", "equipo_desarrollador"]},
    {"id": "riesgos", "titulo": "Riesgos, supuestos y restricciones", "nivel": "general",
     "claves": ["riesgos", "supuestos", "restricciones"]},
    # ----- Parte II · Discovery técnico (profundo) -----
    {"id": "expertos", "titulo": "Expertos técnicos, por país y certificadores", "nivel": "tecnico",
     "claves": ["expertos_datos", "expertos_por_pais", "certificadores"]},
    {"id": "fuentes", "titulo": "Fuentes de datos a la nube", "nivel": "tecnico",
     "claves": ["fuentes", "frecuencia_latencia", "logica_negocio", "calidad_datos", "entidades"]},
    {"id": "sensibles", "titulo": "Datos sensibles / privados / regulados", "nivel": "tecnico",
     "claves": ["datos_sensibles", "controles_seguridad"]},
    {"id": "habilitacion", "titulo": "Habilitación técnica", "nivel": "tecnico",
     "claves": ["habilitacion_tecnica"]},
    {"id": "dependencias", "titulo": "Dependencias, impedimentos y accesos", "nivel": "tecnico",
     "claves": ["dependencias", "impedimentos", "accesos"]},
    {"id": "hipotesis", "titulo": "Hipótesis de valor y arquetipos DataMesh", "nivel": "tecnico",
     "claves": ["hipotesis", "arquetipos_datamesh"]},
    {"id": "costos", "titulo": "Costos preliminares (FinOps)", "nivel": "tecnico",
     "claves": ["costos_finops"]},
    # ----- Cierre · Evaluación, temas faltantes y trazabilidad -----
    {"id": "veredicto", "titulo": "Veredicto de factibilidad", "nivel": "cierre",
     "claves": ["veredicto"]},
    {"id": "temas_faltantes", "titulo": "Temas faltantes y deuda técnica", "nivel": "cierre",
     "claves": ["temas_faltantes"]},
    {"id": "cobertura", "titulo": "Cobertura de evidencia", "nivel": "cierre",
     "claves": ["cobertura"]},
    {"id": "brechas", "titulo": "Brechas y preguntas poderosas pendientes", "nivel": "cierre",
     "claves": ["brechas"]},
]

# Títulos de las dos vistas + cierre (los usa el ensamblador y el export docx).
PARTES = {
    "general": "Parte I — Discovery inicial (general)",
    "tecnico": "Parte II — Discovery técnico (profundo)",
    "cierre": "Cierre — Evaluación, temas faltantes y trazabilidad",
}

ETIQUETAS: Dict[str, str] = {
    "nombre_caso_uso": "Nombre del caso de uso",
    "resumen_ejecutivo": "Resumen ejecutivo",
    "necesidad_negocio": "Problema de negocio / necesidad que resuelve",
    "objetivo": "Objetivo del caso de uso",
    "valor_esperado": "Beneficio de atender el caso / valor esperado y prioridad",
    "alcance_in": "Alcance incluido",
    "alcance_out": "Alcance excluido",
    "metricas_exito": "Métricas de éxito / KPIs",
    "consumidores": "Consumidores y forma de consumo",
    "solicitante": "Solicitante del caso de uso",
    "dueno_producto": "Dueño final del producto de datos",
    "equipo_desarrollador": "Equipo desarrollador (roles)",
    "expertos_datos": "Expertos técnicos / del dato",
    "expertos_por_pais": "Expertos por país",
    "certificadores": "Certificadores del producto de datos",
    "fuentes": "Fuentes / tablas a llevar a la nube",
    "servidor_origen": "Servidor / origen (on-premise/cloud)",
    "volumetria": "Volumetría por tabla (≥1 año)",
    "columnas": "Columnas necesarias",
    "librerias": "Librerías / drivers de origen",
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
    "riesgos": "Riesgos identificados",
    "supuestos": "Supuestos",
    "restricciones": "Restricciones",
    "temas_faltantes": "Temas faltantes y deuda técnica",
    "cobertura": "Cobertura de evidencia",
    "brechas": "Brechas y preguntas pendientes",
    "veredicto": "Veredicto de factibilidad",
}


def schema_vacio() -> Dict[str, object]:
    """Devuelve el schema tipado con valores por defecto (contrato para el Constructor)."""
    return deepcopy(_SCHEMA_BASE)
