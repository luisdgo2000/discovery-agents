"""Tabulador determinista: matrices e inventarios en markdown desde el schema tipado (0 tokens).

La IA decide el contenido (listas de objetos en 30_discovery.json); Python decide el render.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ..common.citas import CITA
from ..common.marcas import PENDIENTE
from ..common.texto import aplanar
from ..knowledge.schema import COLUMNAS_PREFERIDAS, ETIQUETAS, render_como_tabla

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


def render_clave(clave: str, valor: object, forzar_tabla: bool = False) -> str:
    """Render por tipo de una clave del schema.

    Narrativa-first: una lista de objetos se dibuja como PROSA (bullets legibles) por defecto y
    solo como TABLA cuando la clave está en el allowlist (`render_como_tabla`) o `forzar_tabla`
    es True (lo usan los archivos de matrices auxiliares en outputs/tablas/).
    """
    if isinstance(valor, list):
        if valor and isinstance(valor[0], dict):
            if forzar_tabla or render_como_tabla(clave):
                return tabla_md(valor, COLUMNAS_PREFERIDAS.get(clave))
            return _lista_objetos_a_prosa(clave, valor)
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


def _lista_objetos_a_prosa(clave: str, filas: List[dict]) -> str:
    """Convierte una lista de objetos en bullets legibles (narrativa-first, sin saturar de tablas).

    Toma la primera columna preferida como enunciado principal (en negrita) y añade el resto de
    los campos con contenido como cláusulas "Etiqueta: valor". Preserva las citas [E00x].
    """
    cols = COLUMNAS_PREFERIDAS.get(clave) or []
    filas = [f for f in filas if isinstance(f, dict) and any(str(v).strip() for v in f.values())]
    if not filas:
        return f"_{PENDIENTE}_"
    principal = cols[0] if cols else None
    lineas: List[str] = []
    for f in filas:
        # Determina el campo principal (enunciado) y el resto como detalle.
        claves_orden = cols or list(f.keys())
        if principal and str(f.get(principal, "")).strip():
            cabeza = _valor_celda(f.get(principal))
            resto_claves = [c for c in claves_orden if c != principal]
        else:
            cabeza = _valor_celda(next((f[c] for c in claves_orden if str(f.get(c, "")).strip()), ""))
            resto_claves = [c for c in claves_orden if _valor_celda(f.get(c)) != cabeza]
        detalles = [f"{c.replace('_', ' ').capitalize()}: {_valor_celda(f.get(c))}"
                    for c in resto_claves if str(f.get(c, "")).strip() and c != "evidencia"]
        cita = _valor_celda(f.get("evidencia")) if "evidencia" in f else ""
        linea = f"- **{cabeza}**"
        if detalles:
            linea += " — " + " · ".join(detalles)
        if cita.strip():
            linea += f" [{cita}]" if not cita.strip().startswith("[") else f" {cita}"
        lineas.append(linea)
    return "\n".join(lineas)


def _valor_celda(v: object) -> str:
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return str(v or "").strip()


# ---------------------------------------------------------------------------------------------
# Matrices derivadas
# ---------------------------------------------------------------------------------------------
def filas_trazabilidad(discovery: dict) -> List[dict]:
    """Clave del Discovery → evidencias citadas en sus valores. Sale gratis gracias a los IDs.

    Se devuelve como filas y no como markdown para que el Word pueda dibujarlas con su propio
    estilo de tabla en vez de reconvertir un markdown que ya se había formateado.
    """
    filas: List[dict] = []
    for clave, valor in discovery.items():
        citas = sorted(set(CITA.findall(aplanar(valor))))
        if citas:
            filas.append({"campo": ETIQUETAS.get(clave, clave), "evidencias": ", ".join(citas)})
    return filas


def matriz_trazabilidad(discovery: dict) -> str:
    """Matriz de trazabilidad campo → evidencia, en markdown."""
    filas = filas_trazabilidad(discovery)
    if not filas:
        return ("_Sin citas de evidencia [E00x] en el discovery — pedir al Constructor que cite "
                "el origen de cada dato._")
    return tabla_md(filas, ["campo", "evidencias"])


def matriz_decisiones(inconsistencias: Optional[dict]) -> str:
    """Matriz de decisiones pendientes desde 60_inconsistencias.json del Redactor."""
    decisiones = (inconsistencias or {}).get("decisiones_pendientes", [])
    return tabla_md(decisiones, ["decision", "decisor_sugerido", "urgencia"])


def generar_tablas(discovery: dict, inconsistencias: Optional[dict] = None) -> Dict[str, str]:
    """Genera las matrices auxiliares como markdown (archivos separados = tablas reales).

    Estos archivos de outputs/tablas/ SÍ son tablas por definición (son matrices), así que
    fuerzan el render tabular aunque el documento principal use prosa. Devuelve {nombre: md}.
    """
    def tab(clave):
        return render_clave(clave, discovery.get(clave, []), forzar_tabla=True)
    return {
        "inventario_fuentes.md": "# Inventario de fuentes\n\n" + tab("fuentes"),
        "matriz_riesgos.md": "# Matriz de riesgos\n\n" + tab("riesgos"),
        "matriz_hallazgos_tecnicos.md": "# Hallazgos técnicos\n\n" + tab("hallazgos_tecnicos"),
        "matriz_dependencias.md": "# Catálogo de dependencias e impedimentos\n\n## Dependencias\n\n"
            + tab("dependencias")
            + "\n\n## Impedimentos\n\n" + tab("impedimentos")
            + "\n\n## Accesos\n\n" + tab("accesos"),
        "matriz_supuestos_restricciones.md": "# Supuestos y restricciones\n\n## Supuestos\n\n"
            + tab("supuestos")
            + "\n\n## Restricciones\n\n" + tab("restricciones"),
        "matriz_trazabilidad.md": "# Matriz de trazabilidad (campo → evidencia)\n\n"
            + matriz_trazabilidad(discovery),
        "matriz_decisiones.md": "# Matriz de decisiones pendientes\n\n"
            + matriz_decisiones(inconsistencias),
        "matriz_temas_faltantes.md": "# Temas faltantes y deuda técnica\n\n"
            + tab("temas_faltantes"),
    }

