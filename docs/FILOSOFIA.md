# Filosofía y Arquitectura del Agente Discovery

> Documento vivo. Explica **por qué** el agente Discovery es como es: su propósito, la visión que
> lo guía, los principios de diseño y de ingeniería que lo sostienen, cómo se reparte el trabajo
> entre Python y la IA, y cómo debe evolucionar. Si el Blueprint (`BLUEPRINT.md`) responde
> *cómo reconstruirlo*, este documento responde *por qué está construido así*.

---

## 1. Propósito

El agente Discovery convierte una **carpeta de insumos heterogéneos** (transcripciones de reuniones,
Excel de fuentes, Word, PDF, PowerPoint, imágenes, notas técnicas) en **conocimiento consolidado,
estructurado y accionable** sobre un producto de datos: qué se quiere construir, con qué fuentes, con
qué gobierno, con qué riesgos, y **si es factible avanzar** (veredicto Go / Condicional / No-Go).

No es un resumidor de documentos. Es un **consolidador inteligente**: interpreta información de
cualquier formato, la funde en un modelo único tipado, detecta contradicciones, evalúa completitud
contra una rúbrica experta y produce dos entregables listos para decidir —un **documento Word**
técnico-ejecutivo y un **Resumen Ejecutivo HTML** para líderes.

## 2. El problema que resuelve

El Discovery de un producto de datos es caro y frágil de hacer a mano:

- La información llega **dispersa y en formatos incompatibles**; consolidarla manualmente es lento y
  se pierde contexto entre reuniones.
- Los documentos resultantes suelen ser **formularios rellenados**, no análisis: repiten datos, se
  contradicen entre secciones, y mezclan lo que se sabe con lo que se supone.
- La factibilidad se decide por **criterio variable** de quien redacta, no por una regla reproducible.
- Volcar todos los insumos a un LLM es **caro** (el costo crece lineal con el número de reuniones) y
  **arriesgado** (el modelo inventa cuando no tiene el dato).

## 3. Visión

Un agente que **no inventa**, **no olvida** y **no se contradice**: cada afirmación se ancla a una
evidencia rastreable (`[E00x]`), el estado vive en disco (no en la ventana de chat), y el veredicto
es una función determinista y auditable de la evidencia. La IA se reserva para lo que solo ella hace
bien —razonar, sintetizar, narrar y criticar— y todo lo demás lo resuelve código barato y verificable.

El norte: **calidad de consultor senior a costo de script.**

---

## 4. Principios de diseño

Siete principios, en tensión deliberada unos con otros, gobiernan cada decisión:

1. **Lo que se puede calcular, no se prompea.** Extraer, clasificar, consolidar, puntuar, ensamblar,
   diagramar y renderizar son tareas deterministas → Python, 0 tokens. La IA no toca lo que una regla
   resuelve mejor.
2. **Limpieza no destructiva.** Toda transformación de evidencia conserva acceso al original. Ante la
   duda, no se borra. (Nace de un fallo real: una limpieza agresiva llegó a invertir el sentido de
   "no es cierto" → "no es".)
3. **El contexto del chat no es memoria.** La memoria es el workspace en disco (`work/<caso>/`). El
   LLM ve **índices** (~500 tokens), y pide contenido por ID solo cuando lo va a razonar.
4. **La estructura no se aplana.** Lo que se extrae como datos (fuentes, roles, riesgos) viaja como
   datos tipados hasta el render final. Aplanar a texto destruye la posibilidad de tablas, diagramas,
   validación y trazabilidad.
5. **El veredicto es determinista.** Lo calcula el scorer con reglas y umbrales auditables; la IA lo
   explica y lo enriquece, **nunca lo decide**. Así no se puede manipular con un prompt.
6. **Los conflictos se declaran, no se resuelven en silencio.** Si el Excel y una reunión discrepan en
   la volumetría, el sistema localiza el conflicto y lo presenta; ocultarlo sería peor que no tenerlo.
7. **El humano decide en gates explícitos** (G0 estrategia, G1 hechos, G2 aprobación), no parcheando al
   final. Corregir un hecho en el borrador es barato; corregirlo tras la redacción es caro.

Dos principios de calidad del entregable, añadidos en la evolución v3:

