"""CLI determinista para operar el workspace sin MCP ni LLM (Python 3.9+).

Uso:
    python -m discovery_agents manifest    inputs/<caso>             # inventario clasificado
    python -m discovery_agents evidencia   inputs/<caso> [caso]      # extrae y persiste; imprime índice
    python -m discovery_agents get         <caso> <E0xx> [chunk]     # contenido bajo demanda
    python -m discovery_agents pendientes  <caso>                    # transcripciones sin destilar
    python -m discovery_agents consolidar  <caso>                    # une destilados, dedup + conflictos
    python -m discovery_agents validar     <caso>                    # forma de 30_discovery.json
    python -m discovery_agents score       <caso>                    # veredicto determinista
    python -m discovery_agents ensamblar   <caso> [nombre]           # Word + HTML + brechas + artefactos
    python -m discovery_agents formatos                              # extensiones soportadas
    python -m discovery_agents rubrica                               # rúbrica de preguntas poderosas
    python -m discovery_agents schema                                # contrato tipado del Constructor

Todo el trabajo determinista (lo que ahorra tokens) es verificable aquí sin cliente MCP ni LLM.
Las fases de razonamiento (destilar/construir/redactar/criticar) las ejecutan los subagentes,
escribiendo su resultado al workspace vía save_state.
"""
from __future__ import annotations

import json
import sys
from typing import List, Optional

from .. import workspace
from ..ingest.manifest import build_manifest
from ..ingest.pipeline import construir_evidencia
from ..ingest.registry import formatos_soportados
from ..knowledge import consolidador
from ..knowledge.rubrica import rubrica_serializable
from ..knowledge.schema import schema_vacio
from ..knowledge.scorer import score_discovery
from ..knowledge.validador import validar_discovery
from ..render.entregables import construir_entregables

# comando → (mínimo de argumentos posicionales, plantilla de uso para el mensaje de error)
_ARIDAD = {
    "manifest": (1, "manifest <carpeta_de_insumos>"),
    "evidencia": (1, "evidencia <carpeta_de_insumos> [nombre_del_caso]"),
    "get": (2, "get <caso> <E0xx> [chunk]"),
    "pendientes": (1, "pendientes <caso>"),
    "consolidar": (1, "consolidar <caso>"),
    "validar": (1, "validar <caso>"),
    "score": (1, "score <caso>"),
    "ensamblar": (1, "ensamblar <caso> [nombre del caso de uso]"),
    "formatos": (0, "formatos"),
    "rubrica": (0, "rubrica"),
    "schema": (0, "schema"),
}


def _print_json(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _arg(argv: List[str], i: int, default: str = "") -> str:
    return argv[i] if len(argv) > i else default


def main(argv: List[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd, args = argv[0], argv[1:]

    if cmd not in _ARIDAD:
        print(f"Comando desconocido: {cmd}\n{__doc__}")
        return 2

    minimo, uso = _ARIDAD[cmd]
    if len(args) < minimo:
        # Un IndexError crudo no le dice a nadie qué faltaba.
        print(f"Faltan argumentos para '{cmd}'.\n  Uso: python -m discovery_agents {uso}")
        return 2

    if cmd == "manifest":
        _print_json(build_manifest(args[0]))
        return 0

    if cmd == "evidencia":
        # El nombre del caso es opcional y por defecto es el de la carpeta: la tool MCP siempre lo
        # aceptó y la CLI no, de modo que el mismo insumo producía workspaces distintos según por
        # dónde entrara.
        _print_json(construir_evidencia(args[0], caso=_arg(args, 1)))
        return 0

    if cmd == "get":
        chunk_txt = _arg(args, 2, "0")
        if not chunk_txt.lstrip("-").isdigit():
            print(f"El chunk debe ser un número entero, no {chunk_txt!r}.")
            return 2
        _print_json(workspace.get_evidence_chunk(args[0], args[1], int(chunk_txt)))
        return 0

    if cmd == "pendientes":
        _print_json({"pendientes": workspace.evidencias_sin_destilar(args[0])})
        return 0

    if cmd == "consolidar":
        _print_json(consolidador.consolidar(args[0]))
        return 0

    if cmd == "formatos":
        _print_json(formatos_soportados())
        return 0

    if cmd == "rubrica":
        _print_json(rubrica_serializable())
        return 0

    if cmd == "schema":
        _print_json(schema_vacio())
        return 0

    if cmd == "validar":
        discovery = _cargar_discovery(args[0])
        if discovery is None:
            return 1
        informe = validar_discovery(discovery)
        _print_json(informe)
        return 0 if informe["valido"] else 1

    if cmd == "score":
        discovery = _cargar_discovery(args[0])
        if discovery is None:
            return 1
        score = score_discovery(discovery)
        workspace.save_json(args[0], "55_score.json", score)
        workspace.append_metric(args[0], "scoring", {
            "veredicto": score["veredicto"], "completitud": score["completitud_total"],
        })
        print(f"Veredicto: {score['veredicto']} ({score['completitud_total']}%) — "
              f"{score['n_brechas']} brechas")
        for c in score["condiciones_para_avanzar"]:
            print(f"  · {c}")
        return 0

    if cmd == "ensamblar":
        # Fuente única de verdad: la misma función que usa la tool MCP assemble.
        resultado = construir_entregables(args[0], caso_de_uso=_arg(args, 1))
        if "error" in resultado:
            print(resultado["error"])
            for detalle in resultado.get("detalles", []):
                print(f"  · {detalle}")
            return 1
        v = resultado["veredicto"]
        print(f"Veredicto: {v['veredicto']} ({v['completitud_total']}%) — {v['n_brechas']} brechas, "
              f"{v['n_temas_faltantes']} temas faltantes"
              + (" — narrativa incluida" if resultado["narrativa_incluida"]
                 else " — sin narrativa (60_redaccion.json)"))
        print(f"Fidelidad: {resultado['fidelidad']['cobertura_pct']}% de cobertura de evidencia")
        if not resultado["docx_generado"]:
            print("Aviso: .docx omitido — instala python-docx para generarlo.")
        print(f"Entregables ({len(resultado['archivos_generados'])}) en work/{args[0]}/outputs/")
        return 0

    return 2  # inalcanzable: la aridad ya filtró los comandos válidos


def _cargar_discovery(caso: str) -> Optional[dict]:
    discovery = workspace.load_json(caso, "30_discovery.json")
    if discovery is None:
        print(f"No existe work/{caso}/30_discovery.json (el Constructor debe correr primero).")
    return discovery


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
