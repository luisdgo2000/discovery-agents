"""Extractor de archivos técnicos (0 tokens): JSON, YAML, XML, SQL/DDL, notebooks, logs, config.

Estos insumos aparecen en todo Discovery técnico —el DDL de las tablas de origen, el `config.yaml`
del pipeline actual, el `.drawio` del diagrama de arquitectura— y hasta ahora se descartaban con
un "extensión no soportada".

El principio aquí es **resumir por estructura, no volcar el contenido**. Un JSON de 20.000 líneas
no aporta 20.000 líneas de información: aporta su forma. Volcarlo crudo llenaría el contexto del
modelo con ruido repetido, que es exactamente lo que este sistema existe para evitar. Así que de
un JSON se extrae su árbol de claves con valores de muestra, y de un SQL, las tablas que toca.

El SQL merece mención aparte: es la única fuente de insumo que declara **con precisión** qué tablas
y esquemas participan. Lo que se detecta aquí entra a `fuentes_detectadas` y llega al índice, igual
que las tablas de un Excel de volumetría — pero con la certeza de estar leyendo el código real y
no la transcripción de alguien nombrándolas de memoria.
"""
from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Tuple

# Límites de la vista estructural. Un árbol más profundo o más ancho que esto describe la forma
# igual de bien y ocupa mucho menos.
#
# La profundidad se cuenta por nivel de anidamiento, y una lista de objetos consume dos niveles
# (la lista y su elemento), así que un `config.yaml` corriente —sección → lista → objeto → campo—
# necesita seis para llegar a los valores. Con menos, el árbol se corta justo donde estaba el dato.
_MAX_PROFUNDIDAD = 6
_MAX_HIJOS = 12
_MAX_MUESTRA = 80

# --- SQL -------------------------------------------------------------------------------------
# Se buscan los tres lugares donde un script nombra una tabla. El patrón admite el calificador
# opcional de base de datos y esquema (`BD.dbo.TABLA`) y comillas/corchetes de cualquier motor.
_IDENT = r'[\[\"`]?(\w+)[\]\"`]?'
_TABLA_SQL = re.compile(
    r"\b(?:from|join|into|update|create\s+table|create\s+or\s+replace\s+table|merge\s+into)\s+"
    rf"(?:{_IDENT}\.)?(?:{_IDENT}\.)?{_IDENT}",
    re.I,
)
_COMENTARIO_SQL = re.compile(r"--[^\n]*|/\*.*?\*/", re.S)
# Ruido habitual: subconsultas y CTEs que no son tablas físicas.
_NO_TABLAS = {"select", "values", "dual", "lateral", "unnest", "table"}


def extract_estructurado(path: str) -> dict:
    """Extrae la ESTRUCTURA de un archivo técnico. Nunca vuelca el contenido completo."""
    ext = os.path.splitext(path)[1].lower()
    crudo = _leer(path)

    if ext in (".sql", ".ddl"):
        tablas = _tablas_sql(crudo)
        return {
            "archivo": path, "formato": "sql",
            "fuentes_detectadas": tablas,
            "vista_texto": _vista_sql(crudo, tablas),
            "resumen": f"SQL: {len(tablas)} tabla(s) referenciada(s)",
        }

    if ext == ".ipynb":
        celdas = _celdas_notebook(crudo)
        return {
            "archivo": path, "formato": "notebook", "fuentes_detectadas": [],
            "vista_texto": "\n\n".join(celdas),
            "resumen": f"Notebook: {len(celdas)} celda(s) con contenido",
        }

    if ext in (".json",):
        return _desde_datos(path, "json", _parsear_json(crudo))

    if ext in (".yaml", ".yml"):
        return _desde_datos(path, "yaml", _parsear_yaml(crudo))

    if ext in (".xml", ".drawio"):
        etiquetas = _textos_xml(crudo)
        return {
            "archivo": path, "formato": "xml", "fuentes_detectadas": [],
            "vista_texto": "\n".join(etiquetas),
            "resumen": f"XML/diagrama: {len(etiquetas)} etiqueta(s) de texto",
        }

    # .log, .ini, .cfg, .toml → texto tal cual; su valor está en las líneas, no en un árbol.
    lineas = [ln.strip() for ln in crudo.splitlines() if ln.strip()]
    return {
        "archivo": path, "formato": ext.lstrip("."), "fuentes_detectadas": [],
        "vista_texto": "\n".join(lineas),
        "resumen": f"Archivo técnico ({ext.lstrip('.')}): {len(lineas)} líneas",
    }


