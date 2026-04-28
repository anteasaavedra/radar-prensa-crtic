"""Tests: clasificación automática de menciones."""
from app.classifier import classify_tipo, classify_sentimiento, classify_relevancia, classify_area, classify


class TestTipo:
    def test_entrevista(self):
        assert classify_tipo("Entrevista a directora de CRTIC", "") == "Entrevista"

    def test_nota_principal_por_titular(self):
        assert classify_tipo("CRTIC lanza nuevo programa", "") == "Nota principal"

    def test_agenda(self):
        assert classify_tipo("Agenda cultural de la semana", "taller CRTIC inscripciones abiertas") == "Agenda / cartelera"

    def test_mencion_secundaria(self):
        t = "Evento tecnológico contó con la participación de CRTIC, entre otras organizaciones"
        assert classify_tipo("", t) in ("Mención secundaria", "Nota principal", "Otro")

    def test_institucional_corfo(self):
        assert classify_tipo("CORFO anuncia nuevos proyectos", "CRTIC entre los seleccionados") == "Institucional / aliado"


class TestSentimiento:
    def test_positivo(self):
        assert classify_sentimiento("CRTIC lidera innovación en Chile", "logro importante") == "Positivo"

    def test_negativo(self):
        assert classify_sentimiento("Crisis en CRTIC", "denuncia graves problemas") == "Negativo"

    def test_neutro(self):
        assert classify_sentimiento("CRTIC participó en evento", "organización presente") == "Neutro"


class TestRelevancia:
    def test_alta_crtic_en_titulo_y_snippet(self):
        r = classify_relevancia("CRTIC lidera revolución tecnológica", "CRTIC es pionero en Chile", "CRTIC")
        assert r == "Alta"

    def test_media_crtic_solo_en_titulo(self):
        r = classify_relevancia("CRTIC anuncia resultados", "Se realizó el evento", "CRTIC")
        assert r == "Media"

    def test_baja_sin_crtic_en_titulo(self):
        r = classify_relevancia("Evento de innovación", "participaron varios actores", "CRTIC")
        assert r == "Baja"


class TestArea:
    def test_tecnologia_innovacion(self):
        assert classify_area("IA y Unreal Engine en CRTIC", "", "CRTIC") == "Tecnología / Innovación"

    def test_formacion(self):
        assert classify_area("Nuevos cursos de CRTIC", "taller de formación", "CRTIC") == "Formación"

    def test_alianzas(self):
        assert classify_area("CORFO firma convenio con CRTIC", "", "CORFO CRTIC") == "Alianzas"

    def test_crtic_sur(self):
        assert classify_area("CRTIC Sur expande operaciones", "", "CRTIC Sur") == "CRTIC Sur"


class TestClassifyIntegrado:
    def test_classify_agrega_todos_los_campos(self):
        item = {
            "titulo": "CRTIC lanza programa de IA con Meta",
            "snippet": "El centro tecnológico anunció una alianza estratégica",
            "keyword": "Meta AI CRTIC",
        }
        result = classify(item)
        assert "tipo_mencion" in result
        assert "sentimiento" in result
        assert "relevancia" in result
        assert "area_crtic" in result

    def test_classify_no_sobreescribe_url(self):
        item = {
            "titulo": "CRTIC", "snippet": "", "keyword": "CRTIC",
            "url": "https://test.cl",
        }
        result = classify(item)
        assert result["url"] == "https://test.cl"