8. **Narrativa antes que tablas.** El valor está en el texto bien redactado; una tabla se usa **solo
   cuando de verdad aporta** (un inventario de fuentes, una matriz de riesgos). Un documento saturado
   de tablas no es un análisis.
9. **Evidencia o silencio.** Un dato sensible como el beneficio económico se afirma **solo si hay
   evidencia**; si no, se dice explícitamente que no se cuantificó. Nunca se rellena para "quedar bien".

Y dos más, añadidos en la evolución v4:

10. **Un hecho, un lugar.** El documento es fusionado: cada sección tiene un solo cuerpo, y nada se
    cuenta dos veces. La versión anterior ponía la narrativa arriba y repetía los mismos temas en un
    anexo estructurado; ante dos versiones de un mismo hecho, el lector no sabe cuál es la buena.
11. **Ausencia declarada, no disimulada.** Una sección sin información no se imprime llena de
    "PENDIENTE": se recoge en una lista única de lo no capturado. Y "no se identificaron riesgos" se
    escribe entero —*ausencia de evidencia de riesgo, no garantía de su inexistencia*— porque el
    silencio se lee como garantía.

---

## 5. Metodología y patrones arquitectónicos

### 5.1 Arquitectura de dos capas + workspace

- **Capa de orquestación (IA, GitHub Copilot):** un orquestador y cinco subagentes que **solo razonan**.
- **Capa de capacidades (Python, servidor MCP):** todo lo determinista, expuesto como herramientas.
- **Workspace de estado (disco):** la memoria compartida. Cada fase escribe su resultado y la siguiente
  lo lee. Esto hace el proceso **reanudable, incremental y trazable**.

Es una separación **razonamiento / mecánica / memoria**. Ninguna capa asume el trabajo de otra.

### 5.2 Pipeline por fases con gates humanos (F0–F7)

Un flujo lineal y reanudable: manifiesto → extracción → destilado → consolidación → construcción →
hipótesis → score+crítica → redacción → ensamblado. Entre medias, tres gates humanos. Cada fase tiene
una **entrada** y una **salida** en disco declaradas; una fase arranca cuando existe su insumo.

### 5.3 Patrones concretos

- **Pipes and Filters:** cada extractor/transformador es un filtro con contrato estable.
- **Blackboard:** el workspace en disco es la pizarra compartida donde los agentes publican y leen.
- **Strategy:** el `cleaner` selecciona parser según el formato de transcripción detectado.
- **Template Method + parametrización:** los diagramas Mermaid y el HTML ejecutivo son plantillas fijas
  que Python rellena; la IA nunca escribe sintaxis de render.
- **Single Source of Truth:** `construir_entregables()` centraliza el ensamblado para CLI y MCP; la
  rúbrica es la única fuente de verdad del scoring.

### 5.4 Principios de ingeniería de software

- **Responsabilidad única** por módulo (extraer ≠ construir ≠ redactar ≠ criticar ≠ renderizar).
- **Degradación con gracia:** las dependencias opcionales (pptx, pdf, OCR, docx) se degradan sin tumbar
  el pipeline; el HTML es stdlib puro y siempre está disponible.
- **Determinismo y testabilidad:** el núcleo corre sin LLM ni MCP (`python -m discovery_agents`), de modo
  que todo lo que ahorra tokens se prueba con `unittest` en Python 3.9.
- **DRY sin sobre-abstracción:** se unifica lo que divergía (ensamblado), se comparte lo que se repite
  (render por clave), y se acepta duplicación mínima inherente (markdown vs Word).

---

## 6. División de responsabilidades entre agentes (y por qué subagentes)

| Agente | Modelo | Responsabilidad única |
|---|---|---|
| **Orquestador** (Discovery Architect) | Copilot | Estrategia, despacho por fases, gates humanos |
| **Destilador** | IA económica | Convertir transcripciones limpias en evidencia estructurada |
| **Constructor** | IA fuerte | Mapear evidencia → schema tipado, sin inventar ni aplanar |
| **Generador de Hipótesis** | IA fuerte | Proponer arquetipos DataMesh derivables de las fuentes |
| **Crítico** | IA fuerte | Detectar brechas y formular preguntas poderosas sobre el score |
| **Redactor Experto** | IA fuerte | Narrativa empresarial + control intelectual (contradicciones) |

