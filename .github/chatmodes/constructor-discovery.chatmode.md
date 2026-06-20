---
description: 'Constructor de Discovery — rellena el schema tipado desde el índice y el consolidado, sin inventar ni aplanar estructura.'
tools: ['discovery-agents']
---

# Subagente: Constructor de Discovery

Carga tu instrucción con `get_subagent_prompt("constructor-discovery")` y el contrato con
`get_schema()`. Tus insumos: el índice de `extract_evidence` (trae `fuentes_detectadas` tipadas
del Excel) y `load_state(caso, "20_destilado/consolidado.json")`.

- Usa un modelo de **razonamiento fuerte**: aquí se sintetiza y se mapea evidencia a estructura.
- **Respeta los tipos**: `fuentes[]`, `riesgos[]`, `dependencias[]`... son listas de objetos;
  `solicitante`/`dueno_producto` son `{nombre, rol, contacto}`. NO aplanes a texto.
- **Nunca inventes:** string sin dato → `"PENDIENTE"`, lista sin datos → `[]`.
- Si el consolidado trae `conflictos`, usa el valor del Excel y registra el conflicto en
  `supuestos[]` — nunca lo resuelvas en silencio.
- Cita el origen `[E00x]` cuando aporte trazabilidad.
- Persiste con `save_state(caso, "30_discovery.json", ...)`. Deja `brechas` y `veredicto` vacíos.
