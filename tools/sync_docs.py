"""Genera los bloques del Blueprint a partir del código real.

El Blueprint es un documento de reconstrucción: debe contener el código completo para que alguien
pueda rehacer el sistema sin acceso al repositorio. Pero copiar miles de líneas a mano garantiza
que el documento envejezca — describiría rutas que ya no existen, contaría mal las tools y traería
funciones a las que les faltan reglas. Quien lo usara para reconstruir el sistema reconstruiría una
versión inferior sin saberlo.

La solución no es revisar más: es no copiar a mano. Los bloques marcados con
`<!-- BEGIN:x -->` / `<!-- END:x -->` los genera este script desde el código, y una prueba falla si
el documento queda desincronizado. El Blueprint es autosuficiente y no puede mentir.

Uso:
    python tools/sync_docs.py            # reescribe los bloques
    python tools/sync_docs.py --check    # solo verifica (código 1 si hay desincronización)
"""
from __future__ import annotations

import ast
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

BLUEPRINT = os.path.join(RAIZ, "docs", "BLUEPRINT.md")
PAQUETE = "discovery_agents"

# Orden de presentación de las capas: de la que no depende de nadie a la que depende de todas.
CAPAS = [
    ("common", "Capa transversal", "No importa ninguna otra capa del paquete."),
    ("workspace", "Memoria compartida", "Solo stdlib. Es un peer de las capas, no pertenece a ninguna."),
    ("ingest", "Capa de ingesta", "Importa `common/` y `workspace`."),
    ("knowledge", "Capa de conocimiento", "Importa `common/` y `workspace`."),
    ("render", "Capa de render", "Importa `common/` y `knowledge/`."),
    ("interfaces", "Capa de interfaces", "Importa todas las anteriores. Sin lógica de negocio."),
]


# =============================================================================================
# Utilidades de marcadores
# =============================================================================================
def _bloque(nombre: str, contenido: str) -> str:
    return f"<!-- BEGIN:{nombre} -->\n{contenido.rstrip()}\n<!-- END:{nombre} -->"


def _sustituir(texto: str, nombre: str, contenido: str) -> str:
    patron = re.compile(
        rf"<!-- BEGIN:{re.escape(nombre)} -->.*?<!-- END:{re.escape(nombre)} -->", re.S)
    if not patron.search(texto):
        raise SystemExit(f"El Blueprint no tiene el bloque marcado '{nombre}'.")
    return patron.sub(lambda _: _bloque(nombre, contenido), texto)


# =============================================================================================
# Análisis estático del paquete
# =============================================================================================
def _modulos():
    """Todos los módulos del paquete, ordenados, como (ruta_relativa, ruta_absoluta)."""
    salida = []
    base = os.path.join(RAIZ, PAQUETE)
    for actual, dirs, archivos in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for archivo in sorted(archivos):
            if archivo.endswith(".py"):
                absoluta = os.path.join(actual, archivo)
                salida.append((os.path.relpath(absoluta, RAIZ).replace(os.sep, "/"), absoluta))
    return salida


def _leer(ruta_abs: str) -> str:
    with open(ruta_abs, "r", encoding="utf-8") as fh:
        return fh.read()


def _modulo_punteado(rel: str) -> str:
    """'discovery_agents/knowledge/scorer.py' → 'discovery_agents.knowledge.scorer'."""
    sin_ext = rel[:-3] if rel.endswith(".py") else rel
    if sin_ext.endswith("/__init__"):
        sin_ext = sin_ext[: -len("/__init__")]
    return sin_ext.replace("/", ".")


def _resolver_relativo(modulo_actual: str, nivel: int, destino: str) -> str:
    """Resuelve un import relativo a su módulo punteado absoluto."""
    partes = modulo_actual.split(".")
    base = partes[: len(partes) - (nivel - 1)] if nivel > 1 else partes
    if nivel >= 1 and not modulo_actual.endswith("__init__"):
        base = partes[: len(partes) - nivel] if nivel > 1 else partes[:-1]
    return ".".join([p for p in base if p] + ([destino] if destino else []))


