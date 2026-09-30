# Changelog

Cambios notables de Discovery Agents. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y versionado
[SemVer](https://semver.org/lang/es/).

## 2026-09-29 — Publicación

### Cambiado
- La v3 y la v4 vivían solo en disco; quedan commiteadas y fusionadas en `main`. Hasta
  hoy `main` en GitHub mostraba solo la estructura inicial de junio.

### Añadido
- Este CHANGELOG. Tags `v2.0.0` y `v4.0.0`.

## [4.0.0] — 2026-07-28

### Cambiado
- **BREAKING:** `mcp_server/` pasa a ser el paquete `discovery_agents/`, organizado por
  capas: `ingest/`, `knowledge/`, `render/`, `interfaces/` y `common/`. Se ejecuta con
  `python -m discovery_agents`.
- Documento fusionado: cada sección tiene un solo cuerpo y ya no hay un anexo que
  repita la narrativa (principio 10, «un hecho, un lugar»).
- Lo no capturado se reúne en una lista única en lugar de secciones llenas de
  «PENDIENTE»; «no se identificaron riesgos» se escribe completo (principio 11).

### Añadido
- Extractores de correo (`.eml`), contenido embebido, datos estructurados, formatos
  legacy y transcripciones, con un registro central.
- `knowledge/dedup.py` y `knowledge/validador.py`.
- `docs/BLUEPRINT.md` y `tools/sync_docs.py`; caso de ejemplo `inputs/discovery_demo`.

### Verificación
- 83 pruebas unittest en verde.

## 3.0.0 — 2026-07-25

Sin commit propio: se versionó junto con la 4.0.0.

### Añadido
- Resumen Ejecutivo HTML standalone (`resumen_ejecutivo.html`): sin red, responsive,
  tema claro y oscuro, acento de color dirigido por el veredicto.
- Schema tipado ampliado: contexto, problemática, casos de uso, beneficio económico
  (solo con evidencia `[E00x]`), product owner y líder técnico, hallazgos técnicos y
  productos relacionados. Nueva sección «Gobierno del producto».
- Soporte de `.csv`; los binarios legacy `.doc`, `.xls` y `.ppt` se detectan y avisan
  (antes fallaban en silencio).
- `docs/FILOSOFIA.md` y `tools/generar_bundle_databricks.py`.

### Cambiado
- Ensamblado unificado: `render/entregables.py` es la fuente única que usan la tool MCP
  `assemble` y el CLI `ensamblar`. Antes el `.docx` y `65_fidelidad.json` solo salían por
  CLI.
- Word narrativo-first: las tablas se reservan para fuentes, riesgos, certificadores y
  hallazgos técnicos.
- `artefactos/` se renombra a `render/`.

## 2026-06-23 — Documentador de doble vista

### Añadido
- El documento se arma como dos vistas: Parte I (Discovery inicial) y Parte II
  (Discovery técnico), con cierre de temas faltantes y deuda técnica.
- Validador de fidelidad (`65_fidelidad.json`): todo cita su evidencia `[E00x]`.
- Export a `.docx`.

## [2.0.0] — 2026-06-12

Tras la revisión integral de [docs/REVISION_INTEGRAL.md](docs/REVISION_INTEGRAL.md).
Publicado como estructura inicial del repositorio el 2026-06-20.

### Añadido
- Workspace de estado `work/<caso>/`: las tools devuelven índices y el contenido se pide
  bajo demanda (`get_evidence`).
- Parsers reales de transcripciones de Teams (VTT y `.docx`) y extractor de PowerPoint.
- Consolidador con detección de conflictos numéricos (más de 10 % de diferencia se
  declara, nunca se resuelve en silencio).
- Subagente Redactor Experto: narrativa as-is/to-be y factibilidad S/M/L/XL.
- Diagramas Mermaid y matrices generados sin tokens.
- Flujo F0 a F7 con gates humanos G0, G1 y G2.

### Cambiado
- Limpieza de transcripciones no destructiva: el original siempre accesible.
- Schema tipado con validadores en el scorer.

## 1.0.0 — 2026-06

Anterior al repositorio.

### Añadido
- Arquitectura de dos capas: agentes de GitHub Copilot para orquestar y un servidor MCP
  en Python para todo lo determinista.
- Veredicto Go / Condicional / No-Go determinista (`scorer` + `rubric`).

[4.0.0]: https://github.com/luisdgo2000/discovery-agents/releases/tag/v4.0.0
[2.0.0]: https://github.com/luisdgo2000/discovery-agents/releases/tag/v2.0.0