**¿Por qué subagentes y no un único prompt gigante?** Porque son habilidades en tensión. Mapear
evidencia a campos exige precisión y exhaustividad; redactar narrativa ejecutiva exige síntesis y
criterio; criticar exige escepticismo. Un solo prompt que hace todo degrada las tres. Separar además
permite usar **el modelo más barato que resuelva bien cada tarea** (destilar es barato; redactar es
caro) y dar a cada agente **solo el estado que necesita** (el Crítico lee el score, no la evidencia
cruda), lo que reduce contaminación de contexto y costo.

---

## 7. Cuándo Python y cuándo IA

La regla es simple y se aplica sin excepción:

- **Python (determinista, 0 tokens)** cuando el resultado es **calculable o verificable por reglas**:
  leer archivos, extraer texto/tablas, clasificar por convención, limpiar con regex seguro, consolidar
  JSONs, comparar números, puntuar contra una rúbrica, verificar citas, y **renderizar** (markdown,
  Word, HTML, Mermaid).
- **IA** cuando el resultado exige **comprensión, juicio o creatividad**: destilar lenguaje natural,
  mapear evidencia ambigua a estructura, generar hipótesis, criticar vacíos, redactar narrativa,
  sintetizar mensajes ejecutivos, y ver imágenes que el OCR no resolvió.

La frontera se mueve en una sola dirección: cuando la IA hace algo **repetitivo y mecánico** una y otra
vez, esa tarea se **promueve a Python**. Nunca al revés.

---

## 8. Cómo se optimiza el consumo de tokens

Cuatro mecanismos, medibles en `work/<caso>/_metrics.json`:

1. **Índices en vez de contenido.** La extracción persiste todo en disco y devuelve un índice compacto
   (~500 tokens) en lugar del paquete completo (que en un caso real serían ~70.000). El contenido se
   pide por ID y por *chunk*, solo lo que se va a razonar ahora.
2. **Entregables server-side.** El documento, el .docx, el HTML, los diagramas y las matrices se
   escriben a disco; **nunca viajan por el chat**.
3. **Modelo por tarea.** Económico para destilar/ver; fuerte solo para construir/idear/criticar/redactar.
4. **Incrementalidad.** `pending_distillation` evita re-destilar lo ya hecho; una reunión nueva solo
   re-destila esa y re-corre las fases finales sobre el estado.

Resultado estimado en un caso real (6 reuniones + docs + Excels): de ~180-230k tokens (mayoría modelo
fuerte) a ~100k (mayoría modelo económico) → **60-75% menos costo**.

## 9. Cómo se preserva el contexto

- **El estado vive en disco, no en la ventana.** El contexto es siempre reconstruible; una fase puede
  correr en un chat nuevo leyendo su índice + su *slice*.
- **Trazabilidad por ID.** Cada dato del documento cita `[E00x]` o `[E00x seg-NNN]`, auditable hasta el
  segmento original de la transcripción.
- **No destructivo.** El original de cada segmento se conserva; ante ambigüedad, el destilador pide el
  texto crudo.

## 10. Cómo se garantiza la calidad

- **Veredicto determinista** con validadores por tipo: un texto basura no "cuenta" como respondido (la
  volumetría debe tener números, la persona un nombre, la fuente un servidor).
- **Verificador de fidelidad** (`fidelidad.py`): mide qué porcentaje de los campos con dato citan
  evidencia real, detecta citas a IDs inexistentes y párrafos de narrativa sin anclar. El lector sabe
  exactamente qué está respaldado y qué no.
- **Detector de conflictos** que localiza contradicciones numéricas entre fuentes y las declara.
- **Recolector de temas faltantes** que reúne automáticamente todo lo no conocido (brechas de rúbrica,
  vacíos del redactor, supuestos sin validar) para que nada se pierda.
- **Suite de pruebas** determinista en Python 3.9: cleaner no destructivo, formatos de Teams, índice
  anti-token-bomb, validadores del scorer, narrativa-first, HTML standalone, ensamblado unificado.

---

## 11. Cómo se evita la redundancia y la pérdida de información

Son el mismo problema visto por sus dos caras: **la información se duplica o se pierde en las
costuras entre agentes**. Ninguna de las dos se resuelve pidiéndoselo a un modelo — se resuelven con
código, en cinco puntos del pipeline:

