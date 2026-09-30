"""Normalización y comparación de texto — la base determinista de la deduplicación.

Un Discovery real recorre cinco o seis reuniones, y el mismo hecho se dice en varias: "la réplica
evita bloqueos", "hay que replicar para no bloquear producción", "usamos réplica no transaccional
por los bloqueos". Un destilado honesto extrae los tres. Sin este módulo, los tres llegan al
documento y el lector lee tres veces lo mismo.

Comparar textos es un problema de similitud, no de igualdad, y se resuelve con código: no hace
falta un modelo para saber que dos frases dicen lo mismo cuando comparten sus palabras con
contenido. Todo aquí es stdlib pura y determinista — mismo par de textos, mismo resultado, siempre.
"""
from __future__ import annotations

import os
import re
import unicodedata
from difflib import SequenceMatcher
from typing import List, Set

# Palabras vacías del español: no aportan a la identidad semántica de una frase, así que no deben
# inflar el parecido entre dos textos que solo comparten conectores.
STOPWORDS: Set[str] = {
    "a", "al", "algo", "alguna", "algunas", "alguno", "algunos", "ante", "antes", "aquel",
    "aquella", "aquello", "aqui", "asi", "aun", "aunque", "cada", "como", "con", "contra",
    "cual", "cuales", "cuando", "cuanto", "de", "del", "desde", "donde", "dos", "e", "el",
    "ella", "ellas", "ello", "ellos", "en", "entre", "era", "eran", "es", "esa", "esas", "ese",
    "eso", "esos", "esta", "estan", "estas", "este", "esto", "estos", "fue", "fueron", "ha",
    "haber", "hace", "hacer", "hacia", "han", "hasta", "hay", "la", "las", "le", "les", "lo",
    "los", "mas", "me", "mi", "mientras", "muy", "ni", "no", "nos", "o", "otra", "otras",
    "otro", "otros", "para", "pero", "poco", "por", "porque", "que", "quien", "se", "segun",
    "ser", "si", "sin", "sobre", "solo", "son", "su", "sus", "tambien", "tan", "tanto", "te",
    "tiene", "tienen", "todo", "todos", "tras", "un", "una", "uno", "unos", "y", "ya",
}

_NO_ALFANUM = re.compile(r"[^a-z0-9]+")
_ESPACIOS = re.compile(r"\s+")


def sin_acentos(texto: object) -> str:
    """Quita diacríticos preservando la letra base ('réplica' → 'replica')."""
    crudo = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(c for c in crudo if unicodedata.category(c) != "Mn")


def normalizar(texto: object) -> str:
    """Forma canónica para comparar: minúsculas, sin acentos, sin puntuación, espacios colapsados."""
    plano = sin_acentos(texto).lower()
    plano = _NO_ALFANUM.sub(" ", plano)
    return _ESPACIOS.sub(" ", plano).strip()


# El recorte va en tres pasadas, y el orden no es negociable: "facturaciones" tiene que perder
# primero el plural, luego la derivación y solo entonces la vocal. Hacerlo en otro orden deja
# raíces distintas para la misma palabra en singular y en plural, que es justo el error que este
# recortador existe para no cometer.
_PLURALES = ("es", "os", "as", "s")

_DERIVACION = tuple(sorted((
    # derivación nominal
    "amiento", "imiento", "aciones", "iciones", "idades", "ciones",
    "adores", "amente", "adora", "ador", "cion", "sion", "mente", "dad",
    # conjugación verbal
    "ieron", "iendo", "aron", "aban", "ando", "emos", "imos", "amos",
    "aba", "ara", "era", "ian", "an", "en", "on", "ar", "er", "ir",
), key=len, reverse=True))

# Por debajo de esta longitud, recortar deja de distinguir palabras y empieza a confundirlas.
_MINIMO_RAIZ = 3


