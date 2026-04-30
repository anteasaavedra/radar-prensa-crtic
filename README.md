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

# Contraseña para el panel de administración de keywords
ADMIN_PASSWORD=tu_contraseña_admin
```

> `SMTP_PASSWORD` debe ser una **contraseña de aplicación** de Google, no la contraseña de la cuenta.  
> Generarla en: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

> `ADMIN_PASSWORD` protege la pestaña "⚙️ Configuración de búsquedas" del dashboard. Sin este valor configurado, la sección no permite acceso.

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

ADMIN_PASSWORD = "tu_contraseña_admin"
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
│   ├── config.py           # Variables de entorno (st.secrets + .env)
│   ├── database.py         # SQLite
│   ├── search.py           # SerpAPI / NewsAPI / Google PSE
│   ├── classifier.py       # Clasificación automática
│   ├── valuation.py        # Cálculo VEM
│   ├── report.py           # Reportes HTML + exportaciones
│   ├── emailer.py          # Envío SMTP
│   ├── email_config.py     # Filtros y config de reportes por correo
│   ├── dashboard.py        # Dashboard Streamlit
│   └── main.py             # CLI
├── data/
│   ├── media_values.json         # Valores base por medio (editable)
│   ├── search_config.json        # Keywords de búsqueda (editable desde dashboard)
│   └── email_report_config.json  # Filtros de reportes por correo (editable desde dashboard)
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

## Configuración de keywords — `data/search_config.json`

Los keywords de búsqueda se administran desde la pestaña **⚙️ Configuración de búsquedas** del dashboard (requiere `ADMIN_PASSWORD`). Los cambios se guardan en `data/search_config.json`.

| Categoría | Descripción | Se busca |
|---|---|---|
| `keywords_primary` | Términos principales de CRTIC | ✅ Sí |
| `keywords_secondary` | Términos combinados con socios | ✅ Sí |
| `people` | Nombres de personas vinculadas a CRTIC | ✅ Sí |
| `partners` | Socios y aliados (referencial) | ❌ No |
| `exclude_terms` | Términos para filtrar resultados irrelevantes | — |
| `priority_media` | Dominios de medios prioritarios para alertas | — |

Cada keyword puede activarse o desactivarse sin eliminarlo. Los desactivados se guardan en el campo `disabled` del JSON.

---

## Reportes por correo — `data/email_report_config.json`

La pestaña **📧 Reportes por correo** del dashboard (requiere `ADMIN_PASSWORD`) permite configurar qué menciones se envían en el reporte diario sin tocar código.

### Campos configurables

| Campo | Descripción | Default |
|---|---|---|
| `enabled` | Activa o desactiva el envío diario | `true` |
| `send_only_new_mentions` | Solo envía menciones con estado "nueva" | `true` |
| `send_empty_report` | Envía correo aunque no haya menciones | `false` |
| `min_relevance` | Relevancia mínima: `alta`, `media`, `baja` | `media` |
| `include_keywords` | Solo se envían menciones de estos keywords | lista CRTIC |
| `exclude_keywords` | Menciones de estos keywords se omiten siempre | `[]` |
| `priority_media` | Estos medios siempre se incluyen (ignoran otros filtros) | lista top medios |
| `included_areas` | Solo áreas CRTIC seleccionadas | todas |
| `recipients` | Destinatarios del correo | usa `EMAIL_TO` si vacío |
| `send_time` | Hora referencial de envío (HH:MM) | `09:00` |

### Lógica de filtrado

1. Si `enabled = false` → no se envía nada
2. Las menciones de `priority_media` siempre se incluyen (saltan los filtros de keyword, área y relevancia)
3. Se excluyen las menciones de `exclude_keywords`
4. Si `include_keywords` tiene valores, solo pasan las menciones de esos keywords
5. Se filtran por `included_areas` y `min_relevance`
6. Si el resultado está vacío y `send_empty_report = false` → no se envía correo
7. Si el resultado está vacío y `send_empty_report = true` → se envía correo indicando "sin menciones"

---

## Notas sobre clasificación

El campo **sentimiento** (Positivo / Neutro / Negativo) sigue calculándose automáticamente en el backend y está disponible en la pestaña **✏️ Corrección manual** para ajuste individual. No se muestra como filtro ni KPI en el dashboard principal para evitar sobreinterpretar el análisis automático.

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
