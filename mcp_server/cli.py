"""CLI determinista para operar el workspace sin MCP ni LLM (Python 3.9+).

Uso:
    python -m mcp_server.cli manifest    inputs/<caso>           # inventario clasificado
    python -m mcp_server.cli evidencia   inputs/<caso>           # extrae y persiste; imprime índice
    python -m mcp_server.cli get         <caso> <E0xx> [chunk]   # contenido bajo demanda
    python -m mcp_server.cli pendientes  <caso>                  # transcripciones sin destilar
    python -m mcp_server.cli consolidar  <caso>                  # une destilados + conflictos
    python -m mcp_server.cli score       <caso>                  # veredicto determinista
    python -m mcp_server.cli ensamblar   <caso>                  # doc final + brechas + artefactos
    python -m mcp_server.cli rubrica                             # rúbrica de preguntas poderosas
    python -m mcp_server.cli schema                              # contrato tipado del Constructor

Todo el trabajo determinista (lo que ahorra tokens) es verificable aquí sin Copilot. Las fases
de razonamiento (destilar/construir/redactar/criticar) las hacen los subagentes en Copilot,
escribiendo su resultado al workspace vía save_state.
"""
from __future__ import annotations

import json
import os
import sys
from typing import List

from . import consolidator, workspace
from .artefactos.mermaid import generar_diagramas
from .artefactos.tablas import generar_tablas
from .discovery.assembler import ensamblar_discovery
from .discovery.rubric import rubrica_serializable
from .discovery.scorer import score_discovery
from .discovery.template import schema_vacio
from .extractors.manifest import build_manifest
from .pipeline import construir_evidencia


def _print_json(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv: List[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]

    if cmd == "manifest":
        _print_json(build_manifest(argv[1]))
        return 0

    if cmd == "evidencia":
        _print_json(construir_evidencia(argv[1]))
        return 0

    if cmd == "get":
        chunk = int(argv[3]) if len(argv) > 3 else 0
        _print_json(workspace.get_evidence_chunk(argv[1], argv[2], chunk))
        return 0

    if cmd == "pendientes":
        _print_json({"pendientes": workspace.evidencias_sin_destilar(argv[1])})
        return 0

    if cmd == "consolidar":
        _print_json(consolidator.consolidar(argv[1]))
        return 0

    if cmd == "rubrica":
        _print_json(rubrica_serializable())
        return 0

    if cmd == "schema":
        _print_json(schema_vacio())
        return 0

    if cmd == "score":
        caso = argv[1]
        discovery = workspace.load_json(caso, "30_discovery.json")
        if discovery is None:
            print(f"No existe work/{caso}/30_discovery.json (el Constructor debe correr primero).")
            return 1
        score = score_discovery(discovery)
        workspace.save_json(caso, "55_score.json", score)
        print(f"Veredicto: {score['veredicto']} ({score['completitud_total']}%) — "
              f"{score['n_brechas']} brechas")
        for c in score["condiciones_para_avanzar"]:
            print(f"  · {c}")
        return 0

    if cmd == "ensamblar":
        caso = argv[1]
        discovery = workspace.load_json(caso, "30_discovery.json")
        if discovery is None:
            print(f"No existe work/{caso}/30_discovery.json (el Constructor debe correr primero).")
            return 1
        redaccion = workspace.load_text(caso, "60_redaccion.md")
        inconsistencias = workspace.load_json(caso, "60_inconsistencias.json")
        resultado = ensamblar_discovery(discovery, caso_de_uso=caso, redaccion_md=redaccion)

        workspace.save_text(caso, "outputs/discovery_final.md", resultado["markdown"])
        workspace.save_text(caso, "outputs/brechas.md", resultado["brechas_markdown"])
        workspace.save_json(caso, "outputs/veredicto.json", resultado["veredicto"])
        workspace.save_json(caso, "55_score.json", resultado["score"])
        for nombre, contenido in generar_diagramas(discovery, caso).items():
            workspace.save_text(caso, os.path.join("outputs", "diagramas", nombre), contenido)
        for nombre, contenido in generar_tablas(discovery, inconsistencias).items():
            workspace.save_text(caso, os.path.join("outputs", "tablas", nombre), contenido)

        v = resultado["veredicto"]
        print(f"Veredicto: {v['veredicto']} ({v['completitud_total']}%) — {v['n_brechas']} brechas"
              + (" — narrativa del Redactor incluida" if redaccion else " — sin narrativa (60_redaccion.md)"))
        print(f"Entregables en work/{caso}/outputs/ (doc, brechas, veredicto, diagramas/, tablas/)")
        return 0

    print(f"Comando desconocido: {cmd}\n{__doc__}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
