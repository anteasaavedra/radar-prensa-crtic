"""
Generación de reportes HTML (diario y mensual) y exportación CSV/Excel.
"""
import logging
import calendar
from datetime import datetime
from pathlib import Path
import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.config import TEMPLATES_DIR, EXPORTS_DIR
from app.database import (
    get_menciones, get_vem_diario, get_vem_mensual, get_vem_comparativo,
    get_stats_por_campo,
)

logger = logging.getLogger("radar_prensa.report")

MESES_ES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )


def _format_clp(value: float) -> str:
    return f"$ {int(value):,}".replace(",", ".")


def _pct_change(actual: float, anterior: float) -> str:
    if anterior == 0:
        return "—"
    pct = ((actual - anterior) / anterior) * 100
    arrow = "▲" if pct >= 0 else "▼"
    return f"{arrow} {abs(pct):.1f}%"


def _recomendaciones(menciones: list) -> list:
    recs = []
    neg = [m for m in menciones if m["sentimiento"] == "Negativo"]
    alta = [m for m in menciones if m["relevancia"] == "Alta"]
    entrevistas = [m for m in menciones if m["tipo_mencion"] == "Entrevista"]

    if neg:
        recs.append(f"⚠️ {len(neg)} mención(es) negativa(s). Evaluar respuesta o aclaración pública.")
    if alta:
        recs.append(f"⭐ {len(alta)} mención(es) de alta relevancia. Repostear en RRSS y guardar para memoria anual.")
    if entrevistas:
        recs.append(f"🎙️ {len(entrevistas)} entrevista(s). Agradecer al medio y amplificar en canales CRTIC.")
    for m in menciones:
        text = f"{m.get('titulo','')} {m.get('snippet','')}".lower()
        if "crtic" not in text and "tecnocreat" not in text:
            recs.append(f"📝 Verificar denominación en: '{m.get('titulo','')[:50]}' ({m.get('medio','')})")
            break
    if not recs:
        recs.append("✅ Sin alertas críticas. Monitoreo rutinario.")
    return recs


# ── Reporte diario ─────────────────────────────────────────────────────────────

def generate_daily_html(fecha=None, menciones_override=None) -> str:
    fecha = fecha or datetime.now().strftime("%Y-%m-%d")
    if menciones_override is not None:
        menciones = menciones_override
    else:
        menciones = get_menciones(fecha_desde=fecha, fecha_hasta=fecha, estado="nueva", limit=200)
    vem_total = get_vem_diario(fecha)
    top3 = sorted(menciones, key=lambda m: m.get("vem", 0), reverse=True)[:3]
    negativas = [m for m in menciones if m["sentimiento"] == "Negativo"]
    altas = [m for m in menciones if m["relevancia"] == "Alta"]

    env = _jinja_env()
    html = env.get_template("reporte_diario.html").render(
        fecha=fecha,
        total_menciones=len(menciones),
        vem_total=_format_clp(vem_total),
        vem_total_raw=vem_total,
        menciones=menciones,
        top3=top3,
        negativas=negativas,
        altas=altas,
        recomendaciones=_recomendaciones(menciones),
        format_clp=_format_clp,
        generado=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )
    out = EXPORTS_DIR / f"reporte_{fecha}.html"
    out.write_text(html, encoding="utf-8")
    logger.info("Reporte diario HTML guardado: %s", out)
    return str(out)


# ── Reporte mensual ────────────────────────────────────────────────────────────