def _analizar(rel: str, ruta_abs: str) -> dict:
    """Metadatos de un módulo: propósito, exportaciones y dependencias."""
    fuente = _leer(ruta_abs)
    arbol = ast.parse(fuente)
    modulo = _modulo_punteado(rel)

    doc = ast.get_docstring(arbol) or ""
    proposito = doc.strip().split("\n")[0] if doc else ""

    funciones, clases, constantes = [], [], []
    for nodo in arbol.body:
        if isinstance(nodo, ast.FunctionDef) and not nodo.name.startswith("_"):
            args = ", ".join(a.arg for a in nodo.args.args)
            retorno = f" -> {ast.unparse(nodo.returns)}" if getattr(nodo, "returns", None) else ""
            funciones.append(f"{nodo.name}({args}){retorno}")
        elif isinstance(nodo, ast.ClassDef) and not nodo.name.startswith("_"):
            clases.append(nodo.name)
        elif isinstance(nodo, (ast.Assign, ast.AnnAssign)):
            objetivos = nodo.targets if isinstance(nodo, ast.Assign) else [nodo.target]
            for t in objetivos:
                if isinstance(t, ast.Name) and t.id.isupper() and not t.id.startswith("_"):
                    constantes.append(t.id)

    internas, externas = set(), set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom):
            if nodo.level:
                internas.add(_resolver_relativo(modulo, nodo.level, nodo.module or ""))
            elif nodo.module:
                raiz = nodo.module.split(".")[0]
                (internas if raiz == PAQUETE else externas).add(nodo.module)
        elif isinstance(nodo, ast.Import):
            for alias in nodo.names:
                externas.add(alias.name.split(".")[0])

    return {
        "ruta": rel,
        "modulo": modulo,
        "proposito": proposito,
        "docstring": doc,
        "fuente": fuente,
        "lineas": len(fuente.splitlines()),
        "funciones": funciones,
        "clases": clases,
        "constantes": constantes,
        "internas": sorted(internas),
        "externas": sorted(e for e in externas if e not in ("__future__",)),
    }


def _grafo():
    """Analiza todo el paquete y calcula, además, los consumidores de cada módulo."""
    modulos = {rel: _analizar(rel, absoluta) for rel, absoluta in _modulos()}
    for datos in modulos.values():
        datos["consumidores"] = []
    por_nombre = {d["modulo"]: d for d in modulos.values()}
    for datos in modulos.values():
        for dep in datos["internas"]:
            objetivo = por_nombre.get(dep)
            if objetivo is not None and objetivo is not datos:
                objetivo["consumidores"].append(datos["modulo"])
    for datos in modulos.values():
        datos["consumidores"] = sorted(set(datos["consumidores"]))
    return modulos


def _capa_de(rel: str) -> str:
    partes = rel.split("/")
    if len(partes) == 2:
        return "workspace" if partes[1] == "workspace.py" else "raiz"
    return partes[1]


# =============================================================================================
# Generadores de bloques
# =============================================================================================
def gen_arbol() -> str:
    """Árbol real del paquete, con el tamaño de cada módulo."""
    omitir = {"__pycache__"}
    lineas = ["```"]
    base = os.path.join(RAIZ, PAQUETE)
    for actual, dirs, archivos in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in omitir)
        rel = os.path.relpath(actual, RAIZ)
        nivel = rel.count(os.sep)
        lineas.append("  " * nivel + os.path.basename(actual) + "/")
        for archivo in sorted(archivos):
            if archivo.endswith((".pyc", ".DS_Store")):
                continue
            ruta = os.path.join(actual, archivo)
            if archivo.endswith(".py"):
                n = len(_leer(ruta).splitlines())
                lineas.append("  " * (nivel + 1) + f"{archivo:24} {n:>4} líneas")
            else:
                lineas.append("  " * (nivel + 1) + archivo)
    lineas.append("```")
    return "\n".join(lineas)


