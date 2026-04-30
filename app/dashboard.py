"""
Dashboard Streamlit v2 – Radar de Prensa CRTIC
Ejecutar: streamlit run app/dashboard.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from app.database import (
    init_db, get_menciones, get_vem_diario, get_vem_mensual,
    update_estado, update_mencion, get_mencion_by_id,
    get_vem_comparativo, get_stats_por_campo,
)
from app.report import export_daily, export_monthly, export_historico, generate_monthly_html
from app.emailer import send_monthly_report

init_db()

st.set_page_config(page_title="Radar de Prensa CRTIC", page_icon="📡", layout="wide")

st.markdown("""
<style>
  .metric-box { background:#f0f4ff; border-radius:12px; padding:18px; text-align:center; }
  .vem-val    { font-size:1.7rem; font-weight:700; color:#1a237e; }
  .tag        { display:inline-block; border-radius:5px; padding:2px 8px; font-size:.75rem; font-weight:600; }
  .pos { background:#c8e6c9; color:#1b5e20; }
  .neg { background:#ffcdd2; color:#b71c1c; }
  .neu { background:#e3f2fd; color:#0d47a1; }
  section[data-testid="stSidebar"] { min-width:260px; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.image("https://i.imgur.com/placeholder.png", width=40) if False else None
st.sidebar.title("📡 Radar CRTIC")
st.sidebar.caption("Filtros globales")

hoy = datetime.now().date()
fecha_desde = st.sidebar.date_input("Desde", value=hoy - timedelta(days=30))
fecha_hasta = st.sidebar.date_input("Hasta", value=hoy)

filtro_rel  = st.sidebar.selectbox("Relevancia",  ["Todos","Alta","Media","Baja"])
filtro_area = st.sidebar.selectbox("Área CRTIC",  [
    "Todos","Formación","Comunicaciones","Proyectos / Emprendimiento",
    "CRTIC Sur","Alianzas","Tecnología / Innovación","Institucional","Otro",
])
filtro_tipo = st.sidebar.selectbox("Tipo de mención", [
    "Todos","Nota principal","Entrevista","Reportaje",
    "Mención secundaria","Agenda / cartelera","Institucional / aliado","Otro",
])
filtro_est = st.sidebar.selectbox("Estado", ["Todos","nueva","revisada","descartada"])

# ── Botón de búsqueda ──────────────────────────────────────────────────────────
st.sidebar.divider()
st.sidebar.markdown("**Actualizar menciones**")
if st.sidebar.button("🔍 Ejecutar búsqueda ahora", use_container_width=True, type="primary"):
    with st.sidebar:
        with st.spinner("Buscando menciones..."):
            try:
                from app.search import run_daily_search
                from app.classifier import classify
                from app.valuation import calculate_vem
                from app.database import insert_mencion
                results = run_daily_search()
                nuevas = 0
                negativas_alerta = []
                for item in results:
                    item = classify(item)
                    item = calculate_vem(item)
                    item["estado"] = "nueva"
                    inserted_id = insert_mencion(item)
                    if inserted_id:
                        nuevas += 1
                        if item.get("sentimiento") == "Negativo":
                            item["id"] = inserted_id
                            negativas_alerta.append(item)
                if negativas_alerta:
                    from app.emailer import send_negative_alert
                    for m in negativas_alerta:
                        try:
                            send_negative_alert(m)
                        except Exception:
                            pass
                # Generar reporte y enviar correo
                from datetime import datetime as _dt
                from app.report import generate_daily_html
                from app.emailer import send_report
                from app.database import get_vem_diario
                fecha_hoy = _dt.now().strftime("%Y-%m-%d")
                html_path = generate_daily_html(fecha_hoy)
                vem_str = f"$ {int(get_vem_diario(fecha_hoy)):,}".replace(",", ".")
                total_hoy = len(get_menciones(fecha_desde=fecha_hoy, fecha_hasta=fecha_hoy))
                try:
                    send_report(html_path, fecha_hoy, vem_str, total_hoy)
                    from app.config import EMAIL_TO as _to
                    st.success(f"✅ {nuevas} nuevas · Reporte enviado a {', '.join(_to)}")
                except Exception as e:
                    st.warning(f"✅ {nuevas} nuevas · Reporte generado pero no enviado: {e}")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
st.sidebar.caption("Ejecuta la búsqueda con los 18 keywords y actualiza el dashboard.")

# ── Carga de datos ─────────────────────────────────────────────────────────────
menciones = get_menciones(
    fecha_desde=str(fecha_desde),
    fecha_hasta=str(fecha_hasta),
    relevancia=None  if filtro_rel  == "Todos" else filtro_rel,
    area_crtic=None  if filtro_area == "Todos" else filtro_area,
    estado=None      if filtro_est  == "Todos" else filtro_est,
    limit=3000,
)
df = pd.DataFrame(menciones) if menciones else pd.DataFrame()

if not df.empty and filtro_tipo != "Todos":
    df = df[df["tipo_mencion"] == filtro_tipo]

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("📡 Radar de Prensa CRTIC")
st.caption("Monitoreo de menciones mediáticas — valores referenciales de exposición mediática (VEM)")

# ── KPIs ───────────────────────────────────────────────────────────────────────
k1, k2, k3 = st.columns(3)
vem_sum = int(df["vem"].sum()) if not df.empty else 0
alta_n  = int((df["relevancia"] == "Alta").sum()) if not df.empty else 0

k1.metric("Total menciones", len(df))
k2.metric("VEM acumulado",   f"$ {vem_sum:,}".replace(",", "."))
k3.metric("Alta relevancia", alta_n)

st.divider()

# ── Pestañas ───────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Visualizaciones",
    "📈 Comparativo VEM",
    "📋 Tabla de menciones",
    "✏️ Corrección manual",
    "📥 Exportar",
    "⚙️ Configuración de búsquedas",
])

# ════════════════════════════════════════════════════════════════
# TAB 1 — Visualizaciones
# ════════════════════════════════════════════════════════════════
with tab1:
    if df.empty:
        st.info("Sin datos para el período seleccionado.")
    else:
        # Fila 1
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("VEM por día")
            vem_dia = df.groupby("fecha_deteccion")["vem"].sum().reset_index()
            vem_dia.columns = ["Fecha", "VEM"]
            fig = px.bar(vem_dia, x="Fecha", y="VEM",
                         color_discrete_sequence=["#1a237e"],
                         labels={"VEM": "VEM referencial (CLP)"})
            fig.update_layout(margin=dict(t=10,b=10))
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.subheader("Menciones por relevancia")
            rel = df["relevancia"].value_counts().reset_index()
            rel.columns = ["Relevancia","n"]
            fig2 = px.pie(rel, values="n", names="Relevancia",
                          color="Relevancia",
                          color_discrete_map={"Alta":"#1a237e","Media":"#42a5f5","Baja":"#b0bec5"})
            fig2.update_layout(margin=dict(t=10,b=10))
            st.plotly_chart(fig2, use_container_width=True)

        # Fila 2
        c3, c4 = st.columns(2)
        with c3:
            st.subheader("VEM por medio (top 10)")
            top_m = df.groupby("medio")["vem"].sum().nlargest(10).reset_index()
            top_m.columns = ["Medio","VEM"]
            fig3 = px.bar(top_m, x="VEM", y="Medio", orientation="h",
                          color_discrete_sequence=["#283593"],
                          labels={"VEM":"VEM referencial (CLP)"})
            fig3.update_layout(margin=dict(t=10,b=10))
            st.plotly_chart(fig3, use_container_width=True)

        with c4:
            st.subheader("Menciones por área CRTIC")
            area = df["area_crtic"].value_counts().reset_index()
            area.columns = ["Área","n"]
            fig4 = px.bar(area, x="n", y="Área", orientation="h",
                          color_discrete_sequence=["#1565c0"],
                          labels={"n":"Menciones"})
            fig4.update_layout(margin=dict(t=10,b=10))
            st.plotly_chart(fig4, use_container_width=True)

        # Fila 3
        c5, c6 = st.columns(2)
        with c5:
            st.subheader("Menciones por tipo")
            tipo = df["tipo_mencion"].value_counts().reset_index()
            tipo.columns = ["Tipo","n"]
            fig5 = px.pie(tipo, values="n", names="Tipo",
                          color_discrete_sequence=px.colors.qualitative.Set3)
            fig5.update_layout(margin=dict(t=10,b=10))
            st.plotly_chart(fig5, use_container_width=True)

        with c6:
            st.subheader("VEM por área CRTIC")
            vem_area = df.groupby("area_crtic")["vem"].sum().reset_index()
            vem_area.columns = ["Área","VEM"]
            fig6 = px.pie(vem_area, values="VEM", names="Área",
                          color_discrete_sequence=px.colors.qualitative.Pastel)
            fig6.update_layout(margin=dict(t=10,b=10))
            st.plotly_chart(fig6, use_container_width=True)


# ════════════════════════════════════════════════════════════════
# TAB 2 — Comparativo VEM mensual
# ════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Comparativo VEM mensual (últimos 6 meses)")
    comp = get_vem_comparativo(n_meses=6)

    if not comp:
        st.info("Aún no hay suficientes datos mensuales para comparar.")
    else:
        comp_df = pd.DataFrame(comp)
        comp_df["periodo"] = comp_df["mes"] + "/" + comp_df["anio"]
        comp_df["vem_total"] = comp_df["vem_total"].astype(float)
        comp_df["vem_M"] = (comp_df["vem_total"] / 1_000_000).round(2)

        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(
            x=comp_df["periodo"], y=comp_df["vem_total"],
            name="VEM mensual", marker_color="#1a237e",
            text=[f"$ {int(v):,}".replace(",",".") for v in comp_df["vem_total"]],
            textposition="outside",
        ))
        fig_comp.add_trace(go.Scatter(
            x=comp_df["periodo"], y=comp_df["total"],
            name="Nº menciones", yaxis="y2",
            mode="lines+markers", line=dict(color="#f57c00", width=2),
            marker=dict(size=8),
        ))
        fig_comp.update_layout(
            yaxis=dict(title="VEM referencial (CLP)"),
            yaxis2=dict(title="Menciones", overlaying="y", side="right"),
            legend=dict(orientation="h", y=-0.2),
            margin=dict(t=20, b=40),
        )
        st.plotly_chart(fig_comp, use_container_width=True)

        # Tabla resumen
        st.subheader("Detalle por mes")
        comp_show = comp_df[["periodo","total","vem_total"]].copy()
        comp_show["VEM (CLP)"] = comp_show["vem_total"].apply(lambda v: f"$ {int(v):,}".replace(",","."))
        comp_show["Variación"] = ""
        for i in range(1, len(comp_show)):
            v_act = comp_show.iloc[i]["vem_total"]
            v_ant = comp_show.iloc[i-1]["vem_total"]
            if v_ant > 0:
                pct = ((v_act - v_ant) / v_ant) * 100
                arrow = "▲" if pct >= 0 else "▼"
                comp_show.at[comp_show.index[i], "Variación"] = f"{arrow} {abs(pct):.1f}%"
        st.dataframe(
            comp_show[["periodo","total","VEM (CLP)","Variación"]].rename(
                columns={"periodo":"Mes","total":"Menciones"}
            ),
            use_container_width=True, hide_index=True,
        )

    # Generar y enviar reporte mensual
    st.divider()
    st.subheader("Generar reporte mensual")
    col_m, col_a, col_btn = st.columns([2, 2, 2])
    with col_m:
        mes_rep = st.selectbox("Mes", range(1, 13), index=hoy.month - 1, key="mes_rep")
    with col_a:
        anio_rep = st.number_input("Año", value=hoy.year, key="anio_rep")
    with col_btn:
        st.write("")
        st.write("")
        if st.button("📊 Generar y enviar"):
            with st.spinner("Generando reporte mensual..."):
                html_path = generate_monthly_html(int(anio_rep), int(mes_rep))
                from app.database import get_vem_mensual as gvm
                import calendar as cal
                vem = gvm(int(anio_rep), int(mes_rep))
                ult = cal.monthrange(int(anio_rep), int(mes_rep))[1]
                pref = f"{int(anio_rep)}-{int(mes_rep):02d}"
                total_m = len(get_menciones(fecha_desde=f"{pref}-01", fecha_hasta=f"{pref}-{ult:02d}"))
                vem_s = f"$ {int(vem):,}".replace(",",".")
                try:
                    send_monthly_report(html_path, f"{int(mes_rep):02d}/{int(anio_rep)}", vem_s, total_m)
                    st.success(f"✅ Reporte enviado. Guardado en: {html_path}")
                except Exception as e:
                    st.warning(f"Reporte generado pero no enviado: {e}\n\nArchivo: {html_path}")


# ════════════════════════════════════════════════════════════════
# TAB 3 — Tabla de menciones
# ════════════════════════════════════════════════════════════════
with tab3:
    if df.empty:
        st.info("Sin menciones para el período y filtros seleccionados.")
    else:
        busq = st.text_input("🔍 Buscar por medio o título", "", key="busq_tabla")
        show = df.copy()
        if busq:
            mask = (
                show["medio"].str.contains(busq, case=False, na=False) |
                show["titulo"].str.contains(busq, case=False, na=False)
            )
            show = show[mask]

        cols = ["id","fecha_deteccion","medio","titulo","url",
                "tipo_mencion","sentimiento","relevancia","area_crtic","vem","estado"]
        avail = [c for c in cols if c in show.columns]

        st.dataframe(
            show[avail].rename(columns={
                "id":"ID","fecha_deteccion":"Fecha","medio":"Medio",
                "titulo":"Título","url":"URL","tipo_mencion":"Tipo",
                "sentimiento":"Sentimiento","relevancia":"Relevancia",
                "area_crtic":"Área CRTIC","vem":"VEM (ref.)","estado":"Estado",
            }),
            use_container_width=True, height=460,
            column_config={
                "URL": st.column_config.LinkColumn("URL"),
                "VEM (ref.)": st.column_config.NumberColumn(format="$ %d"),
            },
        )

        # Cambio rápido de estado
        st.subheader("Cambiar estado rápido")
        ci, ce, cb = st.columns([2, 2, 1])
        with ci:
            mid = st.number_input("ID mención", min_value=1, step=1, key="mid_estado")
        with ce:
            nest = st.selectbox("Nuevo estado", ["revisada","descartada","nueva"], key="nest")
        with cb:
            st.write(""); st.write("")
            if st.button("Actualizar estado"):
                update_estado(int(mid), nest)
                st.success(f"ID {mid} → {nest}")
                st.rerun()


# ════════════════════════════════════════════════════════════════
# TAB 4 — Corrección manual
# ════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("✏️ Corrección manual de clasificación y valorización")
    st.caption("Permite a Comunicaciones corregir cualquier campo de una mención ya guardada.")

    edit_id = st.number_input("ID de la mención a editar", min_value=1, step=1, key="edit_id")

    if st.button("🔍 Cargar mención"):
        m = get_mencion_by_id(int(edit_id))
        if m:
            st.session_state["mencion_edit"] = m
        else:
            st.error(f"No se encontró la mención con ID {edit_id}.")

    if "mencion_edit" in st.session_state:
        m = st.session_state["mencion_edit"]
        st.info(f"**{m.get('titulo','(sin título)')}** — {m.get('medio','')} | {m.get('fecha_deteccion','')}")
        if m.get("url"):
            st.markdown(f"[🔗 Ver nota]({m['url']})")

        st.divider()
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Clasificación**")
            tipo_opts = ["Nota principal","Entrevista","Reportaje","Mención secundaria",
                         "Agenda / cartelera","Institucional / aliado","Otro"]
            nuevo_tipo = st.selectbox("Tipo de mención",     tipo_opts,
                                      index=tipo_opts.index(m.get("tipo_mencion","Otro"))
                                      if m.get("tipo_mencion") in tipo_opts else 6, key="e_tipo")

            sent_opts = ["Positivo","Neutro","Negativo"]
            nuevo_sent = st.selectbox("Sentimiento",         sent_opts,
                                      index=sent_opts.index(m.get("sentimiento","Neutro"))
                                      if m.get("sentimiento") in sent_opts else 1, key="e_sent")

            rel_opts = ["Alta","Media","Baja"]
            nuevo_rel  = st.selectbox("Relevancia",          rel_opts,
                                      index=rel_opts.index(m.get("relevancia","Media"))
                                      if m.get("relevancia") in rel_opts else 1, key="e_rel")

            area_opts = ["Formación","Comunicaciones","Proyectos / Emprendimiento",
                         "CRTIC Sur","Alianzas","Tecnología / Innovación","Institucional","Otro"]
            nuevo_area = st.selectbox("Área CRTIC",          area_opts,
                                      index=area_opts.index(m.get("area_crtic","Otro"))
                                      if m.get("area_crtic") in area_opts else 7, key="e_area")

            est_opts = ["nueva","revisada","descartada"]
            nuevo_est  = st.selectbox("Estado",              est_opts,
                                      index=est_opts.index(m.get("estado","nueva"))
                                      if m.get("estado") in est_opts else 0, key="e_est")

        with col2:
            st.markdown("**Valorización**")
            nuevo_vb  = st.number_input("Valor base medio (CLP)",
                                        value=float(m.get("valor_base_medio", 200000)),
                                        step=100000.0, key="e_vb")
            nuevo_fv  = st.number_input("Factor visibilidad",
                                        value=float(m.get("factor_visibilidad", 1.0)),
                                        min_value=0.1, max_value=3.0, step=0.1, key="e_fv")
            nuevo_fe  = st.number_input("Factor estratégico",
                                        value=float(m.get("factor_estrategico", 1.0)),
                                        min_value=0.1, max_value=3.0, step=0.1, key="e_fe")
            vem_calc  = round(nuevo_vb * nuevo_fv * nuevo_fe)
            st.metric("VEM calculado (ref.)", f"$ {vem_calc:,}".replace(",","."),
                      delta=f"Anterior: $ {int(m.get('vem',0)):,}".replace(",","."))

            st.markdown("**Nota de corrección**")
            nota = st.text_area("Motivo del ajuste (opcional)", height=80, key="e_nota")

        if st.button("💾 Guardar corrección", type="primary"):
            update_mencion(int(edit_id), {
                "tipo_mencion":       nuevo_tipo,
                "sentimiento":        nuevo_sent,
                "relevancia":         nuevo_rel,
                "area_crtic":         nuevo_area,
                "estado":             nuevo_est,
                "valor_base_medio":   nuevo_vb,
                "factor_visibilidad": nuevo_fv,
                "factor_estrategico": nuevo_fe,
                "vem":                vem_calc,
            })
            st.success(f"✅ Mención {edit_id} actualizada correctamente.")
            del st.session_state["mencion_edit"]
            st.rerun()


# ════════════════════════════════════════════════════════════════
# TAB 5 — Exportar
# ════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("Exportar datos")
    e1, e2, e3 = st.columns(3)

    with e1:
        st.markdown("**Reporte diario**")
        f_exp = st.date_input("Fecha", value=hoy, key="exp_d")
        fmt_d = st.radio("Formato", ["csv","excel"], key="fmt_d")
        if st.button("Exportar día"):
            p = export_daily(str(f_exp), fmt_d)
            st.success(f"Guardado: {p}")

    with e2:
        st.markdown("**Reporte mensual**")
        mes_e  = st.selectbox("Mes",  range(1,13), index=hoy.month-1, key="exp_mes")
        anio_e = st.number_input("Año", value=hoy.year, key="exp_anio")
        fmt_m  = st.radio("Formato", ["csv","excel"], key="fmt_m")
        if st.button("Exportar mes"):
            p = export_monthly(int(anio_e), int(mes_e), fmt_m)
            st.success(f"Guardado: {p}")

    with e3:
        st.markdown("**Histórico completo**")
        fmt_h = st.radio("Formato", ["csv","excel"], key="fmt_h")
        if st.button("Exportar histórico"):
            p = export_historico(fmt_h)
            st.success(f"Guardado: {p}")


# ════════════════════════════════════════════════════════════════
# TAB 6 — Configuración de búsquedas (admin)
# ════════════════════════════════════════════════════════════════
import json as _json

_SEARCH_CFG_PATH = Path(__file__).resolve().parent.parent / "data" / "search_config.json"

_CAT_LABELS = {
    "keywords_primary":   "🎯 Keywords principales",
    "keywords_secondary": "🔗 Keywords secundarias",
    "people":             "👤 Personas",
    "partners":           "🤝 Aliados / Partners",
    "exclude_terms":      "🚫 Términos excluidos",
    "priority_media":     "📰 Medios prioritarios",
}

_CAT_HELP = {
    "keywords_primary":   "Términos que siempre se buscan. Se usan en todas las búsquedas.",
    "keywords_secondary": "Términos combinados con socios. Se usan en todas las búsquedas.",
    "people":             "Nombres de personas vinculadas a CRTIC. Se usan en todas las búsquedas.",
    "partners":           "Socios y aliados (referencial, no se buscan directamente).",
    "exclude_terms":      "Términos que filtran resultados irrelevantes.",
    "priority_media":     "Dominios de medios prioritarios para alertas.",
}


def _load_search_cfg() -> dict:
    try:
        with open(_SEARCH_CFG_PATH, encoding="utf-8") as f:
            return _json.load(f)
    except Exception:
        return {
            "keywords_primary": [], "keywords_secondary": [],
            "people": [], "partners": [],
            "exclude_terms": [], "priority_media": [],
            "search_frequency": "daily", "disabled": [],
        }


def _save_search_cfg(cfg: dict) -> None:
    with open(_SEARCH_CFG_PATH, "w", encoding="utf-8") as f:
        _json.dump(cfg, f, ensure_ascii=False, indent=2)


with tab6:
    st.subheader("⚙️ Configuración de búsquedas")

    if "admin_ok" not in st.session_state:
        st.session_state["admin_ok"] = False

    if not st.session_state["admin_ok"]:
        st.info("Esta sección es solo para administradores. Ingresa la contraseña para continuar.")
        col_pw, col_btn = st.columns([3, 1])
        with col_pw:
            pw_input = st.text_input("Contraseña de administración", type="password", key="admin_pw_input")
        with col_btn:
            st.write(""); st.write("")
            login_btn = st.button("Ingresar", key="admin_login")
        if login_btn:
            from app.config import _get as _cfg_get
            admin_pw = _cfg_get("ADMIN_PASSWORD", "")
            if admin_pw and pw_input == admin_pw:
                st.session_state["admin_ok"] = True
                st.rerun()
            elif not admin_pw:
                st.error("ADMIN_PASSWORD no configurado en .env o Secrets.")
            else:
                st.error("Contraseña incorrecta.")
    else:
        # ── Carga configuración ──────────────────────────────────────────────────
        cfg = _load_search_cfg()
        disabled: set = set(cfg.get("disabled", []))

        # ── Selector de categoría ────────────────────────────────────────────────
        cat_key = st.selectbox(
            "Seleccionar categoría",
            list(_CAT_LABELS.keys()),
            format_func=lambda k: _CAT_LABELS[k],
            key="admin_cat",
        )
        st.caption(_CAT_HELP.get(cat_key, ""))

        items: list = cfg.get(cat_key, [])
        is_search_cat = cat_key in ("keywords_primary", "keywords_secondary", "people")

        # ── Lista de términos ────────────────────────────────────────────────────
        st.markdown(f"**{_CAT_LABELS[cat_key]}** — {len(items)} término(s)")

        _toggle_item = None
        _delete_item = None

        if items:
            for i, term in enumerate(items):
                is_active = term not in disabled
                col_term, col_tog, col_del = st.columns([6, 1, 1])
                with col_term:
                    style = "" if is_active else "color:#aaa; text-decoration:line-through;"
                    st.markdown(f'<span style="{style}">{term}</span>', unsafe_allow_html=True)
                if is_search_cat:
                    with col_tog:
                        tog_label = "✅" if is_active else "⬜"
                        if st.button(tog_label, key=f"tog_{cat_key}_{i}", help="Activar/Desactivar"):
                            _toggle_item = term
                with col_del:
                    if st.button("🗑️", key=f"del_{cat_key}_{i}", help="Eliminar"):
                        _delete_item = term
        else:
            st.caption("(Sin términos en esta categoría)")

        # ── Agregar nuevo término ────────────────────────────────────────────────
        st.divider()
        col_new, col_add = st.columns([5, 1])
        with col_new:
            new_term = st.text_input("Nuevo término", placeholder="Escribe y haz clic en Agregar", key=f"new_{cat_key}")
        with col_add:
            st.write(""); st.write("")
            add_btn = st.button("➕ Agregar", key=f"add_btn_{cat_key}")

        # ── Acciones ─────────────────────────────────────────────────────────────
        if _toggle_item is not None:
            if _toggle_item in disabled:
                disabled.discard(_toggle_item)
            else:
                disabled.add(_toggle_item)
            cfg["disabled"] = list(disabled)
            _save_search_cfg(cfg)
            st.rerun()

        if _delete_item is not None:
            cfg[cat_key] = [x for x in cfg.get(cat_key, []) if x != _delete_item]
            disabled.discard(_delete_item)
            cfg["disabled"] = list(disabled)
            _save_search_cfg(cfg)
            st.success(f"'{_delete_item}' eliminado.")
            st.rerun()

        if add_btn:
            term_clean = new_term.strip()
            if not term_clean:
                st.warning("El término no puede estar vacío.")
            elif term_clean in cfg.get(cat_key, []):
                st.warning(f"'{term_clean}' ya existe en esta categoría.")
            else:
                cfg.setdefault(cat_key, []).append(term_clean)
                cfg["disabled"] = list(disabled)
                _save_search_cfg(cfg)
                st.success(f"✅ '{term_clean}' agregado.")
                st.rerun()

        # ── Frecuencia de búsqueda ────────────────────────────────────────────────
        st.divider()
        st.subheader("Frecuencia de búsqueda automática")
        freq_opts = ["daily", "weekly"]
        cur_freq = cfg.get("search_frequency", "daily")
        freq_sel = st.selectbox(
            "Frecuencia",
            freq_opts,
            index=freq_opts.index(cur_freq) if cur_freq in freq_opts else 0,
            key="freq_sel",
        )
        if st.button("Guardar frecuencia"):
            cfg["search_frequency"] = freq_sel
            cfg["disabled"] = list(disabled)
            _save_search_cfg(cfg)
            st.success(f"✅ Frecuencia actualizada a '{freq_sel}'.")

        # ── Restaurar defaults + cerrar sesión ───────────────────────────────────
        st.divider()
        col_restore, col_logout = st.columns(2)

        with col_restore:
            if st.button("↩️ Restaurar keywords por defecto"):
                default_cfg = {
                    "keywords_primary": [
                        "CRTIC",
                        "Centro para la Revolución Tecnológica en Industrias Creativas",
                        "tecnocreatividad", "tecnocreativo", "CRTIC Sur", "LAB CRTIC", "CRTIC Lab",
                    ],
                    "keywords_secondary": [
                        "ChileCreativo CRTIC", "CORFO CRTIC", "Unreal Engine CRTIC",
                        "Meta AI CRTIC", "CAF CRTIC", "BID CRTIC", "COPEC CRTIC",
                        "GAM CRTIC", "ETM Day CRTIC",
                    ],
                    "people": [
                        "Marcela Piña CRTIC", "Isidora Cabezón CRTIC",
                        "Pablo Christiny CRTIC", "Pamela Chovan CRTIC",
                    ],
                    "partners": cfg.get("partners", []),
                    "exclude_terms": cfg.get("exclude_terms", []),
                    "priority_media": cfg.get("priority_media", []),
                    "search_frequency": cfg.get("search_frequency", "daily"),
                    "disabled": [],
                }
                _save_search_cfg(default_cfg)
                st.success("✅ Keywords restaurados a los valores por defecto.")
                st.rerun()

        with col_logout:
            if st.button("🔒 Cerrar sesión admin"):
                st.session_state["admin_ok"] = False
                st.rerun()
