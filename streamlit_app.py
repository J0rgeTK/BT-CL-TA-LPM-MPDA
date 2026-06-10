"""
streamlit_app.py -- Modelo de afluencia EFE/Fesur 2027.

Versión metodológica mensual-elástica:
- La oferta se edita por servicio, mes y tipo de día.
- La demanda de cada mes se calcula de forma independiente.
- El calendario 2027 incorpora feriados nacionales y reglas operacionales por servicio.
- No se reparte un total anual fijo: el total anual resulta de sumar los 12 meses.
- El cambio de oferta en un mes afecta ese mes y el total anual, no redistribuye el resto del año.
"""
import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

import pipeline_afluencia as P
import oferta as O
import od_biotren_hibrido as OD

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
            '<p>Motor mensual-elástico · feriados 2027 · escenario 2027 actualizado · oferta editable por mes y tipo de día</p></div>', unsafe_allow_html=True)


def fmt(n):
    return f"{int(round(float(n))):,}".replace(",", ".")


def fmt_pct(delta):
    if pd.isna(delta):
        return "s/i"
    return f"{delta:+.1f}%".replace(".", ",")


@st.cache_data(show_spinner=False)
def calcular_od_biotren_cached(periodos, valores):
    serie = pd.Series([float(v) for v in valores], index=list(periodos))
    return OD.distribuir_proyeccion_biotren(serie)


def render_od_biotren(serv):
    st.markdown("#### Distribución OD mensual de afluencia e ingresos")
    st.caption("Módulo espacial complementario: distribuye la afluencia mensual proyectada de Biotren por par origen-destino y tipo de pasajero, preservando el orden original de estaciones.")

    try:
        serie = serv["BIOTREN"].astype(float).copy()
        resultado = calcular_od_biotren_cached(tuple(serie.index.tolist()), tuple(serie.values.tolist()))
        station_order = list(resultado["station_order"])
    except Exception as e:
        st.warning(f"No fue posible calcular la distribución OD de Biotren: {e}")
        return

    with st.expander("Metodología de distribución OD e ingresos", expanded=False):
        st.markdown("""
El módulo OD opera después de la proyección mensual de Biotren. Su función no es proyectar demanda total, sino asignar espacialmente la demanda ya estimada entre pares origen-destino y por tipo de pasajero.

**Flujo de cálculo**

1. Se toma la afluencia mensual proyectada de Biotren.
2. La demanda se segmenta en Normal, Estudiante y Adulto Mayor usando participaciones históricas mensuales por tipo.
3. Para cada tipo se construye una matriz OD base con la estructura histórica mensual observada.
4. Se incorpora un componente gravitacional parcial basado en tarifa y distancia como control de sensibilidad espacial.
5. Se aplica balance IPF/Furness para conservar producciones por origen, atracciones por destino y total mensual por tipo.
6. La matriz de ingresos se obtiene multiplicando viajes OD por la matriz tarifaria 2026 correspondiente.

**Ecuaciones principales**

`Demanda_{p,m} = Demanda_{Biotren,m} × Participación_{p,m}`

`C_{ij,p} = α × Tarifa_normalizada_{ij,p} + β × Distancia_normalizada_{ij}`

`K_{ij,p,m} = w_p × S_{ij,p,m} + (1 - w_p) × G_{ij,p,m}`

`T_{ij,p,m} = IPF(K_{ij,p,m}, O_{i,p,m}, D_{j,p,m})`

`Ingreso_{ij,p,m} = T_{ij,p,m} × Tarifa_{ij,p,2026}`

El componente histórico tiene mayor peso que el gravitacional, porque la matriz OD observada presenta una estructura espacial estable. El componente gravitacional se conserva como ajuste metodológico y análisis de sensibilidad ante tarifa y distancia, sin reemplazar el patrón OD observado.

**Tipos de pasajero utilizados**

- Normal: bloque `T. Monedero`.
- Estudiante: bloque `T. Estudiante`.
- Adulto Mayor: bloque `T. Tercera Edad`.

Las matrices se muestran y exportan con el orden original de estaciones de las matrices fuente. La homologación de nombres se usa sólo para cruzar OD, tarifas y distancias, sin alterar la posición final de filas y columnas.

La estimación de ingresos es preliminar y depende de la cobertura de la matriz tarifaria disponible. En próximas iteraciones puede reemplazarse la segmentación agregada por una matriz mensual-anual más detallada por tipo de tarjeta, permitiendo mejorar ingresos por tipo de pago y preparar una futura estimación de subsidio.
""")

    periodos = list(serie.index)
    meses_nombre = {f"2027-{m:02d}": f"{m:02d} - 2027" for m in range(1, 13)}
    csel1, csel2 = st.columns([1, 1])
    with csel1:
        periodo = st.selectbox("Mes proyectado", periodos, format_func=lambda x: meses_nombre.get(x, x), key="od_biotren_periodo")
    with csel2:
        tipo = st.selectbox("Tipo de pasajero", OD.TIPOS, key="od_biotren_tipo")

    M = resultado["matrices_viajes"][(periodo, tipo)].reindex(index=station_order, columns=station_order).copy(deep=True)
    R = resultado["matrices_ingresos"][(periodo, tipo)].reindex(index=station_order, columns=station_order).copy(deep=True)
    viajes = float(M.to_numpy(dtype=float, copy=True).sum())
    ingresos = float(R.to_numpy(dtype=float, copy=True).sum())
    tarifa_media = ingresos / viajes if viajes > 0 else 0.0
    total_mes = float(serie.loc[periodo])

    km = st.columns(4)
    km[0].metric("Afluencia Biotren mes", fmt(total_mes))
    km[1].metric(f"Viajes {tipo}", fmt(viajes), f"{viajes / total_mes * 100:.1f}%".replace(".", ",") if total_mes else "s/i")
    km[2].metric("Ingreso proyectado", f"$ {fmt(ingresos)}")
    km[3].metric("Tarifa media", f"$ {fmt(tarifa_media)}")

    t1, t2, t3, t4 = st.tabs(["Matriz OD viajes", "Matriz OD ingresos", "Resumen y controles", "Descargas"])
    with t1:
        st.dataframe(M.round(0).astype(int).copy(deep=True), use_container_width=True, height=560)
    with t2:
        st.dataframe(R.round(0).astype(int).copy(deep=True), use_container_width=True, height=560)
    with t3:
        resumen_mes = resultado["resumen"][resultado["resumen"]["periodo"].eq(periodo)].copy(deep=True)
        st.markdown("**Resumen del mes seleccionado por tipo de pasajero**")
        st.dataframe(resumen_mes, use_container_width=True, height=170)
        st.markdown("**Validación del enfoque híbrido con meses observados recientes**")
        try:
            st.dataframe(OD.validar_hibrido_2026(), use_container_width=True, height=230)
        except Exception as e:
            st.info(f"No fue posible cargar la validación OD: {e}")
        try:
            cobertura = pd.read_csv(OD.OD_OUT / "validacion_cobertura_tarifa_distancia.csv")
            st.markdown("**Cobertura de tarifa y distancia**")
            st.dataframe(cobertura, use_container_width=True, height=140)
        except Exception:
            pass
    with t4:
        v_csv = M.to_csv().encode("utf-8-sig")
        r_csv = R.to_csv().encode("utf-8-sig")
        c1, c2, c3, c4 = st.columns(4)
        c1.download_button("⬇ Matriz viajes seleccionada", v_csv, f"OD_viajes_{periodo}_{tipo}.csv", key=f"dl_od_v_{periodo}_{tipo}")
        c2.download_button("⬇ Matriz ingresos seleccionada", r_csv, f"OD_ingresos_{periodo}_{tipo}.csv", key=f"dl_od_i_{periodo}_{tipo}")
        c3.download_button("⬇ Viajes OD 2027 long", resultado["viajes_long"].to_csv(index=False).encode("utf-8-sig"), "od_2027_viajes_por_tipo_long.csv", key="dl_od_v_long")
        c4.download_button("⬇ Ingresos OD 2027 long", resultado["ingresos_long"].to_csv(index=False).encode("utf-8-sig"), "od_2027_ingresos_por_tipo_long.csv", key="dl_od_i_long")

