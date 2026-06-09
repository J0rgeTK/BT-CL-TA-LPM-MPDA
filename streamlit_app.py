"""
streamlit_app.py -- Modelo de afluencia EFE/Fesur 2027.
Punto de entrada para Streamlit Cloud.  Local:  streamlit run streamlit_app.py

Navegacion por pestanias (una por servicio + resumen). La OFERTA de trenes es la
variable de planificacion, editable por TIPO DE DIA (L-V / Sabado / Domingo) y mes.
El escenario recomendado aplica calibracion con mayo 2026 y usa la oferta como
variable editable. La base 2027 mantiene la proyeccion por oferta calibrada para
servicios regionales y ajusta Biotren a un rango prudente de 12,5-12,6 millones
antes de simular aumentos leves de oferta futura. Sin clima.
Biotren usa el total oficial diario con SSE; Llanquihue-PM se normaliza solo contra dias L-V.
"""
import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

import pipeline_afluencia as P
import oferta as O

st.set_page_config(page_title="Afluencia EFE/Fesur 2027", layout="wide", page_icon="🚆")

PAL = {"BIOTREN": "#1f6feb", "CORTO_LAJA": "#0e9f6e", "TREN_ARAUCANIA": "#d97706", "LLANQUIHUE_PM": "#9333ea"}
CONF = {"BIOTREN": "ALTA", "CORTO_LAJA": "ALTA", "TREN_ARAUCANIA": "MEDIA", "LLANQUIHUE_PM": "BAJA"}
CONF_C = {"ALTA": "#0e9f6e", "MEDIA": "#d97706", "BAJA": "#dc2626"}
DATA = os.path.join(os.path.dirname(__file__), "data")

