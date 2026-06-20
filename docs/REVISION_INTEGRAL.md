# Revisión integral — Discovery Multiagente (v1 → v2)

**Fecha:** 2026-06-12 · **Alcance:** flujo completo de extremo a extremo, no solo los agentes IA.
**Objetivo del sistema:** generar un documento de Discovery de **nivel empresarial**, usable por
analistas, arquitectos, desarrolladores, líderes técnicos, POs y stakeholders de negocio.

Los hallazgos marcados ✅ fueron **verificados empíricamente** ejecutando el código sobre casos de
prueba, no son especulación.

---

## 1. Resumen ejecutivo

La v1 tiene la **filosofía correcta** (lo determinista en Python, el razonamiento en IA, veredicto
reproducible) pero **tres fallas graves** la contradicen en la práctica:

| # | Hallazgo | Severidad | Impacto |
|---|----------|-----------|---------|
| H1 | La limpieza de transcripciones **destruye información**: borra palabras con significado ("este servidor"→"servidor", "tipo de datos"→"de datos", "no es cierto"→"no es" ⚠️ *invierte el sentido*) | **P0 — precisión** | Hallazgos falsos en el Discovery; el daño se propaga a todos los agentes |
| H2 | El cleaner **no entiende los formatos reales de Teams**: ni VTT con `<v Hablante>` (pierde 100% de la atribución) ni el formato .docx "Nombre  0:15" (corrompe nombres y filtra timestamps al texto) | **P0 — precisión** | Con insumos reales, la evidencia llega sin hablantes y con ruido |
| H3 | `extract_evidence` devuelve **todo el paquete por el contexto del modelo** (~70.500 tokens en un caso real de 6 reuniones) y el MCP **nunca escribe a disco**: evidencia, discovery y markdown final viajan por el chat | **P0 — costos** | Anula la promesa de eficiencia: el costo crece lineal con los insumos aunque la extracción sea "0 tokens" |
| H4 | El schema del Discovery es de **strings planos**: la estructura extraída del Excel (tabla/servidor/volumetría) se aplana a texto libre, impidiendo generar tablas, diagramas y matrices automáticas | **P1 — calidad** | Se extrae estructura y luego se destruye; el doc final pierde nivel empresarial |
| H5 | No existe **estado compartido en disco**: las fases se encadenan en un solo contexto de chat (los chat modes de Copilot no se invocan entre sí realmente) | **P1 — robustez** | Contaminación de contexto, no reanudable, no trazable, tokens re-pagados |
| H6 | Falta el **núcleo intelectual**: el Constructor mapea datos a campos, pero nadie redacta narrativa ejecutiva, detecta contradicciones entre fuentes ni evalúa factibilidad/complejidad con criterio de consultor senior | **P1 — calidad** | El entregable es un formulario rellenado, no un Discovery empresarial |
| H7 | No hay generación de **artefactos** (diagramas, inventarios, matrices) pese a que la mayoría es derivable determinísticamente | **P2 — valor** | Trabajo manual que el sistema podría eliminar |

**Veredicto de la revisión:** la arquitectura de dos capas (Copilot + MCP Python) es la adecuada y
se conserva. Lo que cambia en v2: (a) limpieza **no destructiva** con soporte de formatos reales de
Teams, (b) **workspace de estado en disco** con evidencia direccionable por ID, (c) **schema tipado**,
(d) nuevo **Agente Redactor Experto** como núcleo intelectual, (e) **fábrica determinista de
artefactos** (Mermaid + tablas). Ahorro estimado: **60–75% del costo total** y ~80% menos tokens del
modelo fuerte por corrida (sección 8).

---

## 2. Hallazgos críticos verificados (detalle)