def hist_valor(servicio, anio, meses=None):
    h = hist[hist.servicio == servicio].copy()
    h = h[h.anio.astype(int) == int(anio)]
    if meses is not None:
        h = h[h.mes.astype(int).isin([int(m) for m in meses])]
    if h.empty:
        return None
    return float(h["afluencia_mensual_normalizada"].sum())


def hist_resumen(servicio, anio):
    h = hist_anual[(hist_anual.servicio == servicio) & (hist_anual.anio.astype(int) == int(anio))].copy()
    if h.empty:
        return None
    r = h.iloc[0]
    return {
        "total": float(r["afluencia_observada_normalizada"]),
        "meses": int(r["meses_observados"]),
        "primer_mes": int(r["primer_mes"]),
        "ultimo_mes": int(r["ultimo_mes"]),
    }


def var_pct(valor, base):
    if base is None or base == 0 or pd.isna(base):
        return None
    return (float(valor) / float(base) - 1.0) * 100.0


def resumen_validacion_servicio(s, serv, uni, detalle):
    total = float(serv[s].sum())
    viajes = float(detalle[detalle.servicio == s]["viajes_operados_plan"].sum())
    pax_viaje = total / viajes if viajes > 0 else 0.0
    meses = serv[s].astype(float)
    rows = [
        {"Indicador": "Proyección anual 2027", "Valor": fmt(total)},
        {"Indicador": "Viajes operados proyectados", "Valor": fmt(viajes)},
        {"Indicador": "Pasajeros por viaje proyectado", "Valor": fmt(pax_viaje)},
        {"Indicador": "Mes de mayor afluencia", "Valor": f"{meses.idxmax()} ({fmt(meses.max())})"},
        {"Indicador": "Mes de menor afluencia", "Valor": f"{meses.idxmin()} ({fmt(meses.min())})"},
    ]
    for y in [2024, 2025]:
        hs = hist_resumen(s, y)
        if hs is not None:
            if hs["meses"] >= 12:
                rows.append({"Indicador": f"Comparación anual con {y}", "Valor": f"{fmt(hs['total'])} histórico; variación {fmt_pct(var_pct(total, hs['total']))}"})
            else:
                rows.append({"Indicador": f"Histórico {y} observado", "Valor": f"{fmt(hs['total'])} entre meses {hs['primer_mes']:02d}-{hs['ultimo_mes']:02d}; no comparable como año completo"})
    h26 = hist_valor(s, 2026)
    if h26 is not None:
        meses_obs = sorted(hist[(hist.servicio == s) & (hist.anio.astype(int) == 2026)]["mes"].astype(int).unique().tolist())
        if meses_obs:
            proy_mismos = float(serv.loc[[f"2027-{m:02d}" for m in meses_obs], s].sum())
            rows.append({"Indicador": f"Comparación con 2026 observado ({min(meses_obs):02d}-{max(meses_obs):02d})", "Valor": f"{fmt(h26)} histórico parcial; 2027 mismos meses {fmt(proy_mismos)}; variación {fmt_pct(var_pct(proy_mismos, h26))}"})
    return pd.DataFrame(rows)


