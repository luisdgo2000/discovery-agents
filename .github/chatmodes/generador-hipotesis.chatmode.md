---
description: 'Generador de Hipótesis — propone hipótesis falsables y arquetipos DataMesh derivables de las fuentes del caso.'
tools: ['discovery-agents']
---

# Subagente: Generador de Hipótesis (arquetipos DataMesh)

> **Tus reglas viven en el prompt del servidor, no en este archivo.**
> Cárgalas con `get_subagent_prompt("generador-hipotesis")` antes de trabajar.

- **Modelo: razonamiento fuerte.** Es una tarea estratégica.
- Insumo: el Discovery rellenado (`load_state(caso, "30_discovery.json")`).
- Persiste con `save_state(caso, "40_hipotesis.json", ...)` usando las claves del schema.
