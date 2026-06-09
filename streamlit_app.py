"""
streamlit_app.py -- Modelo de afluencia EFE/Fesur 2027.

El escenario principal usa oferta vigente/editable, calibracion con mayo 2026 y
redistribucion mensual con patrones historicos 2024-2026 por servicio. No muestra
un contraste contra otra base de calculo; la serie historica se presenta solo como contexto para
auditar el patron mensual.
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
    hist = O.analisis_mensual_historico(mdf)
    return diario, params, mdf, hist


try:
    diario, params, mdf, hist = cargar()
except Exception as e:
    st.error(f"No se pudieron cargar los datos en /data: {e}")
    st.stop()

st.markdown('<div class="hero"><h1>🚆 Modelo de afluencia 2027 — EFE/Fesur</h1>'
            '<p>Oferta editable por tipo de dia y mes · calibrado con mayo 2026 · '
            'distribucion mensual basada en comportamiento historico 2024-2026</p></div>', unsafe_allow_html=True)


def fmt(n):
    return f"{int(round(float(n))):,}".replace(",", ".")


def editor_oferta(unit, label, base_df=None):
    if base_df is None:
        sub = params[params.unit == unit].pivot(index="mes", columns="dt", values="servicios_dia")[O.DTYPES]
    else:
        sub = base_df[base_df.unit == unit].pivot(index="mes", columns="dt", values="servicios_dia")[O.DTYPES]
    sub.index.name = "Mes"
    st.caption(f"**{label}** — servicios por dia (editable).")
    cfg = {dt: st.column_config.NumberColumn(O.DTNOMBRE[dt], min_value=0.0, step=1.0, format="%.1f") for dt in O.DTYPES}
    ed = st.data_editor(sub, use_container_width=True, key=f"of_{unit}", column_config=cfg)
    plan = ed.reset_index().melt(id_vars="Mes", var_name="dt", value_name="servicios_dia").rename(columns={"Mes": "mes"})
    plan["unit"] = unit
    plan["mes"] = plan["mes"].astype(int)
    plan["servicios_dia"] = pd.to_numeric(plan["servicios_dia"], errors="coerce")
    return plan[["unit", "mes", "dt", "servicios_dia"]]


def editor_tren_araucania():
    st.info("La oferta se edita por tramo. Para demanda, Victoria-Temuco tiene mayor peso relativo; Pitrufquen y Claret se transforman en oferta equivalente con menor efecto marginal.")
    base_tramos = O.oferta_tren_araucania_tramos_df(mensual=True)
    cols = st.columns(3)
    planes = []
    for i, unit in enumerate(O.TA_TRAMOS):
        with cols[i]:
            planes.append(editor_oferta(unit, O.TA_TRAMO_NOMBRE[unit], base_df=base_tramos))
    plan_tramos = pd.concat(planes, ignore_index=True)
    plan_agregado = O.plan_tren_araucania_agregado(plan_tramos)
    with st.expander("Oferta equivalente usada para demanda"):
        st.dataframe(plan_agregado.pivot(index="mes", columns="dt", values="servicios_dia")[O.DTYPES], use_container_width=True)
        st.caption("La oferta equivalente conserva el nivel actual con la programacion vigente y modera el efecto de aumentos en Pitrufquen/Claret.")
    return plan_tramos, plan_agregado


def ocupacion(units, plan=None, contingencia_extra=None):
    nd = O.dias_por_tipo()
    p = O.calibrar_productividad_reciente(params)
    if plan is not None:
        pl = plan[["unit", "mes", "dt", "servicios_dia"]].rename(columns={"servicios_dia": "sd_plan"})
        p = p.merge(pl, on=["unit", "mes", "dt"], how="left")
        p["servicios_dia"] = pd.to_numeric(p["sd_plan"], errors="coerce").fillna(p["servicios_dia"])
        p = p.drop(columns="sd_plan")
    p = p[p.unit.isin(units)].merge(nd, on=["mes", "dt"])
    ce = contingencia_extra or {}
    p["f_sup"] = (1 - p["tasa_sup"] - p["unit"].map(ce).fillna(0)).clip(0, 1)
    p["viajes"] = p["servicios_dia"] * p["n_dias"] * p["f_sup"]
    p["pax"] = p["viajes"] * p["pax_x_viaje"]
    pormes = p.groupby("mes").apply(lambda x: x["pax"].sum() / max(x["viajes"].sum(), 1))
    bydt = p.groupby("dt").apply(lambda x: x["pax"].sum() / max(x["viajes"].sum(), 1)).reindex(O.DTYPES)
    return pormes, bydt


def grafico_historico_y_proyeccion(s, serv):
    h = mdf[mdf.servicio == s].copy().sort_values("mes")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[str(m) for m in h["mes"]], y=h["pax_norm"], name="Historico mensual",
                             mode="lines", line=dict(color=PAL[s], width=3),
                             fill="tozeroy", fillcolor="rgba(31,111,235,.07)"))
    fig.add_trace(go.Scatter(x=list(serv.index), y=serv[s].astype(float), name="Proyeccion 2027",
                             mode="lines+markers", line=dict(color="#dc2626", width=3, dash="dash")))
    fig.update_layout(height=330, margin=dict(l=8, r=8, t=8, b=8), plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=1.15, x=0),
                      hovermode="x unified", font=dict(family="Segoe UI", color="#0f2740"))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#eef2f7", title="pax/mes")
    st.plotly_chart(fig, use_container_width=True)


def tabla_historica_servicio(s):
    h = hist[hist.servicio == s].copy()
    if h.empty:
        return pd.DataFrame()
    h["mes"] = h["mes"].map(lambda x: f"{int(x):02d}")
    piv = h.pivot_table(index="mes", columns="anio", values="afluencia_mensual_normalizada", aggfunc="first")
    return piv.round(0).astype("Int64")


def render_servicio(s):
    cf = CONF[s]
    st.markdown(f"### {O.NOMBRE[s]} &nbsp;<span class='badge' style='background:{CONF_C[cf]}'>Confianza {cf}</span>",
                unsafe_allow_html=True)

    st.markdown("#### Oferta 2027")
    ce = {}
    plan_tramos = None
    if s == "BIOTREN":
        st.info("Biotren se edita por linea. La proyeccion total mantiene una base cercana a 12,5-12,6 millones con la oferta vigente.")
        c1, c2 = st.columns(2)
        with c1:
            plan_l1 = editor_oferta("BIOTREN_L1", "Linea 1")
        with c2:
            plan_l2 = editor_oferta("BIOTREN_L2", "Linea 2")
        plan = pd.concat([plan_l1, plan_l2], ignore_index=True)
    elif s == "TREN_ARAUCANIA":
        plan_tramos, plan = editor_tren_araucania()
    else:
        plan = editor_oferta(O.UNIDADES_DE[s][0], O.NOMBRE[s])

    with st.expander("Contingencia extra sobre supresion historica"):
        unidades_ce = O.UNIDADES_DE[s]
        cc = st.columns(len(unidades_ce))
        for i, u in enumerate(unidades_ce):
            ce[u] = cc[i].number_input(f"{u} (+% supresion)", 0.0, 30.0, 0.0, 1.0, key=f"ce_{u}") / 100.0

    uni, serv, perfiles = O.proyectar_base_ajustada(params, mdf, plan=plan, contingencia_extra=ce)
    viajes = O.viajes_anuales(params, plan=plan, contingencia_extra=ce, units=O.UNIDADES_DE[s])
    ocup_proy = serv[s].dropna().sum() / max(viajes, 1)
    pk = serv[s].astype(float).idxmax()

    k = st.columns(4)
    k[0].metric("Total anual 2027", fmt(serv[s].dropna().sum()))
    k[1].metric("Pax/viaje proyectado", fmt(ocup_proy))
    k[2].metric("Mes peak", pk, fmt(serv[s].max()))
    k[3].metric("Mes menor", serv[s].astype(float).idxmin(), fmt(serv[s].min()))

    g, t = st.columns([3, 2])
    with g:
        st.markdown("#### Historico mensual y proyeccion")
        grafico_historico_y_proyeccion(s, serv)
    with t:
        st.markdown("#### Proyeccion mensual 2027")
        out = pd.DataFrame(index=serv.index)
        if s == "BIOTREN":
            out["L1"] = uni["BIOTREN_L1"]
            out["L2"] = uni["BIOTREN_L2"]
        elif s == "TREN_ARAUCANIA":
            tr = O.desagregar_tren_araucania_por_tramo(serv[s], plan_tramos=plan_tramos)
            out["Temuco - Victoria"] = tr.get("TA_TEMUCO_VICTORIA")
            out["Temuco - Pitrufquen"] = tr.get("TA_TEMUCO_PITRUFQUEN")
            out["Claret"] = tr.get("TA_CLARET")
        out["Total proyectado"] = serv[s]
        st.dataframe(out, use_container_width=True, height=330)

    st.markdown("#### Comportamiento mensual historico por anio")
    st.dataframe(tabla_historica_servicio(s), use_container_width=True)

    st.markdown("#### Pasajeros promedio por servicio")
    pormes, ocup_dt = ocupacion(O.UNIDADES_DE[s], plan=plan, contingencia_extra=ce)
    o1, o2 = st.columns([3, 2])
    with o1:
        figo = go.Figure(go.Bar(x=[f"{m:02d}" for m in pormes.index], y=pormes.values, marker_color=PAL[s]))
        figo.update_layout(height=240, margin=dict(l=8, r=8, t=8, b=8), plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Segoe UI", color="#0f2740"))
        figo.update_xaxes(title="mes")
        figo.update_yaxes(gridcolor="#eef2f7", title="pax/viaje")
        st.plotly_chart(figo, use_container_width=True)
    with o2:
        dd = ocup_dt.rename(index=O.DTNOMBRE).round(0).astype("Int64").rename("pax/viaje").to_frame()
        st.dataframe(dd, use_container_width=True)
        st.caption("Corresponde a pasajeros promedio por servicio operado; no equivale a ocupacion fisica del tren.")

    if s == "CORTO_LAJA":
        st.warning("Oferta base corregida: 8 servicios todos los dias, salvo sabados y domingos de enero-febrero con 10 servicios.")
    if s == "LLANQUIHUE_PM":
        st.warning("Enero y febrero mantienen un comportamiento estival similar al observado en 2026. El servicio no considera fines de semana planificados.")
    st.download_button(f"⬇ Descargar proyeccion {O.NOMBRE[s]} (CSV)", out.to_csv().encode(),
                       f"proyeccion_2027_{s}.csv", key=f"dl_{s}")


tabs = st.tabs(["📊 Resumen"] + [O.NOMBRE[s] for s in O.SERVICIOS])
with tabs[0]:
    uni, serv, perfiles = O.proyectar_base_ajustada(params, mdf)
    tramos_ta = O.desagregar_tren_araucania_por_tramo(serv["TREN_ARAUCANIA"])
    st.markdown("### Proyeccion 2027 — escenario base ajustado")
    st.info("El escenario usa la oferta vigente como base, calibra productividad con mayo 2026 y distribuye los resultados mensuales segun patrones historicos 2024-2026 por servicio.")
    with st.expander("Oferta vigente considerada"):
        st.dataframe(O.oferta_actual_df(detalle=True), use_container_width=True)
        st.caption("Laja-Talcahuano: 8 servicios todos los dias, excepto sabados y domingos de enero-febrero con 10 servicios.")
    with st.expander("Oferta Tren Araucania por tramo"):
        st.dataframe(O.oferta_tren_araucania_tramos_df(mensual=False), use_container_width=True)
        st.caption("Los pesos de demanda aplicados son: Victoria-Temuco 1,00; Pitrufquen 0,16; Claret 0,08.")
    with st.expander("Comportamiento mensual historico por servicio"):
        st.dataframe(hist, use_container_width=True)

    kk = st.columns(4)
    for i, s in enumerate(O.SERVICIOS):
        viajes = O.viajes_anuales(params, units=O.UNIDADES_DE[s])
        om = serv[s].dropna().sum() / max(viajes, 1)
        kk[i].metric(O.NOMBRE[s], fmt(serv[s].dropna().sum()), f"{fmt(om)} pax/viaje")

    fig = go.Figure()
    for s in O.SERVICIOS:
        fig.add_trace(go.Scatter(x=list(serv.index), y=serv[s].astype(float), name=O.NOMBRE[s],
                                 mode="lines+markers", line=dict(color=PAL[s], width=3)))
    fig.update_layout(height=380, margin=dict(l=8, r=8, t=8, b=8), plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=1.1, x=0),
                      hovermode="x unified", font=dict(family="Segoe UI", color="#0f2740"))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#eef2f7", title="pax/mes")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Resumen mensual 2027")
    st.dataframe(serv, use_container_width=True)
    cda, cdb, cdc, cdd = st.columns(4)
    cda.download_button("⬇ Resumen por servicio", serv.to_csv().encode(), "proyeccion_2027_resumen_base_ajustada.csv")
    cdb.download_button("⬇ Detalle por unidad", uni.to_csv().encode(), "proyeccion_2027_unidades_base_ajustada.csv")
    cdc.download_button("⬇ Tren Araucania por tramo", tramos_ta.to_csv().encode(), "proyeccion_2027_tren_araucania_tramos.csv")
    cdd.download_button("⬇ Perfil mensual utilizado", perfiles.to_csv(index=False).encode(), "perfil_mensual_utilizado_2027.csv")

for i, s in enumerate(O.SERVICIOS):
    with tabs[i + 1]:
        render_servicio(s)
