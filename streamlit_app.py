"""
streamlit_app.py -- Modelo de afluencia EFE/Fesur 2027.
Punto de entrada para Streamlit Cloud.  Local:  streamlit run streamlit_app.py

4 secciones (una por servicio). La OFERTA de trenes es la variable de planificacion,
editable por TIPO DE DIA (Lunes-Viernes / Sabado / Domingo) y mes. Para Biotren,
L1 y L2 por separado. Base: estacionalidad + reporte operacional. Sin clima.
"""
import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

import pipeline_afluencia as P
import oferta as O

st.set_page_config(page_title="Afluencia EFE/Fesur 2027", layout="wide",
                   page_icon="🚆", initial_sidebar_state="expanded")

PALETTE = {"BIOTREN": "#1f6feb", "CORTO_LAJA": "#0e9f6e",
           "TREN_ARAUCANIA": "#d97706", "LLANQUIHUE_PM": "#9333ea"}
CONF = {"BIOTREN": "ALTA", "CORTO_LAJA": "ALTA", "TREN_ARAUCANIA": "MEDIA", "LLANQUIHUE_PM": "BAJA"}
CONF_COLOR = {"ALTA": "#0e9f6e", "MEDIA": "#d97706", "BAJA": "#dc2626"}
DATA = os.path.join(os.path.dirname(__file__), "data")

