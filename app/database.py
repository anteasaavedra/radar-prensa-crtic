import sqlite3
import logging
from datetime import datetime
from contextlib import contextmanager
from typing import Optional
from app.config import DB_PATH

logger = logging.getLogger("radar_prensa.database")

SCHEMA = """
CREATE TABLE IF NOT EXISTS menciones (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_deteccion     TEXT NOT NULL,
    fecha_publicacion   TEXT,
    medio               TEXT,
    titulo              TEXT,
    url                 TEXT UNIQUE NOT NULL,
    snippet             TEXT,
    keyword             TEXT,
    tipo_mencion        TEXT DEFAULT 'Otro',
    sentimiento         TEXT DEFAULT 'Neutro',
    relevancia          TEXT DEFAULT 'Media',
    area_crtic          TEXT DEFAULT 'Otro',
    valor_base_medio    REAL DEFAULT 0,
    factor_visibilidad  REAL DEFAULT 1.0,
    factor_estrategico  REAL DEFAULT 1.0,
    vem                 REAL DEFAULT 0,
    estado              TEXT DEFAULT 'nueva'
);

CREATE INDEX IF NOT EXISTS idx_fecha ON menciones(fecha_deteccion);
CREATE INDEX IF NOT EXISTS idx_url   ON menciones(url);
CREATE INDEX IF NOT EXISTS idx_estado ON menciones(estado);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
    logger.info("Base de datos inicializada en %s", DB_PATH)


def url_exists(url: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM menciones WHERE url = ?", (url,)).fetchone()
        return row is not None


def insert_mencion(data: dict) -> Optional[int]:
    """Inserta una mención. Retorna el id insertado o None si ya existe."""
    if url_exists(data["url"]):
        logger.debug("Duplicado ignorado: %s", data["url"])
        return None

    cols = [
        "fecha_deteccion", "fecha_publicacion", "medio", "titulo", "url",
        "snippet", "keyword", "tipo_mencion", "sentimiento", "relevancia",
        "area_crtic", "valor_base_medio", "factor_visibilidad",
        "factor_estrategico", "vem", "estado",
    ]
    placeholders = ", ".join("?" for _ in cols)
    col_names = ", ".join(cols)
    values = [data.get(c) for c in cols]

    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO menciones ({col_names}) VALUES ({placeholders})", values
        )
        logger.info("Nueva mención guardada [id=%s]: %s", cur.lastrowid, data.get("titulo", "")[:60])
        return cur.lastrowid


def get_menciones(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    estado: Optional[str] = None,
    medio: Optional[str] = None,
    relevancia: Optional[str] = None,
    sentimiento: Optional[str] = None,
    area_crtic: Optional[str] = None,
    limit: int = 500,
) -> list:
    clauses, params = [], []

    if fecha_desde:
        clauses.append("fecha_deteccion >= ?")
        params.append(fecha_desde)
    if fecha_hasta:
        clauses.append("fecha_deteccion <= ?")
        params.append(fecha_hasta)
    if estado:
        clauses.append("estado = ?")
        params.append(estado)
    if medio:
        clauses.append("medio LIKE ?")
        params.append(f"%{medio}%")
    if relevancia:
        clauses.append("relevancia = ?")
        params.append(relevancia)
    if sentimiento:
        clauses.append("sentimiento = ?")
        params.append(sentimiento)
    if area_crtic:
        clauses.append("area_crtic = ?")
        params.append(area_crtic)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    query = f"SELECT * FROM menciones {where} ORDER BY fecha_deteccion DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def update_estado(mencion_id: int, estado: str):
    with get_conn() as conn:
        conn.execute("UPDATE menciones SET estado = ? WHERE id = ?", (estado, mencion_id))


def update_mencion(mencion_id: int, campos: dict):
    """Actualiza campos editables de una mención (corrección manual)."""
    editables = [
        "tipo_mencion", "sentimiento", "relevancia", "area_crtic",
        "valor_base_medio", "factor_visibilidad", "factor_estrategico", "vem", "estado",
    ]
    sets, vals = [], []
    for k, v in campos.items():
        if k in editables:
            sets.append(f"{k} = ?")
            vals.append(v)
    if not sets:
        return
    # Recalcular VEM si se cambiaron los factores pero no el VEM directamente
    if "vem" not in campos and all(f in campos for f in ("valor_base_medio", "factor_visibilidad", "factor_estrategico")):
        vem = round(campos["valor_base_medio"] * campos["factor_visibilidad"] * campos["factor_estrategico"])
        sets.append("vem = ?")
        vals.append(vem)
    vals.append(mencion_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE menciones SET {', '.join(sets)} WHERE id = ?", vals)
    logger.info("Mención %d actualizada manualmente: %s", mencion_id, list(campos.keys()))


def get_mencion_by_id(mencion_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM menciones WHERE id = ?", (mencion_id,)).fetchone()
    return dict(row) if row else None


def get_vem_diario(fecha: str) -> float:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(vem), 0) FROM menciones WHERE fecha_deteccion = ? AND estado != 'descartada'",
            (fecha,),
        ).fetchone()
    return float(row[0])


def get_vem_mensual(anio: int, mes: int) -> float:
    prefix = f"{anio}-{mes:02d}"
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(vem), 0) FROM menciones WHERE fecha_deteccion LIKE ? AND estado != 'descartada'",
            (f"{prefix}%",),
        ).fetchone()
    return float(row[0])


def get_vem_comparativo(n_meses: int = 6) -> list:
    """Retorna lista [{mes, anio, vem, total_menciones}] de los últimos n_meses."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT
                strftime('%Y', fecha_deteccion) AS anio,
                strftime('%m', fecha_deteccion) AS mes,
                COALESCE(SUM(vem), 0)           AS vem_total,
                COUNT(*)                         AS total
            FROM menciones
            WHERE estado != 'descartada'
            GROUP BY anio, mes
            ORDER BY anio DESC, mes DESC
            LIMIT ?
        """, (n_meses,)).fetchall()
    return [dict(r) for r in reversed(rows)]


def get_menciones_nuevas_negativas(fecha: str) -> list:
    """Menciones negativas insertadas hoy (para alerta inmediata)."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM menciones WHERE fecha_deteccion = ? AND sentimiento = 'Negativo' AND estado = 'nueva'",
            (fecha,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_stats_por_campo(campo: str, fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None) -> list:
    """Agrupación por campo con suma VEM y conteo."""
    campos_validos = {"medio", "area_crtic", "tipo_mencion", "sentimiento", "relevancia"}
    if campo not in campos_validos:
        return []
    clauses, params = ["estado != 'descartada'"], []
    if fecha_desde:
        clauses.append("fecha_deteccion >= ?")
        params.append(fecha_desde)
    if fecha_hasta:
        clauses.append("fecha_deteccion <= ?")
        params.append(fecha_hasta)
    where = "WHERE " + " AND ".join(clauses)
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT {campo}, COUNT(*) as total, COALESCE(SUM(vem),0) as vem_total "
            f"FROM menciones {where} GROUP BY {campo} ORDER BY vem_total DESC",
            params,
        ).fetchall()
    return [dict(r) for r in rows]
