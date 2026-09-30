"""Diagramador determinista: Mermaid desde el schema tipado (0 tokens).

El LLM nunca escribe sintaxis Mermaid (caro y propenso a errores): la IA decide el contenido
(JSON pequeño) y estas plantillas deciden el dibujo. Mermaid renderiza nativo en GitHub,
VS Code y SharePoint moderno sin binarios.
"""
from __future__ import annotations

import re
from collections import OrderedDict
from typing import Dict, List


def _nid(texto: object) -> str:
    """ID de nodo Mermaid seguro."""
    s = re.sub(r"[^A-Za-z0-9]", "_", str(texto or "")).strip("_")
    return s or "nodo"


def _lbl(texto: object) -> str:
    """Etiqueta segura (sin comillas/saltos que rompan la sintaxis)."""
    return str(texto or "").replace('"', "'").replace("\n", " ").strip()


def flujo_datos(fuentes: List[dict], nombre_producto: str = "Producto de Datos") -> str:
    """Flujo estándar: servidores on-prem → réplica → Data Factory → Medallion → consumo."""
    servidores = list(OrderedDict(
        (str(f.get("servidor", "")).strip(), None) for f in fuentes if str(f.get("servidor", "")).strip()
    ).keys())
    lineas = ["flowchart LR"]
    lineas.append('  subgraph OnPrem["Fuentes on-premise"]')
    if servidores:
        for srv in servidores:
            tablas = [str(f.get("tabla", "")) for f in fuentes
                      if str(f.get("servidor", "")).strip() == srv]
            lineas.append(f'    {_nid(srv)}["{_lbl(srv)}<br/>{_lbl(", ".join(tablas[:4]))}"]')
    else:
        lineas.append('    SRC["Fuentes (PENDIENTE)"]')
    lineas.append("  end")
    lineas.append('  REPL["Réplica no transaccional<br/>(evita bloqueos)"]')
    lineas.append('  ADF["Azure Data Factory"]')
    lineas.append('  subgraph Medallion["Lakehouse — Medallion"]')
    lineas.append('    BR["Bronce"] --> PL["Plata"] --> OR["Oro"]')
    lineas.append("  end")
    lineas.append(f'  CONS["Consumo<br/>{_lbl(nombre_producto)}"]')
    for srv in (servidores or ["SRC"]):
        lineas.append(f"  {_nid(srv)} --> REPL")
    lineas.append("  REPL --> ADF --> BR")
    lineas.append("  OR --> CONS")
    return _bloque(lineas)


def fuentes_por_servidor(fuentes: List[dict]) -> str:
    """Inventario visual: subgraph por servidor con sus tablas y volumetría."""
    lineas = ["flowchart TB"]
    por_srv: Dict[str, List[dict]] = OrderedDict()
    for f in fuentes:
        por_srv.setdefault(str(f.get("servidor", "Servidor PENDIENTE")).strip() or "Servidor PENDIENTE",
                           []).append(f)
    if not por_srv:
        lineas.append('  X["Sin fuentes registradas"]')
    for srv, fs in por_srv.items():
        lineas.append(f'  subgraph {_nid(srv)}["{_lbl(srv)}"]')
        for f in fs:
            extra = f" — {f.get('volumetria')}" if str(f.get("volumetria", "")).strip() else ""
            cols = f.get("columnas")
            n_cols = len(cols) if isinstance(cols, list) else (1 if str(cols or "").strip() else 0)
            extra += f" · {n_cols} col." if n_cols else ""
            sensible = " 🔒" if str(f.get("sensible", "")).strip().lower().startswith(("sí", "si")) else ""
            lineas.append(f'    {_nid(srv)}_{_nid(f.get("tabla"))}["{_lbl(f.get("tabla"))}{_lbl(extra)}{sensible}"]')
        lineas.append("  end")
    return _bloque(lineas)


def datamesh(arquetipos: List[dict], nombre_producto: str = "Producto de Datos") -> str:
    """Mapa Data Mesh: dominios → productos derivables del caso de uso."""
    lineas = ["flowchart LR", f'  CORE(("{_lbl(nombre_producto)}"))']
    por_dominio: Dict[str, List[dict]] = OrderedDict()
    for a in arquetipos:
        por_dominio.setdefault(str(a.get("dominio", "Dominio")).strip() or "Dominio", []).append(a)
    if not por_dominio:
        lineas.append('  P["Arquetipos PENDIENTES"]')
        lineas.append("  CORE --> P")
    for dom, arqs in por_dominio.items():
        lineas.append(f'  subgraph {_nid(dom)}["{_lbl(dom)}"]')
        for a in arqs:
            lineas.append(f'    {_nid(dom)}_{_nid(a.get("nombre"))}["{_lbl(a.get("nombre"))}"]')
        lineas.append("  end")
        for a in arqs:
            lineas.append(f"  CORE --> {_nid(dom)}_{_nid(a.get('nombre'))}")
    return _bloque(lineas)


def entidades_preliminar(entidades: List[dict]) -> str:
    """Boceto ER preliminar (no es el diseño: ese pertenece a la etapa de Diseño del flujo)."""
    lineas = ["erDiagram"]
    nombres = {_nid(e.get("nombre")) for e in entidades if str(e.get("nombre", "")).strip()}
    if not nombres:
        return _bloque(['flowchart LR', '  X["Entidades PENDIENTES"]'])
    for e in entidades:
        nombre = _nid(e.get("nombre"))
        if not str(e.get("nombre", "")).strip():
            continue
        for rel in (e.get("relaciones") or []):
            destino = _nid(rel)
            if destino in nombres and destino != nombre:
                lineas.append(f'  {nombre} ||--o{{ {destino} : "se relaciona"')
    if len(lineas) == 1:  # entidades sin relaciones declaradas: listarlas sueltas
        for e in entidades:
            if str(e.get("nombre", "")).strip():
                lineas.append(f"  {_nid(e.get('nombre'))} {{ }}")
    return _bloque(lineas)


