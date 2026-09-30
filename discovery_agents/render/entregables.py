"""Ensamblado unificado de TODOS los entregables (0 tokens) — fuente única de verdad.

Esta función es el ÚNICO camino de ensamblado: la CLI y la tool MCP la llaman por igual y por
tanto no pueden divergir. Si cada interfaz tuviera su propio pipeline, una de las dos acabaría
produciendo un entregable inferior sin que nadie lo notara. Pasos:

  1. Rellena `fecha_discovery` desde el manifiesto (determinista) si el Constructor la dejó vacía.
  2. Verifica fidelidad (citas [E00x] reales contra el índice) → 65_fidelidad.json.
  3. Ensambla el documento (md + brechas + veredicto + score + temas faltantes).
  4. Genera diagramas Mermaid y matrices auxiliares.
  5. Exporta el documento Word (.docx) — narrativa-first.
  6. Exporta el Resumen Ejecutivo HTML standalone.

Devuelve un resumen compacto (veredicto, fidelidad, archivos). El contenido NO viaja por el chat.
"""
from __future__ import annotations

import os
from typing import Optional

from .. import workspace
from .ensamblador import ensamblar_discovery
from ..knowledge.fidelidad import verificar_fidelidad
from ..knowledge.validador import validar_discovery
from .docx_export import docx_disponible, exportar_docx
from .html_export import exportar_html
from .mermaid import generar_diagramas
from .tablas import generar_tablas


def construir_entregables(caso: str, caso_de_uso: str = "") -> dict:
    """Genera todos los entregables en work/<caso>/outputs/. Fuente única para CLI y MCP.

    Returns:
        {veredicto, fidelidad, narrativa_incluida, docx_generado, archivos_generados: [...]}
        o {error: "..."} si falta el discovery.
    """
    discovery = workspace.load_json(caso, "30_discovery.json")
    if discovery is None:
        return {"error": "No existe 30_discovery.json: el Constructor debe correr primero."}

    # (0) Validación de forma. Un Discovery con `fuentes` aplanado a texto no falla al renderizar:
    # produce un documento sin tabla de fuentes, sin diagrama y sin trazabilidad, y nadie se entera
    # hasta que alguien lo lee. Mejor detenerse aquí con un mensaje que diga exactamente qué pasó.
    informe = validar_discovery(discovery)
    if not informe["valido"]:
        return {
            "error": "El Discovery no respeta el contrato tipado del schema; corrígelo y reintenta.",
            "detalles": informe["errores"],
            "avisos": informe["avisos"],
        }

    caso_de_uso = caso_de_uso or discovery.get("nombre_caso_uso") or caso
    redaccion = _cargar_redaccion(caso)
    inconsistencias = workspace.load_json(caso, "60_inconsistencias.json")
    critica = workspace.load_json(caso, "50_critica.json")
    index = workspace.load_json(caso, os.path.join("10_evidence", "index.json"))

    # (1) Fecha del Discovery: la rellena Python desde el manifiesto si no vino del Constructor.
    if not str(discovery.get("fecha_discovery", "")).strip():
        fecha = _fecha_desde_manifest(caso)
        if fecha:
            discovery["fecha_discovery"] = fecha

    # Mensajes clave del Resumen Ejecutivo: el Redactor puede aportarlos en 60_inconsistencias.json.
    if not discovery.get("mensajes_clave") and isinstance(inconsistencias, dict):
        msgs = inconsistencias.get("mensajes_clave")
        if msgs:
            discovery["mensajes_clave"] = msgs

    # (2) Fidelidad (sin inventar): citas reales contra el índice de evidencia.
    fidelidad = verificar_fidelidad(discovery, _prosa_plana(redaccion), index)
    workspace.save_json(caso, "65_fidelidad.json", fidelidad)

    # (3) Ensamblado del documento (markdown + brechas + veredicto + score + temas faltantes).
    resultado = ensamblar_discovery(discovery, caso_de_uso=caso_de_uso, redaccion=redaccion,
                                    inconsistencias=inconsistencias, fidelidad=fidelidad,
                                    critica=critica)
    discovery["temas_faltantes"] = resultado["temas_faltantes"]  # que los artefactos lo reflejen
    score = resultado["score"]

    generados = []
    generados.append(workspace.save_text(caso, "outputs/discovery_final.md", resultado["markdown"]))
    generados.append(workspace.save_text(caso, "outputs/brechas.md", resultado["brechas_markdown"]))
    generados.append(workspace.save_json(caso, "outputs/veredicto.json", resultado["veredicto"]))
    workspace.save_json(caso, "55_score.json", score)

    # (4) Diagramas + matrices.
    diagramas = generar_diagramas(discovery, caso_de_uso)
    for nombre, contenido in diagramas.items():
        generados.append(workspace.save_text(caso, os.path.join("outputs", "diagramas", nombre), contenido))
    for nombre, contenido in generar_tablas(discovery, inconsistencias).items():
        generados.append(workspace.save_text(caso, os.path.join("outputs", "tablas", nombre), contenido))

    # (5) Word (.docx) — degrada con gracia si falta python-docx.
    docx_path = os.path.join(workspace.work_dir(caso), "outputs", "discovery_final.docx")
    docx_ok = exportar_docx(docx_path, discovery, caso=caso_de_uso, score=score,
                            redaccion=redaccion, fidelidad=fidelidad, diagramas=diagramas,
                            secciones_omitidas=resultado["secciones_omitidas"])
    if docx_ok:
        generados.append(docx_path)

    # (6) Resumen Ejecutivo HTML standalone (stdlib puro: siempre disponible).
    html_path = os.path.join(workspace.work_dir(caso), "outputs", "resumen_ejecutivo.html")
    generados.append(exportar_html(html_path, discovery, caso=caso_de_uso, score=score,
                                   fidelidad=fidelidad, inconsistencias=inconsistencias))

    workspace.append_metric(caso, "ensamblado", {
        "archivos": len(generados), "docx": bool(docx_ok), "html": True,
        "cobertura_pct": fidelidad.get("cobertura_pct", 0),
    })

    return {
        "veredicto": resultado["veredicto"],
        "fidelidad": {"cobertura_pct": fidelidad.get("cobertura_pct", 0)},
        "avisos_de_validacion": informe["avisos"],
        "secciones_omitidas": resultado["secciones_omitidas"],
        "narrativa_incluida": bool(redaccion),
        "docx_generado": bool(docx_ok),
        "docx_disponible": docx_disponible(),
        "archivos_generados": generados,
    }