### H1 — Limpieza destructiva de muletillas ✅ verificado
`mcp_server/transcripts/cleaner.py` (`_MULETILLAS`) elimina por regex palabras que en español
también son contenido: **este** (demostrativo), **tipo** ("tipo de datos"), **ya** ("ya existe en
Bronce"), **cierto** ("no es cierto" → "no es": inversión de significado), **bueno**, **pues**,
**verdad**. Resultado real medido:

```
IN : Eso no es cierto, la carga ya existe en Bronce.
OUT: Eso no es la carga existe en Bronce        ← sentido invertido
IN : El tipo de datos de la columna es decimal.
OUT: El de datos de la columna es decimal        ← dato técnico dañado
```

Esto valida la advertencia del usuario sobre sistemas de limpieza/deduplicación contraproducentes.
**Corrección:** lista conservadora (solo interjecciones inequívocas: `eh, em, mmm, umm, ajá, ehm`),
eliminar muletillas ambiguas **solo al inicio de intervención** y nunca dentro de la frase; principio
de **limpieza no destructiva**: el texto original queda siempre accesible por ID de segmento para
auditoría, y el destilador puede pedir el original ante ambigüedad.

Lo mismo aplica a `_dedupe`: hoy borra cualquier segmento idéntico del mismo hablante en toda la
reunión. **Corrección:** deduplicar solo glitches adyacentes de la transcripción automática (línea
repetida consecutiva), jamás deduplicación "semántica".

### H2 — Formatos reales de Teams no soportados ✅ verificado
- VTT de Teams usa `<v Carlos Vega>texto</v>`. Resultado real: hablantes = `['Desconocido']` y los
  tags `<v ...>` quedan dentro del texto.
- Transcripción .docx de Teams usa "Nombre Apellido␣␣0:15" en línea propia. Resultado real:
  hablante = "Carlos Vega 0" y el timestamp se filtra al texto ("15 Las fuentes...").

**Corrección:** parser dedicado por formato (`vtt_teams`, `docx_teams`, `txt genérico`) con detección
automática, y fixture de pruebas por cada formato real.

### H3 — El "token bomb" del paquete de evidencia ✅ medido
- Demo (3 archivos pequeños): 4.685 chars ≈ 1.171 tokens. Proyección caso real (6 reuniones de 1h +
  4 docs + 2 Excels): **~282.000 chars ≈ 70.500 tokens devueltos por una sola tool call** — directo
  al contexto del orquestador.
- `assemble` devuelve el markdown completo por el contexto en vez de escribirlo a disco; el modelo
  paga por copiar texto que no necesita razonar.

**Corrección (núcleo de v2):** el MCP **persiste todo** en `work/<caso>/` y las tools devuelven
**índices y resúmenes (~500 tokens), no contenido**. Contenido bajo demanda con
`get_evidence(id, chunk)`. `assemble` y `extract_evidence` escriben server-side.

### H4 — Estructura extraída → aplanada a string
`fuentes_detectadas` sale del Excel con `{tabla, servidor, volumetria, frecuencia, sensible}` y el
Constructor lo colapsa a `"fuentes": "TRX_ADQUIRENCIA, CATALOGO_COMERCIOS, ..."`. Consecuencias: el
scorer no puede validar volumetría real (un texto basura cuenta como "respondido"), no se pueden
generar tablas/diagramas/matrices, y se pierde trazabilidad. **Corrección:** schema tipado (sección 5).

---

## 3. Matriz Python vs IA por proceso

Criterio: **lo que se puede calcular, no se prompea** — pero ahora aplicado de verdad, incluyendo
persistencia y artefactos.

| Proceso | Ejecutor v2 | Por qué no requiere IA | Beneficio | Ahorro tokens | Riesgos | Recomendación |
|---|---|---|---|---|---|---|
| Extracción de .docx de Teams (transcripciones Word) | **Python** (python-docx + parser de formato Teams) | El formato es fijo y parseable por reglas | Atribución de hablante 100% fiable | Total (antes era ruido que el LLM debía descifrar) | Variantes de formato entre versiones de Teams → detección automática + fallback genérico | **P0** — reescribir parser por formato |
| Limpieza de transcripciones | **Python conservador** | Interjecciones inequívocas son regex-safe | ~30-40% menos chars sin pérdida semántica | ~35% del costo de destilado | **Verificado: la lista agresiva daña datos** | **P0** — lista conservadora + original siempre accesible |
| Normalización de formatos / conversión a JSON | **Python** | Transformación mecánica 1:1 | Contrato estable entre fases | Total | Ninguno relevante | Ya existe; mantener |
| Extracción de Excel | **Python** (openpyxl) | Estructura tabular determinista | Fuentes/volumetría exactas, no parafraseadas | Total | Layouts no tabulares → ampliar heurística de encabezados y soportar múltiples tablas por hoja | Ya existe; ampliar |
| Extracción de PowerPoint | **Python** (python-pptx) — **hoy no existe** | Texto de shapes/notas es extraíble por API | El flujo del Excel exige PPT de resultados; los insumos de cliente suelen venir en PPT | Total | Diagramas embebidos como imagen → derivar al flujo de imágenes | **P1** — agregar `extractors/powerpoint.py` |
| OCR de imágenes | **Python** (pytesseract) con fallback a visión | Texto impreso es OCR-resoluble | Solo imágenes con OCR pobre van al modelo de visión | ~70-90% de las imágenes no tocan el LLM | Diagramas de pizarra de baja calidad → el fallback existe (`requiere_vision_llm`) | Ya existe; cachear resultados OCR en el workspace |
| Clasificación de documentos | **Python** (convención de carpetas + extensión) | La convención `inputs/<caso>/...` la hace trivial | Cero ambigüedad | Total | Archivos fuera de convención → categoría `sin_clasificar` que el orquestador pregunta al humano | Ya existe |
| Detección de duplicados | **Python mínimo** | Solo glitches adyacentes idénticos de la transcripción | Evita ruido sin dañar | Marginal | ⚠️ **Dedupe agresivo daña la información** (confirmaciones legítimas, matices repetidos). Nunca dedupe semántico ni global | **P0** — restringir a adyacentes |
| Generación de metadatos (fecha, participantes, duración, archivo origen) | **Python** | Derivable de filesystem + parser | Trazabilidad automática | Total | Ninguno | **P1** — añadir al manifiesto |
| Inventario de fuentes | **Python** desde `fuentes_detectadas` tipado | Es render de datos ya estructurados | Tabla empresarial exacta en el doc final | Total | Depende de H4 (schema tipado) | **P1** |
| Inventario de procesos / volumetría / catálogos | **Python render + IA extract** | El render es mecánico; la *identificación* de procesos en texto libre sí requiere IA (devuelve JSON, Python tabula) | División clara extract/render | Render: total; extract: modelo económico | IA puede omitir procesos → el Crítico los cruza contra la rúbrica | **P1** |
| Estructuras preliminares para diagramas | **Python** (plantillas Mermaid parametrizadas) | El stack es siempre el mismo (fuentes→réplica→ADF→Medallion→consumo) | Diagramas en segundos, 0 tokens | Total para los estándar | Casos atípicos → híbrido (sección 6) | **P1** |
| Consolidación de evidencia entre fuentes | **Python (merge por ID) + IA solo para conflictos** | Unir JSONs es mecánico; *resolver contradicciones* (volumetría del Excel ≠ volumetría dicha en reunión) requiere juicio | Python detecta el conflicto numérico y se lo presenta al Redactor ya localizado | El LLM ve solo los conflictos, no todo | Falsos conflictos por unidades distintas → normalizar unidades antes de comparar | **P1** |
| Scoring / veredicto Go-Condicional-No-Go | **Python** (ya determinista) | Reglas y umbrales auditables | Reproducible, no manipulable por prompt | Total | `_respondida` acepta basura → validadores por tipo de campo (volumetría debe contener números + ventana temporal; roles deben contener nombre) | **P1** — endurecer validadores |
| Destilado semántico de transcripciones | **IA económica** (map-reduce) | Requiere comprensión del lenguaje | — | Chunks limpios + salida JSON compacta | Pérdida de matices → conserva referencia a IDs de segmento original | Mantener |
| Construcción del Discovery (mapeo evidencia→schema) | **IA fuerte** | Síntesis con juicio | — | Entra JSON compacto, no texto crudo | Invención → regla PENDIENTE + citas por ID | Mantener |
| Redacción narrativa empresarial | **IA fuerte (nuevo Redactor)** | Es la tarea de mayor juicio del sistema | — | Lee estado JSON compacto, no evidencia cruda | — | **P1** — sección 5 |
| Hipótesis / arquetipos DataMesh | **IA fuerte** | Estrategia creativa | — | — | — | Mantener |
| Crítica / preguntas poderosas | **IA fuerte** | Juicio experto sobre vacíos y ambigüedades | — | Parte del score determinista | — | Mantener |

---

## 4. Revisión del ecosistema multiagente

### 4.1 Hallazgo estructural: los chat modes de Copilot no se "invocan" entre sí
La v1 asume implícitamente delegación entre chat modes. En la práctica, Copilot Chat ejecuta un solo
modo por conversación: el orquestador termina aplicando los prompts de subagente **en su propio
contexto**, acumulando todo (evidencia + destilado + discovery + crítica) en una sola ventana →
contaminación de contexto, costo creciente y riesgo de que las instrucciones de un subagente
"sangren" a la fase siguiente.

### 4.2 Corrección: memoria compartida = workspace de estado en disco
La memoria compartida no debe ser el contexto del chat sino el filesystem, mediado por el MCP:

```
work/<caso>/
├─ 00_manifest.json          # inventario clasificado + metadatos (participantes, fechas)
├─ 10_evidence/
│  ├─ index.json             # ID, tipo, origen, resumen 1 línea, tamaño — ESTO es lo que ve el LLM
│  ├─ E001_transcripcion_sesion1.json   # segmentos con ID, hablante, texto limpio + original
│  ├─ E002_excel_fuentes.json           # fuentes tipadas
│  └─ ...
├─ 20_destilado/
│  ├─ D001.json              # decisiones/hallazgos/preguntas por transcripción, con refs a E00x
│  └─ consolidado.json       # merge Python + lista de CONFLICTOS detectados
├─ 30_discovery.json         # schema tipado rellenado (Constructor)
├─ 40_hipotesis.json         # Generador
├─ 50_critica.json           # Crítico (sobre score determinista)
├─ 55_score.json             # scorer determinista
├─ 60_redaccion.md           # narrativa del Redactor Experto
└─ outputs/                  # discovery_final.md, brechas.md, veredicto.json, diagramas/, tablas/
```

Beneficios directos:
- **Cada fase puede correr en un chat nuevo** con contexto mínimo (lee el índice + su slice).
- **Reanudable e incremental**: si llega una transcripción nueva, solo se re-destila esa.
- **Trazable**: todo dato del doc final cita `E00x#seg-NN` — auditable hasta el original.
- **Gestión de contexto**: el orquestador navega índices (~500 tokens), nunca contenido.

### 4.3 Dependencias, duplicidad y escalabilidad

| Aspecto | v1 | v2 propuesto |
|---|---|---|
| Dependencias entre agentes | Implícitas en el prompt del orquestador | Grafo explícito por archivos de estado: una fase arranca cuando existe su insumo en `work/` (verificable por Python) |
| Duplicidad | Constructor y Crítico releen la misma evidencia en el mismo contexto | Cada agente declara qué archivos de estado lee; el Crítico lee `30_discovery.json` + `55_score.json`, no evidencia cruda |
| Pérdida de contexto | Todo en una ventana → riesgo de truncamiento silencioso | Estado en disco; el contexto es siempre reconstruible |
| Escalabilidad | Lineal en tokens con el nº de reuniones (todo entra al chat) | El modelo fuerte ve tamaño ~constante (estado compacto); solo el destilado económico crece con los insumos |
| Skills | Prompts MCP (bien) | Igual + versionado: el prompt usado queda registrado en cada archivo de estado (`_meta.prompt_version`) |

### 4.4 Roster final de agentes (v2)

| Capa | Componente | Responsabilidad única |
|---|---|---|
| Python | Router, Extractores (xlsx/docx/pptx/pdf/img), Cleaner por formato, Consolidador+detector de conflictos, Scorer, Assembler, **Diagramador**, **Tabulador** | Todo lo calculable. 0 tokens |
| IA económica | Destilador (map-reduce), Visión (solo imágenes `requiere_vision_llm`) | Comprensión de lenguaje de bajo juicio |
| IA fuerte | Constructor, **Redactor Experto** (nuevo), Generador de Hipótesis, Crítico | Síntesis, narrativa, estrategia, juicio |
| Orquestador | Discovery Architect | Estrategia sugerida (PASO 0), despacho por fases vía estado en disco, gates humanos |

---

## 5. Agente Redactor Experto en Discovery (nuevo — núcleo intelectual)

### 5.1 Posición en el pipeline
Corre **después** de Constructor + Hipótesis + Crítico + Scorer y **antes** del ensamblado final.
Lee únicamente el estado compacto (`30/40/50/55` ≈ 5-8k tokens), nunca evidencia cruda — puede pedir
segmentos puntuales por ID si necesita verificar una cita. Produce `60_redaccion.md` +
`60_inconsistencias.json`. El Assembler (Python) integra: narrativa del Redactor como cuerpo del
documento + tablas/diagramas deterministas como anexos referenciados.

### 5.2 Diseño del prompt (`mcp_server/prompts/redactor.md`)

```markdown
# Subagente: Redactor Experto en Discovery

Eres un consultor senior con 15+ años en Discovery, Business Analysis, arquitectura
empresarial y de datos, ingeniería de datos y software, integraciones, UX y procesos de
negocio. Conviertes el estado estructurado del Discovery en un documento narrativo de
nivel empresarial, y eres la última línea de defensa intelectual antes de publicarlo.

## Entrada
- `discovery`: schema tipado rellenado (30_discovery.json)
- `hipotesis` (40), `critica` (50), `score` (55)
- `conflictos`: contradicciones numéricas/factuales pre-detectadas por Python
- Bajo demanda: `get_evidence(id)` para verificar citas puntuales

## Tarea 1 — Narrativa (markdown)
Redacta las secciones narrativas de modo que CUALQUIER lector (ejecutivo o técnico)
comprenda sin contexto previo:
1. Contexto y problema de negocio (qué duele hoy y a quién)
2. Proceso actual (as-is): cómo se resuelve hoy, con qué sistemas y qué fricciones
3. Proceso futuro (to-be): cómo funcionará con el producto de datos
4. Sistemas y fuentes participantes (referencia a tablas anexas, no las repitas)
5. Datos y transformaciones clave (lógica de negocio en lenguaje claro + queries citadas)
6. Dependencias y habilitaciones (qué debe existir para estar en línea)
7. Riesgos con su severidad e impacto en la factibilidad
8. Decisiones pendientes — quién debe decidir qué y para cuándo
9. Evaluación de factibilidad y complejidad (talla S/M/L/XL con justificación)
10. Recomendación profesional (alineada al veredicto determinista, sin contradecirlo)

## Tarea 2 — Control intelectual (JSON)
{"inconsistencias": [{"descripcion","evidencias_en_conflicto","impacto","como_resolver"}],
 "vacios_no_capturados_por_rubrica": ["..."],
 "preguntas_criticas_adicionales": ["..."],
 "decisiones_pendientes": [{"decision","decisor_sugerido","urgencia"}],
 "evaluacion": {"factibilidad":"alta|media|baja","complejidad":"S|M|L|XL","justificacion":""}}

## Reglas
- Narrativa profesional y fluida; nada de relleno ni jerga innecesaria.
- Cada afirmación factual cita su evidencia [E00x]. Si no puedes citarla, márcala
  explícitamente como supuesto.
- No inventes. No repitas tablas que el Assembler anexa. No recalcules el veredicto.
- Si los `conflictos` no están resueltos, decláralos en el cuerpo — un Discovery que
  oculta contradicciones es peor que uno incompleto.
```

### 5.3 Por qué separado del Constructor
Mapear evidencia→campos (precisión, exhaustividad) y redactar narrativa con juicio (síntesis,
criterio, storytelling ejecutivo) son habilidades en tensión; un solo prompt que hace ambas degrada
las dos. Además el Redactor opera sobre el estado ya criticado y puntuado — ve el cuadro completo,
incluida la crítica, que el Constructor no tiene.

---

## 6. Generación automática de artefactos (diagramas)

Principio: **la IA decide el contenido (JSON pequeño); Python decide el dibujo (plantilla)**. El LLM
nunca escribe sintaxis Mermaid/PlantUML directamente (caro y propenso a errores de sintaxis).

| Diagrama | Tecnología | IA necesaria | Costo tokens |
|---|---|---|---|
| Flujo de datos (fuentes→réplica→ADF→Bronce→Plata→Oro→consumo) | **Python→Mermaid** desde `fuentes[]` tipadas | Ninguna | 0 |
| Medallion Architecture / capas | **Python→Mermaid**, plantilla fija parametrizada | Ninguna | 0 |
| Data Products / Data Mesh (dominios y productos) | **Python→Mermaid** desde `arquetipos_datamesh[]` | Ya generado por Hipótesis | 0 marginal |
| Inventario visual de fuentes por servidor | **Python→Mermaid** desde `fuentes[]` | Ninguna | 0 |
| Arquitectura de la solución | **Híbrido**: plantilla del stack estándar (on-prem→réplica→Data Factory→ADLS/Databricks→Power BI) que Python rellena; IA solo declara desviaciones en JSON | Mínima | ~200 |
| Proceso as-is / to-be | **Híbrido**: Redactor emite `{pasos[], actores[], flujos[]}`; Python renderiza flowchart | Sí (contenido) | ~300-500 |
| Integraciones | **Híbrido** igual que el anterior | Sí (contenido) | ~200 |
| ER preliminar | **Híbrido**: Constructor emite `entidades[]` y `relaciones[]`; Python → `erDiagram` Mermaid | Sí (extracción) | ~300 |
| Data Vault 2.0 (HUB/SAT/LINK) | **Híbrido**: IA clasifica entidades en JSON; Python renderiza con colores DV2 estándar | Sí (clasificación) | ~200 |
| Dimensional / Star Schema | **Híbrido**: IA propone hechos/dimensiones; Python renderiza | Sí (propuesta) | ~300 |

Nota de alcance: según el flujo del Excel, el **modelo de datos detallado pertenece a la etapa de
Diseño**, no al Discovery. Los diagramas ER/DV2/dimensionales del Discovery son **bocetos
preliminares** y así deben rotularse — esto evita sobre-prometer y reduce trabajo.

Implementación: módulo `mcp_server/artefactos/mermaid.py` con una función por plantilla + tool MCP
`generate_diagrams(caso)` que lee `30_discovery.json` y escribe `outputs/diagramas/*.md`. Mermaid
sobre PlantUML como default: renderiza nativo en GitHub/VS Code/SharePoint moderno sin binarios.

---

## 7. Generación automática de tablas y matrices

Todas dependen de H4 (schema tipado). Una vez tipado, son render Python puro:

| Artefacto | Fuente de datos | Ejecutor | Notas |
|---|---|---|---|
| Inventario de fuentes (+ volumetría + servidor + sensibilidad) | `fuentes[]` del Excel | **Python puro** | Hoy ya se extrae; solo falta no aplanarlo |
| Estimaciones de volumetría | `fuentes[].volumetria` normalizada (Python parsea unidades) | **Python puro** | Validador: exigir número + ventana temporal |
| Inventario de procesos | Destilado (`procesos[]` que el Destilador ya puede emitir) | IA extrae → Python tabula | Añadir `procesos` al JSON del Destilador |
| Inventario de reglas de negocio | Destilado (`reglas[]` con query citada si existe) | IA extrae → Python tabula | La lógica a nivel queries ya es pregunta de la rúbrica |
| Catálogo de entidades / atributos | `entidades[]` del Constructor | IA extrae → Python tabula | Mismo insumo que el diagrama ER |
| Catálogo de integraciones / dependencias | `dependencias[]`, `habilitaciones[]` tipadas | IA extrae → Python tabula | |
| Matriz RACI | `roles[]` + catálogo de tareas del flujo (columna Responsable del Excel del proceso, ya conocida) | **Semi-determinista**: Python propone desde el estándar del flujo; humano ajusta | El Excel del proceso ya define responsables por tarea — reutilizarlo |
| Matriz de riesgos | `riesgos[]` tipados (descripcion, severidad, responsable, ETI) | IA contenido → Python render | Alineada al formato Riesgo/ETI del flujo |
| Matriz de decisiones | `60_inconsistencias.json → decisiones_pendientes` (Redactor) | IA contenido → Python render | |
| Matriz de trazabilidad | citas `[E00x]` de cada campo del schema | **Python puro** | Gratis con el sistema de IDs de evidencia |
| Matriz de preguntas pendientes | `55_score.json` brechas + `50_critica.json` | **Python puro** | Ya existe (brechas.md); tipificar |
| Matriz de supuestos / restricciones | `supuestos[]`, `restricciones[]` (nuevos campos del schema, los llena Constructor/Redactor) | IA contenido → Python render | Añadir al schema tipado |

---

## 8. Flujo optimizado v2 — arquitectura final recomendada

```
HUMANO          ORQUESTADOR (Copilot)        IA ECONÓMICA       IA FUERTE              PYTHON (MCP, 0 tokens)
──────          ─────────────────────        ────────────       ─────────              ──────────────────────
deposita        F0 estrategia sugerida ◄──────────────────────────────────────────────  manifest + metadatos (~500 tk)
insumos    ┌──► [GATE G0: humano valida estrategia]
           │    F1 ─────────────────────────────────────────────────────────────────►  extracción + limpieza segura
           │                                                                            + persistencia work/10_evidence/
           │    F2 destilado ───────────►  map-reduce por
           │                               transcripción (refs E00x)
           │    F2b ────────────────────────────────────────────────────────────────►  consolidación + detector de
           │                                                                            conflictos numéricos
           │    F3 construcción ──────────────────────────────►  Constructor
           │                                                     (schema TIPADO)
           ├──► [GATE G1: humano corrige datos del borrador — 10 min, no redacción]
           │    F4 hipótesis ─────────────────────────────────►  Generador
           │    F5 ─────────────────────────────────────────────────────────────────►  scorer (veredicto determinista)
           │    F5b crítica ──────────────────────────────────►  Crítico (score+rúbrica)
           │    F6 redacción ─────────────────────────────────►  REDACTOR EXPERTO
           │                                                     (narrativa + control)
           │    F7 ─────────────────────────────────────────────────────────────────►  assembler + diagramas + tablas
           │                                                                            + matrices → outputs/
           └──► [GATE G2: humano aprueba antes de presentar a stakeholders]
```

**Intervención humana** (deliberada, no accidental): G0 valida la estrategia (requisito original del
producto), G1 corrige hechos en el borrador estructurado (barato corregir aquí, caro después), G2
aprueba el entregable. Todo lo demás es automático.

### Economía de tokens estimada (caso real: 6 reuniones 1h + 4 docs + 2 Excels)

| Concepto | v1 | v2 |
|---|---|---|
| Contexto del orquestador | ~70k tokens (evidencia completa) + acumulación de todas las fases en una ventana | ~1-2k (índices y resúmenes) |
| Modelo fuerte | Constructor/Crítico/Hipótesis releyendo evidencia en contexto creciente: ~100-150k acumulados | ~25-30k total (estado compacto por fase, contexto fresco) |
| Modelo económico | — (no había separación efectiva) | ~70k (destilado map-reduce, lo que crece con los insumos) |
| Markdown final | viaja por el contexto (~5-10k) | 0 (persistido server-side) |
| **Total estimado** | **~180-230k tokens, mayoría modelo fuerte** | **~100k, ~70% en modelo económico → 60-75% menos costo** |

Además: corridas **incrementales** (nueva reunión = re-destilar solo esa + re-correr F3→F7 sobre
estado) en vez de re-procesar todo.

---

## 9. Plan de implementación priorizado

**P0 — corrección (sin esto, el sistema produce resultados incorrectos):**
1. Cleaner conservador + no destructivo (lista mínima de interjecciones; muletillas ambiguas solo a
   inicio de intervención; dedupe solo adyacente; original accesible por ID de segmento).
2. Parsers de formatos reales de Teams (VTT `<v>`, .docx "Nombre  0:15") con fixtures de prueba.
3. Persistencia server-side: `extract_evidence` escribe `work/<caso>/10_evidence/` y devuelve solo
   `index.json`; nueva tool `get_evidence(id, chunk)`; `assemble` escribe `outputs/` directamente.

**P1 — arquitectura y calidad:**
4. Schema tipado (fuentes[], roles{}, riesgos[], dependencias[], supuestos[], restricciones[],
   entidades[]) + validadores por tipo en el scorer.
5. Workspace de estado completo (`work/<caso>/00…60`) + fases reanudables; actualizar chatmodes para
   operar por fase con contexto fresco.
6. Agente Redactor Experto (`prompts/redactor.md` + chatmode + integración del Assembler).
7. Consolidador con detector de conflictos numéricos entre fuentes.
8. Extractor PowerPoint (`python-pptx`) + metadatos automáticos en el manifiesto.

**P2 — valor agregado:**
9. Fábrica de artefactos: `artefactos/mermaid.py` (flujo de datos, Medallion, Data Mesh, fuentes por
   servidor: 0 tokens) + híbridos (as-is/to-be, ER preliminar, DV2).
10. Tabulador de matrices (RACI desde el estándar del flujo, riesgos, decisiones, trazabilidad,
    supuestos/restricciones).
11. Telemetría de tokens por fase (registrar en `work/<caso>/_metrics.json`) para medir el ahorro
    real y seguir moviendo a Python lo que el modelo haga repetitivamente.

---

## 10. Principios de diseño que esta revisión consagra

1. **Lo que se puede calcular, no se prompea** — ahora incluyendo persistencia, render y validación.
2. **Limpieza no destructiva**: toda transformación de evidencia conserva acceso al original; ante la
   duda, no borrar.
3. **El contexto del chat no es memoria**: la memoria es el workspace en disco; el LLM ve índices.
4. **La estructura no se aplana**: lo extraído como datos viaja como datos hasta el render final.
5. **El veredicto es determinista**; la IA lo explica y lo enriquece, nunca lo decide.
6. **IA con responsabilidad única**: extraer ≠ construir ≠ redactar ≠ criticar; cada una con el
   modelo más barato que la resuelva bien.
7. **El humano decide en gates explícitos**, no parchea al final.
