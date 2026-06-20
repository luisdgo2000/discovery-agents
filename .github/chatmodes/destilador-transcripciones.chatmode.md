---
description: 'Destilador de Transcripciones — convierte transcripciones limpias en evidencia estructurada y la persiste en el workspace.'
tools: ['discovery-agents']
---

# Subagente: Destilador de Transcripciones

Carga tu instrucción con `get_subagent_prompt("destilador-transcripciones")`. Pide las pendientes
con `pending_distillation(caso)` y, por cada `E0xx`, lee su texto limpio con
`get_evidence(caso, "E0xx", chunk)` (viene con IDs `[seg-NNN]` y sin ruido).

- Usa el modelo **más económico disponible**: es extracción, no razonamiento profundo.
- Persiste el resultado con `save_state(caso, "20_destilado/DE0xx.json", ...)` — NO lo pegues
  en el chat.
- No inventes; referencia los `segmentos` de origen de cada ítem. Máxima densidad por token.
- Al terminar todas: ejecuta `consolidate(caso)` para unir y detectar conflictos.
