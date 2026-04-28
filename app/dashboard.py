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

filtro_sent = st.sidebar.selectbox("Sentimiento", ["Todos","Positivo","Neutro","Negativo"])
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
    sentimiento=None if filtro_sent == "Todos" else filtro_sent,
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
k1, k2, k3, k4, k5 = st.columns(5)
vem_sum  = int(df["vem"].sum()) if not df.empty else 0
neg_n    = int((df["sentimiento"] == "Negativo").sum()) if not df.empty else 0
alta_n   = int((df["relevancia"]  == "Alta").sum())     if not df.empty else 0
pos_n    = int((df["sentimiento"] == "Positivo").sum()) if not df.empty else 0

k1.metric("Total menciones",   len(df))
k2.metric("VEM acumulado",     f"$ {vem_sum:,}".replace(",", "."))
k3.metric("Alta relevancia",   alta_n)
k4.metric("Positivas",         pos_n)
k5.metric("⚠️ Negativas",      neg_n, delta=None)

if neg_n:
    st.error(f"⚠️ {neg_n} mención(es) negativa(s) en el período seleccionado. Revisar en la pestaña 'Tabla'.")

st.divider()

# ── Pestañas ───────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Visualizaciones",
    "📈 Comparativo VEM",
    "📋 Tabla de menciones",
    "✏️ Corrección manual",
    "📥 Exportar",
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
            st.subheader("Menciones por sentimiento")
            sent = df["sentimiento"].value_counts().reset_index()
            sent.columns = ["Sentimiento","n"]
            fig2 = px.pie(sent, values="n", names="Sentimiento",
                          color="Sentimiento",
                          color_discrete_map={"Positivo":"#4caf50","Neutro":"#2196f3","Negativo":"#f44336"})
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
