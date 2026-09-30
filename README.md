# Discovery Agents (v4)

Ecosistema multiagente para construir el **Discovery de un producto de datos** de nivel
empresarial a partir de una carpeta de insumos (caso de uso, discovery inicial/técnico, hallazgos,
fuentes, **transcripciones de Teams**, PowerPoint, imágenes), con **veredicto de factibilidad**
determinista (Go / Condicional / No-Go), narrativa de consultor senior, diagramas y matrices
generadas automáticamente.

Compatible con **GitHub Copilot** y diseñado para **máxima eficiencia de tokens**. La revisión
integral que originó la v2 está en [docs/REVISION_INTEGRAL.md](docs/REVISION_INTEGRAL.md).

## Arquitectura (dos capas + workspace)

1. **Orquestación — agentes de GitHub Copilot** (`.github/chatmodes/`): orquestador
   *Discovery Architect* + 5 subagentes (Destilador, Constructor, Hipótesis, Crítico y
   **Redactor Experto**, el núcleo intelectual).
2. **Capacidades — servidor MCP en Python** (`discovery_agents/`): todo lo determinista (0 tokens).
3. **Workspace de estado** (`work/<caso>/`): la memoria compartida es el disco, no el chat.
   Cada fase escribe su resultado (`save_state`) y la siguiente lo lee (`load_state`); el LLM
   solo ve índices (~500 tokens) y pide contenido bajo demanda (`get_evidence(caso, id, chunk)`).

> **Principios:** lo que se puede calcular, no se prompea · limpieza no destructiva (el original
> siempre accesible) · la estructura viaja como datos hasta el render · el veredicto es
> determinista · los conflictos se declaran, nunca se resuelven en silencio.

## Flujo (F0–F7 con gates humanos)

| Fase | Qué pasa | Quién |
|---|---|---|
| F0 | Manifiesto + **estrategia sugerida** · **[G0: humano valida]** | Python + orquestador |
| F1 | Extracción y limpieza segura → `work/<caso>/10_evidence/` (IDs E001…) | Python (0 tk) |
| F2 | Destilado incremental por transcripción (`pending_distillation`) | IA económica |
| F2b | Consolidación + **detección de conflictos numéricos** (Excel vs reunión) | Python (0 tk) |
| F3 | Construcción del schema **tipado** · **[G1: humano corrige hechos]** | IA fuerte |
| F4 | Hipótesis y arquetipos DataMesh | IA fuerte |
| F5 | Score/veredicto determinista + crítica con preguntas poderosas | Python + IA fuerte |
| F6 | **Redactor Experto**: narrativa empresarial (as-is/to-be, factibilidad S/M/L/XL) + inconsistencias | IA fuerte |
| F7 | `assemble` / `ensamblar` (misma función): doc **.md + .docx** narrativo-first, **Resumen Ejecutivo `.html`**, brechas, **temas faltantes**, **fidelidad**, **diagramas Mermaid** y **matrices** · **[G2: humano aprueba]** | Python (0 tk) |

Entregables en `work/<caso>/outputs/`: `discovery_final.md`, **`discovery_final.docx`** (Word
narrativo-first: tablas solo donde aportan) y **`resumen_ejecutivo.html`** (Executive Summary
standalone, moderno y responsive, para presentar a líderes — no es copia del Word). El documento se
arma como **suma de dos vistas**: *Parte I — Discovery inicial (general)* y
*Parte II — Discovery técnico (profundo)*, más un cierre con **Temas faltantes y deuda técnica**
(recolecta automáticamente todo lo no conocido, incl. alcance/objetivo) y **Cobertura de
evidencia** (validador de fidelidad: el agente no inventa, todo cita `[E00x]`; ver
`65_fidelidad.json`). Además `brechas.md`, `veredicto.json`, `diagramas/` (flujo de datos, fuentes
por servidor con columnas, Data Mesh, ER preliminar) y `tablas/` (inventario de fuentes con
**columnas/librerías/servidor origen**, riesgos, dependencias, supuestos/restricciones,
**trazabilidad campo→evidencia**, decisiones pendientes, **temas faltantes**).

## Uso desde GitHub Copilot (VS Code)

1. `pip install -r requirements.txt` (Python ≥ 3.10 para el MCP).
2. Abrir la carpeta en VS Code; el MCP queda registrado por `.vscode/mcp.json`.
3. Insumos en `inputs/<tu_caso>/` (convención abajo).
4. Chat mode **Orquestador Discovery**: *"Construye el discovery de `inputs/<tu_caso>`"*.
   Emite primero la **estrategia sugerida** (G0) y luego ejecuta las fases.

## Convención de la carpeta de insumos

```
inputs/<caso>/
├─ caso_de_uso/        # descripción, necesidad, alcance (docx/pdf/md/pptx)
├─ discovery_inicial/  # notas de la entrevista inicial
├─ discovery_tecnico/  # notas técnicas, lógica de negocio/queries
├─ transcripciones/    # Teams: .vtt (<v Hablante>), .docx ("Nombre  0:15") o .txt genérico
├─ hallazgos/          # findings, impedimentos, dependencias
├─ fuentes/            # Excel con encabezados: Tabla, Servidor, Volumetría, Frecuencia, Sensible
└─ imagenes/           # diagramas, capturas (OCR local; visión LLM solo si el OCR no alcanza)
```

## Uso determinista sin Copilot (CLI, Python ≥ 3.9)

```bash
python -m discovery_agents evidencia   inputs/caso_demo   # extrae y persiste; imprime índice
python -m discovery_agents get         caso_demo E003     # contenido bajo demanda por chunks
python -m discovery_agents pendientes  caso_demo          # transcripciones sin destilar
python -m discovery_agents consolidar  caso_demo          # une destilados + detecta conflictos
python -m discovery_agents score       caso_demo          # veredicto determinista
python -m discovery_agents ensamblar   caso_demo          # doc .md + .docx + resumen_ejecutivo.html + brechas + temas faltantes + fidelidad + diagramas + matrices
python -m discovery_agents schema / rubrica               # contratos
```

## Pruebas

```bash
PYTHONPATH="$PWD" python -m unittest discover -s tests -v   # 80 pruebas
```
Cubren: limpieza no destructiva ("no es cierto", "tipo de datos", "este servidor" se preservan),
formatos reales de Teams, índice compacto (anti token-bomb), evidencia por chunks, lista blanca de
`save_state`, parse de volumetrías ("400M", "300 millones"), detección de conflictos, validadores
del scorer (volumetría sin números NO cuenta), tablas, trazabilidad y diagramas Mermaid.

## Economía de tokens

| Trabajo | Dónde | Tokens |
|---|---|---|
| Manifiesto, extracción (Excel/Word/PPTX/OCR), limpieza, consolidación, conflictos, score, ensamblado, diagramas, matrices | Python (MCP) | **0** |
| Destilado de transcripciones limpias (incremental) | Copilot económico | bajo |
| Construcción, hipótesis, crítica, redacción | Copilot fuerte | medio (estado compacto, contexto fresco por fase) |

El índice de evidencia reemplaza al volcado completo (~423 tokens vs ~70.000 en un caso real) y
los entregables se escriben server-side: nunca viajan por el contexto.

## Nota sobre Python

El núcleo determinista corre en Python ≥ 3.9 (stdlib + openpyxl + python-docx; pypdf/python-pptx/
pytesseract opcionales con degradación limpia). El servidor MCP requiere Python ≥ 3.10 (`mcp[cli]`).
