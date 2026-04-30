"""
Carga, guarda y aplica la configuración de reportes por correo.
Lee/escribe data/email_report_config.json.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger("radar_prensa.email_config")

_CFG_PATH = Path(__file__).resolve().parent.parent / "data" / "email_report_config.json"

_DEFAULTS = {
    "enabled": True,
    "send_only_new_mentions": True,
    "send_empty_report": False,
    "min_relevance": "media",
    "include_keywords": [
        "CRTIC",
        "Centro para la Revolución Tecnológica en Industrias Creativas",
        "tecnocreatividad",
        "CRTIC Sur",
        "LAB CRTIC",
    ],
    "exclude_keywords": [],
    "priority_media": [
        "latercera.com",
        "emol.com",
        "df.cl",
        "biobiochile.cl",
        "elmostrador.cl",
    ],
    "included_areas": [
        "Formación",
        "Comunicaciones",
        "Proyectos / Emprendimiento",
        "CRTIC Sur",
        "Alianzas",
        "Tecnología / Innovación",
        "Institucional",
    ],
    "recipients": [],
    "send_time": "09:00",
    "timezone": "America/Santiago",
}

_REL_ORDER = {"Alta": 3, "Media": 2, "Baja": 1}


def load_email_cfg() -> dict:
    """Carga configuración; si no existe la crea con defaults."""
    try:
        with open(_CFG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        for k, v in _DEFAULTS.items():
            cfg.setdefault(k, v)
        return cfg
    except FileNotFoundError:
        save_email_cfg(_DEFAULTS.copy())
        return _DEFAULTS.copy()
    except json.JSONDecodeError as e:
        logger.error("email_report_config.json inválido: %s", e)
        return _DEFAULTS.copy()


def save_email_cfg(cfg: dict) -> None:
    _CFG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    logger.info("email_report_config.json guardado.")


def get_recipients() -> list:
    """Destinatarios desde config JSON; fallback a EMAIL_TO de config.py."""
    cfg = load_email_cfg()
    recs = [r.strip() for r in cfg.get("recipients", []) if r.strip()]
    if recs:
        return recs
    from app.config import EMAIL_TO
    return list(EMAIL_TO)


def filter_menciones_for_email(menciones: list) -> list:
    """
    Filtra la lista de menciones según email_report_config.json.
    Menciones de medios prioritarios ignoran los filtros de keyword/área/relevancia.
    """
    cfg = load_email_cfg()

    if not cfg.get("enabled", True):
        return []

    include_kw    = set(cfg.get("include_keywords", []))
    exclude_kw    = set(cfg.get("exclude_keywords", []))
    priority_med  = set(cfg.get("priority_media", []))
    included_areas = set(cfg.get("included_areas", []))
    min_rel       = cfg.get("min_relevance", "media").capitalize()
    only_new      = cfg.get("send_only_new_mentions", True)
    min_rel_val   = _REL_ORDER.get(min_rel, 2)

    filtered = []
    for m in menciones:
        kw    = m.get("keyword", "")
        medio = m.get("medio", "")
        area  = m.get("area_crtic", "")
        rel   = m.get("relevancia", "Baja")
        estado = m.get("estado", "nueva")

        is_priority = medio in priority_med

        # Estado: solo nuevas (medios prioritarios también respetan esto)
        if only_new and estado != "nueva":
            continue

        # Keywords excluidas (siempre aplica)
        if exclude_kw and kw in exclude_kw:
            continue

        # Los medios prioritarios saltan los demás filtros
        if is_priority:
            filtered.append(m)
            continue

        # Keyword incluida
        if include_kw and kw not in include_kw:
            continue

        # Área CRTIC
        if included_areas and area not in included_areas:
            continue

        # Relevancia mínima
        if _REL_ORDER.get(rel, 1) < min_rel_val:
            continue

        filtered.append(m)

    return filtered
