# 📡 Radar de Prensa CRTIC

Sistema interno de monitoreo de menciones mediáticas para el **Centro para la Revolución Tecnológica en Industrias Creativas (CRTIC)**.

## Contexto institucional

CRTIC es un centro público-privado chileno que impulsa la **tecnocreatividad** en Chile, integrando tecnología y creatividad para el desarrollo del ecosistema de industrias creativas. Trabaja con aliados como CORFO, GAM, CAF, BID, COPEC, Meta AI, ChileCreativo y desarrolla programas en Unreal Engine, IA aplicada y emprendimiento tecnocreativo.

---

## Funcionalidades

| Módulo | Descripción |
|---|---|
| **Búsqueda automática** | 18 keywords CRTIC via SerpAPI / NewsAPI / Google PSE |
| **Clasificación** | Tipo, sentimiento, relevancia y área CRTIC por reglas heurísticas |
| **VEM** | Valor Estimado de Exposición Mediática referencial (editable en `data/media_values.json`) |
| **Reporte diario** | HTML por correo con top menciones, alertas y recomendaciones |
| **Reporte mensual** | Comparativo VEM mes a mes, stats por medio, área y tipo |
| **Alertas inmediatas** | Correo automático al detectar mención negativa nueva |
| **Dashboard** | Streamlit con gráficos, filtros y corrección manual |
| **Exportación** | CSV / Excel diario, mensual e histórico |

---

## Instalación local

```bash
git clone https://github.com/tu-usuario/radar-prensa-crtic.git
cd radar-prensa-crtic

python -m venv venv
source venv/bin/activate          # Mac/Linux
# venv\Scripts\activate           # Windows

pip install -r requirements.txt

cp .env.example .env
# Editar .env con tus credenciales
```

### Configurar `.env`

```env
SEARCH_API_PROVIDER=serpapi
SEARCH_API_KEY=tu_key_de_serpapi

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu@correo.cl
SMTP_PASSWORD=contraseña_de_aplicacion_gmail
EMAIL_FROM=tu@correo.cl
EMAIL_TO=destinatario@crtic.cl

TIMEZONE=America/Santiago
```

> `SMTP_PASSWORD` debe ser una **contraseña de aplicación** de Google, no la contraseña de la cuenta.  
> Generarla en: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

---

## Ejecución local

```bash
# Inicializar base de datos
python -m app.main init-db

# Búsqueda diaria + reporte + correo
python -m app.main run-daily

# Reporte mensual (mes anterior por defecto)
python -m app.main run-monthly

# Dashboard interactivo
streamlit run app/dashboard.py
```

### Exportaciones

```bash
python -m app.main export-daily --fecha 2024-05-01 --formato excel
python -m app.main export-monthly --mes 5 --anio 2024
python -m app.main export-historico --formato csv
```

---

## Deploy en Streamlit Community Cloud

### 1. Subir el repositorio a GitHub

```bash
git init
git add .
git commit -m "Initial commit Radar Prensa CRTIC"
git branch -M main
git remote add origin https://github.com/tu-usuario/radar-prensa-crtic.git
git push -u origin main
```

### 2. Conectar en Streamlit Cloud

1. Ir a [share.streamlit.io](https://share.streamlit.io)
2. Clic en **New app**
3. Seleccionar el repositorio `radar-prensa-crtic`
4. **Main file path:** `app/dashboard.py`
5. Clic en **Deploy**

### 3. Configurar Secrets en Streamlit Cloud

En **Settings → Secrets** del app, pegar:

```toml
SEARCH_API_PROVIDER = "serpapi"
SEARCH_API_KEY      = "tu_key"

SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = "587"
SMTP_USER     = "tu@correo.cl"
SMTP_PASSWORD = "contraseña_aplicacion"
EMAIL_FROM    = "tu@correo.cl"
EMAIL_TO      = "destinatario@crtic.cl"

TIMEZONE = "America/Santiago"
```

> El sistema detecta automáticamente si está en Streamlit Cloud y usa `st.secrets`; en local usa `.env`.

### ⚠️ Nota sobre persistencia en Streamlit Cloud

Streamlit Community Cloud tiene **sistema de archivos efímero**: la base de datos SQLite se reinicia con cada deploy. Para uso en producción con datos persistentes se recomienda:
- Ejecutar `run-daily` desde un servidor o GitHub Actions (ver `.github/workflows/radar_diario.yml`)
- Usar el dashboard de Streamlit principalmente para visualización

---

## Ejecución automática (cron / GitHub Actions)

### Cron en servidor

```bash
crontab -e
```

```cron
# Búsqueda diaria 09:00
0 9 * * * cd /ruta/radar-prensa-crtic && /ruta/venv/bin/python -m app.main run-daily >> logs/radar.log 2>&1

# Reporte mensual día 1 de cada mes 09:00
0 9 1 * * cd /ruta/radar-prensa-crtic && /ruta/venv/bin/python -m app.main run-monthly >> logs/radar.log 2>&1
```

### GitHub Actions

El workflow `.github/workflows/radar_diario.yml` ejecuta `run-daily` cada día a las 08:00 AM Santiago. Configurar los mismos valores como **Repository Secrets** en GitHub.

---

## Estructura del proyecto

```
radar-prensa-crtic/
├── app/
│   ├── config.py        # Variables de entorno (st.secrets + .env)
│   ├── database.py      # SQLite
│   ├── search.py        # SerpAPI / NewsAPI / Google PSE
│   ├── classifier.py    # Clasificación automática
│   ├── valuation.py     # Cálculo VEM
│   ├── report.py        # Reportes HTML + exportaciones
│   ├── emailer.py       # Envío SMTP
│   ├── dashboard.py     # Dashboard Streamlit
│   └── main.py          # CLI
├── data/
│   └── media_values.json   # Valores base por medio (editable)
├── templates/
│   ├── reporte_diario.html
│   ├── reporte_mensual.html
│   └── alerta_negativa.html
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
├── tests/
├── .github/workflows/
├── .gitignore
├── .env.example
├── requirements.txt
└── README.md
```

---

## Pruebas

```bash
pip install pytest
pytest tests/ -v
```

---

## VEM — Metodología

> Los valores son **estimados referenciales de exposición mediática** de uso interno. No equivalen a tarifas publicitarias comerciales.

```
VEM = valor_base_medio × factor_visibilidad × factor_estratégico
```

Editar valores en `data/media_values.json`.

---

*Radar de Prensa CRTIC — Sistema interno de monitoreo mediático*  
*Centro para la Revolución Tecnológica en Industrias Creativas*
