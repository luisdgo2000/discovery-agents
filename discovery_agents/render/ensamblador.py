"""Ensamblado determinista del documento final (0 tokens) — v4: documento FUSIONADO.

El documento es **fusionado**, y esa decisión es estructural. La alternativa —narrativa primero y
un anexo con la información estructurada después— hace que ambos bloques hablen de lo mismo: los
riesgos aparecen en la prosa y otra vez en la tabla de riesgos, las fuentes en el relato y otra vez
en el inventario. El documento se alarga, se repite y, peor, ante dos versiones del mismo hecho no
hay forma de saber cuál es la buena.

Aquí cada sección tiene **un solo cuerpo**: la prosa que le toca y, debajo, los datos
estructurados que la sostienen. Un hecho aparece una vez, en el lugar donde se explica. Las
matrices completas viven en los anexos, que es donde se consultan y no donde se lee.

Tres reglas hacen el trabajo, y las tres son código y no instrucciones a un modelo:

1. **Una sección, un cuerpo.** El esqueleto lo declara `knowledge/schema.SECCIONES`, donde cada
   sección dice qué slot de prosa le corresponde y qué claves del schema se pliegan dentro.
2. **Las secciones vacías no se imprimen.** Una sección sin prosa y con todas sus claves ausentes
   se recoge en una única lista al cierre. Dieciocho párrafos que dicen "PENDIENTE" no informan de
   nada que no informe mejor una lista de lo que falta.
3. **Tabla solo donde gana su espacio.** Lo decide el allowlist `CLAVES_TABLA`; el resto de las
   listas se redacta como prosa.

El LLM no interviene aquí: solo se formatea y se cruzan datos ya producidos.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ..common.citas import tiene_cita
from ..common.marcas import es_ausente
from ..knowledge.fidelidad import seccion_cobertura_md
from ..knowledge.schema import (ETIQUETA_TIPO_RIESGO, ETIQUETAS, ORDEN_PARTES, PARTES, SECCIONES,
                                TIPOS_RIESGO)
from ..knowledge.scorer import score_discovery
from .tablas import render_clave

_SIN_BENEFICIO = "No cuantificado con evidencia en el Discovery."


def ensamblar_discovery(discovery: Dict[str, object], caso_de_uso: str = "",
                        redaccion: Optional[dict] = None,
                        inconsistencias: Optional[dict] = None,
                        fidelidad: Optional[dict] = None,
                        critica: Optional[dict] = None) -> dict:
    """Arma el documento fusionado y todos los datos derivados.

    Args:
        discovery: `30_discovery.json` ya rellenado por el Constructor.
        caso_de_uso: título del documento.
        redaccion: prosa por sección, `{"secciones": {slot: texto}}` (60_redaccion.json).
        inconsistencias: control intelectual del Redactor (60_inconsistencias.json).
        fidelidad: informe del verificador de citas (65_fidelidad.json).
        critica: brechas priorizadas del Crítico (50_critica.json).

    Returns:
        {markdown, brechas_markdown, veredicto, score, temas_faltantes, secciones_omitidas}
    """
    score = score_discovery(discovery)
    d = dict(discovery)

    temas = _dedup_temas(recolectar_temas_faltantes(score, d, inconsistencias, critica))
    d["temas_faltantes"] = temas

    prosa = _slots_de_prosa(redaccion)
    titulo = caso_de_uso or str(d.get("nombre_caso_uso") or "Producto de datos")

    partes: List[str] = [f"# Discovery — {titulo}\n", _badge_veredicto(score), ""]
    partes.extend(_resumen_ejecutivo(d, score, prosa))

    omitidas: List[str] = []
    for parte in ORDEN_PARTES:
        secciones_parte = [s for s in SECCIONES if s["parte"] == parte]
        cuerpos = []
        for seccion in secciones_parte:
            if not tiene_contenido(seccion, d, prosa):
                omitidas.append(str(seccion["titulo"]))
                continue
            cuerpo = _render_seccion(seccion, d, score, fidelidad, prosa)
            if cuerpo is None:
                # Una sección calculada que no produjo nada (p. ej. cobertura sin informe de
                # fidelidad) se salta en silencio: no es información que faltara capturar.
                if not _es_calculada(seccion):
                    omitidas.append(str(seccion["titulo"]))
                continue
            cuerpos.append(cuerpo)
        if cuerpos:
            partes.append(f"# {PARTES[parte]}\n")
            partes.extend(cuerpos)

    if omitidas:
        partes.append(_bloque_no_capturado(omitidas))

    return {
        "markdown": "\n".join(partes).rstrip() + "\n",
        "brechas_markdown": _reporte_brechas(score, titulo),
        "veredicto": {
            "caso_de_uso": titulo,
            "veredicto": score["veredicto"],
            "completitud_total": score["completitud_total"],
            "condiciones_para_avanzar": score["condiciones_para_avanzar"],
            "n_brechas": score["n_brechas"],
            "n_temas_faltantes": len(temas),
            "bloques": [{"titulo": b["titulo"], "completitud": b["completitud"],
                         "critico": b["critico"]} for b in score["bloques"]],
        },
        "score": score,
        "temas_faltantes": temas,
        "secciones_omitidas": omitidas,
    }


# ---------------------------------------------------------------------------------------------
# Prosa del Redactor
# ---------------------------------------------------------------------------------------------
# Encabezados que el Redactor usaba en el formato .md antiguo → slot equivalente. Sirve para que
# un `60_redaccion.md` de antes siga produciendo un documento correcto: el contrato cambió, pero
# el trabajo ya hecho con el contrato viejo no se tira.
_ENCABEZADO_A_SLOT = {
    "contexto y problema de negocio": "contexto",
    "contexto": "contexto",
    "proceso actual": "proceso",
    "proceso actual (as-is)": "proceso",
    "proceso futuro": "proceso",
    "proceso futuro (to-be)": "proceso",
    "sistemas y fuentes participantes": "fuentes",
    "datos y transformaciones clave": "datos",
    "dependencias y habilitaciones": "habilitacion",
    "riesgos": "riesgos",
    "decisiones pendientes": "recomendacion",
    "evaluacion de factibilidad y complejidad": "evaluacion",
    "evaluación de factibilidad y complejidad": "evaluacion",
    "evaluación de factibilidad": "evaluacion",
    "recomendacion profesional": "recomendacion",
    "recomendación profesional": "recomendacion",
}


def _slots_de_prosa(redaccion: Optional[object]) -> Dict[str, str]:
    """Normaliza la redacción a `{slot: prosa}` venga como JSON nuevo o como markdown antiguo."""
    if not redaccion:
        return {}
    if isinstance(redaccion, dict):
        # Contrato anterior: un único markdown que hay que repartir por sus encabezados.
        if "markdown" in redaccion:
            return _slots_desde_markdown(str(redaccion["markdown"]))
        secciones = redaccion.get("secciones", redaccion)
        if not isinstance(secciones, dict):
            return {}
        return {str(k): str(v).strip() for k, v in secciones.items()
                if isinstance(v, str) and v.strip()}
    return _slots_desde_markdown(str(redaccion))


def _slots_desde_markdown(md: str) -> Dict[str, str]:
    """Reparte un `60_redaccion.md` en slots usando sus encabezados `##`."""
    slots: Dict[str, str] = {}
    actual = ""
    cuerpo: List[str] = []

    def cerrar() -> None:
        if actual and cuerpo:
            texto = "\n".join(cuerpo).strip()
            if texto:
                slots[actual] = (slots.get(actual, "") + "\n\n" + texto).strip()

    for linea in md.splitlines():
        if linea.lstrip().startswith("#"):
            cerrar()
            cuerpo = []
            titulo = linea.lstrip("#").strip().lower().rstrip(".")
            actual = _ENCABEZADO_A_SLOT.get(titulo, "")
            if not actual:
                # Encabezado desconocido: su prosa se conserva bajo el contexto para no perderla.
                actual = "contexto"
        else:
            cuerpo.append(linea)
    cerrar()
    return slots


# ---------------------------------------------------------------------------------------------
# Render de una sección fusionada
# ---------------------------------------------------------------------------------------------
# Claves que siempre tienen algo que decir, incluso vacías: "no se identificaron riesgos" y "no
# quedaron temas pendientes" son conclusiones del Discovery, no ausencias de información.
CLAVES_SIEMPRE_PRESENTES = {"riesgos", "temas_faltantes"}


def con_dato(valor: object) -> bool:
    """True si el valor aporta información real (ni vacío ni marca de ausencia)."""
    if isinstance(valor, str):
        return not es_ausente(valor)
    if isinstance(valor, list):
        return any(con_dato(v) for v in valor)
    if isinstance(valor, dict):
        return any(con_dato(v) for v in valor.values())
    return bool(valor)


def tiene_contenido(seccion: dict, discovery: dict, prosa: Dict[str, str]) -> bool:
    """Si una sección merece imprimirse.

    Es la regla que evita el documento lleno de "PENDIENTE": una sección sin prosa y con todas sus
    claves ausentes no informa de nada que no informe mejor la lista de lo que falta. Vive aquí y
    la importa el exportador Word, para que el markdown y el .docx no puedan discrepar sobre qué
    secciones existen.
    """
    if prosa.get(str(seccion.get("narrativa") or ""), "").strip():
        return True
    for clave in seccion["claves"]:
        if str(clave).startswith("_") or clave in CLAVES_SIEMPRE_PRESENTES:
            return True
        if con_dato(discovery.get(clave)):
            return True
    return False


def _es_calculada(seccion: dict) -> bool:
    """Secciones cuyo contenido lo calcula el sistema (veredicto, cobertura, completitud)."""
    return all(str(c).startswith("_") for c in seccion["claves"]) and bool(seccion["claves"])


def _render_seccion(seccion: dict, d: dict, score: dict, fidelidad: Optional[dict],
                    prosa: Dict[str, str]) -> Optional[str]:
    """Cuerpo markdown de una sección, o None si no hay nada que decir en ella."""
    slot = str(seccion.get("narrativa") or "")
    texto = prosa.get(slot, "").strip()
    bloques: List[str] = []

    if texto:
        bloques.append(texto)

    for clave in seccion["claves"]:
        fragmento = _render_clave(clave, d, score, fidelidad, ya_narrado=bool(texto))
        if fragmento:
            bloques.append(fragmento)

    if not bloques:
        return None
    return f"## {seccion['titulo']}\n\n" + "\n\n".join(bloques) + "\n"


def _render_clave(clave: str, d: dict, score: dict, fidelidad: Optional[dict],
                  ya_narrado: bool) -> str:
    """Render de una clave dentro de su sección. Devuelve '' si no aporta nada."""
    if clave == "_veredicto":
        return _veredicto_inline(score)
    if clave == "_cobertura":
        # Sin informe de fidelidad no hay nada que reportar; imprimir "0%" afirmaría que no hay
        # evidencia cuando en realidad no se midió.
        return seccion_cobertura_md(fidelidad) if fidelidad else ""
    if clave == "_completitud_bloques":
        return _tabla_bloques(score)
    if clave == "riesgos":
        return _riesgos_md(d.get("riesgos"))
    if clave == "temas_faltantes":
        return _temas_md(d.get("temas_faltantes"))

    valor = d.get(clave)

    if clave == "beneficio_economico":
        # Afirmar un beneficio monetario sin cifra citada es la afirmación más costosa que puede
        # colarse en un Discovery: se convierte en presupuesto. Sin evidencia, se declara ausente.
        if es_ausente(valor) or not tiene_cita(valor):
            return f"**{ETIQUETAS[clave]}:** _{_SIN_BENEFICIO}_"
        return f"**{ETIQUETAS[clave]}:** {valor}"

    if isinstance(valor, str):
        if es_ausente(valor):
            # Un "PENDIENTE" suelto no informa cuando la prosa ya explicó la sección; sí informa
            # cuando la sección no tiene más contenido que sus campos.
            return "" if ya_narrado else f"**{ETIQUETAS.get(clave, clave)}:** _PENDIENTE_"
        return f"**{ETIQUETAS.get(clave, clave)}:** {valor}"

    if isinstance(valor, dict):
        persona = _persona_str(valor)
        return f"**{ETIQUETAS.get(clave, clave)}:** {persona}" if persona else ""

    if isinstance(valor, list) and valor:
        cuerpo = render_clave(clave, valor)
        return f"**{ETIQUETAS.get(clave, clave)}**\n\n{cuerpo}" if cuerpo.strip() else ""

    return ""


def _persona_str(p: dict) -> str:
    nombre = str(p.get("nombre", "")).strip()
    if es_ausente(nombre):
        return ""
    rol = str(p.get("rol", "")).strip()
    contacto = str(p.get("contacto", "")).strip()
    salida = nombre
    if rol and not es_ausente(rol):
        salida += f" ({rol})"
    if contacto and not es_ausente(contacto):
        salida += f" — {contacto}"
    return salida


def _riesgos_md(riesgos: object) -> str:
    """Riesgos agrupados por tipo. Si no hay, se dice — y se dice con precisión."""
    validos = [r for r in (riesgos or []) if isinstance(r, dict)
               and not es_ausente(r.get("descripcion"))]
    if not validos:
        # La distinción importa: el Discovery no encontró riesgos, que no es lo mismo que afirmar
        # que no los hay. Escribir la diferencia evita que el silencio se lea como garantía.
        return ("_No se identificaron riesgos durante el Discovery. Ausencia de evidencia de "
                "riesgo, no garantía de su inexistencia._")

    por_tipo = _riesgos_por_tipo(validos)
    if len(por_tipo) == 1:
        # Con un solo grupo, encabezarlo no clasifica nada: solo añade una línea.
        return render_clave("riesgos", validos, forzar_tabla=True)

    partes: List[str] = []
    for tipo, riesgos_del_tipo in por_tipo.items():
        partes.append(f"**{ETIQUETA_TIPO_RIESGO[tipo]}**\n\n"
                      + render_clave("riesgos", riesgos_del_tipo, forzar_tabla=True))
    return "\n\n".join(partes)


def _riesgos_por_tipo(riesgos: List[dict]) -> Dict[str, List[dict]]:
    """Agrupa por tipo respetando el orden declarado, con los sin clasificar al final."""
    agrupados: Dict[str, List[dict]] = {}
    for r in riesgos:
        tipo = str(r.get("tipo", "")).strip().lower()
        agrupados.setdefault(tipo if tipo in TIPOS_RIESGO else "", []).append(r)
    orden = [t for t in TIPOS_RIESGO if t in agrupados] + ([""] if "" in agrupados else [])
    return {t: agrupados[t] for t in orden}


def _temas_md(temas: object) -> str:
    """Temas faltantes agrupados por impacto; si no hay ninguno, se dice explícitamente."""
    lista = [t for t in (temas or []) if isinstance(t, dict) and str(t.get("punto", "")).strip()]
    if not lista:
        return ("_El Discovery respondió todas las preguntas de la rúbrica y no dejó supuestos sin "
                "validar: no hay temas faltantes ni deuda técnica registrada._")

    partes: List[str] = []
    for impacto, titulo in (("Bloqueante", "Bloqueantes"), ("Recomendado", "Recomendados"),
                            ("Opcional", "Opcionales")):
        grupo = [t for t in lista if str(t.get("impacto", "")) == impacto]
        if grupo:
            partes.append(f"**{titulo}**\n\n" + _temas_bullets(grupo))
    resto = [t for t in lista
             if str(t.get("impacto", "")) not in ("Bloqueante", "Recomendado", "Opcional")]
    if resto:
        partes.append("**Otros temas abiertos**\n\n" + _temas_bullets(resto))
    return "\n\n".join(partes)


def _temas_bullets(temas: List[dict]) -> str:
    lineas: List[str] = []
    for t in temas:
        linea = f"- **{t['punto']}**"
        detalle = str(t.get("detalle", "")).strip()
        accion = str(t.get("accion_sugerida", "")).strip()
        extras = [x for x in (detalle, accion) if x and not es_ausente(x)]
        if extras:
            linea += " — " + " · ".join(extras)
        origen = str(t.get("origen", "")).strip()
        if origen:
            linea += f" _(detectado por: {origen})_"
        lineas.append(linea)
    return "\n".join(lineas)


def _tabla_bloques(score: dict) -> str:
    """Completitud por bloque de la rúbrica: una tabla que sí gana su espacio."""
    filas = [{
        "bloque": b["titulo"],
        "completitud": f"{b['completitud']}%",
        "peso": f"{b['peso']}%",
        "critico": "Sí" if b["critico"] else "No",
        "pendientes": len(b["pendientes"]),
    } for b in score.get("bloques", [])]
    if not filas:
        return ""
    from .tablas import tabla_md
    return tabla_md(filas, ["bloque", "completitud", "peso", "critico", "pendientes"])


def _resumen_ejecutivo(d: dict, score: dict, prosa: Dict[str, str]) -> List[str]:
    """Resumen ejecutivo: lo que hay que retener si solo se lee una página."""
    bloques: List[str] = []
    texto = str(d.get("resumen_ejecutivo") or "").strip()
    mensajes = [m for m in (d.get("mensajes_clave") or []) if str(m).strip()]

    if es_ausente(texto) and not mensajes:
        return bloques

    bloques.append("## Resumen ejecutivo\n")
    if not es_ausente(texto):
        bloques.append(texto + "\n")
    if mensajes:
        bloques.append("**Mensajes clave**\n")
        bloques.extend(f"- {m}" for m in mensajes)
        bloques.append("")
    return bloques


def _bloque_no_capturado(omitidas: List[str]) -> str:
    """Lo que el Discovery no llegó a cubrir, en una lista y no en 18 párrafos vacíos."""
    return ("## Información no capturada en este Discovery\n\n"
            "Las siguientes secciones no se incluyen porque no se obtuvo información para "
            "ninguno de sus campos. Cada una está registrada como brecha en «Temas faltantes y "
            "deuda técnica».\n\n"
            + "\n".join(f"- {t}" for t in omitidas) + "\n")


# ---------------------------------------------------------------------------------------------
# Recolector determinista de "Temas faltantes / deuda técnica"
# ---------------------------------------------------------------------------------------------
def recolectar_temas_faltantes(score: dict, discovery: dict,
                               inconsistencias: Optional[dict],
                               critica: Optional[dict] = None) -> List[dict]:
    """Reúne todo lo que NO se conoció, de las cuatro fuentes que lo saben.

    Brechas de la rúbrica (determinista), vacíos y decisiones pendientes del Redactor, brechas
    priorizadas del Crítico, y supuestos que nadie validó. Así, si falta cualquier punto —incluido
    el alcance o el objetivo— aparece aquí sin que nadie tenga que acordarse de anotarlo.
    """
    temas: List[dict] = []

    for br in score.get("brechas", []):
        if br["obligatoria"]:
            tipo = "falta_dato"
            impacto = "Bloqueante" if br["critico"] else "Recomendado"
        else:
            tipo = "desconocido"
            impacto = "Opcional"
        temas.append({
            "punto": br["pregunta"], "tipo": tipo, "impacto": impacto,
            "detalle": f"Bloque: {br['bloque']}", "origen": "rúbrica",
            "accion_sugerida": "Responder en la próxima sesión de discovery",
        })

    inc = inconsistencias or {}
    for v in inc.get("vacios_no_capturados_por_rubrica", []):
        temas.append({"punto": str(v), "tipo": "desconocido", "impacto": "",
                      "detalle": "No capturado por la rúbrica", "origen": "redactor",
                      "accion_sugerida": ""})
    for q in inc.get("preguntas_criticas_adicionales", []):
        temas.append({"punto": str(q), "tipo": "desconocido", "impacto": "",
                      "detalle": "Pregunta crítica adicional del experto", "origen": "redactor",
                      "accion_sugerida": ""})
    for dec in inc.get("decisiones_pendientes", []):
        if isinstance(dec, dict):
            temas.append({"punto": dec.get("decision", ""), "tipo": "decision_pendiente",
                          "impacto": dec.get("urgencia", ""), "detalle": "Decisión pendiente",
                          "origen": "redactor",
                          "accion_sugerida": f"Decisor sugerido: {dec.get('decisor_sugerido', '')}"})

    # El Crítico producía `50_critica.json` y ningún módulo lo leía: su trabajo —las preguntas
    # poderosas, que son lo más valioso que aporta— no llegaba al documento. Ahora sí.
    crit = critica or {}
    for br in crit.get("brechas_priorizadas", []):
        if not isinstance(br, dict):
            continue
        temas.append({
            "punto": str(br.get("pregunta_poderosa") or br.get("que_falta") or ""),
            "tipo": "pregunta_poderosa",
            "impacto": _impacto_de_severidad(br.get("severidad")),
            "detalle": str(br.get("por_que_importa") or f"Bloque: {br.get('bloque', '')}"),
            "origen": "crítico",
            "accion_sugerida": "Plantear en la próxima sesión de discovery",
        })
    for q in crit.get("preguntas_para_proxima_sesion", []):
        temas.append({"punto": str(q), "tipo": "pregunta_poderosa", "impacto": "",
                      "detalle": "Pregunta para la próxima sesión", "origen": "crítico",
                      "accion_sugerida": ""})
    for amb in crit.get("ambiguedades", []):
        punto = amb.get("descripcion", "") if isinstance(amb, dict) else str(amb)
        temas.append({"punto": str(punto), "tipo": "ambiguedad", "impacto": "",
                      "detalle": "Ambigüedad detectada en la revisión", "origen": "crítico",
                      "accion_sugerida": "Precisar con el equipo"})

    for s in discovery.get("supuestos", []):
        if isinstance(s, dict) and es_ausente(s.get("validado_por")):
            temas.append({"punto": s.get("descripcion", ""), "tipo": "supuesto_no_validado",
                          "impacto": "", "detalle": "Supuesto asumido sin validar",
                          "origen": "discovery", "accion_sugerida": "Validar con el responsable"})

    return [t for t in temas if str(t.get("punto", "")).strip()]


def _impacto_de_severidad(severidad: object) -> str:
    return {"alta": "Bloqueante", "media": "Recomendado", "baja": "Opcional"}.get(
        str(severidad or "").strip().lower(), "")


def _dedup_temas(temas: List[dict]) -> List[dict]:
    """Un mismo vacío detectado por la rúbrica, el Redactor y el Crítico es un vacío, no tres.

    Se compara por similitud y no por igualdad exacta: las tres fuentes describen lo mismo con
    palabras distintas, que es precisamente el caso que una comparación exacta no atrapa.
    """
    from ..common.texto import similitud

    salida: List[dict] = []
    for t in temas:
        punto = str(t.get("punto", "")).strip()
        if not punto:
            continue
        gemelo = next((s for s in salida if similitud(punto, s.get("punto", "")) >= 0.85), None)
        if gemelo is None:
            salida.append(t)
            continue
        # Se conserva el registro más severo y se anota que varias fuentes lo señalaron: una
        # brecha vista por la rúbrica y por el Crítico es más urgente, no menos.
        if _peso_impacto(t.get("impacto")) < _peso_impacto(gemelo.get("impacto")):
            gemelo.update({k: v for k, v in t.items() if v})
        origenes = {gemelo.get("origen", ""), t.get("origen", "")} - {""}
        gemelo["origen"] = " · ".join(sorted(origenes))
    return salida


def _peso_impacto(impacto: object) -> int:
    return {"Bloqueante": 0, "Recomendado": 1, "Opcional": 2}.get(str(impacto or ""), 3)


# ---------------------------------------------------------------------------------------------
# Render de badges/bloques
# ---------------------------------------------------------------------------------------------
def _badge_veredicto(score: dict) -> str:
    v = score["veredicto"]
    icono = {"Go": "✅", "Condicional": "🟡", "No-Go": "⛔"}.get(v, "•")
    return (f"> {icono} **Veredicto: {v}** · Completitud: {score['completitud_total']}% · "
            f"Brechas: {score['n_brechas']}")


def _veredicto_inline(score: dict) -> str:
    out = [_badge_veredicto(score), ""]
    cond = score["condiciones_para_avanzar"]
    if cond:
        out.append("**Condiciones para avanzar:**")
        out.extend(f"- {c}" for c in cond)
    else:
        out.append("_Sin condiciones bloqueantes pendientes._")
    out.append("")
    out.append(_brechas_inline(score))
    return "\n".join(out)


def _brechas_inline(score: dict) -> str:
    if not score["brechas"]:
        return "_Sin brechas: el discovery responde todas las preguntas de la rúbrica._\n"
    out: List[str] = ["**Brechas y preguntas pendientes:**"]
    for br in score["brechas"]:
        sev = "🔴" if (br["critico"] and br["obligatoria"]) else "🟠" if br["obligatoria"] else "⚪"
        out.append(f"- {sev} [{br['bloque']}] {br['pregunta']}")
    return "\n".join(out) + "\n"


def _reporte_brechas(score: dict, titulo: str) -> str:
    out = [f"# Brechas y preguntas poderosas pendientes — {titulo}\n",
           _badge_veredicto(score), ""]
    if not score["brechas"]:
        out.append("_Sin brechas pendientes._")
        return "\n".join(out) + "\n"
    criticas = [b for b in score["brechas"] if b["critico"] and b["obligatoria"]]
    otras = [b for b in score["brechas"] if not (b["critico"] and b["obligatoria"])]
    if criticas:
        out.append("## 🔴 Bloqueantes (responder antes de avanzar)\n")
        out.extend(f"- [{b['bloque']}] {b['pregunta']}" for b in criticas)
        out.append("")
    if otras:
        out.append("## 🟠 Recomendadas\n")
        out.extend(f"- [{b['bloque']}] {b['pregunta']}" for b in otras)
    return "\n".join(out) + "\n"
