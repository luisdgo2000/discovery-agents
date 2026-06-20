"""System prompts de los subagentes de razonamiento.

Se cargan desde los .md hermanos y se exponen como MCP *prompts* para que sean una sola fuente
de verdad, reutilizable desde GitHub Copilot y otros clientes MCP. Mantenerlos cortos y enfocados es
parte de la estrategia de eficiencia de tokens.
"""
from __future__ import annotations

import os
from typing import Dict, List

_DIR = os.path.dirname(__file__)

# nombre lógico -> archivo
PROMPTS: Dict[str, str] = {
    "destilador-transcripciones": "destilador.md",
    "constructor-discovery": "constructor.md",
    "generador-hipotesis": "hipotesis.md",
    "critico-brechas": "critico.md",
    "redactor-experto": "redactor.md",
}


def cargar_prompt(nombre: str) -> str:
    archivo = PROMPTS.get(nombre)
    if not archivo:
        raise KeyError(f"Prompt desconocido: {nombre}. Disponibles: {list(PROMPTS)}")
    with open(os.path.join(_DIR, archivo), "r", encoding="utf-8") as fh:
        return fh.read()


def listar_prompts() -> List[str]:
    return list(PROMPTS.keys())