def render_justificacion_servicio(s, serv, uni, detalle):
    total = float(serv[s].sum())
    det_s = detalle[detalle.servicio == s].copy()
    viajes = float(det_s["viajes_operados_plan"].sum())
    pax_viaje = total / viajes if viajes > 0 else 0.0
    meses = serv[s].astype(float)
    h2024 = hist_valor(s, 2024)
    h2025 = hist_valor(s, 2025)
    h2026 = hist_valor(s, 2026)

    with st.expander("Justificación metodológica del resultado proyectado", expanded=True):
        st.markdown("""
Esta sección explica por qué el resultado proyectado es coherente con los antecedentes históricos, la oferta operacional 2027 y los supuestos particulares del servicio. La validación se realiza contra los valores efectivamente calculados por el modelo vigente, no contra una referencia externa visible.
""")
        st.dataframe(resumen_validacion_servicio(s, serv, uni, detalle), use_container_width=True, hide_index=True)

        if s == "BIOTREN":
            l1 = float(uni["BIOTREN_L1"].sum()) if "BIOTREN_L1" in uni.columns else 0.0
            l2 = float(uni["BIOTREN_L2"].sum()) if "BIOTREN_L2" in uni.columns else 0.0
            janmay_2027 = float(serv.loc[["2027-01", "2027-02", "2027-03", "2027-04", "2027-05"], s].sum())
            st.markdown(f"""
**Lectura del resultado.** La proyección anual de Biotren alcanza **{fmt(total)} pasajeros**, compuesta por **{fmt(l1)}** en L1 y **{fmt(l2)}** en L2. El resultado se sustenta en una mejora de oferta operacional, pero con respuesta de demanda parcial: L1 opera con 48 servicios de lunes a viernes durante todo 2027 y L2 pasa de 106 a 109 servicios de lunes a viernes desde mayo. Los feriados nacionales se descuentan como días sin operación.

**Coherencia histórica.** El resultado queda {fmt_pct(var_pct(total, h2024)) if h2024 else 's/i'} respecto de 2024 y {fmt_pct(var_pct(total, h2025)) if h2025 else 's/i'} respecto de 2025. Para los meses observados del año reciente, la proyección 2027 suma **{fmt(janmay_2027)} pasajeros**, comparada con **{fmt(h2026) if h2026 else 's/i'}** del mismo bloque mensual. Esta magnitud es consistente con un escenario de crecimiento conservador y con la oferta considerada.

**Perfil mensual.** El bloque marzo-abril se regulariza para evitar una concentración artificial en abril. La suma conjunta se conserva y la distribución mensual queda prácticamente nivelada, con una leve mayor participación de marzo según la evidencia histórica disponible.
""")
        elif s == "CORTO_LAJA":
            st.markdown(f"""
**Lectura del resultado.** La proyección anual de Laja-Talcahuano alcanza **{fmt(total)} pasajeros**, asociada a una recuperación operacional moderada. El escenario considera 8 servicios diarios como base, con excepción de sábados y domingos de enero-febrero, donde se aplican 10 servicios. Los feriados nacionales operan con oferta de fin de semana.

**Coherencia histórica.** El resultado queda {fmt_pct(var_pct(total, h2024)) if h2024 else 's/i'} respecto de 2024 y {fmt_pct(var_pct(total, h2025)) if h2025 else 's/i'} respecto de 2025. Esta posición es metodológicamente consistente: incorpora recuperación frente a un escenario de menor confiabilidad, pero no replica completamente el año de mejor desempeño disponible.

**Supuesto técnico principal.** La supresión base se acota para representar una mejora de confiabilidad, manteniendo elasticidad parcial de oferta y mayor peso de la estacionalidad histórica de mejor desempeño. Con ello, el modelo evita prolongar afectaciones operacionales recientes como si fueran permanentes.
""")
        elif s == "TREN_ARAUCANIA":
            tramos = {col: float(uni[col].sum()) for col in ["TA_TEMUCO_VICTORIA", "TA_TEMUCO_PITRUFQUEN", "TA_CLARET"] if col in uni.columns}
            st.markdown(f"""
**Lectura del resultado.** La proyección anual de Tren Araucanía alcanza **{fmt(total)} pasajeros**. La demanda se calcula por tipo de servicio, no con una proporción fija agregada. El tramo Temuco-Victoria tiene mayor capacidad de generación de demanda que Pitrufquén-Temuco y Claret, por lo que el aumento a 15 servicios de lunes a viernes se modela con mayor peso relativo, pero con elasticidad menor que 1 para evitar una respuesta proporcional excesiva.

**Descomposición anual.** Temuco-Victoria proyecta **{fmt(tramos.get('TA_TEMUCO_VICTORIA', 0))}**, Temuco-Pitrufquén **{fmt(tramos.get('TA_TEMUCO_PITRUFQUEN', 0))}** y Claret **{fmt(tramos.get('TA_CLARET', 0))}** pasajeros. Claret se restringe a marzo-diciembre por su carácter escolar, por lo que enero y febrero no generan demanda en ese componente.

**Coherencia histórica.** El resultado es superior al histórico anual 2025, pero se modera respecto de una extrapolación directa del aumento de oferta. La calibración hacia aproximadamente 950 mil pasajeros evita que el incremento Victoria-Temuco sobredimensione todo el servicio, especialmente porque Pitrufquén y Claret no tienen la misma productividad marginal.
""")
        elif s == "LLANQUIHUE_PM":
            ene_feb = float(serv.loc[["2027-01", "2027-02"], s].sum())
            st.markdown(f"""
**Lectura del resultado.** La proyección anual de Llanquihue-Puerto Montt alcanza **{fmt(total)} pasajeros**, con **{fmt(ene_feb)}** pasajeros concentrados en enero-febrero. El modelo conserva una señal estival alta, coherente con 2026, y mantiene oferta sólo de lunes a viernes.

**Coherencia operacional.** La proyección descuenta feriados nacionales como días sin operación y no incorpora servicios de fin de semana planificados. Por ello, aun cuando enero y febrero son fuertes por estacionalidad, el nivel anual queda contenido por la ausencia de operación sábado-domingo y feriados.

**Criterio metodológico.** El comportamiento 2026 tiene mayor peso en este servicio porque el histórico disponible es más corto. La proyección no extrapola linealmente enero-febrero al resto del año, sino que combina estacionalidad observada, calendario operacional 2027 y productividad por servicio.
""")

        st.markdown("**Componentes que explican el resultado mensual.**")
        tabla_comp = tabla_detalle_mes(detalle, s)
        if not tabla_comp.empty:
            st.dataframe(tabla_comp[["periodo", "viajes_operados_plan", "demanda_proyectada", "var_oferta_operada_pct", "var_demanda_pct", "elasticidad_media"]], use_container_width=True, hide_index=True)
        st.caption("La elasticidad menor que 1 implica rendimiento marginal decreciente: un aumento de oferta eleva la demanda, pero no en la misma proporción que los servicios adicionales.")


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
    st.info("La oferta se edita por tipo de servicio. Claret se considera servicio escolar y sólo opera entre marzo y diciembre; enero y febrero se fuerzan a cero.")
    base_tramos = O.oferta_tren_araucania_tramos_df(mensual=True)
    cols = st.columns(3)
    planes = []
    for i, unit in enumerate(O.TA_TRAMOS):
        with cols[i]:
            planes.append(editor_oferta(unit, O.TA_TRAMO_NOMBRE[unit], base_df=base_tramos))
    plan_tramos = pd.concat(planes, ignore_index=True)
    plan_tramos.loc[(plan_tramos.unit == "TA_CLARET") & (plan_tramos.mes.isin([1, 2])), "servicios_dia"] = 0.0
    with st.expander("Distribución histórica usada por tipo de servicio"):
        dist = O.perfil_distribucion_tren_araucania_por_tramo()
        piv = dist.pivot(index="mes", columns="unit", values="participacion_demanda_historica")
        piv = piv.rename(columns=O.TA_TRAMO_NOMBRE)
        st.dataframe((piv * 100).round(1), use_container_width=True)
        st.caption("Participación mensual ponderada con TA-Dist.xlsx. Claret queda en 0% para enero y febrero. La respuesta ante cambios de oferta se calcula tramo por tramo, no como redistribución fija 13/87.")
    return plan_tramos, plan_tramos


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