def gen_inventario() -> str:
    """Tabla maestra: cada módulo con su propósito, tamaño, dependencias y consumidores."""
    modulos = _grafo()
    lineas = []
    for capa, titulo, regla in CAPAS:
        de_capa = [d for r, d in sorted(modulos.items()) if _capa_de(r) == capa]
        if not de_capa:
            continue
        lineas.append(f"\n#### {titulo} — `{capa}`\n")
        lineas.append(f"> {regla}\n")
        lineas.append("| Módulo | Líneas | Propósito | Depende de | Consumido por |")
        lineas.append("|---|---:|---|---|---|")
        for d in de_capa:
            internas = ", ".join(f"`{x.replace(PAQUETE + '.', '')}`" for x in d["internas"]) or "—"
            consumidores = ", ".join(
                f"`{x.replace(PAQUETE + '.', '')}`" for x in d["consumidores"]) or "—"
            lineas.append(f"| `{d['ruta'].replace(PAQUETE + '/', '')}` | {d['lineas']} | "
                          f"{d['proposito']} | {internas} | {consumidores} |")
    return "\n".join(lineas)


def gen_dependencias_externas() -> str:
    """Qué librería de terceros usa cada módulo y con qué política de degradación."""
    modulos = _grafo()
    stdlib = {
        "ast", "base64", "copy", "csv", "collections", "dataclasses", "difflib", "email",
        "html", "importlib", "io", "json", "os", "pathlib", "re", "shutil", "subprocess",
        "sys", "tempfile", "time", "typing", "unicodedata", "zipfile",
    }
    uso = {}
    for d in modulos.values():
        for ext in d["externas"]:
            if ext in stdlib:
                continue
            uso.setdefault(ext, []).append(d["ruta"].replace(PAQUETE + "/", ""))

    porque = {
        "openpyxl": ("Leer .xlsx/.xlsm sin Excel instalado.", "Opcional"),
        "docx": ("Escribir el .docx del Discovery (paquete `python-docx`).", "Opcional"),
        "pptx": ("Leer .pptx (paquete `python-pptx`).", "Opcional"),
        "pypdf": ("Extraer texto de PDF.", "Opcional"),
        "PyPDF2": ("Alternativa histórica a `pypdf`; se intenta si el primero falta.", "Opcional"),
        "pytesseract": ("OCR de imágenes; requiere además el binario `tesseract`.", "Opcional"),
        "PIL": ("Abrir imágenes para el OCR (paquete `Pillow`).", "Opcional"),
        "pillow_heif": ("Decodificar .heic/.heif.", "Opcional"),
        "yaml": ("Parsear .yaml/.yml (paquete `PyYAML`).", "Opcional"),
        "extract_msg": ("Leer correos .msg de Outlook.", "Opcional"),
        "mcp": ("SDK del servidor MCP. Requiere Python 3.10+.", "Obligatoria solo para el MCP"),
    }
    lineas = ["| Librería | Requerida por | Para qué | Política |", "|---|---|---|---|"]
    for lib in sorted(uso):
        detalle, politica = porque.get(lib, ("—", "Opcional"))
        modulos_txt = ", ".join(f"`{m}`" for m in sorted(set(uso[lib])))
        lineas.append(f"| `{lib}` | {modulos_txt} | {detalle} | {politica} |")
    lineas.append("\nToda librería marcada **Opcional** se importa dentro de la función que la usa, "
                  "nunca en la cabecera del módulo: importar el paquete no puede fallar por una "
                  "dependencia ausente, y su falta produce un aviso legible en vez de una excepción.")
    return "\n".join(lineas)


def gen_grafo_importaciones() -> str:
    """Diagrama de dependencias internas entre capas."""
    modulos = _grafo()
    aristas = set()
    for d in modulos.values():
        origen = _capa_de(d["ruta"])
        for dep in d["internas"]:
            rel_dep = dep.replace(".", "/") + ".py"
            destino = _capa_de(rel_dep if rel_dep in modulos else dep.replace(".", "/") + "/__init__.py")
            if destino == "raiz" and dep.endswith("workspace"):
                destino = "workspace"
            if origen != destino and destino not in ("raiz",):
                aristas.add((origen, destino))
    lineas = ["```mermaid", "graph TD"]
    etiqueta = {"common": "common<br/>citas · marcas · texto",
                "workspace": "workspace<br/>memoria en disco",
                "ingest": "ingest<br/>manifest · registry · pipeline · extractores",
                "knowledge": "knowledge<br/>schema · rubrica · scorer · dedup · validador",
                "render": "render<br/>ensamblador · docx · html · tablas · mermaid",
                "interfaces": "interfaces<br/>cli · mcp_server",
                "prompts": "prompts<br/>instrucciones de subagentes"}
    for capa in ("common", "workspace", "ingest", "knowledge", "render", "interfaces", "prompts"):
        lineas.append(f'    {capa}["{etiqueta.get(capa, capa)}"]')
    for origen, destino in sorted(aristas):
        lineas.append(f"    {origen} --> {destino}")
    lineas.append("```")
    return "\n".join(lineas)


