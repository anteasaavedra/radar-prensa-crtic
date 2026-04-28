"""
Cálculo del Valor Estimado de Exposición Mediática (VEM).
VEM = valor_base_medio * factor_visibilidad * factor_estrategico

Todos los valores son referenciales y no equivalen a tarifas comerciales exactas.
"""
import json
import logging
import re
from urllib.parse import urlparse
from app.config import MEDIA_VALUES_PATH

logger = logging.getLogger("radar_prensa.valuation")

_data: dict = {}


def _load():
    global _data
    if not _data:
        with open(MEDIA_VALUES_PATH, encoding="utf-8") as f:
            _data = json.load(f)
    return _data


def _get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def get_valor_base(url: str, medio: str = "") -> tuple[float, str]:
    """Retorna (valor_base, clave_usada)."""
    data = _load()
    medios = data.get("medios", {})
    dominios_uni = set(data.get("dominios_universitarios", []))

    domain = _get_domain(url)

    # Búsqueda exacta por dominio
    if domain in medios:
        entry = medios[domain]
        return float(entry["valor_base"]), domain

    # Búsqueda parcial (ej. subdominio)
    for key, entry in medios.items():
        if key.startswith("default"):
            continue
        if key in domain or domain.endswith(f".{key}"):
            return float(entry["valor_base"]), key

    # Universidades
    if any(domain.endswith(u) for u in dominios_uni):
        return float(medios["default_universidad"]["valor_base"]), "default_universidad"

    # Medio regional si contiene "regional" en el nombre
    medio_lower = medio.lower()
    if any(w in medio_lower for w in ("regional", "soy", "soychile", "ciudad", "local")):
        return float(medios["default_regional"]["valor_base"]), "default_regional"

    return float(medios["default"]["valor_base"]), "default"


def get_factor_visibilidad(tipo_mencion: str, titulo: str) -> float:
    data = _load()
    fv = data.get("factores_visibilidad", {})

    tipo_lower = tipo_mencion.lower()
    if "entrevista" in tipo_lower or "reportaje" in tipo_lower:
        return fv.get("entrevista", 1.4)
    if "nota principal" in tipo_lower:
        # Extra si CRTIC aparece en el titular
        return fv.get("titular", 1.2)
    if "mención secundaria" in tipo_lower:
        return fv.get("mencion_secundaria", 0.5)
    if "agenda" in tipo_lower or "cartelera" in tipo_lower:
        return fv.get("agenda", 0.3)
    if "institucional" in tipo_lower or "aliado" in tipo_lower:
        return fv.get("institucional", 0.6)
    return fv.get("nota_completa", 1.0)


def get_factor_estrategico(area_crtic: str, keyword: str) -> float:
    data = _load()
    fe = data.get("factores_estrategicos", {})

    area_lower = area_crtic.lower()
    kw_lower = keyword.lower()

    if any(w in area_lower or w in kw_lower for w in ("tecnolog", "innovaci", "unreal",
                                                        "internacion", "meta ai",
                                                        "inteligencia artificial")) or \
       any(re.search(r'\bia\b', t) for t in (area_lower, kw_lower)):
        return fe.get("ia_innovacion_internacionalizacion", 1.2)
    if any(w in area_lower or w in kw_lower for w in ("alianza", "convenio", "acuerdo", "corfo", "caf",
                                                        "bid", "copec", "gam", "chilecreativo")):
        return fe.get("alianzas_estrategicas", 1.1)
    if any(w in area_lower or w in kw_lower for w in ("formaci", "curso", "taller", "capacita", "bootcamp")):
        return fe.get("formacion_cursos", 1.0)
    if any(w in area_lower or w in kw_lower for w in ("evento", "agenda", "convocatoria", "etm")):
        return fe.get("evento_menor", 0.8)
    if area_crtic in ("Mención secundaria", "Otro"):
        return fe.get("mencion_tangencial", 0.6)
    return 1.0


def calculate_vem(item: dict) -> dict:
    """Calcula y añade valor_base_medio, factor_visibilidad, factor_estrategico y vem al dict."""
    valor_base, _ = get_valor_base(item.get("url", ""), item.get("medio", ""))
    fv = get_factor_visibilidad(item.get("tipo_mencion", ""), item.get("titulo", ""))
    fe = get_factor_estrategico(item.get("area_crtic", ""), item.get("keyword", ""))

    vem = round(valor_base * fv * fe)

    item["valor_base_medio"] = valor_base
    item["factor_visibilidad"] = fv
    item["factor_estrategico"] = fe
    item["vem"] = vem
    return item