def tabla_calendario_servicio(s):
    cal = O.calendario_operacional_resumen(2027).copy()
    if s == "BIOTREN":
        units = ["BIOTREN_L1", "BIOTREN_L2"]
    elif s == "TREN_ARAUCANIA":
        units = O.TA_TRAMOS
    else:
        units = O.UNIDADES_DE[s]
    cal = cal[cal["unit"].isin(units)].copy()
    cal["mes"] = cal["mes"].map(lambda x: f"{int(x):02d}")
    return cal.sort_values(["unit", "mes", "dt"])


def tabla_feriados_2027():
    f = O.feriados_chile(2027).copy()
    if f.empty:
        return f
    f["fecha"] = f["fecha"].dt.strftime("%Y-%m-%d")
    return f.rename(columns={"dt_calendario": "tipo_dia_calendario"})


def render_ecuacion_servicio(s):
    """Muestra la ecuación específica usada por el motor para el servicio seleccionado."""
    e = O.ELASTICIDAD_OFERTA_SERVICIO.get(s, 0.45)
    fn = O.AJUSTE_NIVEL_SERVICIO.get(s, 1.0)
    fe = O.FUERZA_ESTACIONALIDAD.get(s, 0.5)
    st.markdown("#### Ecuación específica de proyección")

    if s == "BIOTREN":
        latex = r"""
        D_{\mathrm{BT},m} =
        \sum_{u \in \{L1,L2\}}\sum_{d \in \{LV,Sab,Dom\}}
        \left[
        S_{1,u,m,d}\,N^{op}_{u,m,d}\,(1-\tau_{u,m,d}-c_u)\,q_{u,m,d}\,FN\,F_{est,\mathrm{BT},m}
        \left(\frac{V_{1,u,m,d}}{V_{0,u,m,d}}\right)^{EPS}
        \right]
        """
        st.latex(latex.replace("FN", f"{fn:.3f}").replace("EPS", f"{e:.2f}"))
        st.caption(f"Biotren usa días operacionales sin feriados nacionales, elasticidad de oferta {e:.2f}, factor de nivel {fn:.3f} y fuerza estacional {fe:.2f}. La suma operacional se realiza sobre L1 y L2; Laja-Talcahuano se mantiene separado para evitar doble conteo. El perfil mensual incorpora una regularización estacional del bloque marzo-abril para evitar peaks no respaldados por el comportamiento observado.")

    elif s == "CORTO_LAJA":
        latex = r"""
        D_{\mathrm{LT},m} =
        \sum_{d \in \{LV,Sab,Dom\}}
        \left[
        S_{1,\mathrm{LT},m,d}\,N^{op}_{\mathrm{LT},m,d}\,(1-\tau^*_{\mathrm{LT},m,d}-c)\,q_{\mathrm{LT},m,d}\,FN\,F_{est,\mathrm{LT},m}
        \left(\frac{V_{1,\mathrm{LT},m,d}}{V_{0,\mathrm{LT},m,d}}\right)^{EPS}
        \right]
        """
        st.latex(latex.replace("FN", f"{fn:.3f}").replace("EPS", f"{e:.2f}"))
        st.latex(r"\tau^*_{\mathrm{LT},m,d}=\min(\tau_{\mathrm{LT},m,d},0.01)")
        st.caption(f"Laja-Talcahuano opera feriados con oferta de fin de semana e incorpora recuperación de confiabilidad: supresión base acotada a 1%, mayor peso del patrón histórico de mejor desempeño y factor de recuperación {fn:.3f}. Esto permite representar una recuperación operacional parcial sin asumir el máximo histórico como meta directa.")

    elif s == "TREN_ARAUCANIA":
        st.latex(r"""
        D_{\mathrm{TA},m}=\sum_{r\in\{VT,PT,CL\}}D_{r,m}
        """)
        st.latex(r"""
        D_{r,m}=D^{base}_{\mathrm{TA},m}\cdot\alpha_{r,m}^{hist}\cdot
        \left(\frac{V_{1,r,m}}{V_{0,r,m}}\right)^{\varepsilon_r}
        """)
        st.latex(r"""
        V_{r,m}=\sum_{d\in\{LV,Sab,Dom\}}S_{r,m,d}\cdot N^{op}_{r,m,d}\cdot(1-\tau_{\mathrm{TA},m,d}-c)
        """)
        st.latex(r"\alpha_{CL,m}=0\quad\text{para }m\in\{enero,febrero\}")
        st.caption("Tren Araucanía no opera feriados nacionales en el escenario base y usa distribución mensual observada por tipo de servicio. La oferta se edita por tramo y cada tramo tiene elasticidad diferenciada: Victoria-Temuco 0,46; Pitrufquén-Temuco 0,28; Claret 0,12. Así, un aumento en Victoria-Temuco genera mayor efecto que un aumento equivalente en Pitrufquén o Claret.")

    elif s == "LLANQUIHUE_PM":
        latex = r"""
        D_{\mathrm{LLPM},m} =
        \sum_{d \in \{LV,Sab,Dom\}}
        \left[
        S_{1,\mathrm{LLPM},m,d}\,N^{op}_{\mathrm{LLPM},m,d}\,(1-\tau_{\mathrm{LLPM},m,d}-c)\,q_{\mathrm{LLPM},m,d}\,FN\,F_{est,\mathrm{LLPM},m}
        \left(\frac{V_{1,\mathrm{LLPM},m,d}}{V_{0,\mathrm{LLPM},m,d}}\right)^{EPS}
        \right]
        """
        st.latex(latex.replace("FN", f"{fn:.3f}").replace("EPS", f"{e:.2f}"))
        st.caption(f"Llanquihue-Puerto Montt no opera feriados nacionales en el escenario base y conserva una señal estival en enero-febrero. Se aplica elasticidad de oferta {e:.2f}; los días sábado y domingo quedan en cero salvo modificación explícita de oferta.")

