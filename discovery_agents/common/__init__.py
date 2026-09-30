"""Utilidades transversales, sin dependencias de otras capas.

`common/` es la única capa que puede importarse desde cualquier otra. No importa nada del
proyecto: si un módulo de `common/` necesitara `knowledge/` o `render/`, es señal de que la
utilidad no era transversal y pertenece a esa capa.
"""