def _cargar_redaccion(caso: str) -> Optional[dict]:
    """Prosa del Redactor, con el contrato actual o con el anterior.

    El contrato vigente es `60_redaccion.json`, que indexa la prosa por sección para que el
    ensamblador pueda fusionarla con los datos de esa misma sección. Un `60_redaccion.md` de antes
    se sigue aceptando y se reparte por sus encabezados: cambiar el contrato no debe invalidar el
    trabajo ya hecho.
    """
    datos = workspace.load_json(caso, "60_redaccion.json")
    if isinstance(datos, dict):
        return datos
    md = workspace.load_text(caso, "60_redaccion.md")
    return {"markdown": md} if md else None


def _prosa_plana(redaccion: Optional[dict]) -> str:
    """Toda la prosa concatenada, para que el verificador de fidelidad la audite de una vez."""
    if not redaccion:
        return ""
    if "markdown" in redaccion:
        return str(redaccion["markdown"])
    secciones = redaccion.get("secciones", redaccion)
    return "\n\n".join(str(v) for v in secciones.values() if isinstance(v, str))


def _fecha_desde_manifest(caso: str) -> str:
    """Deriva la fecha del Discovery del manifiesto: rango de fechas de modificación de insumos.

    Determinista y sin tokens. Formatea 'YYYY-MM-DD' o 'YYYY-MM-DD a YYYY-MM-DD' si abarca varios días.
    """
    manifest = workspace.load_json(caso, "00_manifest.json")
    if not manifest:
        return ""
    fechas = sorted({str(it.get("modificado", ""))[:10]
                     for it in manifest.get("items", []) if str(it.get("modificado", "")).strip()})
    fechas = [f for f in fechas if f]
    if not fechas:
        return ""
    return fechas[-1] if len(fechas) == 1 else f"{fechas[0]} a {fechas[-1]}"
