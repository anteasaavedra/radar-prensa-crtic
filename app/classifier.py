"""
Clasificación automática de menciones CRTIC.
Reglas heurísticas basadas en keywords y patrones de texto.
"""
import re
import logging

logger = logging.getLogger("radar_prensa.classifier")

# ── Tipo de mención ────────────────────────────────────────────────────────────

_TIPO_PATTERNS = [
    ("Entrevista",         [r"\bentrevist", r"\bconvers[aó]", r"\bhabla con\b", r"\bdice\b.*\bCRTIC"]),
    ("Reportaje",          [r"\breportaje\b", r"\binvestigaci[oó]n\b", r"\binforme especial\b"]),
    ("Nota principal",     [r"\bCRTIC\b.{0,60}(lidera|anuncia|lanza|presenta|inaugura|firma)"]),
    ("Agenda / cartelera", [r"\bagenda\b", r"\bcartelera\b", r"\BCRTIC\b.*\bevento\b", r"\bcurso\b.*CRTIC", r"\btaller\b.*CRTIC"]),
    ("Institucional / aliado", [r"\bCORFO\b", r"\bCAF\b", r"\bBID\b", r"\bCOPEC\b", r"\bGAM\b",
                                r"\bChileCreativo\b", r"\bMeta AI\b", r"\bETM Day\b"]),
    ("Mención secundaria", [r"\btambi[eé]n\b", r"\bentre ellos\b", r"\bparticip[oó]\b",
                             r"\basistieron\b", r"\bjunto a\b"]),
]

_TIPO_DEFAULT = "Otro"


def classify_tipo(titulo: str, snippet: str) -> str:
    text = f"{titulo} {snippet}".lower()
    for tipo, patterns in _TIPO_PATTERNS:
        if any(re.search(p, text, re.IGNORECASE) for p in patterns):
            return tipo
    # Heurística simple: si CRTIC aparece en el título → nota principal
    if re.search(r"\bCRTIC\b", titulo, re.IGNORECASE):
        return "Nota principal"
    return _TIPO_DEFAULT


# ── Sentimiento ────────────────────────────────────────────────────────────────

_POS_WORDS = [
    "exitoso", "éxito", "logro", "ganó", "premio", "reconocimiento", "innova",
    "lidera", "destaca", "lanzó", "inaugura", "fortalece", "alianza", "acuerdo",
    "beneficio", "oportunidad", "avance", "crecimiento", "pionero", "referente",
    "capacita", "forma", "emprendimiento", "creatividad",
]
_NEG_WORDS = [
    "crisis", "problema", "denuncia", "critic", "fracas", "falla", "error",
    "escándalo", "corrupción", "quiebre", "cierre", "demanda", "conflicto",
    "controversial", "polémic", "cuestionado", "irregularidad",
]


def classify_sentimiento(titulo: str, snippet: str) -> str:
    text = f"{titulo} {snippet}".lower()
    pos = sum(1 for w in _POS_WORDS if w in text)
    neg = sum(1 for w in _NEG_WORDS if w in text)
    if neg > pos:
        return "Negativo"
    if pos > neg:
        return "Positivo"
    return "Neutro"


# ── Relevancia ─────────────────────────────────────────────────────────────────

def classify_relevancia(titulo: str, snippet: str, keyword: str) -> str:
    text = f"{titulo} {snippet}"
    crtic_count = len(re.findall(r"\bCRTIC\b", text, re.IGNORECASE))

    # Keyword compuesta → relevancia mayor
    compound = len(keyword.split()) > 1

    if re.search(r"\bCRTIC\b", titulo, re.IGNORECASE) and crtic_count >= 2:
        return "Alta"
    if re.search(r"\bCRTIC\b", titulo, re.IGNORECASE) or (compound and crtic_count >= 1):
        return "Media"
    return "Baja"


# ── Área CRTIC ─────────────────────────────────────────────────────────────────

_AREA_PATTERNS = [
    ("Formación",                   [r"\bcurso\b", r"\btaller\b", r"\bcapacita", r"\bformaci[oó]n\b",
                                     r"\bprograma\b.*educati", r"\bdiploma\b", r"\bbootcamp\b"]),
    ("Comunicaciones",              [r"\bcomunicaci[oó]n\b", r"\bprensa\b", r"\bmedios\b", r"\bnota\b",
                                     r"\bpublicaci[oó]n\b", r"\bredes sociales\b"]),
    ("Proyectos / Emprendimiento",  [r"\bemprendimiento\b", r"\bstartup\b", r"\bproyecto\b",
                                     r"\bfondo\b", r"\bconcurso\b", r"\bpostula\b"]),
    ("CRTIC Sur",                   [r"\bCRTIC Sur\b", r"\bsur\b.*CRTIC", r"\bPatagonia\b"]),
    ("Alianzas",                    [r"\balianza\b", r"\bconvenio\b", r"\bacuerdo\b", r"\bsoci[oa]\b",
                                     r"\bCORFO\b", r"\bCAF\b", r"\bBID\b", r"\bCOPEC\b",
                                     r"\bGAM\b", r"\bMeta AI\b", r"\bChileCreativo\b"]),
    ("Tecnología / Innovación",     [r"\bIA\b", r"\binteligencia artificial\b", r"\bUnreal Engine\b",
                                     r"\binnovaci[oó]n\b", r"\btecnolog[ií]a\b", r"\bdigital\b",
                                     r"\btecnocreat", r"\bvideojuego\b", r"\bgaming\b"]),
    ("Institucional",               [r"\binstitucional\b", r"\bautoridad\b", r"\bministeri\b",
                                     r"\bgobierno\b", r"\bpolítica p[uú]blica\b"]),
]

_AREA_DEFAULT = "Otro"


def classify_area(titulo: str, snippet: str, keyword: str) -> str:
    text = f"{titulo} {snippet} {keyword}"
    for area, patterns in _AREA_PATTERNS:
        if any(re.search(p, text, re.IGNORECASE) for p in patterns):
            return area
    return _AREA_DEFAULT


# ── Clasificador completo ──────────────────────────────────────────────────────

def classify(item: dict) -> dict:
    titulo = item.get("titulo", "") or ""
    snippet = item.get("snippet", "") or ""
    keyword = item.get("keyword", "") or ""

    item["tipo_mencion"] = classify_tipo(titulo, snippet)
    item["sentimiento"] = classify_sentimiento(titulo, snippet)
    item["relevancia"] = classify_relevancia(titulo, snippet, keyword)
    item["area_crtic"] = classify_area(titulo, snippet, keyword)
    return item
