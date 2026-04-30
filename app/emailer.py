"""
Envío de correos: reporte diario, reporte mensual y alertas de menciones negativas.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
    EMAIL_FROM, EMAIL_TO, TEMPLATES_DIR,
)

logger = logging.getLogger("radar_prensa.emailer")


def _jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )


def _send(subject: str, html: str, to: list = None):
    recipients = to or EMAIL_TO
    if not recipients:
        logger.warning("Sin destinatarios. Correo no enviado.")
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html", "utf-8"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, recipients, msg.as_string())
        logger.info("Correo '%s' enviado a: %s", subject[:50], recipients)
    except smtplib.SMTPException as e:
        logger.error("Error al enviar correo: %s", e)
        raise


def send_report(html_path: str, fecha: str, vem_total: str, total_menciones: int):
    from app.email_config import get_recipients
    html = Path(html_path).read_text(encoding="utf-8")
    subject = f"📡 Radar CRTIC – {fecha} | {total_menciones} menciones | VEM {vem_total}"
    _send(subject, html, to=get_recipients())


def send_monthly_report(html_path: str, periodo: str, vem_total: str, total_menciones: int):
    html = Path(html_path).read_text(encoding="utf-8")
    subject = f"📊 Radar CRTIC — Reporte mensual {periodo} | {total_menciones} menciones | VEM {vem_total}"
    _send(subject, html)


def send_negative_alert(mencion: dict):
    """Alerta inmediata cuando se detecta una mención negativa."""
    env = _jinja_env()
    template = env.get_template("alerta_negativa.html")
    html = template.render(mencion=mencion)
    subject = f"⚠️ ALERTA CRTIC: mención negativa en {mencion.get('medio', 'medio desconocido')}"
    _send(subject, html)