st.markdown("""
<style>
  .stApp { background: #f6f8fb; }
  #MainMenu, footer, header [data-testid="stToolbar"] { visibility: hidden; }
  .block-container { padding-top: 2rem; max-width: 1250px; }
  h1, h2, h3 { font-family: 'Segoe UI', system-ui, sans-serif; color: #0f2740; letter-spacing:-.3px; }
  .hero { background: linear-gradient(110deg,#0f2740,#1f4e79); color:#fff; padding:22px 28px;
          border-radius:16px; margin-bottom:18px; box-shadow:0 8px 24px rgba(15,39,64,.18); }
  .hero h1 { color:#fff; margin:0; font-size:1.7rem; }
  .hero p { margin:.35rem 0 0; opacity:.85; font-size:.95rem; }
  div[data-testid="stMetric"] { background:#fff; border:1px solid #e6ebf2; border-radius:14px;
          padding:14px 18px; box-shadow:0 2px 8px rgba(15,39,64,.05); }
  div[data-testid="stMetricLabel"] { color:#5b6b7d; font-weight:600; }
  div[data-testid="stMetricValue"] { color:#0f2740; }
  .badge { display:inline-block; padding:3px 12px; border-radius:999px; color:#fff;
           font-size:.78rem; font-weight:700; }
  section[data-testid="stSidebar"] { background:#0f2740; }
  section[data-testid="stSidebar"] * { color:#dce6f2 !important; }
  .stDataFrame, .stPlotlyChart { background:#fff; border:1px solid #e6ebf2; border-radius:14px; padding:6px; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def cargar():
    diario = pd.read_csv(os.path.join(DATA, "afluencia_diaria_consolidada.csv"), parse_dates=["fecha"])
    params = pd.read_csv(os.path.join(DATA, "oferta_params.csv"))
    mdf = P.mensualizar(diario)
    base, meta = P.proyectar_2027(mdf)
    return diario, params, mdf, base, meta


try:
    diario, params, mdf, base, meta = cargar()
except Exception as e:
    st.error(f"No se pudieron cargar los datos en /data: {e}")
    st.stop()

st.markdown('<div class="hero"><h1>🚆 Modelo de afluencia 2027 — EFE/Fesur</h1>'
            '<p>La oferta de trenes es la variable de planificacion · editable por tipo de dia '
            '(L-V / Sabado / Domingo) y mes · base: estacionalidad + reporte operacional</p></div>',
            unsafe_allow_html=True)

st.sidebar.markdown("### Navegacion")
seccion = st.sidebar.radio("Seccion", ["Resumen general"] + [O.NOMBRE[s] for s in O.SERVICIOS],
                           label_visibility="collapsed")
INV = {v: k for k, v in O.NOMBRE.items()}


def kpi_row(serv):
    cols = st.columns(4)
    for i, s in enumerate(O.SERVICIOS):
        total = int(serv[s].dropna().sum()) if s in serv else 0
        cols[i].metric(O.NOMBRE[s], f"{total:,}".replace(",", "."),
                       help=f"Confianza del pronostico: {CONF[s]}")


def chart_servicio(s, proj):
    h = mdf[mdf.servicio == s].sort_values("mes")
    xh = [str(m) for m in h["mes"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xh, y=h["pax_norm"], name="Historico",
                             mode="lines", line=dict(color=PALETTE[s], width=3),
                             fill="tozeroy", fillcolor="rgba(31,111,235,.07)"))
    fig.add_trace(go.Scatter(x=list(proj.index), y=proj.values, name="Proyeccion 2027",
                             mode="lines+markers", line=dict(color="#dc2626", width=3, dash="dash"),
                             marker=dict(size=6)))
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", y=1.12, x=0), hovermode="x unified",
                      font=dict(family="Segoe UI, system-ui", color="#0f2740"))
    fig.update_xaxes(showgrid=False); fig.update_yaxes(gridcolor="#eef2f7", title="pax/mes")
    st.plotly_chart(fig, use_container_width=True)


def editor_oferta(unit, label):
    sub = params[params.unit == unit].pivot(index="mes", columns="dt", values="servicios_dia")[O.DTYPES]
    sub.index.name = "Mes"
    st.caption(f"**{label}** — servicios por dia (editable). Default = oferta historica operada.")
    cfg = {dt: st.column_config.NumberColumn(O.DTNOMBRE[dt], min_value=0.0, step=1.0, format="%.0f")
           for dt in O.DTYPES}
    ed = st.data_editor(sub, use_container_width=True, key=f"of_{unit}", column_config=cfg)
    plan = ed.reset_index().melt(id_vars="Mes", var_name="dt", value_name="servicios_dia")
    plan = plan.rename(columns={"Mes": "mes"})
    plan["unit"] = unit
    plan["mes"] = plan["mes"].astype(int)
    plan["servicios_dia"] = pd.to_numeric(plan["servicios_dia"], errors="coerce")
    return plan[["unit", "mes", "dt", "servicios_dia"]]


def render_servicio(s):
    c = CONF[s]
    st.markdown(f"## {O.NOMBRE[s]} &nbsp;<span class='badge' style='background:{CONF_COLOR[c]}'>"
                f"Confianza {c}</span>", unsafe_allow_html=True)

    st.markdown("#### Oferta 2027 (variable de planificacion)")
    planes = []
    if s == "BIOTREN":
        st.info("Biotren: edite **Linea 1** y **Linea 2** por separado. La afluencia se reparte "
                "20/80 (L1/L2, matriz OD); cada linea tiene su carga por viaje. Los servicios "
                "Laja-Talcahuano circulan por L1 (Hualqui-Talcahuano) pero figuran como linea "
                "propia en el RROO (no se duplican).")
        c1, c2 = st.columns(2)
        with c1:
            planes.append(editor_oferta("BIOTREN_L1", "Linea 1"))
        with c2:
            planes.append(editor_oferta("BIOTREN_L2", "Linea 2"))
    else:
        planes.append(editor_oferta(O.UNIDADES_DE[s][0], O.NOMBRE[s]))

    with st.expander("Contingencia extra (sobre la supresion historica)"):
        ce = {}
        cc = st.columns(len(O.UNIDADES_DE[s]))
        for i, u in enumerate(O.UNIDADES_DE[s]):
            ce[u] = cc[i].number_input(f"{u} (+% supresion)", 0.0, 30.0, 0.0, 1.0) / 100.0

    plan = pd.concat(planes, ignore_index=True)
    uni, serv = O.proyectar(params, plan=plan, contingencia_extra=ce)

    k1, k2, k3 = st.columns(3)
    k1.metric("Total anual 2027 (por oferta)", f"{int(serv[s].dropna().sum()):,}".replace(",", "."))
    k2.metric("Referencia estacional", f"{int(base[s].sum()):,}".replace(",", "."))
    pk = serv[s].astype(float).idxmax()
    k3.metric("Mes peak", pk, f"{int(serv[s].max()):,}".replace(",", "."))

    g, t = st.columns([3, 2])
    with g:
        st.markdown("#### Afluencia: historico + proyeccion 2027")
        chart_servicio(s, serv[s])
    with t:
        st.markdown("#### Detalle mensual 2027")
        out = pd.DataFrame(index=serv.index)
        if s == "BIOTREN":
            out["L1"] = uni["BIOTREN_L1"]; out["L2"] = uni["BIOTREN_L2"]
        out["Total"] = serv[s]
        out["Ref. estacional"] = base[s].values
        st.dataframe(out, use_container_width=True, height=360)

    if s == "CORTO_LAJA":
        st.warning("Laja-Talcahuano: oferta plana (CV 3%), casi sin correlacion con la demanda. "
                   "El modo por oferta sobreestima (ignora la tendencia a la baja). Usar la "
                   "referencia estacional como base; la oferta solo para escenarios.")
    if s == "LLANQUIHUE_PM":
        st.warning("Llanquihue-PM: 13 meses, solape RROO delgado (algunos meses imputados). "
                   "corr(oferta,demanda)=+0.76 (prometedor pero fragil). Confianza BAJA.")
    st.download_button(f"⬇ Descargar proyeccion {O.NOMBRE[s]} (CSV)",
                       out.to_csv().encode(), f"proyeccion_2027_{s}.csv")


if seccion == "Resumen general":
    uni, serv = O.proyectar(params)
    st.markdown("### Proyeccion 2027 — escenario base (oferta historica)")
    kpi_row(serv)
    st.markdown("#### Afluencia mensual proyectada 2027 por servicio")
    fig = go.Figure()
    for s in O.SERVICIOS:
        fig.add_trace(go.Scatter(x=list(serv.index), y=serv[s].astype(float), name=O.NOMBRE[s],
                                 mode="lines+markers", line=dict(color=PALETTE[s], width=3)))
    fig.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", y=1.1, x=0), hovermode="x unified",
                      font=dict(family="Segoe UI, system-ui", color="#0f2740"))
    fig.update_xaxes(showgrid=False); fig.update_yaxes(gridcolor="#eef2f7", title="pax/mes")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("#### Tabla 12 x 4")
    st.dataframe(serv, use_container_width=True)
    st.caption("Entra a cada seccion para editar la oferta por tipo de dia y ver el efecto. "
               "Biotren se desglosa en Linea 1 / Linea 2.")
    cda, cdb = st.columns(2)
    cda.download_button("⬇ Resumen por servicio (CSV)", serv.to_csv().encode(), "proyeccion_2027_resumen.csv")
    cdb.download_button("⬇ Detalle por unidad / L1-L2 (CSV)", uni.to_csv().encode(), "proyeccion_2027_unidades.csv")
else:
    render_servicio(INV[seccion])
