"""
Punto de entrada principal del Radar de Prensa CRTIC.

Uso:
  python -m app.main run-daily
  python -m app.main run-monthly
  python -m app.main export-monthly
  python -m app.main export-daily --fecha 2024-05-01
  python -m app.main export-historico --formato excel
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import click
from datetime import datetime

from app.config import logger
from app.database import init_db, get_menciones, get_vem_diario, get_vem_mensual
from app.search import run_daily_search
from app.classifier import classify
from app.valuation import calculate_vem
from app.database import insert_mencion
from app.report import generate_daily_html, generate_monthly_html, export_daily, export_monthly, export_historico
from app.emailer import send_report, send_monthly_report, send_negative_alert


def _process_results(results: list) -> tuple:
    """Clasifica, valora e inserta. Retorna (nuevas, duplicadas, negativas_nuevas)."""
    nuevas, duplicadas = 0, 0
    negativas_nuevas = []
    for item in results:
        item = classify(item)
        item = calculate_vem(item)
        item["estado"] = "nueva"
        inserted_id = insert_mencion(item)
        if inserted_id:
            nuevas += 1
            if item.get("sentimiento") == "Negativo":
                item["id"] = inserted_id
                negativas_nuevas.append(item)
        else:
            duplicadas += 1
    return nuevas, duplicadas, negativas_nuevas


@click.group()
def cli():
    """Radar de Prensa CRTIC — sistema de monitoreo mediático."""


@cli.command("run-daily")
@click.option("--no-email", is_flag=True, default=False, help="No enviar correo al finalizar.")
@click.option("--fecha", default=None, help="Fecha manual YYYY-MM-DD (por defecto: hoy).")
def run_daily(no_email, fecha):
    """Búsqueda diaria, clasificación, VEM, reporte y correo. Alerta inmediata si hay menciones negativas."""
    fecha = fecha or datetime.now().strftime("%Y-%m-%d")
    logger.info("=== Iniciando ciclo diario Radar CRTIC [%s] ===", fecha)

    init_db()

    logger.info("Fase 1/4: Búsqueda de menciones...")
    results = run_daily_search()

    logger.info("Fase 2/4: Clasificación y valorización...")
    nuevas, duplicadas, negativas_nuevas = _process_results(results)
    logger.info("Nuevas: %d | Duplicadas: %d | Negativas nuevas: %d", nuevas, duplicadas, len(negativas_nuevas))

    # Alerta inmediata por cada mención negativa nueva
    if negativas_nuevas and not no_email:
        logger.info("Enviando %d alerta(s) de mención(es) negativa(s)...", len(negativas_nuevas))
        for m in negativas_nuevas:
            try:
                send_negative_alert(m)
            except Exception as e:
                logger.error("Error enviando alerta negativa: %s", e)

    logger.info("Fase 3/4: Generando reporte HTML...")
    html_path = generate_daily_html(fecha)

    if not no_email:
        logger.info("Fase 4/4: Enviando reporte diario...")
        vem_str = f"$ {int(get_vem_diario(fecha)):,}".replace(",", ".")
        try:
            send_report(html_path, fecha, vem_str, nuevas)
        except Exception as e:
            logger.error("No se pudo enviar el reporte: %s", e)
    else:
        logger.info("Fase 4/4: Envío omitido (--no-email).")

    logger.info("=== Ciclo completado. Reporte en: %s ===", html_path)
    click.echo(f"✅  Reporte generado: {html_path}")
    click.echo(f"   Nuevas menciones : {nuevas}")
    click.echo(f"   Menciones negativas nuevas: {len(negativas_nuevas)}")
    click.echo(f"   VEM del día: $ {int(get_vem_diario(fecha)):,}".replace(",", "."))


@cli.command("run-monthly")
@click.option("--no-email", is_flag=True, default=False)
@click.option("--mes", default=None, type=int, help="Mes (1-12). Por defecto: mes anterior.")
@click.option("--anio", default=None, type=int)
def run_monthly(no_email, mes, anio):
    """Genera y envía el reporte mensual con comparativo VEM."""
    now = datetime.now()
    # Por defecto: mes anterior
    if not mes:
        mes = now.month - 1 if now.month > 1 else 12
        anio = anio or (now.year if now.month > 1 else now.year - 1)
    anio = anio or now.year

    logger.info("=== Generando reporte mensual %d-%02d ===", anio, mes)
    init_db()

    html_path = generate_monthly_html(anio, mes)

    if not no_email:
        vem = get_vem_mensual(anio, mes)
        import calendar
        import gc
        from app.database import get_menciones
        ultimo_dia = calendar.monthrange(anio, mes)[1]
        prefix = f"{anio}-{mes:02d}"
        total = len(get_menciones(fecha_desde=f"{prefix}-01", fecha_hasta=f"{prefix}-{ultimo_dia:02d}"))
        vem_str = f"$ {int(vem):,}".replace(",", ".")
        periodo = f"{mes:02d}/{anio}"
        try:
            send_monthly_report(html_path, periodo, vem_str, total)
        except Exception as e:
            logger.error("No se pudo enviar el reporte mensual: %s", e)

    click.echo(f"✅  Reporte mensual generado: {html_path}")


@cli.command("export-daily")
@click.option("--fecha", default=None)
@click.option("--formato", default="csv", type=click.Choice(["csv", "excel"]))
def cmd_export_daily(fecha, formato):
    """Exporta menciones de un día."""
    init_db()
    path = export_daily(fecha, formato)
    click.echo(f"Exportado: {path}")


@cli.command("export-monthly")
@click.option("--mes", default=None, type=int)
@click.option("--anio", default=None, type=int)
@click.option("--formato", default="csv", type=click.Choice(["csv", "excel"]))
def cmd_export_monthly(mes, anio, formato):
    """Exporta menciones del mes indicado."""
    init_db()
    path = export_monthly(anio, mes, formato)
    click.echo(f"Exportado: {path}")


@cli.command("export-historico")
@click.option("--formato", default="csv", type=click.Choice(["csv", "excel"]))
def cmd_export_historico(formato):
    """Exporta el histórico completo."""
    init_db()
    path = export_historico(formato)
    click.echo(f"Exportado: {path}")


@cli.command("init-db")
def cmd_init_db():
    """Inicializa la base de datos."""
    init_db()
    click.echo("Base de datos lista.")


if __name__ == "__main__":
    cli()
