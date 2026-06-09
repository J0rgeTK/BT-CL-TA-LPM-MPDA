"""
streamlit_app.py -- Modelo de afluencia EFE/Fesur 2027.

Versión metodológica mensual-elástica:
- La oferta se edita por servicio, mes y tipo de día.
- La demanda de cada mes se calcula de forma independiente.
- No se reparte un total anual fijo: el total anual resulta de sumar los 12 meses.
- El cambio de oferta en un mes afecta ese mes y el total anual, no redistribuye el resto del año.
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
  .method { background:#fff; border:1px solid #e6ebf2; border-radius:14px; padding:18px 22px; }
  code { white-space: pre-wrap; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def cargar():
    diario = pd.read_csv(os.path.join(DATA, "afluencia_diaria_consolidada.csv"), parse_dates=["fecha"])
    params = O.aplicar_oferta_actual(pd.read_csv(os.path.join(DATA, "oferta_params.csv")))
    mdf = P.mensualizar(diario)
    hist = O.analisis_mensual_historico(mdf)
    hist_anual = O.resumen_historico_anual(mdf)
    return diario, params, mdf, hist, hist_anual


try:
    diario, params, mdf, hist, hist_anual = cargar()
except Exception as e:
    st.error(f"No se pudieron cargar los datos en /data: {e}")
    st.stop()

st.markdown('<div class="hero"><h1>🚆 Modelo de afluencia 2027 — EFE/Fesur</h1>'
            '<p>Motor mensual-elástico · oferta editable por mes y tipo de día · calibrado con mayo 2026 · histórico 2024-2026</p></div>', unsafe_allow_html=True)


def fmt(n):
    return f"{int(round(float(n))):,}".replace(",", ".")


def editor_oferta(unit, label, base_df=None):
    if base_df is None:
        sub = params[params.unit == unit].pivot(index="mes", columns="dt", values="servicios_dia")[O.DTYPES]
    else:
        sub = base_df[base_df.unit == unit].pivot(index="mes", columns="dt", values="servicios_dia")[O.DTYPES]
    sub.index.name = "Mes"
    st.caption(f"**{label}** — servicios por día. Cada modificación impacta directamente el mes editado.")
    cfg = {dt: st.column_config.NumberColumn(O.DTNOMBRE[dt], min_value=0.0, step=1.0, format="%.1f") for dt in O.DTYPES}
    ed = st.data_editor(sub, use_container_width=True, key=f"of_{unit}", column_config=cfg)
    plan = ed.reset_index().melt(id_vars="Mes", var_name="dt", value_name="servicios_dia").rename(columns={"Mes": "mes"})
    plan["unit"] = unit
    plan["mes"] = plan["mes"].astype(int)
    plan["servicios_dia"] = pd.to_numeric(plan["servicios_dia"], errors="coerce")
    return plan[["unit", "mes", "dt", "servicios_dia"]]


def editor_tren_araucania():
    st.info("La oferta se edita por tramo. Para demanda, Victoria-Temuco tiene mayor peso relativo que Pitrufquén y Claret.")
    base_tramos = O.oferta_tren_araucania_tramos_df(mensual=True)
    cols = st.columns(3)
    planes = []
    for i, unit in enumerate(O.TA_TRAMOS):
        with cols[i]:
            planes.append(editor_oferta(unit, O.TA_TRAMO_NOMBRE[unit], base_df=base_tramos))
    plan_tramos = pd.concat(planes, ignore_index=True)
    plan_agregado = O.plan_tren_araucania_agregado(plan_tramos)
    with st.expander("Oferta equivalente usada en el motor de demanda"):
        st.dataframe(plan_agregado.pivot(index="mes", columns="dt", values="servicios_dia")[O.DTYPES], use_container_width=True)
        st.caption("Victoria-Temuco tiene peso 1,00; Pitrufquén 0,16; Claret 0,08. La equivalencia evita asumir que todos los tramos tienen igual productividad marginal.")
    return plan_tramos, plan_agregado


def grafico_historico_y_proyeccion(s, serv):
    h = mdf[mdf.servicio == s].copy().sort_values("mes")
    fig = go.Figure()
    if not h.empty:
        fig.add_trace(go.Scatter(x=h["mes"].astype(str), y=h["pax_norm"], name="Histórico mensual", mode="lines",
                                 line=dict(color=PAL[s], width=3), fill="tozeroy", fillcolor="rgba(31,111,235,.07)"))
    fig.add_trace(go.Scatter(x=list(serv.index), y=serv[s].astype(float), name="Proyección 2027", mode="lines+markers",
                             line=dict(color="#dc2626", width=3, dash="dash")))
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


def tabla_detalle_mes(detalle, s):
    d = detalle[detalle.servicio == s].copy()
    if d.empty:
        return pd.DataFrame()
    g = d.groupby(["periodo", "mes"]).agg(
        servicios_dia_base=("servicios_dia", "sum"),
        servicios_dia_plan=("servicios_dia_plan", "sum"),
        viajes_operados_base=("viajes_operados_base", "sum"),
        viajes_operados_plan=("viajes_operados_plan", "sum"),
        demanda_base=("demanda_base_mensual", "sum"),
        demanda_proyectada=("afl", "sum"),
        elasticidad_media=("elasticidad", "mean"),
        factor_estacionalidad_medio=("factor_estacionalidad", "mean"),
    ).reset_index().sort_values("mes")
    g["impacto_mes_vs_base"] = g["demanda_proyectada"] - g["demanda_base"]
    g["var_oferta_operada_pct"] = (g["viajes_operados_plan"] / g["viajes_operados_base"].replace(0, pd.NA) - 1) * 100
    g["var_demanda_pct"] = (g["demanda_proyectada"] / g["demanda_base"].replace(0, pd.NA) - 1) * 100
    cols = ["periodo", "servicios_dia_base", "servicios_dia_plan", "viajes_operados_base", "viajes_operados_plan",
            "demanda_base", "demanda_proyectada", "impacto_mes_vs_base", "var_oferta_operada_pct", "var_demanda_pct", "elasticidad_media"]
    return g[cols].round({"servicios_dia_base": 1, "servicios_dia_plan": 1, "viajes_operados_base": 0,
                          "viajes_operados_plan": 0, "demanda_base": 0, "demanda_proyectada": 0,
                          "impacto_mes_vs_base": 0, "var_oferta_operada_pct": 1,
                          "var_demanda_pct": 1, "elasticidad_media": 2})


def render_metodologia():
    st.markdown("### Marco metodológico del modelo")
    st.markdown("""
