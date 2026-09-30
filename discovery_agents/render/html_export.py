"""Exportador del Resumen Ejecutivo a HTML standalone (0 tokens, sin dependencias externas).

Segundo entregable del Discovery, junto al Word. **No es una copia del documento**: es un
Executive Summary que destaca solo lo que un líder necesita para decidir — veredicto, completitud,
factibilidad, mensajes clave, riesgos, gobierno, fuentes y temas pendientes. El Word responde
"qué encontramos"; esto responde "qué hacemos con lo que encontramos".

Reparto de trabajo, igual que en el resto del sistema: la IA decide el CONTENIDO, Python decide el
DIBUJO. La plantilla visual vive en `assets/executive.html` —fija, reutilizable, con identidad
propia— y aquí solo se sustituye la información dinámica. Cada Discovery nuevo reemplaza los datos;
nadie vuelve a diseñar nada.

Es stdlib puro, así que este entregable nunca degrada: no hay entorno donde falte.
"""
from __future__ import annotations

import html
import os
import re
from typing import Dict, List, Optional

from ..common.citas import sin_citas, tiene_cita
from ..common.marcas import es_ausente
from ..knowledge.scorer import UMBRAL_GO, score_discovery

_TPL = os.path.join(os.path.dirname(__file__), "assets", "executive.html")

_CLASE_VEREDICTO = {"Go": "go", "Condicional": "cond", "No-Go": "nogo"}
_ICONO_VEREDICTO = {"Go": "✓", "Condicional": "!", "No-Go": "×"}
_NOTA_VEREDICTO = {
    "Go": "El Discovery reúne lo necesario para avanzar a la etapa de diseño.",
    "Condicional": "Viable con condiciones: hay puntos bloqueantes por resolver antes de avanzar.",
    "No-Go": "Aún no es viable avanzar: faltan definiciones críticas del Discovery.",
}

# Topes de la vista ejecutiva. Un resumen que lo lista todo deja de ser un resumen: si hay veinte
# riesgos, los seis más severos son los que se discuten en el comité y el resto está íntegro en el
# Word, que es el documento donde sí cabe el detalle completo.
_MAX_MENSAJES = 6
_MAX_CONDICIONES = 6
_MAX_RIESGOS = 6
_MAX_TABLAS_POR_SERVIDOR = 6
_MAX_TEMAS = 7


def _e(texto: object) -> str:
    """Escapa texto para HTML. Todo dato dinámico pasa por aquí antes de entrar a la plantilla."""
    return html.escape(str(texto if texto is not None else "").strip())


def _limpio(texto: object) -> str:
    """Texto ejecutivo: sin marcas de cita y escapado.

    Las citas `[E00x]` no desaparecen del sistema —siguen íntegras en el Word y en la matriz de
    trazabilidad—; simplemente no se le muestran a quien viene a leer la conclusión.
    """
    return _e(sin_citas(texto))


