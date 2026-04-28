"""Tests: cálculo VEM y lógica de valorización."""
import pytest
from app.valuation import calculate_vem, get_factor_visibilidad, get_factor_estrategico, get_valor_base


class TestValorBase:
    def test_emol_reconocido(self):
        valor, clave = get_valor_base("https://www.emol.com/noticias/nota.html")
        assert valor == 2500000
        assert clave == "emol.com"

    def test_latercera_reconocido(self):
        valor, _ = get_valor_base("https://www.latercera.com/nota")
        assert valor == 2200000

    def test_medio_desconocido_retorna_default(self):
        valor, clave = get_valor_base("https://www.medioinventado999.cl/nota")
        assert valor == 200000
        assert "default" in clave

    def test_sin_url_retorna_default(self):
        valor, _ = get_valor_base("")
        assert valor == 200000


class TestFactorVisibilidad:
    def test_entrevista(self):
        assert get_factor_visibilidad("Entrevista", "") == 1.4

    def test_nota_principal(self):
        assert get_factor_visibilidad("Nota principal", "CRTIC lidera evento") == 1.2

    def test_mencion_secundaria(self):
        assert get_factor_visibilidad("Mención secundaria", "") == 0.5

    def test_agenda(self):
        assert get_factor_visibilidad("Agenda / cartelera", "") == 0.3

    def test_institucional(self):
        assert get_factor_visibilidad("Institucional / aliado", "") == 0.6


class TestFactorEstrategico:
    def test_ia_innovacion(self):
        f = get_factor_estrategico("Tecnología / Innovación", "Meta AI CRTIC")
        assert f == 1.2

    def test_alianzas(self):
        f = get_factor_estrategico("Alianzas", "CORFO CRTIC")
        assert f == 1.1

    def test_formacion(self):
        f = get_factor_estrategico("Formación", "curso CRTIC")
        assert f == 1.0


class TestCalculateVem:
    def _item(self, **kwargs):
        base = {
            "url": "https://www.emol.com/nota",
            "medio": "Emol",
            "tipo_mencion": "Entrevista",
            "area_crtic": "Tecnología / Innovación",
            "keyword": "CRTIC",
            "titulo": "CRTIC y Meta AI firman alianza",
        }
        base.update(kwargs)
        return base

    def test_vem_es_positivo(self):
        item = calculate_vem(self._item())
        assert item["vem"] > 0

    def test_vem_formula_correcta(self):
        item = calculate_vem(self._item())
        esperado = round(item["valor_base_medio"] * item["factor_visibilidad"] * item["factor_estrategico"])
        assert item["vem"] == esperado

    def test_entrevista_emol_vem_alto(self):
        # Entrevista en Emol sobre IA → VEM = 2500000 * 1.4 * 1.2 = 4200000
        item = calculate_vem(self._item())
        assert item["vem"] == 4200000

    def test_mencion_secundaria_medio_desconocido_vem_bajo(self):
        item = calculate_vem(self._item(
            url="https://medioinventado999.cl/nota",
            tipo_mencion="Mención secundaria",
            area_crtic="Otro",
        ))
        assert item["vem"] < 500000

    def test_todos_los_campos_presentes(self):
        item = calculate_vem(self._item())
        for campo in ("valor_base_medio", "factor_visibilidad", "factor_estrategico", "vem"):
            assert campo in item