<div class="method">
<b>Objetivo.</b> Estimar afluencia mensual por servicio para 2027 vinculando explícitamente la oferta programada con la demanda proyectada. El modelo evita asumir que todo servicio adicional genera pasajeros en la misma proporción que la productividad promedio histórica.
<br><br>
<b>Unidad de cálculo.</b> La proyección se calcula por unidad operacional, mes y tipo de día: lunes-viernes, sábado y domingo. El total mensual del servicio se obtiene sumando sus unidades operacionales.
<br><br>
<b>Principio operacional.</b> Cada mes se calcula de forma independiente. Si se modifica la oferta de marzo, cambia marzo y cambia el total anual por suma; no se redistribuyen pasajeros desde o hacia otros meses.
</div>
""", unsafe_allow_html=True)

    st.markdown("#### Fórmulas utilizadas")
    st.latex(r"V_{0,u,m,d}=S_{0,u,m,d}\cdot N_{m,d}\cdot (1-\tau_{u,m,d})")
    st.latex(r"D_{0,u,m,d}=V_{0,u,m,d}\cdot q_{u,m,d}\cdot F_{nivel,s}\cdot F_{est,s,m}")
    st.latex(r"V_{1,u,m,d}=S_{1,u,m,d}\cdot N_{m,d}\cdot (1-\tau_{u,m,d}-c_u)")
    st.latex(r"D_{1,u,m,d}=D_{0,u,m,d}\cdot \left(\frac{V_{1,u,m,d}}{V_{0,u,m,d}}\right)^{\varepsilon_s}")
    st.markdown("""