def cargar_plantilla() -> str:
    with open(_TPL, "r", encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------------------------
# Fragmentos dinámicos
# ---------------------------------------------------------------------------------------------
def _thesis(discovery: dict) -> str:
    """Una frase que resume el Discovery: el primer mensaje clave o la primera del resumen."""
    msgs = [m for m in (discovery.get("mensajes_clave") or []) if str(m).strip()]
    if msgs:
        return _limpio(msgs[0])
    resumen = sin_citas(discovery.get("resumen_ejecutivo") or discovery.get("objetivo") or "")
    if resumen:
        return _e(re.split(r"(?<=[.!?])\s+", resumen)[0])
    return "Resumen ejecutivo del Discovery del producto de datos."


def _kpis(discovery: dict, score: dict, evaluacion: dict) -> str:
    fuentes = _fuentes_validas(discovery)
    servidores = sorted({str(f.get("servidor", "")).strip() for f in fuentes
                         if str(f.get("servidor", "")).strip()})
    n_riesgos = len([r for r in discovery.get("riesgos", [])
                     if isinstance(r, dict) and str(r.get("descripcion", "")).strip()])
    tarjetas = [
        ("Factibilidad", _e((evaluacion.get("factibilidad") or "—").capitalize()),
         "Juicio del consultor"),
        ("Complejidad", _e(evaluacion.get("complejidad") or "—"), "Talla S · M · L · XL"),
        ("Fuentes", str(len(fuentes)), f"{len(servidores)} servidor(es)"),
        ("Riesgos", str(n_riesgos), "Identificados"),
        ("Brechas", str(score.get("n_brechas", 0)), "Preguntas pendientes"),
    ]
    return "\n".join(
        f'<div class="indicador"><div class="rotulo">{_e(rotulo)}</div>'
        f'<div class="valor">{valor}</div><div class="nota">{_e(nota)}</div></div>'
        for rotulo, valor, nota in tarjetas
    )


def _mensajes(discovery: dict) -> str:
    msgs = [m for m in (discovery.get("mensajes_clave") or []) if str(m).strip()]
    if not msgs:
        msgs = _mensajes_fallback(discovery)
    if not msgs:
        return '<p class="vacio">Sin mensajes clave registrados.</p>'
    return "\n".join(
        f'<div class="mensaje"><span class="punto" aria-hidden="true"></span>'
        f'<p>{_limpio(m)}</p></div>'
        for m in msgs[:_MAX_MENSAJES]
    )


def _mensajes_fallback(discovery: dict) -> List[str]:
    """Si el Redactor no aportó mensajes, se arman del estado en vez de dejar el hueco."""
    salida: List[str] = []
    for clave in ("objetivo", "valor_esperado"):
        valor = discovery.get(clave)
        if not es_ausente(valor):
            salida.append(sin_citas(valor))
    beneficio = discovery.get("beneficio_economico")
    if beneficio and tiene_cita(beneficio):   # solo con evidencia
        salida.append(sin_citas(beneficio))
    return [s for s in salida if s]


def _bloque_condiciones(score: dict) -> str:
    condiciones = score.get("condiciones_para_avanzar") or []
    if not condiciones:
        return ""
    filas = "\n".join(
        f'<div class="fila"><span class="franja" style="background:var(--dictamen)"></span>'
        f'<div class="cuerpo"><p class="principal">{_limpio(c)}</p></div></div>'
        for c in condiciones[:_MAX_CONDICIONES]
    )
    return ('<section class="revelar"><div class="titulo-seccion">'
            '<h2>Condiciones para avanzar</h2></div>'
            f'<div class="pila">{filas}</div></section>')


def _riesgos(discovery: dict) -> str:
    riesgos = [r for r in discovery.get("riesgos", [])
               if isinstance(r, dict) and str(r.get("descripcion", "")).strip()]
    if not riesgos:
        # La distinción es deliberada: el Discovery no encontró riesgos, que no es lo mismo que
        # afirmar que no los hay. Decirlo así evita que el silencio se lea como garantía.
        return ('<div class="fila"><span class="franja" style="background:var(--go)"></span>'
                '<div class="cuerpo"><p class="principal">No se identificaron riesgos durante '
                'el Discovery.</p><p class="detalle">Ausencia de evidencia de riesgo, no '
                'garantía de su inexistencia.</p></div></div>')

    orden = {"alta": 0, "media": 1, "baja": 2}
    riesgos = sorted(riesgos, key=lambda r: orden.get(str(r.get("severidad", "")).lower(), 3))
    salida = []
    for r in riesgos[:_MAX_RIESGOS]:
        severidad = str(r.get("severidad", "")).lower()
        clase = severidad if severidad in orden else ""
        detalles = []
        for etiqueta, clave in (("Tipo", "tipo"), ("Responsable", "responsable")):
            valor = str(r.get(clave, "")).strip()
            if valor and not es_ausente(valor):
                detalles.append(f"{etiqueta}: {_e(valor)}")
        detalle = f'<p class="detalle">{" · ".join(detalles)}</p>' if detalles else ""
        distintivo = f'<span class="distintivo {clase}">{_e(severidad or "sin clasificar")}</span>'
        salida.append(
            f'<div class="fila"><span class="franja" style="background:var(--{_color_sev(clase)})">'
            f'</span><div class="cuerpo"><p class="principal">{_limpio(r.get("descripcion"))}</p>'
            f'{detalle}</div>{distintivo}</div>')
    return "\n".join(salida)


def _color_sev(clase: str) -> str:
    return {"alta": "nogo", "media": "cond", "baja": "go"}.get(clase, "grafito")


def _bloques(score: dict) -> str:
    """Completitud por bloque de la rúbrica.

    Es el dato más informativo que el sistema ya calculaba y que este resumen no mostraba: dice
    *dónde* está incompleto el Discovery, no solo cuánto. Barras horizontales —la forma correcta
    para comparar magnitudes entre categorías con nombre—, serie única en el color del veredicto,
    etiqueta directa en cada barra y el umbral de Go como línea de referencia. Los bloques
    críticos se distinguen por forma y no por un segundo color, para que la lectura no dependa
    de percibir bien el color.
    """
    bloques = score.get("bloques") or []
    if not bloques:
        return '<p class="vacio">Sin evaluación por bloque disponible.</p>'

    filas = []
    for b in bloques:
        pct = float(b.get("completitud", 0) or 0)
        marca = '<span class="critico" aria-hidden="true"></span>' if b.get("critico") else ""
        filas.append(
            '<div class="barra-fila">'
            f'<span class="nombre">{marca}{_e(b.get("titulo"))}</span>'
            '<span class="canal">'
            f'<span class="umbral" style="left:{UMBRAL_GO}%"></span>'
            f'<span class="dato" data-objetivo="{pct}"></span></span>'
            f'<span class="pct">{_fmt(pct)}%</span></div>')

    return ('<div class="barras">' + "\n".join(filas) + '</div>'
            '<p class="leyenda-grafico">'
            '<span><span class="critico"></span> Bloque crítico para el veredicto</span>'
            f'<span><span class="marca-umbral"></span> Umbral de Go ({UMBRAL_GO}%)</span></p>')


def _bloque_beneficio(discovery: dict) -> str:
    """Beneficio esperado. El económico solo se afirma si viene con cifra citada."""
    valor = discovery.get("valor_esperado")
    beneficio = discovery.get("beneficio_economico")
    tiene_valor = not es_ausente(valor)
    tiene_economico = bool(beneficio) and not es_ausente(beneficio) and tiene_cita(beneficio)
    if not tiene_valor and not tiene_economico:
        return ""

    cuerpo = f'<p>{_limpio(valor)}</p>' if tiene_valor else ""
    if tiene_economico:
        cuerpo += f'<p class="cifra">Beneficio económico estimado: {_limpio(beneficio)}</p>'
    else:
        cuerpo += ('<p class="cifra">Beneficio económico: no cuantificado con evidencia en el '
                   'Discovery.</p>')
    return ('<section class="revelar"><div class="titulo-seccion">'
            '<h2>Beneficio esperado</h2></div>'
            f'<div class="beneficio">{cuerpo}</div></section>')


def _bloque_gobierno(discovery: dict) -> str:
    """Quién responde por el producto: la pregunta que un comité hace primero."""
    roles = [
        ("Dueño del producto", discovery.get("dueno_producto")),
        ("Product Owner", discovery.get("product_owner")),
        ("Líder técnico", discovery.get("lider_tecnico")),
        ("Solicitante", discovery.get("solicitante")),
    ]
    tarjetas = []
    for rotulo, persona in roles:
        if not isinstance(persona, dict) or es_ausente(persona.get("nombre")):
            continue
        detalle = str(persona.get("rol", "")).strip()
        tarjeta = (f'<div class="tarjeta"><div class="rol">{_e(rotulo)}</div>'
                   f'<div class="nombre">{_e(persona.get("nombre"))}</div>')
        if detalle and not es_ausente(detalle):
            tarjeta += f'<div class="conteo">{_e(detalle)}</div>'
        tarjetas.append(tarjeta + "</div>")

    certificadores = [c for c in discovery.get("certificadores", [])
                      if isinstance(c, dict) and str(c.get("nombre", "")).strip()]
    if certificadores:
        etiquetas = ""
        for c in certificadores:
            ambito = str(c.get("ambito", "")).strip()
            etiquetas += ('<span class="etiqueta">' + _e(c.get("nombre"))
                          + (f' · {_e(ambito)}' if ambito else "") + '</span>')
        tarjetas.append(
            '<div class="tarjeta"><div class="rol">Certificadores</div>'
            f'<div class="conteo">{len(certificadores)} por ámbito o país</div>'
            f'<div class="etiquetas">{etiquetas}</div></div>')

    if not tarjetas:
        return ""
    return ('<section class="revelar"><div class="titulo-seccion">'
            '<h2>Gobierno del producto</h2></div>'
            '<div class="rejilla">' + "\n".join(tarjetas) + '</div></section>')


def _fuentes(discovery: dict) -> str:
    fuentes = _fuentes_validas(discovery)
    if not fuentes:
        return '<p class="vacio">Sin fuentes de datos registradas.</p>'
    por_servidor: Dict[str, List[dict]] = {}
    for f in fuentes:
        servidor = str(f.get("servidor", "")).strip() or "Servidor por definir"
        por_servidor.setdefault(servidor, []).append(f)

    salida = []
    for servidor, lista in por_servidor.items():
        sensible = any(str(f.get("sensible", "")).strip().lower().startswith(("sí", "si"))
                       for f in lista)
        candado = (' <span class="candado" title="Incluye datos sensibles" '
                   'aria-label="Incluye datos sensibles">🔒</span>' if sensible else "")
        etiquetas = "".join(f'<span class="etiqueta">{_e(f.get("tabla"))}</span>'
                            for f in lista[:_MAX_TABLAS_POR_SERVIDOR])
        salida.append(
            f'<div class="tarjeta"><div class="nombre">{_e(servidor)}{candado}</div>'
            f'<div class="conteo">{len(lista)} tabla(s)</div>'
            f'<div class="etiquetas">{etiquetas}</div></div>')
    return "\n".join(salida)


def _temas(discovery: dict) -> str:
    temas = [t for t in discovery.get("temas_faltantes", [])
             if isinstance(t, dict) and str(t.get("punto", "")).strip()]
    if not temas:
        return ('<div class="fila"><span class="franja" style="background:var(--go)"></span>'
                '<div class="cuerpo"><p class="principal">Sin temas pendientes: el Discovery '
                'respondió todas las preguntas de la rúbrica.</p></div></div>')

    peso = {"Bloqueante": 0, "Recomendado": 1}
    temas = sorted(temas, key=lambda t: peso.get(str(t.get("impacto", "")), 2))
    salida = []
    for t in temas[:_MAX_TEMAS]:
        impacto = str(t.get("impacto", "")).strip()
        clase = ("alta" if impacto == "Bloqueante"
                 else "media" if impacto == "Recomendado" else "")
        distintivo = f'<span class="distintivo {clase}">{_e(impacto)}</span>' if impacto else ""
        accion = str(t.get("accion_sugerida", "")).strip()
        detalle = (f'<p class="detalle">{_e(accion)}</p>'
                   if accion and not es_ausente(accion) else "")
        salida.append(
            f'<div class="fila"><span class="franja" style="background:var(--{_color_sev(clase)})">'
            f'</span><div class="cuerpo"><p class="principal">{_limpio(t.get("punto"))}</p>'
            f'{detalle}</div>{distintivo}</div>')
    return "\n".join(salida)


def _fuentes_validas(discovery: dict) -> List[dict]:
    return [f for f in discovery.get("fuentes", [])
            if isinstance(f, dict) and str(f.get("tabla", "")).strip()]


# ---------------------------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------------------------
def render_html(discovery: dict, caso: str = "", score: Optional[dict] = None,
                fidelidad: Optional[dict] = None, inconsistencias: Optional[dict] = None) -> str:
    """Devuelve el HTML del Resumen Ejecutivo (string autónomo, listo para escribir a disco)."""
    score = score or score_discovery(discovery)
    evaluacion = ((inconsistencias or {}).get("evaluacion", {})
                  if isinstance(inconsistencias, dict) else {})
    veredicto = score.get("veredicto", "Condicional")
    titulo = str(discovery.get("nombre_caso_uso") or caso or "Producto de datos").strip()
    n_casos = len([c for c in discovery.get("casos_uso", [])
                   if isinstance(c, dict) and str(c.get("nombre", "")).strip()])

    reemplazos = {
        "TITULO": _limpio(titulo),
        "FECHA": _e(discovery.get("fecha_discovery") or "—"),
        "VEREDICTO": _e(veredicto),
        "VEREDICTO_CLASE": _CLASE_VEREDICTO.get(veredicto, "cond"),
        "VEREDICTO_ICONO": _ICONO_VEREDICTO.get(veredicto, "•"),
        "VEREDICTO_NOTA": _e(_NOTA_VEREDICTO.get(veredicto, "")),
        "COMPLETITUD": _fmt(score.get("completitud_total", 0)),
        "COBERTURA": _fmt((fidelidad or {}).get("cobertura_pct", 0)),
        "N_CASOS": str(n_casos or 1),
        "N_FUENTES": str(len(_fuentes_validas(discovery))),
        "THESIS": _thesis(discovery),
        "KPIS": _kpis(discovery, score, evaluacion),
        "MENSAJES": _mensajes(discovery),
        "BLOQUE_CONDICIONES": _bloque_condiciones(score),
        "RIESGOS": _riesgos(discovery),
        "BLOQUES": _bloques(score),
        "BLOQUE_BENEFICIO": _bloque_beneficio(discovery),
        "FUENTES": _fuentes(discovery),
        "BLOQUE_GOBIERNO": _bloque_gobierno(discovery),
        "TEMAS": _temas(discovery),
    }
    tpl = cargar_plantilla()
    for clave, valor in reemplazos.items():
        tpl = tpl.replace("{{" + clave + "}}", valor)
    return tpl


def exportar_html(path: str, discovery: dict, caso: str = "", score: Optional[dict] = None,
                  fidelidad: Optional[dict] = None, inconsistencias: Optional[dict] = None) -> str:
    """Escribe el Resumen Ejecutivo HTML en `path` y devuelve la ruta."""
    contenido = render_html(discovery, caso=caso, score=score, fidelidad=fidelidad,
                            inconsistencias=inconsistencias)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(contenido)
    return path


def _fmt(v: object) -> str:
    """Número legible: sin decimal cuando es entero (87.0 → '87', 87.5 → '87.5')."""
    try:
        f = float(v)
        return str(int(f)) if f == int(f) else str(round(f, 1))
    except (TypeError, ValueError):
        return "0"
