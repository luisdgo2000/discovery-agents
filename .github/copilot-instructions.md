# Instrucciones globales — Discovery Agents (v4)

Este repo construye el **Discovery de productos de datos** con un orquestador + subagentes
apoyados en el servidor MCP `discovery-agents` y un **workspace de estado en disco**
(`work/<caso>/`).

> Este archivo sigue la convención de nombre que el cliente de agentes espera encontrar; su
> contenido son las reglas de trabajo del sistema, no de ninguna herramienta concreta.

## Principio rector: eficiencia de tokens

> **Lo que se puede calcular, NO se prompea.** El modelo solo razona; Python extrae, estructura,
> deduplica, consolida, puntúa, valida, ensambla y dibuja.

- **El contexto del chat NO es memoria.** Cada fase escribe su resultado al workspace con
  `save_state` y la siguiente lo lee con `load_state`. Nunca pegues contenido extenso en el chat.
- **No leas archivos crudos** (Excel, .docx, .pptx, transcripciones, correos, SQL) con el modelo.
  Usa SIEMPRE las herramientas MCP: `extract_evidence` devuelve un índice; el contenido se pide por
  partes con `get_evidence(caso, id, chunk)` y SOLO el que vas a razonar ahora.
- **Incremental**: `pending_distillation(caso)` te dice qué falta; no re-proceses lo ya destilado.
- La extracción, la deduplicación, la consolidación, el scoring, la validación, el ensamblado, los
  diagramas, las tablas, el **Word (.docx)** y el **Resumen Ejecutivo (.html)** son **deterministas
  (0 tokens)**. Resérvate para: destilar, construir, generar hipótesis, criticar y redactar.
  `assemble` genera TODOS los entregables con una sola llamada; no hay divergencia CLI/MCP.
- Para imágenes, solo las marcadas `requiere_vision_llm: true` (el OCR resolvió el resto). Esto
  incluye las incrustadas en .pptx y .docx, que el sistema extrae y lee por su cuenta.
- Modelo **económico** para destilado/visión; modelo **fuerte** para construcción, hipótesis,
  crítica y redacción.

## Reglas de calidad

- Idioma: **español**.
- **Nunca inventes datos.** String que el equipo debe definir → `PENDIENTE`; string que no surgió en
  los insumos → `DESCONOCIDO`; lista sin datos → `[]`. Las dos marcas cuentan como "sin dato" en el
  scoring: un Discovery lleno de `DESCONOCIDO` no puede alcanzar Go, y así debe ser.
- **Respeta los tipos del schema**: las listas son listas de objetos, no texto aplanado. Aplanar una
  lista no rompe el documento, lo vacía en silencio; `validate_discovery` lo detecta antes.
- Cita el insumo de origen `[E00x]` o `[E00x seg-NNN]` de cada dato relevante.
- **No inventes riesgos** para que la sección no quede vacía. Si no se identificaron, el documento
  dice "no se identificaron" — que es información, y muy distinta de un riesgo genérico.
- **No repitas.** Cada hecho se explica una vez, en la sección que le corresponde. El documento
  final es fusionado: no existe un anexo que vuelva a contar lo ya narrado.
- El **veredicto** (Go/Condicional/No-Go) lo da el scorer determinista, no el modelo.
- Los **conflictos** detectados entre fuentes se declaran, nunca se resuelven en silencio.

## Dónde viven las reglas

Las instrucciones de cada subagente están en `discovery_agents/prompts/*.md` y se cargan con
`get_subagent_prompt(nombre)`. **Los chat modes no las repiten**: solo dicen qué modelo usar y por
dónde empezar. Cuando una regla vivía en dos sitios, las copias divergían y la más débil era la que
el modelo leía primero.

## Flujo

Sigue el chat mode **Orquestador Discovery** (fases F0–F7 con gates humanos G0/G1/G2). Subagentes:
destilador-transcripciones, constructor-discovery, generador-hipotesis, critico-brechas y
**redactor-experto** (núcleo intelectual: narrativa empresarial + detección de contradicciones).