def _seccion_modulo(d: dict, nivel: str = "####") -> str:
    """Ficha completa de un módulo: propósito, API, dependencias y código íntegro."""
    partes = [f"{nivel} `{d['ruta']}`\n"]
    partes.append(f"**Módulo:** `{d['modulo']}` · **Tamaño:** {d['lineas']} líneas\n")

    tabla = ["| Aspecto | Detalle |", "|---|---|"]
    tabla.append(f"| Propósito | {d['proposito'] or '—'} |")
    if d["clases"]:
        tabla.append("| Clases | " + ", ".join(f"`{c}`" for c in d["clases"]) + " |")
    if d["funciones"]:
        tabla.append("| Funciones públicas | " + ", ".join(f"`{f}`" for f in d["funciones"]) + " |")
    if d["constantes"]:
        tabla.append("| Constantes | " + ", ".join(f"`{c}`" for c in d["constantes"]) + " |")
    tabla.append("| Dependencias internas | "
                 + (", ".join(f"`{x}`" for x in d["internas"]) or "ninguna") + " |")
    tabla.append("| Dependencias externas | "
                 + (", ".join(f"`{x}`" for x in d["externas"]) or "solo stdlib") + " |")
    tabla.append("| Consumido por | "
                 + (", ".join(f"`{x}`" for x in d["consumidores"]) or "nadie (punto de entrada)")
                 + " |")
    partes.append("\n".join(tabla) + "\n")
    partes.append("```python\n" + d["fuente"].rstrip() + "\n```")
    return "\n".join(partes)


def _gen_codigo_capa(capa: str) -> str:
    modulos = _grafo()
    de_capa = [d for r, d in sorted(modulos.items()) if _capa_de(r) == capa]
    return "\n\n---\n\n".join(_seccion_modulo(d) for d in de_capa)


def gen_codigo_common() -> str:
    return _gen_codigo_capa("common")


def gen_codigo_workspace() -> str:
    return _gen_codigo_capa("workspace")


def gen_codigo_ingest() -> str:
    return _gen_codigo_capa("ingest")


def gen_codigo_knowledge() -> str:
    return _gen_codigo_capa("knowledge")


def gen_codigo_render() -> str:
    return _gen_codigo_capa("render")


def gen_codigo_interfaces() -> str:
    modulos = _grafo()
    de_capa = [d for r, d in sorted(modulos.items())
               if _capa_de(r) in ("interfaces", "raiz", "prompts")]
    return "\n\n---\n\n".join(_seccion_modulo(d) for d in de_capa)


def gen_plantilla_html() -> str:
    """La plantilla ejecutiva completa: es un entregable, no un detalle de implementación."""
    ruta = os.path.join(RAIZ, PAQUETE, "render", "assets", "executive.html")
    with open(ruta, "r", encoding="utf-8") as fh:
        contenido = fh.read()
    n = len(contenido.splitlines())
    return (f"**Archivo:** `{PAQUETE}/render/assets/executive.html` · **Tamaño:** {n} líneas\n\n"
            "```html\n" + contenido.rstrip() + "\n```")


