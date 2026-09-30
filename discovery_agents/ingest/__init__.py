"""Ingesta: de una carpeta de insumos heterogéneos a evidencia direccionable en disco.

Es la capa que hace posible la economía de tokens del sistema. Ningún byte de un insumo entra al
contexto de un modelo por defecto: se clasifica (`manifest`), se extrae a `10_evidence/`
(`pipeline`) y solo se devuelve un índice compacto. El contenido se pide después, por trozos y
solo el que se va a razonar.

`registry` es el punto único donde una extensión se asocia a su extractor: añadir un formato es
añadir una entrada, no editar tres archivos.
"""