def render_metodologia():
    st.markdown("### Marco metodológico del modelo")
    st.markdown("""
<div class="method">
<b>Propósito.</b> El modelo estima la afluencia mensual proyectada por servicio para 2027. Para Biotren incorpora además una capa espacial OD por tipo de pasajero y una estimación preliminar de ingresos por par origen-destino.
<br><br>
<b>Separación metodológica.</b> El programa distingue tres componentes: (i) modelo temporal de afluencia mensual, (ii) módulo espacial OD para Biotren y (iii) módulo preliminar de ingresos OD. El módulo OD no reemplaza la proyección temporal: distribuye espacialmente la demanda mensual que ya fue estimada.
<br><br>
<b>Principio de cálculo.</b> Cada mes se calcula de forma independiente. Si se modifica la oferta de un mes, cambia la afluencia de ese mes y el total anual cambia por suma; no se redistribuye un total anual fijo.
</div>
""", unsafe_allow_html=True)

    with st.expander("1. Modelo temporal de afluencia mensual", expanded=True):
        st.markdown("""
El cálculo se realiza por unidad operacional, mes y tipo de día: lunes-viernes, sábado y domingo. La demanda base se obtiene combinando viajes operados esperados, productividad por viaje, factores de nivel, estacionalidad mensual y elasticidad parcial frente a variaciones de oferta.
""")
        st.latex(r"V_{0,u,m,d}=S_{0,u,m,d}\cdot N^{op}_{u,m,d}\cdot (1-\tau_{u,m,d})")
        st.latex(r"D_{0,u,m,d}=V_{0,u,m,d}\cdot q_{u,m,d}\cdot F_{nivel,s}\cdot F_{est,s,m}")
        st.latex(r"V_{1,u,m,d}=S_{1,u,m,d}\cdot N^{op}_{u,m,d}\cdot (1-\tau_{u,m,d}-c_u)")
        st.latex(r"D_{1,u,m,d}=D_{0,u,m,d}\cdot \left(\frac{V_{1,u,m,d}}{V_{0,u,m,d}}\right)^{\varepsilon_s}")
        st.markdown("""
- `S0` corresponde a la oferta base del escenario.
- `S1` corresponde a la oferta editada en la aplicación.
- `N_op` corresponde a días operacionales efectivos, después de aplicar feriados y reglas por servicio.
- `τ` representa la supresión histórica incorporada al cálculo.
- `q` representa la productividad media por servicio, construida a partir de los datos históricos disponibles.
- `F_nivel` ajusta el nivel general del servicio.
- `F_est` incorpora el comportamiento mensual observado.
- `ε` es la elasticidad de demanda respecto de oferta; al ser menor que 1 evita asumir que más servicios producen demanda proporcional.
- `c` es una contingencia adicional de supresión definida por el usuario.
""")

    with st.expander("2. Calendario operacional y feriados", expanded=False):
        st.info("Para Biotren, Tren Araucanía y Llanquihue-Puerto Montt, los feriados nacionales tienen oferta efectiva cero. Para Laja-Talcahuano, los feriados operan con oferta de fin de semana; si el feriado cae lunes-viernes se imputa como domingo operacional.")
        st.dataframe(tabla_feriados_2027(), use_container_width=True, height=240)
        st.markdown("**Resumen de días operacionales por unidad, mes y tipo de día**")
        st.dataframe(O.calendario_operacional_resumen(2027), use_container_width=True, height=280)

    with st.expander("3. Parámetros del modelo", expanded=False):
        p1, p2 = st.columns(2)
        with p1:
            st.dataframe(pd.DataFrame([{"servicio": O.NOMBRE[k], "elasticidad_oferta": v} for k, v in O.ELASTICIDAD_OFERTA_SERVICIO.items()]), use_container_width=True)
        with p2:
            st.dataframe(pd.DataFrame([{"servicio": O.NOMBRE[k], "factor_nivel": v, "fuerza_estacionalidad": O.FUERZA_ESTACIONALIDAD.get(k)} for k, v in O.AJUSTE_NIVEL_SERVICIO.items()]), use_container_width=True)
        st.markdown("**Parámetros por tramo de Tren Araucanía**")
        st.dataframe(pd.DataFrame([
            {"tramo": O.TA_TRAMO_NOMBRE[k], "elasticidad_tramo": v, "restriccion": "Marzo-diciembre" if k == "TA_CLARET" else "Todo el año"}
            for k, v in O.TA_TRAMO_ELASTICIDAD.items()
        ]), use_container_width=True)

    with st.expander("4. Tratamiento por servicio", expanded=False):
        st.markdown("""
- **Biotren:** se modela separando L1 y L2. La oferta se edita por línea, mes y tipo de día. La curva mensual se apoya en comportamiento histórico, calendario operacional, feriados y respuesta parcial a cambios de oferta. Laja-Talcahuano se mantiene como servicio separado para evitar doble conteo.
- **Laja-Talcahuano:** se calcula como servicio propio, con regla especial de operación en feriados y una hipótesis de recuperación de confiabilidad. La oferta base considera 8 servicios diarios, salvo fines de semana de enero y febrero con 10 servicios.
- **Tren Araucanía:** se calcula por tipo de servicio: Temuco-Victoria, Temuco-Pitrufquén y Claret. Cada tramo tiene elasticidad diferenciada y Claret se restringe a meses lectivos.
- **Llanquihue-Puerto Montt:** se modela con operación de lunes a viernes, sin fines de semana ni feriados nacionales en el escenario base. Enero y febrero conservan una señal estival dentro del perfil mensual.
""")

    with st.expander("5. Módulo OD híbrido de Biotren", expanded=False):
        st.markdown("""
El módulo OD distribuye la demanda mensual proyectada de Biotren entre pares origen-destino y por tipo de pasajero. Su objetivo es generar una salida espacial trazable, no reemplazar el modelo temporal.

**Flujo metodológico**

`Proyección mensual Biotren → segmentación por tipo de pasajero → matriz OD histórica mensual → ajuste gravitacional parcial → balance IPF/Furness → matriz OD proyectada → ingresos OD preliminares`

**Fórmulas**

`Demanda_{p,m} = Demanda_{Biotren,m} × Participación_{p,m}`

`C_{ij,p} = α × Tarifa_normalizada_{ij,p} + β × Distancia_normalizada_{ij}`

`K_{ij,p,m} = w_p × S_{ij,p,m} + (1 - w_p) × G_{ij,p,m}`

`T_{ij,p,m} = IPF(K_{ij,p,m}, O_{i,p,m}, D_{j,p,m})`

`Ingreso_{ij,p,m} = T_{ij,p,m} × Tarifa_{ij,p,2026}`

La matriz histórica mensual por tipo es el componente principal, mientras que el gravitacional se usa como ajuste parcial de sensibilidad espacial. Las matrices se exportan manteniendo el orden original de estaciones.
""")

    with st.expander("6. Validaciones, limitaciones y próximos pasos", expanded=False):
        st.markdown("""
**Validaciones incorporadas**
- Consistencia entre totales mensuales proyectados y matrices OD por tipo.
- Cobertura de tarifas y distancias para pares OD con viajes proyectados.
- Conservación del orden original de estaciones.
- Sensibilidad de la demanda al cambio de oferta mensual.
- Aplicación de feriados según regla operacional por servicio.
- Generación de salidas CSV y Excel.

**Limitaciones**
- El modelo no es causal completo; representa una proyección operacional y espacial condicionada por los datos disponibles.
- Tarifa y distancia no capturan todos los determinantes de movilidad.
- Los ingresos OD son preliminares si no existe una matriz tarifaria completamente desagregada por tipo de tarjeta.
- El subsidio no está incorporado en esta versión.
- Variables como tiempos de viaje, capacidad, atrasos, cancelaciones y contingencias deben incorporarse desde bases operacionales complementarias.

**Próximos pasos**
- Construir matrices OD mensuales-anuales por tipo de tarjeta.
- Mejorar ingresos por tipo de pago y descuento.
- Incorporar estimación de subsidio.
- Agregar tiempos de viaje, capacidad y ocupación.
- Validar resultados con datos reales futuros.
""")

    st.markdown("#### Bibliografía")
    st.markdown("""
- Transportation Research Board. *TCRP Report 95, Chapter 9: Transit Scheduling and Frequency*. Washington, D.C., 2004. https://trb.org/publications/tcrp/tcrp_rpt_95c9.pdf
- Balcombe, R. et al. *The Demand for Public Transport: A Practical Guide*. TRL Report TRL593, 2004. https://www.trl.co.uk/uploads/trl/documents/TRL593%20-%20The%20Demand%20for%20Public%20Transport.pdf
- Paulley, N. et al. *The demand for public transport: The effects of fares, quality of service, income and car ownership*. Transport Policy, 13(4), 295-306, 2006. https://eprints.whiterose.ac.uk/id/eprint/2034/1/ITS23_The_demand_for_public_transport_UPLOADABLE.pdf
- Berrebi, S., Joshi, S. & Watkins, K. *On Ridership and Frequency*. Transportation Research Part A, 2021. https://doi.org/10.48550/arXiv.2002.02493
- Feriados de Chile. *Feriados de Chile — Año 2027*. Fuente basada en Biblioteca del Congreso Nacional. https://www.feriados.cl/2027.htm
""")

