"""
Autenticación de administrador para el dashboard CRTIC.

Prioridad:
  1. Hash en data/admin_auth.json  (creado al primer cambio de contraseña)
  2. ADMIN_PASSWORD en st.secrets / .env  (contraseña inicial / fallback)
"""
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path

import bcrypt

logger = logging.getLogger("radar_prensa.auth")

_AUTH_PATH = Path(__file__).resolve().parent.parent / "data" / "admin_auth.json"


# ── Leer ADMIN_PASSWORD de entorno / st.secrets ───────────────────────────────

def _env_password() -> str:
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "ADMIN_PASSWORD" in st.secrets:
            return str(st.secrets["ADMIN_PASSWORD"])
    except Exception:
        pass
    return os.getenv("ADMIN_PASSWORD", "")


# ── Cargar / guardar admin_auth.json ──────────────────────────────────────────

def _load_auth() -> dict:
    try:
        with open(_AUTH_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_auth(data: dict) -> None:
    _AUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_AUTH_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── API pública ───────────────────────────────────────────────────────────────

def verify_password(password: str) -> bool:
    """
    Verifica la contraseña de administrador.
    Primero intenta contra el hash en admin_auth.json;
    si no existe, compara directamente con ADMIN_PASSWORD de entorno.
    """
    if not password:
        return False
    auth = _load_auth()
    stored_hash = auth.get("password_hash", "")
    if stored_hash:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
        except Exception as e:
            logger.error("Error verificando hash: %s", e)
            return False
    # Fallback: ADMIN_PASSWORD en texto plano desde secrets/.env
    env_pw = _env_password()
    return bool(env_pw) and password == env_pw


def set_password(new_password: str, admin_name: str = "", admin_email: str = "") -> None:
    """Hashea y guarda la nueva contraseña en admin_auth.json."""
    hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    auth = _load_auth()
    auth["password_hash"] = hashed
    auth["updated_at"] = datetime.now().isoformat()
    if admin_name:
        auth["admin_name"] = admin_name
    if admin_email:
        auth["admin_email"] = admin_email
    _save_auth(auth)
    logger.info("Contraseña de administrador actualizada.")


def get_admin_info() -> dict:
    """Retorna nombre y email del admin si están guardados."""
    auth = _load_auth()
    return {
        "admin_name":  auth.get("admin_name", ""),
        "admin_email": auth.get("admin_email", ""),
        "updated_at":  auth.get("updated_at", ""),
        "has_hash":    bool(auth.get("password_hash", "")),
    }


def check_requirements(password: str) -> list:
    """
    Valida la complejidad de la contraseña.
    Retorna lista de requisitos no cumplidos (vacía = OK).
    """
    errors = []
    if len(password) < 10:
        errors.append("Mínimo 10 caracteres")
    if not re.search(r"[A-Z]", password):
        errors.append("Al menos una letra mayúscula")
    if not re.search(r"[a-z]", password):
        errors.append("Al menos una letra minúscula")
    if not re.search(r"\d", password):
        errors.append("Al menos un número")
    if not re.search(r"""[!@#$%^&*()\-_=+\[\]{}|;:'",.<>?/\\`~]""", password):
        errors.append("Al menos un símbolo (!@#$%...)")
    return errors