def _leer(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _parsear_json(crudo: str):
    try:
        return json.loads(crudo)
    except (ValueError, TypeError):
        return None


def _parsear_yaml(crudo: str):
    try:
        import yaml  # dependencia opcional
    except ImportError:
        return None
    try:
        return yaml.safe_load(crudo)
    except Exception:  # noqa: BLE001 — un YAML inválido es un aviso, no una caída
        return None


def _desde_datos(path: str, formato: str, datos: object) -> dict:
    if datos is None:
        crudo = _leer(path)
        return {
            "archivo": path, "formato": formato, "fuentes_detectadas": [],
            "vista_texto": crudo[:4000],
            "resumen": f"{formato.upper()} no parseable: se conserva el texto crudo",
        }
    lineas = _arbol(datos)
    return {
        "archivo": path, "formato": formato, "fuentes_detectadas": [],
        "vista_texto": "\n".join(lineas),
        "resumen": f"{formato.upper()}: {len(lineas)} nodo(s) de estructura",
    }


def _arbol(datos: object, prefijo: str = "", nivel: int = 0) -> List[str]:
    """Árbol de claves con valores de muestra. La forma del dato, no el dato."""
    if nivel >= _MAX_PROFUNDIDAD:
        return [f"{prefijo}: …"]
    lineas: List[str] = []

    if isinstance(datos, dict):
        for i, (clave, valor) in enumerate(datos.items()):
            if i >= _MAX_HIJOS:
                lineas.append(f"{prefijo}.… ({len(datos) - _MAX_HIJOS} claves más)")
                break
            lineas.extend(_arbol(valor, f"{prefijo}.{clave}" if prefijo else str(clave), nivel + 1))
    elif isinstance(datos, list):
        if not datos:
            lineas.append(f"{prefijo}: []")
        else:
            # Una lista homogénea se describe con su primer elemento y su longitud.
            lineas.append(f"{prefijo}[] ({len(datos)} elementos)")
            lineas.extend(_arbol(datos[0], f"{prefijo}[0]", nivel + 1))
    else:
        muestra = str(datos)
        if len(muestra) > _MAX_MUESTRA:
            muestra = muestra[:_MAX_MUESTRA] + "…"
        lineas.append(f"{prefijo}: {muestra}")
    return lineas


def _tablas_sql(crudo: str) -> List[Dict[str, str]]:
    """Tablas referenciadas por el script, con su esquema y base de datos si vienen calificados."""
    sin_comentarios = _COMENTARIO_SQL.sub(" ", crudo)
    vistas: Dict[str, Dict[str, str]] = {}
    for m in _TABLA_SQL.finditer(sin_comentarios):
        primero, segundo, tercero = m.group(1), m.group(2), m.group(3)
        # El último grupo es siempre la tabla; los previos, sus calificadores.
        partes = [p for p in (primero, segundo, tercero) if p]
        tabla = partes[-1]
        if not tabla or tabla.lower() in _NO_TABLAS:
            continue
        registro: Dict[str, str] = {"tabla": tabla, "origen_deteccion": "sql"}
        if len(partes) >= 2:
            registro["esquema"] = partes[-2]
        if len(partes) >= 3:
            registro["base_datos"] = partes[-3]
        vistas.setdefault(tabla.upper(), registro)
    return list(vistas.values())


def _vista_sql(crudo: str, tablas: List[Dict[str, str]]) -> str:
    """El script íntegro precedido de su inventario: el SQL en sí es evidencia citable."""
    cabecera = "== Tablas referenciadas ==\n" + "\n".join(
        " · " + " . ".join(filter(None, (t.get("base_datos"), t.get("esquema"), t["tabla"])))
        for t in tablas
    ) if tablas else "== Sin tablas detectadas =="
    return f"{cabecera}\n\n== Script ==\n{crudo}"


def _celdas_notebook(crudo: str) -> List[str]:
    """Celdas de markdown y de código de un notebook, en orden y etiquetadas."""
    datos = _parsear_json(crudo)
    if not isinstance(datos, dict):
        return []
    salida: List[str] = []
    for i, celda in enumerate(datos.get("cells", []), start=1):
        if not isinstance(celda, dict):
            continue
        fuente = celda.get("source", [])
        texto = ("".join(fuente) if isinstance(fuente, list) else str(fuente)).strip()
        if texto:
            salida.append(f"[Celda {i} · {celda.get('cell_type', 'code')}]\n{texto}")
    return salida


# Nodos de texto de un XML/drawio: `<mxCell value="Servidor SQL">` y `<text>contenido</text>`.
_ATRIBUTO_TEXTO = re.compile(r'(?:value|label|name)\s*=\s*"([^"]{2,})"', re.I)
_TEXTO_NODO = re.compile(r">([^<>]{2,})<")
_ENTIDAD = re.compile(r"&(?:amp|lt|gt|quot|#39|apos);")


def _textos_xml(crudo: str) -> List[str]:
    """Etiquetas legibles de un XML o de un diagrama draw.io, sin duplicados y en orden."""
    candidatos = _ATRIBUTO_TEXTO.findall(crudo) + _TEXTO_NODO.findall(crudo)
    vistos: List[str] = []
    for c in candidatos:
        limpio = _ENTIDAD.sub(" ", c)
        limpio = re.sub(r"<[^>]+>", " ", limpio)
        limpio = re.sub(r"\s{2,}", " ", limpio).strip()
        if len(limpio) > 1 and limpio not in vistos:
            vistos.append(limpio)
    return vistos


def extraer(ruta: str) -> Tuple[dict, str, dict]:
    """Adaptador del registro."""
    data = extract_estructurado(ruta)
    registro = {
        "formato_detectado": data["formato"],
        "fuentes_detectadas": data["fuentes_detectadas"],
        "vista_texto": data["vista_texto"],
    }
    return registro, data["resumen"], {"fuentes": data["fuentes_detectadas"]}