def render_resumen():
    uni, serv, detalle = O.proyectar_mensual_elastico(params, mdf, return_detalle=True)
    st.markdown("### Resumen 2027")
    st.info("El total anual es la suma de los meses proyectados. No existe redistribución posterior de un total anual fijo.")

    kk = st.columns(4)
    for i, s in enumerate(O.SERVICIOS):
        viajes = detalle[detalle.servicio == s]["viajes_operados_plan"].sum()
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

    st.markdown("#### Calendario operacional 2027 aplicado")
    st.dataframe(O.calendario_operacional_resumen(2027), use_container_width=True, height=260)

    st.markdown("#### Comportamiento histórico anual observado")
    st.dataframe(hist_anual, use_container_width=True)

    tramos_ta = uni[[c for c in uni.columns if str(c).startswith("TA_")]].copy()
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
        st.info("Biotren se edita por línea. L1 considera 48 servicios L-V durante todo 2027; L2 considera 106 servicios L-V entre enero-abril y 109 desde mayo. La afluencia mensual queda vinculada al mes editado, sin repartir un total anual fijo.")
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
    viajes = detalle[detalle.servicio == s]["viajes_operados_plan"].sum()
    ocup_proy = serv[s].dropna().sum() / max(viajes, 1)
    pk = serv[s].astype(float).idxmax()

    k = st.columns(4)
    k[0].metric("Total anual 2027", fmt(serv[s].dropna().sum()))
    k[1].metric("Pax/viaje proyectado", fmt(ocup_proy))
    k[2].metric("Mes peak", pk, fmt(serv[s].max()))
    k[3].metric("Mes menor", serv[s].astype(float).idxmin(), fmt(serv[s].min()))

    render_justificacion_servicio(s, serv, uni, detalle)
    render_ecuacion_servicio(s)

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
            out["Temuco - Victoria"] = uni.get("TA_TEMUCO_VICTORIA")
            out["Temuco - Pitrufquén"] = uni.get("TA_TEMUCO_PITRUFQUEN")
            out["Claret"] = uni.get("TA_CLARET")
        out["Total proyectado"] = serv[s]
        st.dataframe(out, use_container_width=True, height=330)

    st.markdown("#### Detalle mensual del cálculo oferta-demanda")
    st.dataframe(tabla_detalle_mes(detalle, s), use_container_width=True)

    with st.expander("Calendario operacional aplicado al servicio"):
        st.dataframe(tabla_calendario_servicio(s), use_container_width=True)
    st.caption("La columna impacto_mes_vs_base permite verificar que un cambio de oferta afecta el mes modificado y que el total anual resulta de la suma mensual.")

    st.markdown("#### Comportamiento mensual histórico por año")
    st.dataframe(tabla_historica_servicio(s), use_container_width=True)

    if s == "CORTO_LAJA":
        st.warning("Oferta base: 8 servicios todos los días; sólo sábados y domingos de enero-febrero tienen 10 servicios. El escenario incorpora recuperación parcial de confiabilidad, supresión base acotada y mayor peso del patrón histórico de mejor desempeño.")
    if s == "TREN_ARAUCANIA":
        st.warning("Claret se considera servicio escolar: enero y febrero quedan sin oferta ni demanda proyectada para este tipo de servicio. Las modificaciones de oferta se evalúan por tramo con elasticidad diferenciada.")
    if s == "LLANQUIHUE_PM":
        st.warning("Enero y febrero mantienen una señal estival dentro del perfil mensual; no se consideran servicios planificados de fin de semana.")

    if s == "BIOTREN":
        render_od_biotren(serv)

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
