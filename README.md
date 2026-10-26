# Discovery Agents

![Versión](https://img.shields.io/badge/versi%C3%B3n-4.0.0-blue)
![Python](https://img.shields.io/badge/python-3.9%2B%20(MCP%203.10%2B)-blue)
![Pruebas](https://img.shields.io/badge/pruebas-83%20OK-brightgreen)
![Licencia](https://img.shields.io/badge/licencia-propietaria-lightgrey)

> **En una frase:** le entregas una carpeta con todo lo que se sabe de un proyecto de datos
> —documentos, notas, correos, reuniones de Teams, un Excel de fuentes— y Discovery Agents te
> devuelve un **Discovery profesional**: un documento Word, un resumen ejecutivo para líderes,
> diagramas, tablas y un **veredicto claro: Go, Condicional o No-Go**. Cada dato cita el archivo del
> que salió, nada se inventa y el veredicto lo calcula una regla fija, no una opinión.

**Cómo leer este documento.** Si no eres técnico, lee las secciones 1 a 8 (y abre la guía visual
[docs/como_funciona_el_agente.html](docs/como_funciona_el_agente.html) en tu navegador). Si vas a
usarlo, lee de la 9 a la 11. Si lo vas a mantener o extender, lee la 12 y la 13 y los documentos de
[`docs/`](docs/). Las palabras técnicas se explican en el [glosario](#17-glosario).

## Tabla de contenido

1. [¿Qué es Discovery Agents?](#1-qué-es-discovery-agents)
2. [El problema que resuelve](#2-el-problema-que-resuelve)
3. [¿Para quién es?](#3-para-quién-es)
4. [El equipo: quién hace qué](#4-el-equipo-quién-hace-qué)
5. [Cómo trabaja: fases y puntos de control](#5-cómo-trabaja-fases-y-puntos-de-control)
6. [Cómo decide: el veredicto](#6-cómo-decide-el-veredicto)
7. [Qué necesita: la carpeta de insumos](#7-qué-necesita-la-carpeta-de-insumos)
8. [Qué entrega](#8-qué-entrega)
9. [Requisitos e instalación](#9-requisitos-e-instalación)
10. [Cómo usarlo](#10-cómo-usarlo)
11. [Ejemplo de principio a fin](#11-ejemplo-de-principio-a-fin)
12. [Por dentro: workspace, herramientas y principios](#12-por-dentro-workspace-herramientas-y-principios)
13. [Estructura del repositorio y pruebas](#13-estructura-del-repositorio-y-pruebas)
14. [Seguridad y privacidad](#14-seguridad-y-privacidad)
15. [Preguntas frecuentes](#15-preguntas-frecuentes)
16. [Solución de problemas](#16-solución-de-problemas)
17. [Glosario](#17-glosario)
18. [Historia de versiones, autoría y licencia](#18-historia-de-versiones-autoría-y-licencia)

---

## 1. ¿Qué es Discovery Agents?

Antes de construir un producto de datos (un tablero, un modelo, una tabla consolidada en la nube)
hay que hacer un **Discovery**: una etapa de investigación para entender qué problema resuelve, quién
lo pide, de dónde salen los datos, qué falta y si es viable. Normalmente eso toma semanas de
reuniones, notas sueltas y un documento que alguien redacta a mano.

**Discovery Agents automatiza la parte más pesada de ese trabajo: leer, ordenar, cruzar y redactar.**
Funciona como un pequeño equipo de consultoría dentro de GitHub Copilot, y está construido en **tres
capas**:

| Capa | Qué es | Dónde está | ¿Usa IA? |
|---|---|---|---|
| **Los agentes** (el razonamiento) | Un orquestador y cinco especialistas de IA, cada uno con una sola tarea. Se usan desde GitHub Copilot en VS Code | `.github/chatmodes/` y `discovery_agents/prompts/` | Sí |
| **Las herramientas** (lo mecánico) | Un programa Python que abre archivos, limpia transcripciones, compara cifras, calcula el veredicto y arma el Word, el HTML, los diagramas y las tablas | `discovery_agents/` | No: es rápido, gratis de operar y con los mismos datos siempre da el mismo resultado |
| **El workspace** (la memoria) | Una carpeta en disco (`work/<caso>/`) donde cada fase deja su resultado para que la siguiente lo lea | `work/<caso>/` (se crea sola) | No |

La idea que lo gobierna cabe en una línea: ***lo que se puede calcular, no se prompea***. La IA se
reserva para lo que solo ella hace bien (razonar, sintetizar, redactar, criticar) y todo lo demás lo
resuelve código barato y verificable. El objetivo: **calidad de consultor senior a costo de script.**

> **No es un resumidor.** Un resumidor encoge documentos. Discovery Agents es un *consolidador*:
> funde información de formatos distintos en un modelo único, detecta contradicciones entre las
> fuentes, mide qué tan completo está el caso contra una rúbrica experta y recomienda si conviene
> avanzar.

## 2. El problema que resuelve

| Sin Discovery Agents | Con Discovery Agents |
|---|---|
| La información llega dispersa y en formatos incompatibles; consolidarla a mano es lento y se pierde contexto entre reuniones | Una sola carpeta de insumos; el sistema lee Excel, Word, PDF, PowerPoint, correos, transcripciones, imágenes y más |
| Los documentos resultan formularios rellenados: repiten datos, se contradicen entre secciones y mezclan lo que se sabe con lo que se supone | Un documento **fusionado**: cada hecho aparece una sola vez, en su sección, y lo que no se sabe se declara aparte |
| La factibilidad depende del criterio de quien redacta | El veredicto Go / Condicional / No-Go lo calcula una **regla reproducible**; con los mismos insumos siempre es el mismo |
| Dos fuentes dicen cifras distintas y nadie lo nota | Un detector de **conflictos numéricos** los declara en el documento; nunca elige una versión en silencio |
| Volcar todo a un modelo de IA es caro y el modelo inventa cuando no tiene el dato | Un **índice compacto** reemplaza al volcado completo (≈ 423 tokens en lugar de ≈ 70 000, medido en un caso real) y cada afirmación cita su fuente (`[E003]`) |
| Cuando llega una reunión nueva hay que rehacer todo | El proceso es **incremental y reanudable**: solo se procesa lo nuevo |
| Nadie puede verificar de dónde salió un dato | Un **validador de fidelidad** mide qué porcentaje del texto está respaldado por una fuente real |

## 3. ¿Para quién es?

| Rol | Qué obtiene |
|---|---|
| **Analista de negocio / Product Owner** | Un borrador completo del Discovery en horas, con preguntas poderosas listas para hacerle al negocio, y puntos de control para corregir antes de que se redacte nada |
| **Líderes y patrocinadores** | Un resumen ejecutivo de una página (un solo archivo HTML) con el veredicto, los mensajes clave, los riesgos y los pendientes |
| **Ingenieros de datos** | La Parte II del documento: fuentes con columnas, servidor y librerías, habilitación técnica, dependencias y expertos |
| **Equipo técnico que lo instala** | Un paquete Python sin dependencias obligatorias de IA, una CLI para probar todo lo mecánico y un servidor MCP para Copilot |
| **Quien lo mantiene o extiende** | Una arquitectura por capas, 83 pruebas, y los documentos de filosofía y de reconstrucción completa en `docs/` |

## 4. El equipo: quién hace qué

"El agente" son en realidad **siete miembros**. Cada uno tiene una sola tarea, como en una firma de
consultoría. En Copilot aparecen como modos de chat que se pueden elegir.

| Miembro | Equivale a… | Qué hace | Modelo recomendado | Dónde |
|---|---|---|---|---|
| **Orquestador** ("Discovery Architect") | El jefe de proyecto | Revisa qué trajiste, propone un plan, reparte el trabajo en el orden correcto y te consulta en los momentos de decisión. Es con quien hablas | El del chat | `orquestador-discovery.chatmode.md` |
| **Destilador de transcripciones** | Quien toma las minutas | Convierte cada transcripción de Teams en hechos concretos: decisiones, hallazgos, datos de fuentes, procesos actuales, reglas, preguntas abiertas y acciones. Solo procesa las reuniones nuevas | El **más económico** disponible | `destilador-transcripciones` |
| **Constructor de Discovery** | El analista que arma la ficha | Llena la ficha estándar (el *schema* tipado de 45 campos): objetivo, alcance, personas, fuentes, volúmenes, dependencias. Lo que no aparece en los insumos queda `PENDIENTE` o `DESCONOCIDO` | Razonamiento **fuerte** | `constructor-discovery` |
| **Generador de hipótesis** | El estratega | Propone hipótesis falsables y arquetipos *Data Mesh* que las mismas fuentes podrían habilitar | Razonamiento **fuerte** | `generador-hipotesis` |
| **Crítico / Analista de brechas** | El auditor | Busca huecos y ambigüedades sobre el puntaje y formula las **preguntas poderosas** que alguien debe responder antes de avanzar | Razonamiento **fuerte** | `critico-brechas` |
| **Redactor experto** | El consultor senior | Escribe la narrativa para ejecutivos y técnicos (cómo se trabaja hoy, cómo se trabajará, factibilidad con talla S/M/L/XL), detecta contradicciones y aporta los mensajes clave del resumen ejecutivo. Es el núcleo intelectual | El **más fuerte** disponible | `redactor-experto` |
| **Asistente mecánico** (Python) | El archivista con calculadora | Todo lo repetitivo y calculable: abrir archivos, limpiar transcripciones, comparar cifras, calcular el veredicto, armar el Word, el HTML, los diagramas y las tablas | No usa IA | `discovery_agents/` |

Las reglas de cada subagente viven en **un solo lugar**: `discovery_agents/prompts/*.md`. Los modos de
chat de `.github/chatmodes/` solo dicen qué modelo usar y por dónde empezar y apuntan a esos prompts
(`get_subagent_prompt`). Cuando una regla estaba escrita en dos sitios, las copias divergían.

**¿Por qué varios especialistas y no un único prompt gigante?** Porque son habilidades en tensión:
mapear evidencia a campos exige precisión; redactar exige síntesis; criticar exige escepticismo. Un
solo prompt que lo hace todo degrada las tres cosas. Separarlos permite además usar **el modelo más
barato que resuelva bien cada tarea** y darle a cada uno **solo el estado que necesita**.

## 5. Cómo trabaja: fases y puntos de control

El sistema avanza por **ocho fases (F0 a F7)** y se detiene en **tres puntos de control humano (G0,
G1 y G2)**, porque corregir pronto es barato y corregir al final es caro.

```text
 insumos ─► F0 Estrategia ─► F1 Extracción ─► F2 Destilado ─► F3 Construcción ─► F4 Hipótesis
              [G0 tú]                          y consolidación    [G1 tú]
 ┌──────────────────────────────────────────────────────────────────────────────────┐
 └─► F5 Puntaje y crítica ─► F6 Redacción ─► F7 Ensamblado ─► [G2 tú] ─► compartir
```

| Fase | Qué pasa, en palabras simples | Quién lo hace | Herramienta / archivo que deja |
|---|---|---|---|
| **F0** | Lista los archivos **sin abrirlos**, te dice qué parece faltar y propone un plan: qué especialistas intervienen y en qué orden | Python + orquestador | `build_manifest_tool` → `00_manifest.json` |
| **G0** | **Tú validas la estrategia** antes de que empiece el trabajo pesado | Persona | — |
| **F1** | Extrae el contenido de cada archivo, limpia las muletillas de las transcripciones **sin alterar el original** y asigna a cada documento un código de evidencia (`E001`, `E002`…) | Python (0 tokens) | `extract_evidence` → `10_evidence/` |
| **F2** | El Destilador convierte **solo las transcripciones nuevas** en hechos; luego Python junta todo, **elimina repeticiones uniendo su procedencia** y **detecta conflictos numéricos** entre fuentes | IA económica + Python | `20_destilado/DE0xx.json`, `consolidado.json` |
| **F3** | El Constructor llena la ficha tipada del proyecto | IA fuerte | `30_discovery.json` |
| **G1** | **Tú corriges los hechos** (nombres, cifras, responsables) antes de que se redacte nada | Persona | — |
| **F4** | Hipótesis y arquetipos Data Mesh | IA fuerte | `40_hipotesis.json` |
| **F5** | Python calcula el **puntaje y el veredicto**; el Crítico revisa los vacíos y escribe las preguntas poderosas | Python + IA fuerte | `55_score.json`, `50_critica.json` |
| **F6** | El Redactor escribe la narrativa y detecta contradicciones | IA fuerte | `60_redaccion.json`, `60_inconsistencias.json` |
| **F7** | Python valida la forma del Discovery y **ensambla todos los entregables** (Word, HTML, Markdown, diagramas, tablas, brechas, veredicto) | Python (0 tokens) | `outputs/` y `65_fidelidad.json` |
| **G2** | **Tú apruebas** el documento antes de compartirlo | Persona | — |

Las fases son **reanudables e incrementales**: si agregas una transcripción nueva, `pending_distillation`
dice cuáles faltan por destilar y solo esas se procesan; después se vuelven a correr las fases
finales sobre el estado ya construido.

## 6. Cómo decide: el veredicto

**La IA no decide si el proyecto avanza.** El veredicto lo calcula `discovery_agents/knowledge/scorer.py`
con una rúbrica de **39 preguntas** agrupadas en **seis bloques**. Cada pregunta corresponde a un
campo de la ficha; se cuenta como respondida solo si tiene **datos reales**.

| Bloque | Peso (suma 100) | ¿Crítico? | Preguntas (obligatorias) | Ejemplos de lo que pregunta |
|---|---|---|---|---|
| Fuentes y datos | 22 | Sí | 9 (7) | ¿Qué tablas hay que llevar a la nube? ¿En qué servidor? ¿Cuántos registros por tabla? ¿Con qué frecuencia se actualizan? ¿Hay datos sensibles? |
| Negocio / Caso de uso | 20 | Sí | 11 (8) | ¿Cuál es el problema de negocio? ¿Objetivo? ¿Alcance incluido y excluido? ¿KPIs? ¿Quiénes consumen? |
| Técnico / Habilitación | 18 | Sí | 4 (2) | ¿Qué hay que habilitar para ponerlo en línea? ¿Dependencias y accesos? |
| Gobierno / Roles | 15 | Sí | 8 (5) | ¿Quién solicita? ¿Quién es el dueño y el Product Owner? ¿Quién desarrolla? ¿Quiénes son los expertos del dato? |
| Hipótesis y valor | 15 | No | 3 (2) | ¿Cuáles son las hipótesis y cómo se validan? ¿Qué arquetipos Data Mesh podría habilitar? |
| Riesgos y factibilidad | 10 | Sí | 4 (1) | ¿Qué impedimentos hay abiertos y quién los resuelve? |

**Cómo se calcula.** La completitud de cada bloque es el porcentaje de sus preguntas **obligatorias**
respondidas; la completitud total es el promedio ponderado por el peso. Las preguntas opcionales no
bajan el puntaje, pero aparecen como brechas recomendadas.

**Los tres veredictos:**

| Veredicto | Cuándo | Qué significa |
|---|---|---|
| ✅ **Go** | Completitud **≥ 85 %** y **todos los bloques críticos completos** | Se puede avanzar a construir |
| 🟡 **Condicional** | Entre 60 % y 85 %, o algún bloque crítico incompleto | Se avanza solo si se cumplen las condiciones listadas |
| ⛔ **No-Go** | Menos de **60 %**, o **más de 4 condiciones** abiertas | Hay que volver a recoger información antes de seguir |

Las **condiciones para avanzar** son las preguntas obligatorias de bloques críticos que siguen sin
respuesta.

**Por qué no se puede "engañar" al puntaje.** Cada respuesta pasa por un validador de calidad mínima:

- La **volumetría** solo cuenta si **todas** las fuentes traen un número ("la tabla es grande" no es
  una volumetría).
- El **servidor de origen** solo cuenta si todas las fuentes lo indican.
- Una **persona** solo cuenta si trae un nombre real: un rol sin nombre no tiene a quién preguntarle.
- Las marcas de ausencia `PENDIENTE` y `DESCONOCIDO` cuentan como "sin dato". Un expediente lleno de
  `DESCONOCIDO` **no puede** alcanzar Go, y así debe ser.

## 7. Qué necesita: la carpeta de insumos

Creas una carpeta con el nombre del caso dentro de `inputs/` y repartes los archivos en subcarpetas.
**No hace falta tenerlas todas**: mientras más completa, mejor el resultado, y lo que falte el sistema
lo marca como pendiente en lugar de inventarlo.

```text
inputs/mi_caso/
├─ caso_de_uso/         la necesidad, el objetivo y el alcance (Word, PDF, PowerPoint, Markdown o texto)
├─ discovery_inicial/   notas de la entrevista inicial
├─ discovery_tecnico/   notas técnicas, lógica de negocio, consultas SQL
├─ transcripciones/     reuniones de Teams: .vtt, .docx o texto
├─ hallazgos/           impedimentos, dependencias con otras áreas, correos, accesos pendientes
├─ fuentes/             el Excel con las tablas a llevar a la nube
└─ imagenes/            diagramas y capturas de pantalla
```

Las carpetas se reconocen por su nombre exacto. Un `.docx` o `.txt` dentro de `transcripciones/` se
trata como transcripción, no como documento.

**El Excel de fuentes** es el insumo que más valor aporta a la parte técnica. Basta una hoja con estos
encabezados:

| Tabla | Servidor | Volumetría | Frecuencia | Sensible |
|---|---|---|---|---|
| ventas_detalle | SRV-ONPREM-01 | 400M registros | Diaria | No |
| clientes | SRV-CRM | 2.5M registros | Semanal | Sí |
| catalogo_productos | SRV-ONPREM-01 | 15 mil registros | Mensual | No |

*(Filas de ejemplo.)* La volumetría puede escribirse como "400M" o "300 millones": el sistema entiende
ambas, y si dos fuentes difieren en más de un 10 % lo declara como conflicto.

**Transcripciones de Teams.** Se reconocen automáticamente tres formatos: archivos **VTT** con las
etiquetas `<v Hablante>`, la transcripción **.docx** de Teams (el nombre y la hora, como
`Nombre Apellido   0:15`, en su propia línea) y texto genérico con el formato `Hablante: texto`. La
limpieza solo elimina interjecciones inequívocas ("eh", "mmm") y las muletillas ambiguas únicamente
al inicio de la intervención y seguidas de coma, de modo que "este servidor", "tipo de datos" y "no
es cierto" **quedan intactos**. El original de cada segmento siempre sigue accesible.

### 7.1 Formatos soportados

El sistema reconoce **45 extensiones** en ocho familias. Puedes verlas con
`python -m discovery_agents formatos`.

| Familia | Extensiones | Necesita (opcional) |
|---|---|---|
| Excel | `.xlsx` `.xlsm` | `openpyxl` |
| PowerPoint | `.pptx` `.pptm` | `python-pptx` |
| Documentos | `.docx` `.docm` `.pdf` `.txt` `.md` `.markdown` `.csv` `.tsv` `.rtf` `.html` `.htm` | `python-docx`, `pypdf` |
| Transcripciones | `.vtt` `.srt` | — |
| Imágenes | `.png` `.jpg` `.jpeg` `.gif` `.bmp` `.webp` `.tif` `.tiff` `.heic` `.heif` `.svg` | `pytesseract` (y el programa `tesseract`) para OCR; `pillow-heif` para fotos de iPhone |
| Estructurados | `.json` `.yaml` `.yml` `.xml` `.drawio` `.sql` `.ddl` `.toml` `.ini` `.cfg` `.log` `.ipynb` | `PyYAML` para YAML |
| Correo | `.eml` `.msg` | `extract-msg` para `.msg` de Outlook |
| Formatos antiguos | `.xls` `.doc` `.ppt` | LibreOffice (`soffice`), que los convierte al vuelo |

**Todas las dependencias opcionales degradan con gracia:** si falta una, el insumo se registra con un
**aviso en el índice** y el resto del trabajo continúa. Un formato no soportado o ilegible se declara,
nunca se pierde en silencio. Las imágenes se leen primero por OCR; solo las que el OCR no resuelve se
marcan `requiere_vision_llm` para que un modelo con visión las vea.

## 8. Qué entrega

Todo queda en `work/<caso>/outputs/`. El documento principal está pensado para dos públicos a la vez,
así que se divide en **dos vistas del mismo Discovery más un cierre**.

**Estructura del documento** (`discovery_final.docx` y `.md`):

| Parte | Para quién | Secciones |
|---|---|---|
| **Resumen ejecutivo** | Todos | Síntesis del caso |
| **Parte I — Discovery inicial (negocio)** | Líderes y negocio | Contexto y problemática actual · Necesidad, objetivo y alcance · Beneficios esperados · Proceso actual y proceso futuro · Gobierno del producto de datos |
| **Parte II — Discovery técnico (datos y habilitación)** | El equipo que lo construirá | Sistemas fuente y volumetría · Datos, lógica de negocio y calidad · Datos sensibles y controles de seguridad · Hallazgos técnicos y productos relacionados · Expertos técnicos y por país · Habilitación técnica, dependencias y accesos · Restricciones y supuestos · Riesgos identificados · Hipótesis de valor y arquetipos Data Mesh |
| **Cierre — Evaluación, veredicto y temas faltantes** | Todos | Evaluación de factibilidad y complejidad · Veredicto y recomendación · Temas faltantes y deuda técnica · Cobertura de evidencia · Información no capturada |

Una sección sin información **no se imprime llena de "PENDIENTE"**: se recoge en una lista única de lo
no capturado. Y "no se identificaron riesgos" se escribe completo, porque es información (ausencia de
evidencia de riesgo, no garantía de que no existan).

**Archivos entregados** (17 en el caso de demostración):

| Archivo | Qué es |
|---|---|
| `discovery_final.docx` | El documento completo en Word, narrativo y con tablas solo donde aportan (fuentes, riesgos, certificadores, hallazgos técnicos). Con portada, índice navegable y estilos propios |
| `resumen_ejecutivo.html` | **Resumen ejecutivo para líderes**: veredicto, mensajes clave, riesgos principales, completitud por bloque, fuentes y pendientes. Un solo archivo que se abre en cualquier navegador, sin internet, adaptable a móvil, con tema claro y oscuro y un acento de color según el veredicto (verde Go, ámbar Condicional, rojo No-Go). No es una copia del Word |
| `discovery_final.md` | La misma versión en texto, cómoda para guardar en un repositorio |
| `veredicto.json` | Go, Condicional o No-Go, con la completitud total y por bloque y las condiciones para avanzar |
| `brechas.md` | Qué falta, en dos listas: 🔴 **bloqueantes** (responder antes de avanzar) y 🟠 **recomendadas** |
| `diagramas/` (4) | Diagramas Mermaid: flujo de los datos, fuentes agrupadas por servidor, mapa de dominios (Data Mesh) y un modelo preliminar de entidades |
| `tablas/` (8) | Inventario de fuentes (con columnas, librerías y servidor) y matrices de riesgos, dependencias, supuestos y restricciones, decisiones pendientes, hallazgos técnicos, temas faltantes y **trazabilidad** de cada dato hasta su evidencia |

Además, en `work/<caso>/` queda `65_fidelidad.json` (el validador de fidelidad) y `55_score.json` (el
puntaje detallado).

## 9. Requisitos e instalación

### 9.1 Requisitos

| Requisito | Detalle | ¿Obligatorio? |
|---|---|---|
| **Python 3.9 o superior** | Para el núcleo mecánico y la CLI (`python -m discovery_agents`) | Sí |
| **Python 3.10 o superior** | Para el servidor MCP (el SDK `mcp[cli]` lo exige). Es el que usa Copilot | Sí, para el flujo con agentes |
| **VS Code + GitHub Copilot** | Con los modos de chat / agentes personalizados | Sí, para el flujo con agentes |
| `openpyxl`, `python-docx` | Leer Excel y generar el Word | Recomendadas (el resto de entregables se genera sin ellas) |
| Opcionales | `python-pptx`, `pypdf`, `PyYAML`, `extract-msg`, `pytesseract` + `tesseract`, `Pillow`, `pillow-heif`, LibreOffice | Cada una habilita un formato; ver la sección 7.1 |

Todo está en [`requirements.txt`](requirements.txt), con cada dependencia comentada.

### 9.2 Instalación paso a paso

```bash
# 1. Obtén el repositorio
git clone https://github.com/luisdgo2000/discovery-agents.git
cd discovery-agents

# 2. Crea un entorno virtual (recomendado) con Python 3.10 o superior
python3 -m venv .venv
source .venv/bin/activate          # en Windows: .venv\Scripts\activate

# 3. Instala las dependencias
pip install -r requirements.txt

# 4. Comprueba que todo funciona
python -m discovery_agents formatos                                   # lista de formatos y dependencias detectadas
PYTHONPATH="$PWD" python -m unittest discover -s tests               # 83 pruebas, deben pasar
```

El resultado esperado del paso 4 es `Ran 83 tests … OK`.

> **Si solo tienes Python 3.9** (por ejemplo, el Python del sistema en un Mac): el núcleo y la CLI
> funcionan, así que puedes probar todo lo mecánico, pero el SDK `mcp` no se puede instalar y por eso
> no podrás usar el flujo de agentes en Copilot hasta tener Python 3.10+. Sin el SDK, el servidor
> responde con un mensaje claro en lugar de fallar.

### 9.3 Conectar con GitHub Copilot

1. Abre la carpeta del repositorio en VS Code (con el entorno virtual activo, para que `python` sea el
   de Python 3.10+ con `mcp` instalado).
2. El servidor MCP queda registrado por [`.vscode/mcp.json`](.vscode/mcp.json): se ejecuta como
   `python -m discovery_agents.interfaces.mcp_server` dentro de la carpeta del proyecto. Si no arranca
   solo, inícialo desde la lista de servidores MCP de VS Code.
3. En el chat de Copilot, elige el modo **Orquestador Discovery**.

Los modos de chat se encuentran en `.github/chatmodes/`. Desde la versión 1.106, VS Code llama a estos
archivos *agentes personalizados* (`.github/agents/*.agent.md`); sigue reconociendo los
`.chatmode.md` antiguos y ofrece migrarlos. Si en tu versión no aparecen, consulta la
[solución de problemas](#16-solución-de-problemas).

## 10. Cómo usarlo

### 10.1 Con GitHub Copilot (el flujo completo)

1. **Prepara los insumos** en `inputs/<tu_caso>/` (ver la [sección 7](#7-qué-necesita-la-carpeta-de-insumos)).
2. En el chat de Copilot, con el modo **Orquestador Discovery**, escribe:

   > Construye el discovery de `inputs/<tu_caso>`

3. **G0 — Estrategia.** El orquestador lista los archivos y **emite primero una "estrategia
   sugerida"**: qué especialistas intervendrán y en qué orden, qué insumos parecen faltar, los riesgos
   y los atajos de eficiencia. Espera tu confirmación antes de seguir.
4. **F1 y F2.** El sistema extrae la evidencia, destila las transcripciones y consolida. Verás un
   índice compacto, no el contenido.
5. **G1 — Hechos.** Tras construir la ficha, el orquestador te presenta un resumen del borrador
   (roles, fuentes, conflictos, pendientes) y **te pide corregir los hechos** antes de redactar.
   Corregir aquí es barato; después es caro.
6. **F4 a F7.** Hipótesis, puntaje y crítica, redacción y ensamblado.
7. **G2 — Aprobación.** Recibes el veredicto, la completitud, las condiciones para avanzar, los
   conflictos declarados y las preguntas poderosas pendientes. **Nada se comparte hasta que lo apruebes.**

Si ya hay estado en `work/<caso>/` de una corrida anterior, el orquestador retoma desde la fase
pendiente en lugar de reprocesar todo.

### 10.2 Sin Copilot: la CLI determinista

Todo lo mecánico (lo que ahorra tokens) se puede ejecutar y verificar **sin Copilot, sin MCP y sin IA**,
con Python 3.9+:

```bash
python -m discovery_agents manifest   inputs/<caso>           # inventario clasificado de la carpeta
python -m discovery_agents evidencia  inputs/<caso> [caso]    # extrae y guarda la evidencia; imprime el índice
python -m discovery_agents get        <caso> <E0xx> [chunk]   # contenido de una evidencia, por partes
python -m discovery_agents pendientes <caso>                  # transcripciones sin destilar
python -m discovery_agents consolidar <caso>                  # une destilados, deduplica y detecta conflictos
python -m discovery_agents validar    <caso>                  # forma de 30_discovery.json
python -m discovery_agents score      <caso>                  # veredicto determinista
python -m discovery_agents ensamblar  <caso> [nombre]         # Word + HTML + MD + brechas + diagramas + tablas
python -m discovery_agents formatos                           # extensiones soportadas y dependencias
python -m discovery_agents rubrica                            # rúbrica de preguntas poderosas
python -m discovery_agents schema                             # contrato tipado de la ficha del Discovery
```

Las fases de **razonamiento** (destilar, construir, hipótesis, crítica y redacción) las hacen los
agentes; sin ellos, la CLI sirve para ejecutar lo mecánico (el manifiesto F0, la extracción F1, la
consolidación, el puntaje F5 y el ensamblado F7) sobre un estado que ya tengas, y para inspeccionar
cada pieza. Si ejecutas `python -m discovery_agents` sin argumentos (o con un comando desconocido),
imprime esta ayuda.

La carpeta de trabajo es `./work` en el directorio desde el que ejecutas; puedes cambiarla con la
variable de entorno `DISCOVERY_WORK_ROOT`.

### 10.3 Para Databricks

`tools/generar_bundle_databricks.py` genera `discovery-agents-databricks.py`, un notebook de
Databricks que, al ejecutarse, **reconstruye el proyecto archivo por archivo** (como descomprimir un
`.zip`) para llevarlo a un entorno con GitHub Copilot y MCP. No ejecuta los agentes; solo transporta
el proyecto. Es un artefacto derivado y está en el `.gitignore`: se regenera con
`python tools/generar_bundle_databricks.py`.

## 11. Ejemplo de principio a fin

El repositorio incluye dos casos de demostración con datos de ejemplo: `inputs/caso_demo` y
`inputs/discovery_demo`. Las salidas siguientes son **reales**; se abrevian las rutas y los nombres de
personas, y algunos JSON se condensan para que quepan.

### 11.1 Los insumos

`inputs/discovery_demo/` contiene seis archivos de cinco tipos:

```text
inputs/discovery_demo/
├─ caso_de_uso/descripcion.md
├─ discovery_tecnico/carga_incremental.sql
├─ fuentes/inventario_volumetria.xlsx
├─ hallazgos/acuerdo_replica.eml
└─ transcripciones/
   ├─ sesion_negocio_01.txt
   └─ sesion_tecnica_02.txt
```

### 11.2 F0 y F1: el manifiesto y la evidencia (sin IA)

```bash
python -m discovery_agents manifest inputs/discovery_demo
```

```text
"total_items": 6,
"por_categoria": {"fuente": 1, "caso_de_uso": 1, "transcripcion": 2, "discovery_tecnico": 1, "hallazgo": 1},
"por_extractor": {"excel": 1, "documento": 1, "transcripcion": 2, "estructurado": 1, "correo": 1}
```

```bash
python -m discovery_agents evidencia inputs/discovery_demo mi_caso
```

El sistema asigna un código a cada insumo y devuelve solo un **índice compacto** (el contenido se pide
después, por partes, solo cuando se va a razonar sobre él):

```text
E001  excel          inventario_volumetria.xlsx  Excel: 3 fuentes detectadas en 1 hoja(s)
E002  documento      descripcion.md              Documento: 13 párrafos, 797 chars
E003  transcripcion  sesion_negocio_01.txt       Transcripción (txt_teams): 4 segmentos, … reducción 5.9%
E004  transcripcion  sesion_tecnica_02.txt       Transcripción (txt_teams): 4 segmentos, … reducción 6.0%
E005  estructurado   carga_incremental.sql       SQL: 4 tabla(s) referenciada(s)
E006  correo         acuerdo_replica.eml         Correo de …: Acuerdo - replica no transaccional para adquirencia
```

Además, del Excel el índice trae las **fuentes detectadas** ya tipadas (hoja, tabla, esquema, servidor,
volumetría, frecuencia, campos y si es sensible). Y le dice al orquestador qué falta destilar:

```bash
python -m discovery_agents pendientes mi_caso
```

```json
{"pendientes": ["E003", "E004"]}
```

### 11.3 F2 a F6: el trabajo de los agentes

El Destilador convierte **E003** y **E004** en hechos y Python consolida; el Constructor llena la
ficha; se corrige en G1; el Crítico y el Redactor hacen su trabajo. Cada uno deja su resultado en
`work/mi_caso/` (ver la [sección 12.1](#121-el-workspace-de-cada-caso)).

### 11.4 F5 y F7: el veredicto y los entregables (sin IA)

Con el estado de un caso de demostración ya construido:

```bash
python -m discovery_agents validar discovery_demo
python -m discovery_agents score discovery_demo
python -m discovery_agents ensamblar discovery_demo "Replica de adquirencia"
```

```text
{"valido": true, "errores": [], "avisos": [], "claves_desconocidas": []}
Veredicto: Go (100.0%) — 1 brechas
Veredicto: Go (100.0%) — 1 brechas, 6 temas faltantes — narrativa incluida
Fidelidad: 100.0% de cobertura de evidencia
Entregables (17) en work/discovery_demo/outputs/
```

El `veredicto.json` resultante:

```json
{
  "caso_de_uso": "Replica de adquirencia",
  "veredicto": "Go",
  "completitud_total": 100.0,
  "condiciones_para_avanzar": [],
  "n_brechas": 1,
  "n_temas_faltantes": 6,
  "bloques": [
    {"titulo": "Negocio / Caso de uso", "completitud": 100.0, "critico": true},
    {"titulo": "Gobierno / Roles", "completitud": 100.0, "critico": true},
    {"titulo": "Fuentes y datos", "completitud": 100.0, "critico": true},
    {"titulo": "Técnico / Habilitación", "completitud": 100.0, "critico": true},
    {"titulo": "Hipótesis y valor", "completitud": 100.0, "critico": false},
    {"titulo": "Riesgos y factibilidad", "completitud": 100.0, "critico": true}
  ]
}
```

Y `brechas.md` lista lo único que falta, que es una pregunta opcional:

```markdown
> ✅ **Veredicto: Go** · Completitud: 100.0% · Brechas: 1

## 🟠 Recomendadas
- [Técnico / Habilitación] ¿Hay estimación de costos (FinOps)?
```

El estado de esas fases de razonamiento se guarda en `work/`, que no se versiona; por eso un clon
nuevo de este repositorio incluye los insumos de las demostraciones pero no su estado ya construido.

## 12. Por dentro: workspace, herramientas y principios

### 12.1 El workspace de cada caso

Cada caso tiene su carpeta `work/<caso>/`. El **contexto del chat no es memoria**: la memoria es esa
carpeta. Cada fase escribe su resultado y
la siguiente lo lee, lo que hace el proceso reanudable, incremental y trazable. Los prefijos numéricos
marcan el orden de las fases.

```text
work/<caso>/
├─ 00_manifest.json          inventario clasificado de los insumos                  (Python)
├─ 10_evidence/
│  ├─ index.json             lo ÚNICO que ve el orquestador (≈ 500 tokens)          (Python)
│  └─ E001_<nombre>.json     evidencia completa de cada insumo, por código          (Python)
├─ 20_destilado/
│  ├─ DE003.json …           hechos destilados de cada transcripción                (Destilador)
│  └─ consolidado.json       todo unido, sin repeticiones, con conflictos           (Python)
├─ 30_discovery.json         la ficha tipada del Discovery                          (Constructor)
├─ 40_hipotesis.json         hipótesis y arquetipos Data Mesh                       (Generador)
├─ 50_critica.json           brechas y preguntas poderosas                          (Crítico)
├─ 55_score.json             puntaje y veredicto detallados                         (Python)
├─ 60_redaccion.json         la narrativa, indexada por sección                     (Redactor)
├─ 60_inconsistencias.json   contradicciones y mensajes clave                       (Redactor)
├─ 65_fidelidad.json         validador de fidelidad                                 (Python)
├─ _metrics.json             telemetría por fase                                    (Python)
└─ outputs/                  los entregables finales                                (Python)
```

Los agentes solo pueden escribir en los casilleros que les corresponden: `save_state` usa una **lista
blanca** y rechaza cualquier otra ruta (incluida `../fuera.json`). Los entregables de `outputs/` los
escribe Python, nunca el modelo. Los trozos de evidencia que se piden por `get_evidence` son de unos
12 000 caracteres (≈ 3 000 tokens).

### 12.2 Las 14 herramientas del servidor MCP

El servidor `discovery-agents` (módulo `discovery_agents.interfaces.mcp_server`) expone al agente
estas herramientas. La CLI usa las mismas funciones, de modo que **las dos puertas de entrada no pueden
divergir**.

| Herramienta | Fase | Qué hace |
|---|---|---|
| `build_manifest_tool(folder)` | F0 | Escanea la carpeta y devuelve el manifiesto clasificado, sin leer contenido |
| `extract_evidence(folder, caso)` | F1 | Extrae todos los insumos a `10_evidence/` y devuelve solo el índice compacto |
| `get_evidence(caso, evidence_id, chunk)` | F1–F6 | Devuelve una evidencia por partes, solo cuando se va a razonar sobre ella |
| `pending_distillation(caso)` | F2 | Lista las transcripciones que aún no se destilaron |
| `save_state(caso, archivo, contenido)` | F2–F6 | Guarda el resultado de una fase (con lista blanca) |
| `load_state(caso, archivo)` | F3–F7 | Lee el resultado de una fase anterior |
| `consolidate(caso)` | F2 | Une los destilados, deduplica y detecta conflictos numéricos |
| `supported_formats()` | — | Formatos soportados y dependencias detectadas |
| `validate_discovery(caso)` | F7 | Verifica que la ficha respete sus tipos antes de ensamblar |
| `get_schema()` | F3 | El contrato tipado de la ficha |
| `get_rubrica()` | F5 | La rúbrica de preguntas poderosas |
| `get_subagent_prompt(nombre)` | todas | Las reglas de un subagente |
| `score_state(caso)` | F5 | Puntaje y veredicto deterministas |
| `assemble(caso, caso_de_uso)` | F7 | Genera **todos** los entregables en una sola llamada |

### 12.3 Los principios de diseño

El detalle y su justificación están en [docs/FILOSOFIA.md](docs/FILOSOFIA.md). En resumen:

| # | Principio | Qué significa en la práctica |
|---|---|---|
| 1 | **Lo que se puede calcular, no se prompea** | Extraer, consolidar, puntuar, ensamblar y dibujar es Python (0 tokens) |
| 2 | **Limpieza no destructiva** | El original de cada segmento siempre es accesible. Nació de un fallo real: una limpieza agresiva llegó a convertir "no es cierto" en "no es" |
| 3 | **El contexto del chat no es memoria** | La memoria es el workspace en disco; el modelo ve índices |
| 4 | **La estructura no se aplana** | Fuentes, roles y riesgos viajan como datos tipados hasta el render: aplanarlos a texto destruiría tablas, diagramas y trazabilidad |
| 5 | **El veredicto es determinista** | Lo calcula el scorer; la IA lo explica pero nunca lo decide |
| 6 | **Los conflictos se declaran** | Si el Excel y una reunión discrepan, se muestra; no se resuelve en silencio |
| 7 | **El humano decide en gates** | G0, G1 y G2, no parchando al final |
| 8 | **Narrativa antes que tablas** | Una tabla solo donde de verdad aporta |
| 9 | **Evidencia o silencio** | El beneficio económico solo se afirma con evidencia; si no, se dice que no se cuantificó |
| 10 | **Un hecho, un lugar** | Nada se cuenta dos veces en el documento |
| 11 | **Ausencia declarada, no disimulada** | Lo no capturado va en una lista única, no en secciones llenas de "PENDIENTE" |

### 12.4 Economía de tokens

| Trabajo | Dónde | Tokens |
|---|---|---|
| Manifiesto, extracción, limpieza, consolidación, conflictos, puntaje, ensamblado, diagramas, matrices, Word y HTML | Python | **0** |
| Destilado de transcripciones limpias (incremental) | Copilot económico | bajo |
| Construcción, hipótesis, crítica y redacción | Copilot fuerte | medio (estado compacto, contexto fresco por fase) |

El índice de evidencia reemplaza al volcado completo (≈ 423 tokens frente a ≈ 70 000 en un caso real)
y los entregables se escriben en el servidor: nunca viajan por el chat. Las métricas de cada fase
quedan en `_metrics.json`. La estimación de ahorro en un caso real (seis reuniones más documentos y
Excel) es de un 60 a 75 % menos de costo; el razonamiento completo está en el documento de filosofía.

## 13. Estructura del repositorio y pruebas

```text
discovery-agents/
├─ README.md · CHANGELOG.md · LICENSE · requirements.txt · .gitignore
├─ .github/
│  ├─ copilot-instructions.md        reglas globales de trabajo para Copilot
│  └─ chatmodes/                      el orquestador y los 5 subagentes (punteros, no reglas)
├─ .vscode/mcp.json                   registro del servidor MCP para VS Code
├─ discovery_agents/                  EL SISTEMA (python -m discovery_agents)
│  ├─ __main__.py · workspace.py      punto de entrada · la pizarra en disco
│  ├─ common/                         vocabulario compartido: citas · marcas de ausencia · texto
│  ├─ ingest/                         de carpeta de insumos a evidencia con código
│  │  ├─ registry.py                  tabla única de formatos
│  │  ├─ manifest.py · pipeline.py
│  │  ├─ extractores/                 excel · documentos · presentaciones · imágenes · estructurados
│  │  │                               · correo · legacy · embebidos · transcripción
│  │  └─ transcripciones/cleaner.py   limpieza no destructiva
│  ├─ knowledge/                      contratos y evaluación: el corazón conceptual
│  │                                  schema · rubrica · scorer · fidelidad · validador · dedup · consolidador
│  ├─ render/                         de estado a entregables (0 tokens)
│  │  │                               ensamblador · estilos_word · docx_export · html_export · tablas
│  │  │                               · mermaid · entregables
│  │  └─ assets/executive.html        plantilla del resumen ejecutivo
│  ├─ prompts/                        las reglas de cada subagente (única fuente de verdad)
│  └─ interfaces/                     cli.py (Python 3.9) · mcp_server.py (Python 3.10+)
├─ docs/
│  ├─ como_funciona_el_agente.html    guía visual para personas no técnicas
│  ├─ FILOSOFIA.md                    por qué está construido así
│  ├─ BLUEPRINT.md                    plano completo para reconstruir el sistema
│  └─ REVISION_INTEGRAL.md            la revisión que originó la versión 2
├─ inputs/                            insumos; incluye dos casos de demostración
├─ tools/                             sync_docs.py · generar_bundle_databricks.py
└─ tests/test_core.py                 las 83 pruebas
```

`work/` y `outputs/` se crean al ejecutar y **no se versionan**. Cada capa responde a una pregunta
distinta (`common/` ¿qué vocabulario compartimos?, `ingest/` ¿qué hay y qué dice?, `knowledge/` ¿qué
sabemos y qué tan completo está?, `render/` ¿cómo se ve?, `prompts/` ¿cómo razona cada agente?,
`interfaces/` ¿por dónde se entra?), y una regla de dependencias impide que se mezclen.

### 13.1 Pruebas

```bash
PYTHONPATH="$PWD" python -m unittest discover -s tests -v
```

**83 pruebas** (Python 3.9+, con el módulo estándar `unittest`; no hace falta `pytest`). Con las
dependencias de `requirements.txt` instaladas pasan las 83; sin `openpyxl` fallan 3 y sin `python-docx`
se omiten 3 (las del Word). Usan un workspace temporal (`DISCOVERY_WORK_ROOT`), por lo que no tocan tu
carpeta `work/`. Cubren:

- La **limpieza no destructiva** de transcripciones y los **formatos reales de Teams**.
- El **índice compacto** (que no se convierta en un volcado de tokens), la evidencia por partes y la
  lista blanca de `save_state`.
- La **consolidación**, la deduplicación y la detección de **conflictos numéricos** ("400M" frente a
  "300 millones").
- El **puntaje y el veredicto**, incluidos los validadores (una volumetría sin números no cuenta) y su
  coherencia.
- La **estructura del documento** (dos vistas, temas faltantes, narrativa antes que tablas), las
  tablas, la trazabilidad y los diagramas Mermaid.
- El **Word** y el **resumen ejecutivo HTML**, el ensamblado unificado, la fidelidad y la validación
  de forma.
- Los **formatos y extractores**, y que la documentación del Blueprint esté sincronizada con el código.

## 14. Seguridad y privacidad

- **El núcleo Python no hace llamadas de red** (ni importa bibliotecas de red). Lee tus archivos y
  escribe en `work/`.
- **Quién ve el contenido.** Lo que razonan los agentes lo procesa el modelo de **GitHub Copilot**
  bajo las políticas de tu organización. Por diseño, el modelo ve **índices** y pide contenido por
  partes solo cuando lo necesita; los entregables se escriben en disco y no viajan por el chat.
- **Los agentes escriben solo donde deben**: `save_state` tiene una lista blanca y rechaza cualquier
  otra ruta.
- **Trazabilidad:** cada dato relevante cita su evidencia (`[E003]` o `[E003 seg-012]`), auditable
  hasta el segmento original de la transcripción.
- **Tus archivos no se modifican.** Las versiones limpias se guardan aparte.
- **Los datos reales no deben subirse a Git.** `work/` y `outputs/` están en el `.gitignore`, pero
  **`inputs/` no**: el repositorio versiona allí dos casos de demostración con datos de ejemplo. Si
  vas a procesar un caso real, guarda sus insumos **fuera** del repositorio (y pásale esa ruta al
  orquestador) o agrega la carpeta de tu caso al `.gitignore` antes de hacer `git add`.
- Los casos de demostración usan nombres, correos y servidores **de ejemplo**.
- La plantilla del resumen ejecutivo es autocontenida (sin recursos externos). La guía
  `docs/como_funciona_el_agente.html` carga tipografías desde Google Fonts si hay internet y funciona
  igual sin ellas.

## 15. Preguntas frecuentes

**¿La IA decide si el proyecto es viable?**
No. El veredicto lo calcula una regla fija y auditable (sección 6). La IA puede explicarlo y enriquecerlo
con la narrativa, pero no cambiarlo.

**¿Qué pasa si falta información?**
No se rellena. Un dato que el equipo debe definir queda `PENDIENTE`; uno que no surgió en los insumos,
`DESCONOCIDO`; una lista sin datos, `[]`. Las tres cosas cuentan como "sin dato" en el puntaje, aparecen
en *Temas faltantes* y en `brechas.md`, y empujan el veredicto hacia abajo.

**¿Qué pasa si dos fuentes dicen cifras distintas?**
Se declara como **conflicto** en el documento, con las dos versiones y su procedencia; el sistema nunca
elige una en silencio. La detección entiende "400M" y "400 millones", y marca diferencias de más de un 10 %.

**¿Cómo sé de dónde salió cada dato?**
Cada dato relevante cita su evidencia (`[E003]`), y la matriz de **trazabilidad** (`tablas/`) relaciona
cada campo con su fuente. El validador de fidelidad (`65_fidelidad.json`) informa qué porcentaje del
texto está respaldado y detecta citas a evidencias que no existen.

**¿Puedo agregar una reunión nueva más adelante?**
Sí. Copia la transcripción a `transcripciones/`, vuelve a extraer la evidencia y pide continuar:
`pending_distillation` indica qué falta destilar y solo eso se procesa.

**¿Funciona sin GitHub Copilot?**
La parte mecánica sí, con la CLI (sección 10.2). Las fases de razonamiento (destilar, construir,
hipótesis, crítica, redacción) necesitan un cliente de IA con soporte para MCP; el proyecto está
diseñado y probado para GitHub Copilot en VS Code.

**¿Qué diferencia hay entre el documento Word y el resumen ejecutivo HTML?**
El Word es el documento completo, para revisar y archivar. El HTML es una página para líderes: veredicto,
mensajes clave, riesgos, completitud por bloque, fuentes y pendientes. No es una copia del Word.

**¿Dónde está la versión 2?**
El repositorio conserva todas las versiones: la **v2.0.0** está en el tag `v2.0.0` (y en su *Release*);
esta rama `main` contiene la **v4.0.0**. La estructura cambió en la v4 (el paquete `mcp_server/` pasó a
`discovery_agents/`). Para ver la v2: `git checkout v2.0.0`. El historial completo está en la
[sección 18](#18-historia-de-versiones-autoría-y-licencia).

**¿Se puede usar para otro tipo de proyecto que no sea de datos?**
La rúbrica, la ficha y los entregables están pensados para productos de datos. Adaptarlos a otro dominio
implica cambiar el schema, la rúbrica y los prompts (ver `docs/FILOSOFIA.md`, "Cómo debe evolucionar").

## 16. Solución de problemas

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| No veo el modo **Orquestador Discovery** en Copilot | Los *chat modes* pasaron a llamarse *agentes personalizados* en VS Code 1.106 (`.github/agents/*.agent.md`) | Actualiza VS Code; normalmente reconoce los `.chatmode.md` y ofrece migrarlos. Si no aparecen, copia los archivos de `.github/chatmodes/` a `.github/agents/` renombrándolos de `*.chatmode.md` a `*.agent.md` |
| El servidor MCP no arranca | Falta el SDK `mcp`, o el `python` del proyecto es anterior a 3.10, o el comando `python` no existe | Crea el entorno con Python 3.10+, instala `pip install -r requirements.txt` y actívalo antes de abrir VS Code. En macOS/Linux, si `python` no existe, edita `.vscode/mcp.json` para usar `python3` o la ruta del entorno virtual |
| `El SDK 'mcp' no está instalado o requiere Python >= 3.10` | Estás en Python 3.9 o no instalaste `mcp[cli]` | Es el mensaje esperado: el núcleo sigue funcionando con la CLI. Para el flujo de agentes necesitas Python 3.10+ |
| No se genera el `.docx` | Falta `python-docx` | `pip install python-docx`. Los demás entregables se generan igual |
| Un `.pdf`, `.pptx` o `.msg` aparece con aviso en el índice | Falta `pypdf`, `python-pptx` o `extract-msg` | Instálalas (`pip install -r requirements.txt`); mientras tanto, el insumo queda registrado con un aviso |
| Una imagen aparece como `requiere_vision_llm` | El OCR no encontró texto o no está instalado `tesseract` | Instala `pytesseract` y el programa `tesseract`, o deja que un modelo con visión la vea |
| Un `.xls`, `.doc` o `.ppt` antiguo se avisa pero no se lee | Es un formato binario antiguo | Instala LibreOffice (el sistema lo convierte al vuelo) o guarda el archivo en el formato nuevo (`.xlsx`, `.docx`, `.pptx`) |
| `ensamblar` se detiene con "El Discovery no respeta el contrato tipado del schema" | Una lista (por ejemplo `fuentes`) se guardó como texto | Mira los `detalles` del error: dicen qué campo y qué tipo se esperaba. Corrige `30_discovery.json` y reintenta |
| `ensamblar` dice "No existe 30_discovery.json" | El Constructor aún no corrió | Ejecuta las fases F2 y F3 antes de ensamblar |
| El veredicto es **No-Go** aunque la completitud es alta | Hay más de 4 condiciones abiertas (preguntas obligatorias de bloques críticos sin responder) | Mira `condiciones_para_avanzar` en `veredicto.json` y responde esas preguntas |
| Faltan secciones en el documento | Una sección sin información se omite y se recoge en la lista de lo no capturado | Es lo esperado; revisa "Información no capturada" y `secciones_omitidas` en el resumen del ensamblado |
| `python -m discovery_agents --help` responde "Comando desconocido" | La CLI no define `--help`; usa subcomandos | Ejecuta `python -m discovery_agents` sin argumentos o con un comando inválido para ver la ayuda |
| Las pruebas fallan con `ModuleNotFoundError: discovery_agents` | Falta `PYTHONPATH` | Ejecuta desde la raíz con `PYTHONPATH="$PWD" python -m unittest discover -s tests` |
| Fallan 3 pruebas (Excel y evidencia) o se omiten 3 (Word) | Faltan `openpyxl` o `python-docx` en tu entorno | `pip install -r requirements.txt` y vuelve a ejecutar: deben pasar las 83 |

## 17. Glosario

| Término | Qué significa |
|---|---|
| **Discovery** | La etapa de investigación previa a construir: qué se necesita, para quién, con qué datos y si es viable |
| **Producto de datos** | Un conjunto de datos preparado para que otros lo usen: un tablero, una tabla consolidada, un modelo |
| **Fuente** | La tabla o sistema de donde sale un dato, por ejemplo una base de ventas en un servidor de la empresa |
| **Volumetría** | Cuántos registros tiene una tabla; ayuda a estimar costo y esfuerzo |
| **Frecuencia / latencia** | Cada cuánto se actualizan los datos (diaria, semanal, tiempo real) y con qué retraso |
| **Evidencia (`E001`…)** | El código que el sistema asigna a cada documento de entrada para poder citarlo; `[E003 seg-012]` apunta al segmento 12 de una transcripción |
| **Destilar** | Convertir una transcripción limpia en hechos estructurados (decisiones, hallazgos, datos de fuentes, procesos, reglas, acciones) |
| **Consolidar** | Unir los destilados, eliminar repeticiones uniendo su procedencia y detectar conflictos |
| **Ficha / schema tipado** | La estructura estándar del Discovery (45 campos) en la que las listas son listas de objetos, no texto |
| **`PENDIENTE` / `DESCONOCIDO`** | Marcas de ausencia: lo que el equipo debe definir / lo que no surgió en los insumos |
| **Rúbrica** | La lista de 39 "preguntas poderosas" contra la que se mide qué tan completo está el Discovery |
| **Bloque crítico** | Un bloque de la rúbrica que, si está incompleto, impide un Go aunque el total sea alto |
| **Veredicto** | Go, Condicional o No-Go; lo calcula el scorer |
| **Gate (G0, G1, G2)** | Punto de control donde una persona valida antes de continuar |
| **Conflicto** | Dos fuentes que dicen cifras distintas para lo mismo; se declara, no se resuelve en silencio |
| **Fidelidad** | El porcentaje del texto del documento que está respaldado por una evidencia real |
| **Data Mesh** | Forma de organizar los datos por dominios de negocio; el sistema sugiere qué otros productos podrían salir de las mismas fuentes |
| **Situación actual / futura (as-is / to-be)** | Cómo se hace el proceso hoy y cómo se hará con el producto de datos |
| **Talla S / M / L / XL** | Tamaño estimado del esfuerzo para construir el producto |
| **Deuda técnica / temas faltantes** | Lo que queda sin resolver y habrá que atender después |
| **MCP** | *Model Context Protocol*: el estándar con el que un asistente de IA usa herramientas externas; aquí, el servidor Python |
| **Chat mode / agente personalizado** | Una configuración de Copilot con instrucciones y herramientas propias; aquí, el orquestador y cada especialista |
| **Token** | La unidad en que los modelos de IA miden texto y cobran; menos tokens significa menos costo |
| **Workspace** | La carpeta `work/<caso>/` donde cada fase deja su resultado |
| **Mermaid** | Un lenguaje de texto para dibujar diagramas, que muchas herramientas (incluido GitHub) muestran como imagen |
| **OCR** | Reconocimiento óptico de caracteres: leer el texto de una imagen |

## 18. Historia de versiones, autoría y licencia

| Versión | Fecha | Qué trajo |
|---|---|---|
| 1.0.0 | 2026-06 | Arquitectura de dos capas (agentes de Copilot + servidor MCP en Python) y el veredicto determinista |
| **2.0.0** | 2026-06-12 | Workspace de estado en disco, parsers reales de Teams, consolidador con conflictos numéricos, Redactor experto, diagramas y matrices sin tokens, flujo F0–F7 con gates. Nació de la revisión [docs/REVISION_INTEGRAL.md](docs/REVISION_INTEGRAL.md) |
| (2026-06-23) | — | Documentador de doble vista (Parte I y Parte II), validador de fidelidad y exportación a `.docx` |
| 3.0.0 | 2026-07-25 | Resumen ejecutivo HTML, schema ampliado (gobierno del producto, beneficio económico con evidencia), Word narrativo, soporte de `.csv` |
| **4.0.0** | 2026-07-28 | El paquete pasa a `discovery_agents/` por capas; documento fusionado («un hecho, un lugar»); más extractores (correo, embebidos, estructurados, legacy); deduplicación y validador de forma; 83 pruebas |

El detalle de cada versión está en [CHANGELOG.md](CHANGELOG.md), y hay una *Release* de GitHub por
cada tag (`v2.0.0` y `v4.0.0`).

- **Autoría:** Luis Diego Rodríguez Oviedo.
- **Licencia:** todos los derechos reservados; uso interno y propietario. Ver [LICENSE](LICENSE).

**Documentación relacionada**

- [docs/como_funciona_el_agente.html](docs/como_funciona_el_agente.html): guía visual para personas no
  técnicas (descarga el archivo y ábrelo en el navegador).
- [docs/FILOSOFIA.md](docs/FILOSOFIA.md): por qué el sistema está construido así.
- [docs/BLUEPRINT.md](docs/BLUEPRINT.md): plano completo para reconstruirlo.
- [docs/REVISION_INTEGRAL.md](docs/REVISION_INTEGRAL.md): la revisión que originó la versión 2.
- [.github/copilot-instructions.md](.github/copilot-instructions.md): las reglas de trabajo que sigue Copilot.