def gen_pruebas() -> str:
    """La suite completa: fija el contrato de comportamiento que la reconstrucción debe cumplir."""
    ruta = os.path.join(RAIZ, "tests", "test_core.py")
    contenido = _leer(ruta)
    arbol = ast.parse(contenido)
    clases = []
    for nodo in arbol.body:
        if isinstance(nodo, ast.ClassDef):
            metodos = [n.name for n in nodo.body
                       if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
            doc = (ast.get_docstring(nodo) or "").split("\n")[0]
            clases.append((nodo.name, doc, metodos))
    total = sum(len(m) for _, _, m in clases)

    lineas = [f"**{total} pruebas** en {len(clases)} clases, sobre `unittest` de la stdlib "
              f"(sin dependencias de test).\n",
              "| Clase | Qué contrato fija | Pruebas |", "|---|---|---:|"]
    for nombre, doc, metodos in clases:
        lineas.append(f"| `{nombre}` | {doc or '—'} | {len(metodos)} |")
    lineas.append("\n<details>\n<summary>Código completo de la suite</summary>\n")
    lineas.append("```python\n" + contenido.rstrip() + "\n```")
    lineas.append("\n</details>")
    return "\n".join(lineas)


def gen_formatos() -> str:
    from discovery_agents.ingest.registry import FORMATOS
    por_extractor = {}
    for f in FORMATOS:
        por_extractor.setdefault(f.extractor, []).append(f)
    lineas = ["| Extractor | Extensiones | Dependencia opcional |", "|---|---|---|"]
    for extractor, formatos in sorted(por_extractor.items()):
        exts = ", ".join(f"`{f.extension}`" for f in formatos)
        requiere = sorted({f.requiere for f in formatos if f.requiere}) or ["—"]
        lineas.append(f"| `{extractor}` | {exts} | {', '.join(requiere)} |")
    lineas.append(f"\nTotal: **{len(FORMATOS)} extensiones** soportadas.\n")
    lineas.append("| Extensión | Extractor | Descripción |")
    lineas.append("|---|---|---|")
    for f in FORMATOS:
        lineas.append(f"| `{f.extension}` | `{f.extractor}` | {f.descripcion} |")
    return "\n".join(lineas)


def gen_schema() -> str:
    from discovery_agents.knowledge.schema import schema_vacio
    return "```json\n" + json.dumps(schema_vacio(), ensure_ascii=False, indent=2) + "\n```"


def gen_secciones() -> str:
    from discovery_agents.knowledge.schema import ORDEN_PARTES, PARTES, SECCIONES
    lineas = []
    for parte in ORDEN_PARTES:
        lineas.append(f"\n**{PARTES[parte]}**\n")
        lineas.append("| # | Sección | `id` | Slot de prosa | Claves del schema |")
        lineas.append("|---|---|---|---|---|")
        for i, s in enumerate([x for x in SECCIONES if x["parte"] == parte], start=1):
            slot = f"`{s['narrativa']}`" if s["narrativa"] else "—"
            claves = ", ".join(f"`{c}`" for c in s["claves"]) or "—"
            lineas.append(f"| {i} | {s['titulo']} | `{s['id']}` | {slot} | {claves} |")
    return "\n".join(lineas)


def gen_rubrica() -> str:
    from discovery_agents.knowledge.rubrica import RUBRICA
    lineas = ["| Bloque | `id` | Peso | Crítico | Preguntas | Obligatorias |",
              "|---|---|---:|---|---:|---:|"]
    for b in RUBRICA:
        oblig = sum(1 for p in b.preguntas if p.obligatoria)
        lineas.append(f"| {b.titulo} | `{b.id}` | {b.peso}% | {'Sí' if b.critico else 'No'} | "
                      f"{len(b.preguntas)} | {oblig} |")
    lineas.append("")
    for b in RUBRICA:
        lineas.append(f"\n**{b.titulo}** (`{b.id}`, peso {b.peso}%, "
                      f"{'crítico' if b.critico else 'no crítico'})\n")
        for p in b.preguntas:
            marca = "obligatoria" if p.obligatoria else "opcional"
            lineas.append(f"- `{p.clave}` — {p.texto} _({marca})_")
    return "\n".join(lineas)


def gen_tools() -> str:
    """Tools MCP leídas del código fuente, sin importar el SDK (que exige Python 3.10)."""
    ruta = os.path.join(RAIZ, PAQUETE, "interfaces", "mcp_server.py")
    arbol = ast.parse(_leer(ruta))
    lineas = ["| Tool | Parámetros | Devuelve | Qué hace |", "|---|---|---|---|"]
    total = 0
    detalles = []
    for nodo in arbol.body:
        if not isinstance(nodo, ast.FunctionDef):
            continue
        if not any(isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "tool"
                   for d in nodo.decorator_list):
            continue
        total += 1
        params = ", ".join(
            f"{a.arg}: {ast.unparse(a.annotation) if a.annotation else '?'}"
            for a in nodo.args.args) or "—"
        retorno = ast.unparse(nodo.returns) if nodo.returns else "?"
        doc = ast.get_docstring(nodo) or ""
        lineas.append(f"| `{nodo.name}` | {params} | `{retorno}` | {doc.split(chr(10))[0]} |")
        detalles.append(f"\n**`{nodo.name}`**\n\n```\n{doc.strip()}\n```")
    lineas.append(f"\nTotal: **{total} tools MCP**.")
    lineas.extend(detalles)
    return "\n".join(lineas)


def gen_prompts() -> str:
    from discovery_agents.prompts import cargar_prompt, listar_prompts
    partes = []
    for nombre in listar_prompts():
        partes.append(f"#### `{nombre}`\n\n```markdown\n{cargar_prompt(nombre).rstrip()}\n```")
    return "\n\n".join(partes)


def gen_configuracion_cliente() -> str:
    """Ficheros de configuración del cliente de razonamiento, verbatim."""
    partes = []
    for rel in [".vscode/mcp.json", ".github/copilot-instructions.md"]:
        ruta = os.path.join(RAIZ, rel)
        if not os.path.exists(ruta):
            continue
        lenguaje = "json" if rel.endswith(".json") else "markdown"
        partes.append(f"**`{rel}`**\n\n```{lenguaje}\n{_leer(ruta).rstrip()}\n```")
    chatmodes = os.path.join(RAIZ, ".github", "chatmodes")
    if os.path.isdir(chatmodes):
        for archivo in sorted(os.listdir(chatmodes)):
            if archivo.endswith(".md"):
                contenido = _leer(os.path.join(chatmodes, archivo))
                partes.append(f"**`.github/chatmodes/{archivo}`**\n\n"
                              f"```markdown\n{contenido.rstrip()}\n```")
    return "\n\n".join(partes)


def gen_requisitos() -> str:
    ruta = os.path.join(RAIZ, "requirements.txt")
    return "```\n" + _leer(ruta).rstrip() + "\n```"


GENERADORES = {
    "arbol": gen_arbol,
    "inventario": gen_inventario,
    "grafo": gen_grafo_importaciones,
    "dependencias": gen_dependencias_externas,
    "requisitos": gen_requisitos,
    "formatos": gen_formatos,
    "schema": gen_schema,
    "secciones": gen_secciones,
    "rubrica": gen_rubrica,
    "tools": gen_tools,
    "codigo_common": gen_codigo_common,
    "codigo_workspace": gen_codigo_workspace,
    "codigo_ingest": gen_codigo_ingest,
    "codigo_knowledge": gen_codigo_knowledge,
    "codigo_render": gen_codigo_render,
    "codigo_interfaces": gen_codigo_interfaces,
    "plantilla_html": gen_plantilla_html,
    "prompts": gen_prompts,
    "config_cliente": gen_configuracion_cliente,
    "pruebas": gen_pruebas,
}


def sincronizar(verificar: bool = False) -> int:
    with open(BLUEPRINT, "r", encoding="utf-8") as fh:
        original = fh.read()

    actualizado = original
    for nombre, generador in GENERADORES.items():
        actualizado = _sustituir(actualizado, nombre, generador())

    if actualizado == original:
        print("Blueprint sincronizado con el código.")
        return 0

    if verificar:
        print("DESINCRONIZADO: el Blueprint no refleja el código actual.\n"
              "Ejecuta `python tools/sync_docs.py` para regenerarlo.", file=sys.stderr)
        return 1

    with open(BLUEPRINT, "w", encoding="utf-8") as fh:
        fh.write(actualizado)
    print(f"Blueprint actualizado ({len(GENERADORES)} bloques regenerados, "
          f"{len(actualizado.splitlines())} líneas).")
    return 0


if __name__ == "__main__":
    raise SystemExit(sincronizar(verificar="--check" in sys.argv))
