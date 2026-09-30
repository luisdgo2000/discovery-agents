"""Schema/plantilla TIPADA del Discovery final.

La estructura extraída viaja como datos hasta el render final: fuentes, roles, riesgos,
dependencias e hipótesis son listas/objetos, no texto plano. Esto habilita tablas, diagramas,
matrices y validación automática. El Constructor rellena exactamente estas claves; lo no
encontrado queda vacío o "PENDIENTE" — nunca se inventa.

Cubre las tres familias de información que un Discovery empresarial debe capturar: identidad
(casos de uso, fecha, contexto, problemática), gobierno (dueño, PO, líder técnico, expertos,
certificadores) y técnica (fuentes, hallazgos, productos relacionados, beneficio económico con
evidencia). El allowlist `CLAVES_TABLA` mantiene el documento narrativo-first: solo un conjunto
curado de claves se dibuja como tabla.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Dict, List

# Las marcas de ausencia viven en common/ porque las consultan todas las capas. Se re-exportan
# aquí para que quien importa el schema tenga a mano su vocabulario de "sin dato".
from ..common.marcas import (  # noqa: F401  (re-export deliberado)
    DESCONOCIDO, MARCAS_AUSENCIA, PENDIENTE, es_ausente,
)


# ---------------------------------------------------------------------------------------------
# Schema tipado: claves → valor por defecto (str | dict | list).
# Nota: `servidor_origen` y `volumetria` de la rúbrica YA NO son campos propios: se evalúan
# desde fuentes[] (cada fuente trae servidor y volumetría). Ver scorer.VALIDADORES.
# ---------------------------------------------------------------------------------------------
_SCHEMA_BASE: Dict[str, object] = {
    # — identidad del caso (strings) —
    "nombre_caso_uso": "",     # nombre del Discovery / caso principal (título del documento)
    "fecha_discovery": "",     # la rellena Python desde el manifiesto (rango de fechas de insumos)
    "contexto": "",            # contexto de negocio en el que surge el caso
    "problematica_actual": "",  # qué duele hoy (distinto de la necesidad/objetivo)
    # — narrativa (strings) —
    "resumen_ejecutivo": "",
    "necesidad_negocio": "",
    "objetivo": "",
    "valor_esperado": "",       # beneficio general esperado
    "beneficio_economico": "",  # beneficio monetario — SOLO si hay evidencia [E00x] (regla en render)
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
    # — mensajes clave para el Resumen Ejecutivo HTML (los aporta el Redactor; 3-5 bullets) —
    "mensajes_clave": [],       # ["mensaje ejecutivo 1", ...]
    # — casos de uso (lista; el número se deriva) —
    "casos_uso": [],            # [{nombre, descripcion, evidencia}] — el caso puede cubrir varios
    # — personas / gobierno (objetos / listas de objetos) —
    "solicitante": {"nombre": "", "rol": "", "contacto": ""},
    "dueno_producto": {"nombre": "", "rol": "", "contacto": ""},
    "product_owner": {"nombre": "", "rol": "", "contacto": ""},     # PO del producto de datos
    "lider_tecnico": {"nombre": "", "rol": "", "contacto": ""},     # líder técnico de la solución
    "equipo_desarrollador": [],  # [{nombre, rol, contacto}] — equipo que construye el producto
    "expertos_datos": [],     # [{nombre, especialidad, contacto}]
    "expertos_por_pais": [],  # [{nombre, pais, especialidad, contacto}]
    "certificadores": [],     # [{nombre, ambito}]  ambito: REG|CRI|SAL|PAN|GTM|HND|NIC
    # — datos (listas de objetos) —
    # fuentes: cada tabla a llevar a la nube, con servidor origen, columnas necesarias y librerías.
    "fuentes": [],            # [{tabla, esquema, servidor, columnas, librerias, volumetria, frecuencia, sensible, evidencia}]
    "entidades": [],          # [{nombre, descripcion, relaciones}]  (boceto preliminar, no diseño)
    "productos_relacionados": [],  # [{nombre, relacion, evidencia}] — otros productos de datos ligados
    "hallazgos_tecnicos": [],      # [{hallazgo, impacto, evidencia}] — descubrimientos técnicos del discovery
    # — gestión (listas de objetos) —
    "dependencias": [],       # [{descripcion, tipo, responsable, estado}]
    "impedimentos": [],       # [{descripcion, responsable, plan, estado}]
    "accesos": [],            # [{recurso, solicitado_a, estado}]
    # riesgos: `tipo` los clasifica para que el documento pueda agruparlos y para que se note
    # cuando una categoría entera está vacía (un Discovery sin ningún riesgo técnico es un dato).
    "riesgos": [],            # [{descripcion, tipo, severidad, impacto, responsable, evidencia}]
    "supuestos": [],          # [{descripcion, validado_por}]
    "restricciones": [],      # [{descripcion, origen}]  origen: tecnica|regulatoria|negocio
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
    "casos_uso": ["nombre", "descripcion", "evidencia"],
    "fuentes": ["tabla", "esquema", "servidor", "columnas", "librerias", "volumetria",
                "frecuencia", "sensible", "evidencia"],
    "equipo_desarrollador": ["nombre", "rol", "contacto"],
    "expertos_datos": ["nombre", "especialidad", "contacto"],
    "expertos_por_pais": ["nombre", "pais", "especialidad", "contacto"],
    "certificadores": ["nombre", "ambito"],
    "entidades": ["nombre", "descripcion", "relaciones"],
    "productos_relacionados": ["nombre", "relacion", "evidencia"],
    "hallazgos_tecnicos": ["hallazgo", "impacto", "evidencia"],
    "dependencias": ["descripcion", "tipo", "responsable", "estado"],
    "impedimentos": ["descripcion", "responsable", "plan", "estado"],
    "accesos": ["recurso", "solicitado_a", "estado"],
    "riesgos": ["descripcion", "tipo", "severidad", "impacto", "responsable"],
    "supuestos": ["descripcion", "validado_por"],
    "restricciones": ["descripcion", "origen"],
    "hipotesis": ["enunciado", "criterio_validacion", "experimento"],
    "arquetipos_datamesh": ["nombre", "dominio", "valor_de_negocio", "reutiliza_fuentes"],
    "temas_faltantes": ["punto", "tipo", "impacto", "detalle", "accion_sugerida"],
}

# ---------------------------------------------------------------------------------------------
# RENDER_HINT — narrativa-first: qué claves de tipo lista MERECEN una tabla en el documento.
# El principio del usuario: "no saturar de tablas; la mayoría en texto estructurado". Solo las
# claves aquí listadas se dibujan como tabla (aportan valor real); el resto de las listas se
# renderiza como prosa/bullets legibles. Ver render.tablas.render_clave(..., forzar_tabla).
# ---------------------------------------------------------------------------------------------
CLAVES_TABLA: set = {
    "fuentes",            # inventario técnico: una tabla es la forma correcta
    "riesgos",            # matriz de riesgos con severidad
    "certificadores",     # gobierno: quién certifica y en qué ámbito/país
    "hallazgos_tecnicos",  # hallazgos con impacto y evidencia
}


def render_como_tabla(clave: str) -> bool:
    """True si la clave (lista de objetos) debe renderizarse como tabla; si no, como prosa."""
    return clave in CLAVES_TABLA


# ---------------------------------------------------------------------------------------------
# SECCIONES — el esqueleto del documento, en su forma FUSIONADA.
#
# La alternativa —narrativa en un bloque y anexo estructurado en otro— hace que el documento hable
# dos veces de cada cosa: los riesgos en la prosa y otra vez en la tabla de riesgos, las fuentes en
# el relato y otra vez en el inventario. El lector acaba sin saber cuál de las dos versiones es la
# buena.
#
# Aquí cada sección tiene UN SOLO cuerpo: la prosa que le corresponde y, dentro de ella, los
# datos estructurados que la sostienen. Un hecho aparece una vez, en el lugar donde se explica.
# Las matrices completas quedan en los anexos, que es donde se consultan y no donde se lee.
#
# Campos de una sección:
#   id         identificador estable (lo usan el ensamblador, el .docx y las pruebas)
#   titulo     encabezado visible
#   parte      "negocio" | "tecnico" | "cierre" → agrupa en las tres partes del documento
#   narrativa  slot de prosa que el Redactor rellena en 60_redaccion.json; "" si es solo datos
#   claves     claves del schema que se pliegan dentro de esta sección
#
# Las claves que empiezan por "_" son calculadas por el sistema, no vienen del Constructor.
# ---------------------------------------------------------------------------------------------
SECCIONES: List[Dict[str, object]] = [
    # ----- Parte I · Negocio -----
    {"id": "contexto", "titulo": "Contexto y problemática actual", "parte": "negocio",
     "narrativa": "contexto", "claves": ["contexto", "problematica_actual"]},
    {"id": "negocio", "titulo": "Necesidad, objetivo y alcance", "parte": "negocio",
     "narrativa": "necesidad",
     "claves": ["casos_uso", "necesidad_negocio", "objetivo", "alcance_in", "alcance_out"]},
    {"id": "beneficios", "titulo": "Beneficios esperados", "parte": "negocio",
     "narrativa": "beneficios",
     "claves": ["valor_esperado", "beneficio_economico", "metricas_exito", "consumidores"]},
    {"id": "proceso", "titulo": "Proceso actual y proceso futuro", "parte": "negocio",
     "narrativa": "proceso", "claves": []},
    {"id": "gobierno", "titulo": "Gobierno del producto de datos", "parte": "negocio",
     "narrativa": "gobierno",
     "claves": ["solicitante", "dueno_producto", "product_owner", "lider_tecnico",
                "equipo_desarrollador", "certificadores"]},
    # ----- Parte II · Técnico -----
    {"id": "fuentes", "titulo": "Sistemas fuente y volumetría", "parte": "tecnico",
     "narrativa": "fuentes", "claves": ["fuentes", "frecuencia_latencia"]},
    {"id": "datos", "titulo": "Datos, lógica de negocio y calidad", "parte": "tecnico",
     "narrativa": "datos", "claves": ["logica_negocio", "calidad_datos", "entidades"]},
    {"id": "sensibles", "titulo": "Datos sensibles y controles de seguridad", "parte": "tecnico",
     "narrativa": "sensibles", "claves": ["datos_sensibles", "controles_seguridad"]},
    {"id": "hallazgos", "titulo": "Hallazgos técnicos y productos relacionados", "parte": "tecnico",
     "narrativa": "hallazgos", "claves": ["hallazgos_tecnicos", "productos_relacionados"]},
    {"id": "expertos", "titulo": "Expertos técnicos y por país", "parte": "tecnico",
     "narrativa": "", "claves": ["expertos_datos", "expertos_por_pais"]},
    {"id": "habilitacion", "titulo": "Habilitación técnica, dependencias y accesos",
     "parte": "tecnico", "narrativa": "habilitacion",
     "claves": ["habilitacion_tecnica", "dependencias", "impedimentos", "accesos"]},
    {"id": "restricciones", "titulo": "Restricciones y supuestos", "parte": "tecnico",
     "narrativa": "", "claves": ["restricciones", "supuestos"]},
    {"id": "riesgos", "titulo": "Riesgos identificados", "parte": "tecnico",
     "narrativa": "riesgos", "claves": ["riesgos"]},
    {"id": "hipotesis", "titulo": "Hipótesis de valor y arquetipos DataMesh", "parte": "tecnico",
     "narrativa": "hipotesis", "claves": ["hipotesis", "arquetipos_datamesh"]},
    {"id": "costos", "titulo": "Costos preliminares (FinOps)", "parte": "tecnico",
     "narrativa": "", "claves": ["costos_finops"]},
    # ----- Cierre · Evaluación y veredicto -----
    {"id": "evaluacion", "titulo": "Evaluación de factibilidad y complejidad", "parte": "cierre",
     "narrativa": "evaluacion", "claves": ["_completitud_bloques"]},
    {"id": "veredicto", "titulo": "Veredicto y recomendación", "parte": "cierre",
     "narrativa": "recomendacion", "claves": ["_veredicto"]},
    {"id": "temas_faltantes", "titulo": "Temas faltantes y deuda técnica", "parte": "cierre",
     "narrativa": "", "claves": ["temas_faltantes"]},
    {"id": "cobertura", "titulo": "Cobertura de evidencia", "parte": "cierre",
     "narrativa": "", "claves": ["_cobertura"]},
]

# Orden de las partes y su encabezado en el documento.
PARTES = {
    "negocio": "Parte I — Discovery inicial (negocio)",
    "tecnico": "Parte II — Discovery técnico (datos y habilitación)",
    "cierre": "Cierre — Evaluación, veredicto y temas faltantes",
}
ORDEN_PARTES = ["negocio", "tecnico", "cierre"]

# Slots de prosa que el Redactor rellena en `60_redaccion.json`, con lo que se espera de cada uno.
# Es el contrato entre el Redactor y el documento: un slot que el Redactor no escriba deja su
# sección con los datos estructurados solamente, y uno que escriba de más no tiene dónde ir.
SLOTS_NARRATIVA: Dict[str, str] = {
    "contexto": "Qué duele hoy, a quién y desde cuándo.",
    "necesidad": "Qué debe resolver el producto de datos y hasta dónde llega su alcance.",
    "beneficios": "Qué mejora y cómo se medirá. El beneficio económico solo con cifra citada.",
    "proceso": "Cómo se resuelve hoy (as-is) y cómo funcionará con el producto (to-be).",
    "gobierno": "Quién decide, quién construye y quién certifica.",
    "fuentes": "Qué sistemas participan, por qué esas tablas y qué implica su volumetría.",
    "datos": "La lógica de negocio en lenguaje claro y el estado de calidad de los datos.",
    "sensibles": "Qué datos son sensibles o regulados y qué controles exigen.",
    "hallazgos": "Qué se descubrió en el Discovery que cambia el diseño o el esfuerzo.",
    "habilitacion": "Qué debe existir para estar en línea y de quién depende.",
    "riesgos": "Qué puede salir mal, con qué severidad y qué impacto en la factibilidad.",
    "hipotesis": "Qué valor adicional es plausible y cómo se validaría.",
    "evaluacion": "Factibilidad y complejidad (talla S/M/L/XL) con su justificación.",
    "recomendacion": "La recomendación profesional, alineada al veredicto determinista.",
}

ETIQUETAS: Dict[str, str] = {
    "nombre_caso_uso": "Nombre del Discovery / caso de uso",
    "fecha_discovery": "Fecha del Discovery",
    "contexto": "Contexto",
    "problematica_actual": "Problemática actual",
    "resumen_ejecutivo": "Resumen ejecutivo",
    "necesidad_negocio": "Problema de negocio / necesidad que resuelve",
    "objetivo": "Objetivo del caso de uso",
    "valor_esperado": "Beneficio general / valor esperado y prioridad",
    "beneficio_economico": "Beneficio económico o monetario",
    "alcance_in": "Alcance incluido",
    "alcance_out": "Alcance excluido",
    "metricas_exito": "Métricas de éxito / KPIs",
    "consumidores": "Consumidores y forma de consumo",
    "casos_uso": "Casos de uso cubiertos",
    "solicitante": "Solicitante del caso de uso",
    "dueno_producto": "Dueño final del producto de datos",
    "product_owner": "Product Owner (PO)",
    "lider_tecnico": "Líder técnico",
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
    "productos_relacionados": "Productos de datos relacionados",
    "hallazgos_tecnicos": "Hallazgos técnicos",
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
    "brechas": "Brechas y preguntas pendientes",
    "veredicto": "Veredicto de factibilidad",
    "mensajes_clave": "Mensajes clave",
    # Calculadas por el sistema (no las rellena el Constructor).
    "_veredicto": "Veredicto de factibilidad",
    "_cobertura": "Cobertura de evidencia",
    "_completitud_bloques": "Completitud por bloque de la rúbrica",
}

# Tipos de riesgo que el documento reconoce y agrupa. Si una categoría no tiene riesgos, el
# documento lo dice: "no se identificaron" es información, y muy distinta de "no se preguntó".
TIPOS_RIESGO = ["operativo", "tecnico", "calidad", "dependencia", "limitacion"]

ETIQUETA_TIPO_RIESGO = {
    "operativo": "Operativos",
    "tecnico": "Técnicos",
    "calidad": "De calidad de datos",
    "dependencia": "De dependencias",
    "limitacion": "Limitaciones",
    "": "Sin clasificar",
}


def schema_vacio() -> Dict[str, object]:
    """Devuelve el schema tipado con valores por defecto (contrato para el Constructor)."""
    return deepcopy(_SCHEMA_BASE)
