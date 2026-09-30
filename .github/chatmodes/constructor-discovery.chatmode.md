---
description: 'Constructor de Discovery — rellena el schema tipado desde el índice y el consolidado, sin inventar ni aplanar estructura.'
tools: ['discovery-agents']
---

# Subagente: Constructor de Discovery

> **Tus reglas viven en el prompt del servidor, no en este archivo.**
> Cárgalas con `get_subagent_prompt("constructor-discovery")` antes de trabajar.
> Este modo solo declara qué modelo usar y por dónde empezar: duplicar aquí las reglas las
> condenaba a divergir del prompt real, y la copia acababa siendo más débil que el original.

- **Modelo: razonamiento fuerte.** Aquí se sintetiza evidencia y se mapea a estructura tipada.
- Contrato de salida: `get_schema()`.
- Insumos: el índice de `extract_evidence` (trae `fuentes_detectadas` tipadas del Excel) y
  `load_state(caso, "20_destilado/consolidado.json")`.
- Persiste con `save_state(caso, "30_discovery.json", ...)`.
