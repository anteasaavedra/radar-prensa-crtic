import os
import logging
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _get(key: str, default: str = "") -> str:
    """Lee desde st.secrets (Streamlit Cloud) con fallback a .env / variables de entorno."""
    try:
        import streamlit as st
        # hasattr evita KeyError sin lanzar excepción
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.getenv(key, default)


# ── Búsqueda ───────────────────────────────────────────────────────────────────
SEARCH_API_PROVIDER = _get("SEARCH_API_PROVIDER", "serpapi")
SEARCH_API_KEY      = _get("SEARCH_API_KEY", "")
GOOGLE_PSE_CX       = _get("GOOGLE_PSE_CX", "")

# ── Base de datos ──────────────────────────────────────────────────────────────
_db_path_str = _get("DB_PATH", "data/radar_prensa.db")
DB_PATH = BASE_DIR / _db_path_str
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Correo ─────────────────────────────────────────────────────────────────────
SMTP_HOST     = _get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(_get("SMTP_PORT", "587"))
SMTP_USER     = _get("SMTP_USER", "")
SMTP_PASSWORD = _get("SMTP_PASSWORD", "")
EMAIL_FROM    = _get("EMAIL_FROM") or SMTP_USER
EMAIL_TO      = [e.strip() for e in _get("EMAIL_TO", "").split(",") if e.strip()]

# ── General ────────────────────────────────────────────────────────────────────
TIMEZONE  = _get("TIMEZONE", "America/Santiago")
LOG_LEVEL = _get("LOG_LEVEL", "INFO")

MEDIA_VALUES_PATH = BASE_DIR / "data" / "media_values.json"
EXPORTS_DIR       = BASE_DIR / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR     = BASE_DIR / "templates"

# ── Keywords CRTIC ─────────────────────────────────────────────────────────────
KEYWORDS = [
    "CRTIC",
    "Centro para la Revolución Tecnológica en Industrias Creativas",
    "tecnocreatividad",
    "tecnocreativo",
    "CRTIC Sur",
    "LAB CRTIC",
    "CRTIC Lab",
    "ChileCreativo CRTIC",
    "CORFO CRTIC",
    "Unreal Engine CRTIC",
    "Meta AI CRTIC",
    "CAF CRTIC",
    "BID CRTIC",
    "COPEC CRTIC",
    "GAM CRTIC",
    "ETM Day CRTIC",
    "Isidora Cabezón CRTIC",
    "Pablo Christiny CRTIC",
]

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("radar_prensa")