def raiz(palabra: str) -> str:
    """Raíz aproximada de una palabra en español, por recorte de sufijos.

    El español flexiona mucho, y sin esto la comparación de textos falla en lo más obvio:
    "la réplica evita bloqueos" y "las réplicas evitan el bloqueo" no comparten *ninguna* palabra
    exacta pese a decir lo mismo. Con raíces comparten todas.

    Es un recortador conservador, no un lematizador: no consulta diccionario ni resuelve
    irregulares, y a veces junta dos palabras que no debería. No hace falta que acierte siempre —
    hace falta que **acierte igual cada vez**, porque lo que se compara son dos textos entre sí y
    no una palabra contra la gramática. Un recorte consistentemente imperfecto sigue emparejando
    bien; uno que trata distinto al singular y al plural, no.

    Los participios (-ado/-ada/-ido/-ida) se dejan a la pasada de vocales a propósito: recortarlos
    como sufijo produce "pesada"→"pes" pero "pesadas"→"pesad", y esa asimetría rompe la
    comparación exactamente en las palabras más comunes.
    """
    p = palabra
    for sufijo in _PLURALES:
        if p.endswith(sufijo) and len(p) - len(sufijo) >= _MINIMO_RAIZ:
            p = p[: -len(sufijo)]
            break
    for sufijo in _DERIVACION:
        if p.endswith(sufijo) and len(p) - len(sufijo) >= _MINIMO_RAIZ:
            p = p[: -len(sufijo)]
            break
    # Las vocales finales son casi siempre marca de género o conjugación ("bloqueo"/"bloquear"
    # comparten "bloqu"), así que se recortan hasta llegar a la consonante.
    while len(p) > _MINIMO_RAIZ and p[-1] in "aeo":
        p = p[:-1]
    return p


def tokens_significativos(texto: object) -> Set[str]:
    """Conjunto de raíces con contenido: normalizadas, sin stopwords, de 2+ caracteres.

    Se devuelve un conjunto (no una lista) a propósito: la identidad de un hecho no depende del
    orden en que se enuncie. "La réplica evita bloqueos" y "los bloqueos los evita la réplica"
    son el mismo hecho.
    """
    return {raiz(t) for t in normalizar(texto).split() if len(t) > 1 and t not in STOPWORDS}


def similitud(a: object, b: object) -> float:
    """Parecido semántico aproximado entre dos textos, en [0, 1].

    Combina tres señales, cada una ciega a lo que las otras ven:

    - **Jaccard de tokens significativos** — insensible al orden y a la redacción. Es la señal
      principal: dos frases que comparten sus sustantivos y verbos hablan de lo mismo.
    - **Ratio de secuencia** (`difflib`) — sensible al orden. Desempata los casos en que dos frases
      comparten vocabulario pero lo articulan distinto.
    - **Contención** — cuando una frase es un subconjunto estricto de la otra, la corta no aporta
      nada que la larga no diga ya. Solo se aplica con 3+ tokens, para no fusionar fragmentos.

    No pretende ser una medida semántica verdadera: pretende ser *predecible*. Un umbral que se
    puede probar vale más que un parecido que se puede discutir.
    """
    ta, tb = tokens_significativos(a), tokens_significativos(b)
    if not ta or not tb:
        # Sin tokens con contenido (frases de puros conectores): se cae al texto normalizado.
        na, nb = normalizar(a), normalizar(b)
        return 1.0 if na and na == nb else 0.0

    interseccion = len(ta & tb)
    jaccard = interseccion / len(ta | tb)
    ratio = SequenceMatcher(None, normalizar(a), normalizar(b)).ratio()
    mezcla = 0.7 * jaccard + 0.3 * ratio

    minimo = min(len(ta), len(tb))
    if minimo >= 3:
        contencion = interseccion / minimo
        if contencion == 1.0:
            return max(mezcla, 0.9)
    return mezcla


def slug(nombre: str, maximo: int = 40) -> str:
    """Nombre de archivo seguro derivado de un nombre humano ('Acta 01.docx' → 'acta_01')."""
    base = os.path.splitext(os.path.basename(str(nombre or "")))[0].lower()
    limpio = _NO_ALFANUM.sub("_", sin_acentos(base)).strip("_")
    return limpio[:maximo] or "insumo"


def truncar(texto: object, maximo: int = 120) -> str:
    """Recorta un texto a `maximo` caracteres añadiendo elipsis si se cortó."""
    s = str(texto or "").strip()
    return s if len(s) <= maximo else s[:maximo].rstrip() + "…"


def aplanar(valor: object) -> str:
    """Reduce cualquier valor del schema (str, lista, dict, anidados) a un solo texto plano.

    Sirve para preguntarle algo a un valor sin importar su forma: ¿contiene una cita?, ¿se parece
    a este otro? La estructura tipada se conserva íntegra en el estado; esto es solo una lente
    de lectura sobre ella.
    """
    if isinstance(valor, str):
        return valor
    if isinstance(valor, (list, tuple)):
        return " ".join(aplanar(v) for v in valor)
    if isinstance(valor, dict):
        return " ".join(aplanar(v) for v in valor.values())
    return str(valor if valor is not None else "")


def parrafos(texto: object) -> List[str]:
    """Divide un texto en párrafos no vacíos (separados por línea en blanco o salto simple)."""
    return [p.strip() for p in re.split(r"\n\s*\n|\n", str(texto or "")) if p.strip()]
