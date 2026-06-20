# Instrucciones globales — Discovery Agents (v2)

Este repo construye el **Discovery de productos de datos** con un orquestador + subagentes de
GitHub Copilot apoyados en el servidor MCP `discovery-agents` y un **workspace de estado en disco**
(`work/<caso>/`).

## Principio rector: eficiencia de tokens

> **Lo que se puede calcular, NO se prompea.** El modelo solo razona; Python extrae, estructura,
> consolida, puntúa, ensambla y dibuja.

- **El contexto del chat NO es memoria.** Cada fase escribe su resultado al workspace con
  `save_state` y la siguiente lo lee con `load_state`. Nunca pegues contenido extenso en el chat.
- **No leas archivos crudos** (Excel, .docx, .pptx, transcripciones) con el modelo. Usa SIEMPRE
  las herramientas MCP: `extract_evidence` devuelve un índice; el contenido se pide por partes con
  `get_evidence(caso, id, chunk)` y SOLO el que vas a razonar ahora.
- **Incremental**: `pending_distillation(caso)` te dice qué falta; no re-proceses lo ya destilado.
- La extracción, consolidación, scoring, ensamblado, diagramas y tablas son **deterministas
  (0 tokens)**. Resérvate para: destilar, construir, generar hipótesis, criticar y redactar.
- Para imágenes, solo las marcadas `requiere_vision_llm: true` (el OCR resolvió el resto).
- Modelo **económico** para destilado/visión; modelo **fuerte** para construcción, hipótesis,
  crítica y redacción.

## Reglas de calidad

- Idioma: **español**.
- **Nunca inventes datos.** String sin dato → `PENDIENTE`; lista sin datos → `[]`.
- **Respeta los tipos del schema**: las listas son listas de objetos, no texto aplanado.
- Cita el insumo de origen `[E00x]` o `[E00x seg-NNN]` de cada dato relevante.
- El **veredicto** (Go/Condicional/No-Go) lo da el scorer determinista, no el modelo.
- Los **conflictos** detectados entre fuentes se declaran, nunca se resuelven en silencio.

## Flujo

Sigue el chat mode **Orquestador Discovery** (fases F0–F7 con gates humanos G0/G1/G2). Subagentes:
destilador-transcripciones, constructor-discovery, generador-hipotesis, critico-brechas y
**redactor-experto** (núcleo intelectual: narrativa empresarial + detección de contradicciones).
