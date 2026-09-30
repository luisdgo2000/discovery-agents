"""Puertas de entrada al motor. Ninguna contiene lógica de negocio.

- `cli.py` — uso directo desde la terminal; corre en Python 3.9.
- `mcp_server.py` — servidor MCP para clientes con modos de agente; requiere Python 3.10+.

Ambas llaman exactamente a las mismas funciones del núcleo, y `render.entregables.construir_entregables`
es la fuente única del ensamblado. Si cada interfaz tuviera su propio pipeline, una de las dos
acabaría produciendo un resultado inferior en silencio.
"""
