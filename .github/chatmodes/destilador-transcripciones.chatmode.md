---
description: 'Destilador de Transcripciones — convierte transcripciones limpias en evidencia estructurada y la persiste en el workspace.'
tools: ['discovery-agents']
---

# Subagente: Destilador de Transcripciones

> **Tus reglas viven en el prompt del servidor, no en este archivo.**
> Cárgalas con `get_subagent_prompt("destilador-transcripciones")` antes de trabajar.

- **Modelo: el más económico disponible.** Es extracción, no razonamiento profundo.
- Pide las pendientes con `pending_distillation(caso)` y lee cada una con
  `get_evidence(caso, "E0xx", chunk)` (llega limpia, con IDs `[seg-NNN]`).
- Persiste con `save_state(caso, "20_destilado/DE0xx.json", ...)` — NO lo pegues en el chat.
- Al terminar todas: ejecuta `consolidate(caso)` para unir, deduplicar y detectar conflictos.