| Dónde | Qué hace | Por qué ahí |
|---|---|---|
| `knowledge/dedup.py` | Funde los ítems del destilado que dicen lo mismo y **une** sus procedencias | Un hecho dicho en tres reuniones es un hecho respaldado por tres evidencias, no tres hechos. |
| `knowledge/validador.py` | Verifica los tipos del schema antes de ensamblar | Una lista aplanada a texto no rompe el render: **lo vacía**, y nadie se entera hasta leer el documento. |
| `render/ensamblador.py` | Documento fusionado: una sección, un cuerpo | Elimina la duplicación por construcción, no por disciplina del redactor. |
| `knowledge/fidelidad.py` | Detecta párrafos casi idénticos entre secciones | La estructura evita repetir *datos*; esto detecta repetir *historias*. |
| `recolectar_temas_faltantes` | Reúne las cuatro fuentes de vacíos y las deduplica por similitud | La rúbrica, el Redactor y el Crítico describen el mismo vacío con palabras distintas. |

Y una regla de reparto: **la deduplicación fusiona, nunca descarta**. Al unir dos ítems se conserva
el enunciado más informativo y se suman sus evidencias; los grupos fundidos quedan registrados en
`consolidado.fusiones`. Una fusión que no se puede auditar es indistinguible de una pérdida de datos.

---

## 12. Cómo se manejan los errores

El sistema procesa insumos que no controla —archivos corruptos, formatos inesperados, entornos sin
librerías— y por eso su postura ante el fallo es explícita:

1. **Degradar antes que fallar.** Toda dependencia de terceros es opcional y se importa dentro de la
   función que la usa. Sin `python-docx` no hay Word, pero sí markdown, HTML y matrices.
2. **Un insumo malo no cuesta el Discovery.** El pipeline captura por elemento: el archivo ilegible
   genera una advertencia en el índice y el resto continúa.
3. **Nunca perder algo en silencio.** Un formato no soportado, un binario legacy sin LibreOffice o
   un OCR que no encontró texto **se declaran**. Un insumo ausente y declarado es un dato; un insumo
   ausente y callado es un error que aparecerá en la reunión de presentación.
4. **Fallar ruidosamente donde el silencio es caro.** Escribir fuera de la lista blanca lanza
   `ValueError`; un Discovery con los tipos rotos detiene el ensamblado con el detalle exacto. Son
   los dos casos en los que continuar produciría un entregable mutilado con apariencia de correcto.

---

## 13. Estructura del proyecto

```
discovery-agents/
├─ .github/
│  ├─ copilot-instructions.md      # reglas globales de trabajo para Copilot
│  └─ chatmodes/                    # 1 orquestador + 5 subagentes (punteros, no reglas)
├─ .vscode/mcp.json                 # registro del servidor MCP para VS Code
├─ discovery_agents/                # el sistema
│  ├─ __main__.py                   # python -m discovery_agents <comando>
│  ├─ workspace.py                  # la pizarra en disco (estado + chunking + métricas)
│  ├─ common/                       # vocabulario transversal, sin dependencias internas
│  │   citas · marcas · texto
│  ├─ ingest/                       # de carpeta de insumos a evidencia direccionable
│  │   registry (tabla única de formatos) · manifest · pipeline
│  │   ├─ extractores/              # 1 módulo por familia de formato
│  │   │   excel · documentos · presentaciones · imagenes
│  │   │   estructurados · correo · legacy · embebidos · transcripcion
│  │   └─ transcripciones/cleaner.py
│  ├─ knowledge/                    # contratos y evaluación: el corazón conceptual
│  │   schema · rubrica · scorer · fidelidad · validador · dedup · consolidador
│  ├─ render/                       # de estado a entregables (0 tokens)
│  │   ensamblador · estilos_word · docx_export · html_export
│  │   tablas · mermaid · entregables
│  │   └─ assets/executive.html     # plantilla ejecutiva reutilizable
│  ├─ prompts/                      # instrucción de cada subagente (única fuente de verdad)
│  └─ interfaces/                   # puertas de entrada, sin lógica de negocio
│      cli.py (3.9) · mcp_server.py (3.10+)
├─ docs/                            # BLUEPRINT · FILOSOFIA (este) · REVISION_INTEGRAL
├─ tools/                           # sync_docs · generar_bundle_databricks
├─ inputs/<caso>/                   # insumos (runtime; en .gitignore)
├─ work/<caso>/                     # estado + entregables (runtime; en .gitignore)
├─ tests/test_core.py
└─ README.md · requirements.txt
```

