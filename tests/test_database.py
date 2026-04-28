"""Tests: deduplicación por URL y operaciones de base de datos."""
import os
import tempfile
import pytest

# Apuntar a una BD temporal antes de importar el módulo
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DB_PATH"] = _tmp.name

from app.database import init_db, insert_mencion, url_exists, get_menciones


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_file))
    # Recargar la config para que tome el nuevo DB_PATH
    import importlib
    import app.config as cfg
    import app.database as db
    cfg.DB_PATH = db_file
    db.DB_PATH = db_file
    importlib.reload(db)
    db.init_db()
    yield
    if db_file.exists():
        db_file.unlink()


def _mencion(url="https://ejemplo.cl/nota-1", titulo="Nota de prueba"):
    return {
        "fecha_deteccion": "2024-05-01",
        "fecha_publicacion": "2024-05-01",
        "medio": "Ejemplo",
        "titulo": titulo,
        "url": url,
        "snippet": "Texto de prueba sobre CRTIC",
        "keyword": "CRTIC",
        "tipo_mencion": "Nota principal",
        "sentimiento": "Positivo",
        "relevancia": "Alta",
        "area_crtic": "Tecnología / Innovación",
        "valor_base_medio": 1800000.0,
        "factor_visibilidad": 1.2,
        "factor_estrategico": 1.2,
        "vem": 2592000,
        "estado": "nueva",
    }


class TestDeduplicacion:
    def test_primera_insercion_exitosa(self):
        from app.database import insert_mencion
        m = _mencion()
        result = insert_mencion(m)
        assert result is not None
        assert isinstance(result, int)

    def test_url_duplicada_retorna_none(self):
        from app.database import insert_mencion
        m = _mencion()
        insert_mencion(m)
        result = insert_mencion(m)
        assert result is None

    def test_url_diferente_se_inserta(self):
        from app.database import insert_mencion
        insert_mencion(_mencion(url="https://a.cl/1"))
        result = insert_mencion(_mencion(url="https://a.cl/2", titulo="Otra nota"))
        assert result is not None

    def test_url_exists(self):
        from app.database import insert_mencion, url_exists
        m = _mencion()
        assert not url_exists(m["url"])
        insert_mencion(m)
        assert url_exists(m["url"])

    def test_multiples_duplicados(self):
        from app.database import insert_mencion, get_menciones
        url = "https://dup.cl/articulo"
        for _ in range(5):
            insert_mencion(_mencion(url=url))
        rows = get_menciones()
        assert len(rows) == 1
