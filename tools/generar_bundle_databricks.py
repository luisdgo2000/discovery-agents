"""Regenerador determinista del bundle de transporte para Databricks (0 tokens, sin dependencias).

El bundle (`discovery-agents-databricks.py`) es un EMPAQUETADOR: un notebook de Databricks que, al
ejecutarse, reconstruye el proyecto archivo por archivo (como descomprimir un .zip). No ejecuta los
agentes; solo transporta el proyecto a un entorno con GitHub Copilot + MCP.

Este script lo **genera desde la fuente**, de modo que el bundle nunca vuelva a quedar desactualizado
a mano: recorre el repo, excluye lo que es runtime/derivado, y embebe cada archivo en base64 (robusto
para texto y binario por igual). Uso:

    python tools/generar_bundle_databricks.py

Regenera `discovery-agents-databricks.py` en la raíz del repo.
"""
from __future__ import annotations

import base64
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, "discovery-agents-databricks.py")

# Carpetas/archivos que NO se empaquetan (runtime, derivados, control de versiones, el propio bundle).
EXCLUIR_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", "work", "inputs",
                ".vscode-test"}
EXCLUIR_FILES = {".DS_Store", "Thumbs.db", os.path.basename(SALIDA)}
EXCLUIR_EXT = {".pyc", ".pyo"}


def _incluir(rel: str) -> bool:
    partes = rel.split(os.sep)
    if any(p in EXCLUIR_DIRS for p in partes):
        return False
    base = os.path.basename(rel)
    if base in EXCLUIR_FILES or base.startswith("~$"):
        return False
    return os.path.splitext(base)[1].lower() not in EXCLUIR_EXT


def _recolectar() -> list:
    archivos = []
    for dirpath, dirnames, filenames in os.walk(RAIZ):
        dirnames[:] = [d for d in dirnames if d not in EXCLUIR_DIRS]
        for nombre in filenames:
            ruta = os.path.join(dirpath, nombre)
            rel = os.path.relpath(ruta, RAIZ)
            if _incluir(rel):
                archivos.append(rel)
    return sorted(archivos)


_HEADER = '''# Databricks notebook source
# MAGIC %md
# MAGIC # Proyecto `discovery-agents` — Bundle de transporte (no ejecuta agentes)
# MAGIC
# MAGIC **Que es esto:** un EMPAQUETADOR generado automaticamente desde la fuente
# MAGIC (`tools/generar_bundle_databricks.py`). Contiene todo el proyecto multiagente *Discovery Agents*
# MAGIC embebido en base64 y, al correrlo, **reconstruye los archivos en carpetas** (como descomprimir
# MAGIC un .zip). No adapta ni cambia el codigo: lo escribe tal cual (reconstruccion byte a byte).
# MAGIC
# MAGIC **El proposito del agente NO cambia:** sigue siendo un multiagente para **GitHub Copilot + MCP**
# MAGIC (`discovery_agents/server.py`, `.vscode/mcp.json`, `.github/chatmodes/`). Este notebook solo **transporta**
# MAGIC el proyecto; aqui no se "corren los agentes en Databricks".
# MAGIC
# MAGIC **Como usarlo:** *Run all* → cada celda escribe un archivo en su ruta relativa = reconstruye el
# MAGIC proyecto. Luego lleva la carpeta resultante a tu editor con GitHub Copilot y usa el MCP como siempre.
# MAGIC
# MAGIC > Regenerar tras cualquier cambio en la fuente: `python tools/generar_bundle_databricks.py`.

# COMMAND ----------

# DBTITLE 1,Configuracion: BASE y helper de escritura
import base64
import pathlib

try:
    _user = spark.sql("SELECT current_user()").collect()[0][0]
    BASE = pathlib.Path(f"/Workspace/Users/{_user}/discovery-agents")
except Exception:
    BASE = pathlib.Path("/tmp/discovery-agents")

print("Reconstruyendo proyecto en:", BASE)


def write_b64(rel: str, b64: str):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(base64.b64decode(b64))
    print("[archivo]", rel)
'''


def generar() -> str:
    celdas = [_HEADER]
    for rel in _recolectar():
        with open(os.path.join(RAIZ, rel), "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode("ascii")
        rel_posix = rel.replace(os.sep, "/")
        celdas.append(
            f"# COMMAND ----------\n\n# DBTITLE 1,{rel_posix}\n"
            f"write_b64({rel_posix!r}, {b64!r})\n"
        )
    return "\n".join(celdas)


def main() -> None:
    contenido = generar()
    with open(SALIDA, "w", encoding="utf-8") as fh:
        fh.write(contenido)
    n = contenido.count("write_b64(") - 1  # menos la definición del helper
    print(f"Bundle regenerado: {SALIDA} ({n} archivos empaquetados)")


if __name__ == "__main__":
    main()