st.markdown("""
<style>
  .stApp { background:#f6f8fb; }
  .block-container { padding-top:1.6rem; max-width:1280px; }
  h1,h2,h3,h4 { font-family:'Segoe UI',system-ui,sans-serif; color:#0f2740; }
  .hero { background:linear-gradient(110deg,#0f2740,#1f4e79); color:#fff; padding:20px 26px;
          border-radius:16px; margin-bottom:14px; box-shadow:0 8px 24px rgba(15,39,64,.18); }
  .hero h1 { color:#fff; margin:0; font-size:1.55rem; }
  .hero p { margin:.3rem 0 0; opacity:.85; font-size:.9rem; }
  div[data-testid="stMetric"] { background:#fff; border:1px solid #e6ebf2; border-radius:14px;
          padding:12px 16px; box-shadow:0 2px 8px rgba(15,39,64,.05); }
  div[data-testid="stMetricLabel"] p { color:#5b6b7d; font-weight:600; }
  button[data-baseweb="tab"] { font-weight:600; font-size:.95rem; }
  .badge { display:inline-block; padding:3px 12px; border-radius:999px; color:#fff; font-size:.78rem; font-weight:700; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def cargar():
    diario = pd.read_csv(os.path.join(DATA, "afluencia_diaria_consolidada.csv"), parse_dates=["fecha"])
    params = O.aplicar_oferta_actual(pd.read_csv(os.path.join(DATA, "oferta_params.csv")))
    mdf = P.mensualizar(diario)
    base, _ = P.proyectar_2027(mdf)
    return diario, params, mdf, base


try:
    diario, params, mdf, base = cargar()
except Exception as e:
    st.error(f"No se pudieron cargar los datos en /data: {e}")
    st.stop()

st.markdown('<div class="hero"><h1>🚆 Modelo de afluencia 2027 — EFE/Fesur</h1>'
            '<p>Oferta de trenes como variable de planificacion · editable por tipo de dia (L-V / Sabado / '
            'Domingo) y mes · calibrado con resultados reales de mayo 2026</p></div>', unsafe_allow_html=True)


def fmt(n):
    return f"{int(n):,}".replace(",", ".")


def ocupacion(units):
    """Carga media por viaje (pax/servicio) por mes, ponderada por viajes."""
    nd = O.dias_por_tipo()
    p0 = O.calibrar_productividad_reciente(params)
    p = p0[p0.unit.isin(units)].merge(nd, on=["mes", "dt"])
    p["viajes"] = p["servicios_dia"] * p["n_dias"] * (1 - p["tasa_sup"])
    p["pax"] = p["viajes"] * p["pax_x_viaje"]
    pormes = p.groupby("mes").apply(lambda x: x["pax"].sum() / max(x["viajes"].sum(), 1))
    media = p["pax"].sum() / max(p["viajes"].sum(), 1)
    bydt = p.groupby("dt").apply(lambda x: x["pax"].sum() / max(x["viajes"].sum(), 1)).reindex(O.DTYPES)
    return pormes, media, bydt


def editor_oferta(unit, label):
    sub = params[params.unit == unit].pivot(index="mes", columns="dt", values="servicios_dia")[O.DTYPES]
    sub.index.name = "Mes"
    st.caption(f"**{label}** — servicios por dia (editable). Default = oferta vigente informada.")
    cfg = {dt: st.column_config.NumberColumn(O.DTNOMBRE[dt], min_value=0.0, step=1.0, format="%.0f") for dt in O.DTYPES}
    ed = st.data_editor(sub, use_container_width=True, key=f"of_{unit}", column_config=cfg)
    plan = ed.reset_index().melt(id_vars="Mes", var_name="dt", value_name="servicios_dia").rename(columns={"Mes": "mes"})
    plan["unit"] = unit
    plan["mes"] = plan["mes"].astype(int)
    plan["servicios_dia"] = pd.to_numeric(plan["servicios_dia"], errors="coerce")
    return plan[["unit", "mes", "dt", "servicios_dia"]]


def render_servicio(s):
    cf = CONF[s]
    st.markdown(f"### {O.NOMBRE[s]} &nbsp;<span class='badge' style='background:{CONF_C[cf]}'>Confianza {cf}</span>",
                unsafe_allow_html=True)

    st.markdown("#### Oferta 2027 (variable de planificacion)")
    planes = []
    if s == "BIOTREN":
        st.info("Edite **Linea 1** y **Linea 2** por separado. La afluencia se reparte 20/80 (matriz OD); "
                "cada linea mantiene carga por viaje calibrada con el total oficial de mayo 2026.")
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
            ce[u] = cc[i].number_input(f"{u} (+% supresion)", 0.0, 30.0, 0.0, 1.0, key=f"ce_{u}") / 100.0

    plan = pd.concat(planes, ignore_index=True)
    uni, serv = O.proyectar_conservador(params, base_servicios=base, plan=plan, contingencia_extra=ce)
    _, serv_oferta = O.proyectar(params, plan=plan, contingencia_extra=ce)
    pormes, ocup_media, ocup_dt = ocupacion(O.UNIDADES_DE[s])
    viajes = O.viajes_anuales(params, plan=plan, contingencia_extra=ce, units=O.UNIDADES_DE[s])
    ocup_proy = serv[s].dropna().sum() / max(viajes, 1)

    k = st.columns(4)
    k[0].metric("Total anual 2027 base ajustado", fmt(serv[s].dropna().sum()))
    k[1].metric("Referencia estacional", fmt(base[s].sum()))
    k[2].metric("Pax/viaje proyectado", fmt(ocup_proy))
    pk = serv[s].astype(float).idxmax()
    k[3].metric("Mes peak", pk, fmt(serv[s].max()))

    if s in O.AJUSTE_CONSERVADOR:
        st.caption("Escenario base calibrado ajustado: para Biotren se aplica una correccion prudencial; para los demas servicios se mantiene la proyeccion por oferta calibrada.")

    g, t = st.columns([3, 2])
    with g:
        st.markdown("#### Afluencia: historico + proyeccion 2027")
        h = mdf[mdf.servicio == s].sort_values("mes")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[str(m) for m in h["mes"]], y=h["pax_norm"], name="Historico",
                                 mode="lines", line=dict(color=PAL[s], width=3),
                                 fill="tozeroy", fillcolor="rgba(31,111,235,.07)"))
        fig.add_trace(go.Scatter(x=list(serv.index), y=serv[s].astype(float), name="Proyeccion 2027",
                                 mode="lines+markers", line=dict(color="#dc2626", width=3, dash="dash")))
        fig.update_layout(height=330, margin=dict(l=8, r=8, t=8, b=8), plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=1.15, x=0),
                          hovermode="x unified", font=dict(family="Segoe UI", color="#0f2740"))
        fig.update_xaxes(showgrid=False); fig.update_yaxes(gridcolor="#eef2f7", title="pax/mes")
        st.plotly_chart(fig, use_container_width=True)
    with t:
        st.markdown("#### Proyeccion mensual 2027")
        out = pd.DataFrame(index=serv.index)
        if s == "BIOTREN":
            out["L1"] = uni["BIOTREN_L1"]; out["L2"] = uni["BIOTREN_L2"]
        out["Total base ajustado"] = serv[s]
        out["Proy. solo oferta"] = serv_oferta[s]
        out["Ref. estac."] = base[s].values
        st.dataframe(out, use_container_width=True, height=330)

    st.markdown("#### Ocupacion media — pasajeros por viaje")
    o1, o2 = st.columns([3, 2])
    with o1:
        figo = go.Figure(go.Bar(x=[f"{m:02d}" for m in pormes.index], y=pormes.values, marker_color=PAL[s]))
        figo.update_layout(height=240, margin=dict(l=8, r=8, t=8, b=8), plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Segoe UI", color="#0f2740"))
        figo.update_xaxes(title="mes"); figo.update_yaxes(gridcolor="#eef2f7", title="pax/viaje")
        st.plotly_chart(figo, use_container_width=True)
    with o2:
        dd = ocup_dt.rename(index=O.DTNOMBRE).round(0).astype(int).rename("pax/viaje").to_frame()
        st.dataframe(dd, use_container_width=True)
        st.caption("Promedio de pasajeros por servicio (viaje). La ocupacion real "
                   "(pax/asientos) requiere la capacidad por tren, no disponible en los datos.")

    if s == "CORTO_LAJA":
        st.warning("Laja-Talcahuano: la calibracion de mayo 2026 reduce la productividad L-V frente al modelo previo. "
                   "Revisar escenarios expansivos con cautela.")
    if s == "LLANQUIHUE_PM":
        st.warning("Llanquihue-PM: serie corta; la normalizacion fue corregida para dias L-V. Confianza BAJA.")
    st.download_button(f"⬇ Descargar proyeccion {O.NOMBRE[s]} (CSV)", out.to_csv().encode(),
                       f"proyeccion_2027_{s}.csv", key=f"dl_{s}")


tabs = st.tabs(["📊 Resumen"] + [O.NOMBRE[s] for s in O.SERVICIOS])
with tabs[0]:
    uni, serv = O.proyectar_conservador(params, base_servicios=base)
    _, serv_oferta = O.proyectar(params)
    st.markdown("### Proyeccion 2027 — escenario base calibrado ajustado")
    st.info("El escenario recomendado mantiene la proyeccion por oferta calibrada con mayo 2026 para los servicios regionales. En Biotren se aplica un ajuste prudencial para situar el resultado anual en torno a 12,5-12,6 millones antes de evaluar aumentos leves de oferta futura.")
    with st.expander("Oferta vigente considerada en el escenario base"):
        st.dataframe(O.oferta_actual_df(detalle=True), use_container_width=True)
        st.caption("Nota: el cálculo mensual usa la excepción de Laja-Talcahuano: 10 servicios sábado y domingo en enero-febrero; 8 servicios sábado y domingo desde marzo a diciembre.")
    with st.expander("Calibracion de productividad mayo 2026"):
        st.dataframe(O.cargar_calibracion_productividad(), use_container_width=True)
        st.caption("Los factores ajustan parcialmente pasajeros por viaje por tipo de dia; no reemplazan toda la historia por un solo mes.")
    with st.expander("Metodologia del escenario base calibrado ajustado"):
        st.markdown("""
        - **Referencia estacional:** proyeccion mensual basada en el historico disponible actualizado con mayo 2026.
        - **Oferta calibrada:** la productividad pax/viaje se calibra con mayo 2026 por servicio y tipo de dia.
        - **Servicios regionales:** Laja-Talcahuano, Tren Araucania y Llanquihue-Puerto Montt mantienen la proyeccion por oferta calibrada, porque el resultado es coherente con la oferta vigente y la evidencia reciente.
        - **Biotren:** se reconoce el 80% del diferencial entre oferta calibrada y referencia estacional, dejando el total en torno a 12,5-12,6 millones. Esto permite partir desde una base realista antes de simular aumentos leves de servicios.
        """)
    kk = st.columns(4)
    for i, s in enumerate(O.SERVICIOS):
        viajes = O.viajes_anuales(params, units=O.UNIDADES_DE[s])
        om = serv[s].dropna().sum() / max(viajes, 1)
        delta = serv[s].dropna().sum() - serv_oferta[s].dropna().sum()
        kk[i].metric(O.NOMBRE[s], fmt(serv[s].dropna().sum()), f"vs oferta {fmt(delta)} pax")
    fig = go.Figure()
    for s in O.SERVICIOS:
        fig.add_trace(go.Scatter(x=list(serv.index), y=serv[s].astype(float), name=O.NOMBRE[s],
                                 mode="lines+markers", line=dict(color=PAL[s], width=3)))
    fig.update_layout(height=380, margin=dict(l=8, r=8, t=8, b=8), plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=1.1, x=0),
                      hovermode="x unified", font=dict(family="Segoe UI", color="#0f2740"))
    fig.update_xaxes(showgrid=False); fig.update_yaxes(gridcolor="#eef2f7", title="pax/mes")
    st.plotly_chart(fig, use_container_width=True)
    resumen_comp = serv.copy()
    for s in O.SERVICIOS:
        resumen_comp[f"{s}_solo_oferta"] = serv_oferta[s]
        resumen_comp[f"{s}_ref_estacional"] = base[s].values
    st.dataframe(resumen_comp, use_container_width=True)
    cda, cdb = st.columns(2)
    cda.download_button("⬇ Resumen base ajustado por servicio (CSV)", serv.to_csv().encode(), "proyeccion_2027_resumen_base_ajustada.csv")
    cdb.download_button("⬇ Detalle base ajustada por unidad / L1-L2 (CSV)", uni.to_csv().encode(), "proyeccion_2027_unidades_base_ajustada.csv")

for i, s in enumerate(O.SERVICIOS):
    with tabs[i + 1]:
        render_servicio(s)