Donde:
- `S0` es la oferta base vigente y `S1` la oferta editada.
- `N` corresponde a la cantidad de días del tipo respectivo en el mes.
- `τ` es la tasa de supresión histórica.
- `q` es pasajeros promedio por servicio, calibrado con mayo 2026.
- `F_nivel` ajusta el nivel de productividad por servicio.
- `F_est` corrige productividad mensual con el comportamiento histórico 2024, 2025 y 2026.
- `ε` es la elasticidad de demanda respecto de oferta, menor que 1 para representar rendimiento marginal decreciente.
- `c` es una contingencia adicional de supresión definida por el usuario.
""")

    st.markdown("#### Parámetros actuales")
    p1, p2 = st.columns(2)
    with p1:
        st.dataframe(pd.DataFrame([{"servicio": O.NOMBRE[k], "elasticidad_oferta": v} for k, v in O.ELASTICIDAD_OFERTA_SERVICIO.items()]), use_container_width=True)
    with p2:
        st.dataframe(pd.DataFrame([{"servicio": O.NOMBRE[k], "factor_nivel": v, "fuerza_estacionalidad": O.FUERZA_ESTACIONALIDAD.get(k)} for k, v in O.AJUSTE_NIVEL_SERVICIO.items()]), use_container_width=True)

    st.markdown("#### Tratamiento por servicio")
    st.markdown("""
- **Biotren:** se modela separando L1 y L2. El nivel anual base queda en torno a 12,5-12,6 millones, pero cada mes responde a su oferta específica.
- **Laja-Talcahuano:** se corrige la oferta a 8 servicios todos los días; sólo sábados y domingos de enero-febrero usan 10 servicios.
- **Tren Araucanía:** la oferta se edita por tramo. Victoria-Temuco tiene mayor peso marginal que Pitrufquén y Claret.
- **Llanquihue-Puerto Montt:** enero y febrero conservan señal estival 2026; el resto del año se modera con el histórico disponible.
""")

    st.markdown("#### Bibliografía")
    st.markdown("""