### Propósito de cada capa

Cada capa existe porque responde a **una pregunta distinta**, y la regla de dependencias impide que
se mezclen:

- **`common/`** — *¿qué vocabulario compartimos?* Citas, marcas de ausencia, comparación de texto.
  No importa ninguna otra capa. Si un módulo de aquí necesitara `knowledge/`, es que no era
  transversal y pertenecía allá.
- **`ingest/`** — *¿qué hay en la carpeta y qué dice?* Convierte cualquier formato en evidencia con
  ID. `registry.py` es la tabla única: añadir un formato es un extractor y una línea, no editar
  tres archivos que pueden discrepar.
- **`knowledge/`** — *¿qué sabemos y qué tan completo está?* El schema tipado, la rúbrica, el
  veredicto, la fidelidad, la deduplicación y la validación. El corazón conceptual del producto.
- **`render/`** — *¿cómo se ve?* La IA decide el contenido; aquí se decide el dibujo. Añadir un
  entregable es un módulo aquí y una línea en `entregables.py`.
- **`prompts/`** — *¿cómo razona cada agente?* Texto versionable, no incrustado en código. **Única
  fuente de verdad**: los chat modes solo apuntan aquí. Cuando una regla vivía en dos sitios, las
  copias divergían y la más débil era la que el modelo leía primero.
- **`interfaces/`** — *¿por dónde se entra?* CLI y MCP, ambas sobre las mismas funciones. Cuando
  divergieron, el camino primario producía un entregable inferior sin que nadie lo notara.
- **`work/<caso>/`** — la memoria. Los prefijos numéricos (`00_` → `65_`) marcan el orden de fase.

### Convenciones

- **Español** en código, prompts, salidas y documentos: es la lengua del dominio y de los insumos.
- **Marcas de ausencia** explícitas: `PENDIENTE` (el equipo debe definirlo) vs `DESCONOCIDO` (no
  surgió en los insumos) vs `[]`. Las dos cuentan como "sin dato" al puntuar.
- **Citas** `[E00x]` / `[E00x seg-NNN]` en todo dato factual; `[inferencia de E00x]` si se deduce.
- **Tipos del schema** respetados: listas de objetos, nunca texto aplanado.
- **Archivos de estado** con prefijo numérico por fase; la escritura de los agentes está restringida
  por lista blanca.
- **Módulos nombrados por responsabilidad, no por tecnología** (`estilos_word`, no `docx_utils`).
  Esta regla motivó el renombrado del paquete: `mcp_server/` describía una de sus dos puertas de
  entrada, no lo que el sistema es.
- **0 tokens** es el objetivo por defecto de todo lo que se pueda calcular.

---

## 14. Cómo debe evolucionar el agente

- **Nuevos formatos de insumo** → un extractor con `extraer(ruta)` + una línea en
  `ingest/registry.FORMATOS`; nunca meter el parsing en la IA.
- **Nuevos entregables** → nuevo módulo en `render/` + una línea en `entregables.py`; la plantilla es
  fija y Python inyecta lo dinámico.
- **Nuevos campos del Discovery** → ampliar el schema tipado, la rúbrica (calibrando obligatoriedad para
  no degradar veredictos existentes), los validadores del scorer y el render.
- **Nuevas secciones del documento** → una entrada en `schema.SECCIONES`; el ensamblador y el
  exportador Word la recogen solos, incluida la supresión si queda vacía.
- **Otra identidad visual** → los tokens del bloque MARCA en `assets/executive.html`. El Python no
  se toca: por eso la plantilla es una plantilla y no un generador de HTML.
- **Migrar trabajo de IA a Python** cada vez que se observe a un modelo haciendo algo mecánico y
  repetitivo; registrar el ahorro en `_metrics.json`.
- **Mantener los gates humanos.** La automatización sirve al juicio humano; no lo reemplaza.
- **Cada mejora parte del análisis de lo existente**, reutiliza capacidades actuales y evita duplicar.
  El sistema se **evoluciona**, no se reescribe.

> Regla de oro para cualquier cambio futuro: *si la IA lo puede inventar, el sistema no debe permitirlo;
> si Python lo puede calcular, la IA no debe pagarlo.*