def generar_diagramas(discovery: dict, caso: str = "") -> Dict[str, str]:
    """Genera todos los diagramas. Devuelve {nombre_archivo: contenido_markdown}."""
    nombre = caso or "Producto de Datos"
    fuentes = [f for f in discovery.get("fuentes", []) if isinstance(f, dict)]
    arquetipos = [a for a in discovery.get("arquetipos_datamesh", []) if isinstance(a, dict)]
    entidades = [e for e in discovery.get("entidades", []) if isinstance(e, dict)]
    return {
        "flujo_datos.md": f"# Flujo de datos — {nombre}\n\n" + flujo_datos(fuentes, nombre),
        "fuentes_por_servidor.md": f"# Fuentes por servidor — {nombre}\n\n" + fuentes_por_servidor(fuentes),
        "datamesh.md": f"# Arquetipos Data Mesh — {nombre}\n\n" + datamesh(arquetipos, nombre),
        "entidades_preliminar.md": (
            f"# Entidades preliminares — {nombre}\n\n"
            "> ⚠️ Boceto del Discovery. El modelo de datos detallado pertenece a la etapa de Diseño.\n\n"
            + entidades_preliminar(entidades)
        ),
    }


def _bloque(lineas: List[str]) -> str:
    return "```mermaid\n" + "\n".join(lineas) + "\n```\n"


# ---------------------------------------------------------------------------------------------
# Lectura en prosa de cada diagrama
# ---------------------------------------------------------------------------------------------
def describir_diagrama(nombre: str, discovery: dict) -> str:
    """Lo que el diagrama dice, en palabras.

    Mermaid se renderiza en la web y en el markdown, pero dentro de un .docx es solo texto: el
    lector encontraba veinte líneas de `flowchart LR` que no le decían nada. La descripción se
    genera del mismo dato que el diagrama, así que no puede contradecirlo, y sirve además a quien
    lea el documento con un lector de pantalla.
    """
    fuentes = [f for f in discovery.get("fuentes", []) if isinstance(f, dict)]
    clave = nombre.replace(".md", "")

    if clave == "flujo_datos":
        return _prosa_flujo(fuentes)
    if clave == "fuentes_por_servidor":
        return _prosa_servidores(fuentes)
    if clave == "datamesh":
        return _prosa_datamesh([a for a in discovery.get("arquetipos_datamesh", [])
                                if isinstance(a, dict)])
    if clave == "entidades_preliminar":
        return _prosa_entidades([e for e in discovery.get("entidades", [])
                                 if isinstance(e, dict)])
    return ""


def _por_servidor(fuentes: List[dict]) -> Dict[str, List[dict]]:
    agrupadas: Dict[str, List[dict]] = {}
    for f in fuentes:
        if not str(f.get("tabla", "")).strip():
            continue
        servidor = str(f.get("servidor", "")).strip() or "servidor por definir"
        agrupadas.setdefault(servidor, []).append(f)
    return agrupadas


def _prosa_flujo(fuentes: List[dict]) -> str:
    agrupadas = _por_servidor(fuentes)
    if not agrupadas:
        return ("El flujo no puede describirse todavía: no se registraron fuentes de datos en el "
                "Discovery.")
    origenes = ", ".join(f"{srv} ({len(fs)} tabla(s))" for srv, fs in agrupadas.items())
    return (f"Los datos salen de {origenes}. Se leen contra una réplica no transaccional para no "
            f"bloquear los sistemas en producción, se orquestan con Azure Data Factory y aterrizan "
            f"en la arquitectura medallón —Bronce, Plata y Oro— desde donde los consumen los "
            f"usuarios del producto.")


def _prosa_servidores(fuentes: List[dict]) -> str:
    agrupadas = _por_servidor(fuentes)
    if not agrupadas:
        return "No se registraron servidores de origen en el Discovery."
    partes = []
    for servidor, fs in agrupadas.items():
        tablas = ", ".join(str(f.get("tabla")) for f in fs)
        sensibles = [f for f in fs
                     if str(f.get("sensible", "")).strip().lower().startswith(("sí", "si"))]
        detalle = f"{servidor} aporta {len(fs)} tabla(s): {tablas}"
        if sensibles:
            detalle += f" — {len(sensibles)} con datos sensibles"
        partes.append(detalle)
    return ". ".join(partes) + "."


def _prosa_datamesh(arquetipos: List[dict]) -> str:
    if not arquetipos:
        return "No se propusieron arquetipos Data Mesh adicionales en este Discovery."
    partes = [f"{a.get('nombre')} (dominio {a.get('dominio') or 'por definir'})"
              for a in arquetipos if str(a.get("nombre", "")).strip()]
    return ("A partir de este producto se identificaron "
            f"{len(partes)} arquetipo(s) reutilizable(s): " + "; ".join(partes) + ".")


def _prosa_entidades(entidades: List[dict]) -> str:
    if not entidades:
        return "No se bosquejaron entidades preliminares en este Discovery."
    nombres = [str(e.get("nombre")) for e in entidades if str(e.get("nombre", "")).strip()]
    return (f"El boceto preliminar contempla {len(nombres)} entidad(es): " + ", ".join(nombres)
            + ". El modelo de datos detallado corresponde a la etapa de Diseño, no al Discovery.")