- Transportation Research Board. *TCRP Report 95, Chapter 9: Transit Scheduling and Frequency*. Washington, D.C., 2004. https://trb.org/publications/tcrp/tcrp_rpt_95c9.pdf
- Balcombe, R. et al. *The Demand for Public Transport: A Practical Guide*. TRL Report TRL593, 2004. https://www.trl.co.uk/uploads/trl/documents/TRL593%20-%20The%20Demand%20for%20Public%20Transport.pdf
- Paulley, N. et al. *The demand for public transport: The effects of fares, quality of service, income and car ownership*. Transport Policy, 13(4), 295-306, 2006. https://eprints.whiterose.ac.uk/id/eprint/2034/1/ITS23_The_demand_for_public_transport_UPLOADABLE.pdf
- Berrebi, S., Joshi, S. & Watkins, K. *On Ridership and Frequency*. Transportation Research Part A, 2021. https://doi.org/10.48550/arXiv.2002.02493
""")


def render_resumen():
    uni, serv, detalle = O.proyectar_mensual_elastico(params, mdf, return_detalle=True)
    st.markdown("### Resumen 2027")
    st.info("El total anual es la suma de los meses proyectados. No existe redistribución posterior de un total anual fijo.")

    kk = st.columns(4)
    for i, s in enumerate(O.SERVICIOS):
        viajes = O.viajes_anuales(params, units=O.UNIDADES_DE[s])
        om = serv[s].sum() / max(viajes, 1)
        kk[i].metric(O.NOMBRE[s], fmt(serv[s].sum()), f"{fmt(om)} pax/viaje")

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

    st.markdown("#### Proyección mensual 2027")
    st.dataframe(serv, use_container_width=True)

    st.markdown("#### Comportamiento histórico anual observado")
    st.dataframe(hist_anual, use_container_width=True)

    tramos_ta = O.desagregar_tren_araucania_por_tramo(serv["TREN_ARAUCANIA"])
    c1, c2, c3, c4 = st.columns(4)
    c1.download_button("⬇ Resumen por servicio", serv.to_csv().encode(), "proyeccion_2027_resumen_mensual_elastico.csv")
    c2.download_button("⬇ Detalle por unidad", uni.to_csv().encode(), "proyeccion_2027_unidades_mensual_elastico.csv")
    c3.download_button("⬇ Tren Araucanía por tramo", tramos_ta.to_csv().encode(), "proyeccion_2027_tren_araucania_tramos.csv")
    c4.download_button("⬇ Detalle de cálculo", detalle.to_csv(index=False).encode(), "detalle_calculo_mensual_elastico.csv")


def render_servicio(s):
    cf = CONF[s]
    st.markdown(f"### {O.NOMBRE[s]} &nbsp;<span class='badge' style='background:{CONF_C[cf]}'>Confianza {cf}</span>", unsafe_allow_html=True)

    st.markdown("#### Oferta 2027")
    ce = {}
    plan_tramos = None
    if s == "BIOTREN":
        st.info("Biotren se edita por línea. La afluencia mensual queda vinculada al mes editado, sin repartir el total anual.")
        c1, c2 = st.columns(2)
        with c1:
            plan_l1 = editor_oferta("BIOTREN_L1", "Línea 1")
        with c2:
            plan_l2 = editor_oferta("BIOTREN_L2", "Línea 2")
        plan = pd.concat([plan_l1, plan_l2], ignore_index=True)
    elif s == "TREN_ARAUCANIA":
        plan_tramos, plan = editor_tren_araucania()
    else:
        plan = editor_oferta(O.UNIDADES_DE[s][0], O.NOMBRE[s])

    with st.expander("Contingencia adicional sobre supresión histórica"):
        unidades_ce = O.UNIDADES_DE[s]
        cc = st.columns(len(unidades_ce))
        for i, u in enumerate(unidades_ce):
            ce[u] = cc[i].number_input(f"{u} (+% supresión)", 0.0, 30.0, 0.0, 1.0, key=f"ce_{u}") / 100.0

    uni, serv, detalle = O.proyectar_mensual_elastico(params, mdf, plan=plan, contingencia_extra=ce, return_detalle=True)
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
        st.markdown("#### Histórico mensual y proyección")
        grafico_historico_y_proyeccion(s, serv)
    with t:
        st.markdown("#### Proyección mensual 2027")
        out = pd.DataFrame(index=serv.index)
        if s == "BIOTREN":
            out["L1"] = uni.get("BIOTREN_L1")
            out["L2"] = uni.get("BIOTREN_L2")
        elif s == "TREN_ARAUCANIA":
            tr = O.desagregar_tren_araucania_por_tramo(serv[s], plan_tramos=plan_tramos)
            out["Temuco - Victoria"] = tr.get("TA_TEMUCO_VICTORIA")
            out["Temuco - Pitrufquén"] = tr.get("TA_TEMUCO_PITRUFQUEN")
            out["Claret"] = tr.get("TA_CLARET")
        out["Total proyectado"] = serv[s]
        st.dataframe(out, use_container_width=True, height=330)

    st.markdown("#### Detalle mensual del cálculo oferta-demanda")
    st.dataframe(tabla_detalle_mes(detalle, s), use_container_width=True)
    st.caption("La columna impacto_mes_vs_base permite verificar que un cambio de oferta afecta el mes modificado y el total anual por suma.")

    st.markdown("#### Comportamiento mensual histórico por año")
    st.dataframe(tabla_historica_servicio(s), use_container_width=True)

    if s == "CORTO_LAJA":
        st.warning("Oferta base: 8 servicios todos los días; sólo sábados y domingos de enero-febrero tienen 10 servicios.")
    if s == "LLANQUIHUE_PM":
        st.warning("Enero y febrero mantienen una señal estival similar a 2026; no se consideran servicios planificados de fin de semana.")

    st.download_button(f"⬇ Descargar proyección {O.NOMBRE[s]} (CSV)", out.to_csv().encode(),
                       f"proyeccion_2027_{s}.csv", key=f"dl_{s}")


tabs = st.tabs(["📘 Metodología", "📊 Resumen"] + [O.NOMBRE[s] for s in O.SERVICIOS])
with tabs[0]:
    render_metodologia()
with tabs[1]:
    render_resumen()
for i, s in enumerate(O.SERVICIOS):
    with tabs[i + 2]:
        render_servicio(s)