def generate_monthly_html(anio=None, mes=None) -> str:
    now = datetime.now()
    anio = anio or now.year
    mes = mes or now.month
    prefix = f"{anio}-{mes:02d}"
    ultimo_dia = calendar.monthrange(anio, mes)[1]

    menciones = get_menciones(
        fecha_desde=f"{prefix}-01",
        fecha_hasta=f"{prefix}-{ultimo_dia:02d}",
        limit=2000,
    )
    vem_total = get_vem_mensual(anio, mes)
    comparativo = get_vem_comparativo(n_meses=7)

    # Mes anterior para comparativo
    mes_ant = mes - 1 if mes > 1 else 12
    anio_ant = anio if mes > 1 else anio - 1
    vem_anterior = get_vem_mensual(anio_ant, mes_ant)
    variacion = _pct_change(vem_total, vem_anterior)

    top5 = sorted(menciones, key=lambda m: m.get("vem", 0), reverse=True)[:5]
    negativas = [m for m in menciones if m["sentimiento"] == "Negativo"]

    # Stats por campo
    stats_medio = get_stats_por_campo("medio", f"{prefix}-01", f"{prefix}-{ultimo_dia:02d}")[:10]
    stats_area = get_stats_por_campo("area_crtic", f"{prefix}-01", f"{prefix}-{ultimo_dia:02d}")
    stats_tipo = get_stats_por_campo("tipo_mencion", f"{prefix}-01", f"{prefix}-{ultimo_dia:02d}")
    stats_sent = get_stats_por_campo("sentimiento", f"{prefix}-01", f"{prefix}-{ultimo_dia:02d}")

    periodo = f"{MESES_ES[mes].capitalize()} {anio}"

    env = _jinja_env()
    html = env.get_template("reporte_mensual.html").render(
        anio=anio,
        mes=mes,
        periodo=periodo,
        total_menciones=len(menciones),
        vem_total=_format_clp(vem_total),
        vem_total_raw=vem_total,
        vem_anterior=_format_clp(vem_anterior),
        variacion=variacion,
        comparativo=comparativo,
        menciones=menciones,
        top5=top5,
        negativas=negativas,
        stats_medio=stats_medio,
        stats_area=stats_area,
        stats_tipo=stats_tipo,
        stats_sent=stats_sent,
        recomendaciones=_recomendaciones(menciones),
        format_clp=_format_clp,
        generado=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )
    out = EXPORTS_DIR / f"reporte_mensual_{prefix}.html"
    out.write_text(html, encoding="utf-8")
    logger.info("Reporte mensual HTML guardado: %s", out)
    return str(out)


# ── Exportaciones ──────────────────────────────────────────────────────────────

def export_csv(menciones: list, filename: str) -> str:
    path = EXPORTS_DIR / filename
    pd.DataFrame(menciones).to_csv(path, index=False, encoding="utf-8-sig")
    logger.info("CSV exportado: %s", path)
    return str(path)


def export_excel(menciones: list, filename: str) -> str:
    path = EXPORTS_DIR / filename
    df = pd.DataFrame(menciones)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Menciones")
        ws = writer.sheets["Menciones"]
        for col in ws.columns:
            max_len = max((len(str(cell.value or "")) for cell in col), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)
    logger.info("Excel exportado: %s", path)
    return str(path)


def export_daily(fecha=None, fmt: str = "csv") -> str:
    fecha = fecha or datetime.now().strftime("%Y-%m-%d")
    menciones = get_menciones(fecha_desde=fecha, fecha_hasta=fecha)
    fn = f"diario_{fecha}.{fmt}"
    return export_excel(menciones, fn) if fmt == "excel" else export_csv(menciones, fn)


def export_monthly(anio=None, mes=None, fmt: str = "csv") -> str:
    now = datetime.now()
    anio = anio or now.year
    mes = mes or now.month
    prefix = f"{anio}-{mes:02d}"
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    menciones = get_menciones(fecha_desde=f"{prefix}-01", fecha_hasta=f"{prefix}-{ultimo_dia:02d}")
    fn = f"mensual_{prefix}.{fmt}"
    return export_excel(menciones, fn) if fmt == "excel" else export_csv(menciones, fn)


def export_historico(fmt: str = "csv") -> str:
    menciones = get_menciones(limit=10000)
    fn = f"historico_{datetime.now().strftime('%Y%m%d')}.{fmt}"
    return export_excel(menciones, fn) if fmt == "excel" else export_csv(menciones, fn)
