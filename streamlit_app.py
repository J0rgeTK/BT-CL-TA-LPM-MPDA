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
import backtesting as BT
import incertidumbre as INC

st.set_page_config(page_title="Afluencia EFE/Fesur 2027", layout="wide", page_icon="🚆")

PAL = {"BIOTREN": "#1f6feb", "CORTO_LAJA": "#0e9f6e", "TREN_ARAUCANIA": "#d97706", "LLANQUIHUE_PM": "#9333ea"}
CONF = {"BIOTREN": "ALTA", "CORTO_LAJA": "ALTA", "TREN_ARAUCANIA": "MEDIA", "LLANQUIHUE_PM": "BAJA"}
CONF_C = {"ALTA": "#0e9f6e", "MEDIA": "#d97706", "BAJA": "#dc2626"}
DATA = os.path.join(os.path.dirname(__file__), "data")

REFERENCIAS_CIERRE_2026 = os.path.join(DATA, "referencias_cierre_2026")
REF_SERVICIO_TO_MODELO = {
    "Biotren": "BIOTREN",
    "Laja Talcahuano": "CORTO_LAJA",
    "Tren Araucanía": "TREN_ARAUCANIA",
}
REF_TIPO_LABEL = {
    "historico_observado": "Histórico observado",
    "cierre_2026_estimado": "Cierre 2026 estimado",
    "proyeccion_2027_modelo": "Proyección 2027 modelo",
}
REF_TIPO_COLOR = {
    "Histórico observado": "#1f6feb",
    "Cierre 2026 estimado": "#d97706",
    "Proyección 2027 modelo": "#dc2626",
}

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
  .bt-panel { background:#fff; border:1px solid #e6ebf2; border-radius:16px; padding:16px 18px; margin:.55rem 0 1rem 0; box-shadow:0 2px 10px rgba(15,39,64,.05); }
  .bt-panel h4 { margin:.1rem 0 .35rem 0; }
  .bt-note { color:#5b6b7d; font-size:.92rem; margin:.1rem 0 .45rem 0; }
  .bt-chip { display:inline-block; border-radius:999px; padding:4px 10px; margin:2px 4px 2px 0; font-size:.78rem; font-weight:700; background:#eef4ff; color:#1f4e79; }
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
            '<p>Motor mensual-elástico · feriados 2027 · escenario 2027 recalibrado · oferta editable por mes y tipo de día</p></div>', unsafe_allow_html=True)




@st.cache_data
def cargar_referencias_cierre_2026():
    mensual_path = os.path.join(REFERENCIAS_CIERRE_2026, "afluencia_historica_cierre_2026_long.csv")
    anual_path = os.path.join(REFERENCIAS_CIERRE_2026, "afluencia_historica_cierre_2026_resumen_anual.csv")
    mensual = pd.read_csv(mensual_path)
    anual = pd.read_csv(anual_path)
    mensual["servicio_modelo"] = mensual["servicio"].map(REF_SERVICIO_TO_MODELO)
    anual["servicio_modelo"] = anual["servicio"].map(REF_SERVICIO_TO_MODELO)
    mensual["tipo_dato_label"] = mensual["tipo_dato"].map(REF_TIPO_LABEL)
    anual["tipo_dato_label"] = anual["tipo_dato"].map(REF_TIPO_LABEL)
    mensual["periodo"] = mensual["anio"].astype(int).astype(str) + "-" + mensual["mes_num"].astype(int).astype(str).str.zfill(2)
    return mensual, anual


def construir_referencia_anual_visual(serv):
    _, anual = cargar_referencias_cierre_2026()
    proy = pd.DataFrame([
        {
            "servicio": next(k for k, v in REF_SERVICIO_TO_MODELO.items() if v == servicio),
            "servicio_modelo": servicio,
            "anio": 2027,
            "tipo_dato": "proyeccion_2027_modelo",
            "tipo_dato_label": REF_TIPO_LABEL["proyeccion_2027_modelo"],
            "afluencia_anual": float(serv[servicio].sum()),
        }
        for servicio in REF_SERVICIO_TO_MODELO.values()
    ])
    base = anual.copy()
    base = base[base["servicio_modelo"].isin(REF_SERVICIO_TO_MODELO.values())]
    return pd.concat([base, proy], ignore_index=True, sort=False)


def construir_referencia_mensual_visual(serv):
    mensual, _ = cargar_referencias_cierre_2026()
    proy_rows = []
    for servicio in REF_SERVICIO_TO_MODELO.values():
        nombre_ref = next(k for k, v in REF_SERVICIO_TO_MODELO.items() if v == servicio)
        for periodo, valor in serv[servicio].astype(float).items():
            proy_rows.append({
                "servicio": nombre_ref,
                "servicio_modelo": servicio,
                "anio": 2027,
                "mes_num": int(str(periodo)[5:7]),
                "mes": str(periodo)[5:7],
                "periodo": periodo,
                "afluencia": float(valor),
                "tipo_dato": "proyeccion_2027_modelo",
                "tipo_dato_label": REF_TIPO_LABEL["proyeccion_2027_modelo"],
                "fuente": "Modelo operacional 2027 vigente",
            })
    base = mensual[mensual["servicio_modelo"].isin(REF_SERVICIO_TO_MODELO.values())].copy()
    return pd.concat([base, pd.DataFrame(proy_rows)], ignore_index=True, sort=False)

def fmt(n):
    return f"{int(round(float(n))):,}".replace(",", ".")


def fmt_mm(n):
    return f"$ {float(n) / 1_000_000:,.0f} MM".replace(",", ".")


def fmt_pct(delta):
    if pd.isna(delta):
        return "s/i"
    return f"{delta:+.1f}%".replace(".", ",")


def fmt_share(x):
    if pd.isna(x):
        return "s/i"
    return f"{float(x) * 100:.4f}%".replace(".", ",")


@st.cache_data(show_spinner=False)
def calcular_od_biotren_tarjeta_mes_cached(periodo, valor):
    serie = pd.Series([float(valor)], index=[periodo])
    return OD.distribuir_proyeccion_biotren_por_tipo_tarjeta(serie)


@st.cache_data(show_spinner=False)
def calcular_resultado_biotren_tarjeta_anual_cached(serie_dict):
    serie = pd.Series(serie_dict, dtype=float)
    return OD.distribuir_proyeccion_biotren_por_tipo_tarjeta(serie)


@st.cache_data(show_spinner=False)
def calcular_resumen_anual_ingresos_subsidio_biotren_cached(serie_dict):
    resultado = calcular_resultado_biotren_tarjeta_anual_cached(serie_dict)
    return resultado["ingresos_subsidio_biotren"]


def _rol_tarjetario(tipo_tarjeta):
    if tipo_tarjeta in {"monedero", "media_superior", "adulto_mayor"}:
        return "Tarifa directa"
    return "Sin ingreso directo"


def _grupo_subsidio_tarjeta(tipo_tarjeta):
    if tipo_tarjeta == "media_superior":
        return "Subsidio estudiante"
    if tipo_tarjeta == "adulto_mayor":
        return "Fuera de subsidio"
    return "Grupo normal"


def render_indicadores_ejecutivos_biotren_2027(serv):
    serie = serv["BIOTREN"].astype(float).copy()
    ingresos_subsidio = calcular_resumen_anual_ingresos_subsidio_biotren_cached(serie.to_dict())
    anual = ingresos_subsidio["resumen_anual"]
    pasajeros = float(anual["viajes_biotren"])
    ingreso_medio = float(anual["ingreso_total_biotren"]) / pasajeros if pasajeros > 0 else 0.0
    servicios_comerciales = float(O.servicios_comerciales_biotren_mensuales(2027).sum())
    pasajeros_por_servicio = pasajeros / servicios_comerciales if servicios_comerciales > 0 else 0.0
    diag_recal = serv.attrs.get("recalibracion_2027", {}).get("diagnostico_biotren", {})
    referencia_pre_ajuste = float(diag_recal.get("total_pre_ajuste_ocupacion", pasajeros))
    diferencia_pre_ajuste = pasajeros - referencia_pre_ajuste

    st.markdown("## Biotren: afluencia, distribución e ingresos 2027")
    st.markdown(
        """
<div class="bt-panel">
  <h4>Resumen ejecutivo</h4>
  <p class="bt-note">El escenario ajustado considera una validación operacional por ocupación promedio general, oferta vigente y tendencia histórica mensual. Sobre esa base se calculan la venta de pasajes, el subsidio normal y el subsidio estudiante; la distribución OD/tipo de tarjeta se aplica como capa posterior.</p>
  <span class="bt-chip">Afluencia 2027</span><span class="bt-chip">Ingresos tarifarios</span><span class="bt-chip">Subsidios Biotren</span><span class="bt-chip">OD y tipo de tarjeta</span>
</div>
""",
        unsafe_allow_html=True,
    )

    fila_1 = st.columns(4)
    fila_1[0].metric("Pasajeros 2027", fmt(pasajeros))
    fila_1[1].metric("Venta de pasajes", fmt_mm(anual["ingreso_venta"]))
    fila_1[2].metric("Subsidio total", fmt_mm(anual["subsidio_total"]))
    fila_1[3].metric("Ingreso total Biotren", fmt_mm(anual["ingreso_total_biotren"]))

    fila_2 = st.columns(4)
    fila_2[0].metric("Subsidio normal", fmt_mm(anual["subsidio_normal"]))
    fila_2[1].metric("Subsidio estudiante", fmt_mm(anual["subsidio_estudiante"]))
    fila_2[2].metric("Tasa descuento", f"{float(anual['tasa_descuento_normal']) * 100:.1f}%".replace(".", ","))
    fila_2[3].metric("Pax/servicio comercial", f"{pasajeros_por_servicio:,.1f}".replace(",", "X").replace(".", ",").replace("X", "."), f"Δ {fmt(diferencia_pre_ajuste)} vs ref.")

    st.caption("Indicadores específicos de Biotren: la venta de pasajes proviene de tarifas directas; el subsidio normal usa la tasa de descuento parametrizada; la matriz estudiante sin subsidio proviene del presupuesto base; la venta media_superior considera diagonal; el ingreso teórico estudiante sin subsidio excluye diagonal; el subsidio estudiante corresponde a la diferencia agregada entre ambos; el ingreso total corresponde a venta de pasajes + subsidio normal + subsidio estudiante. El cálculo financiero no modifica la afluencia proyectada.")


def render_participacion_redistribucion_biotren(serv):
    st.markdown("### Participación mensual y redistribución 2027")
    mensual_recal = pd.DataFrame(serv.attrs.get("recalibracion_2027", {}).get("mensual", []))
    if mensual_recal.empty or "proyeccion_vigente_pre_redistribucion" not in mensual_recal.columns:
        vigente = serv["BIOTREN"].astype(float)
    else:
        vigente = mensual_recal[mensual_recal["servicio"].eq("BIOTREN")].set_index("mes")["proyeccion_vigente_pre_redistribucion"].astype(float)
    diag = O.diagnostico_redistribucion_biotren_2027(vigente, serv["BIOTREN"].astype(float))
    total = float(serv["BIOTREN"].astype(float).sum())
    servicios = float(O.servicios_comerciales_biotren_mensuales(2027).sum())
    pps = total / servicios if servicios else 0.0
    mayores = diag.sort_values("diferencia_afluencia", ascending=False).head(2)
    menores = diag.sort_values("diferencia_afluencia", ascending=True).head(2)
    c = st.columns(4)
    c[0].metric("Total anual Biotren", fmt(total))
    c[1].metric("Pax/servicio comercial", f"{pps:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c[2].metric("Mayor aumento", ", ".join(mayores["mes"].astype(int).astype(str)))
    c[3].metric("Validación suma", fmt(diag["afluencia_2027_redistribuida"].sum()))

    chart = pd.DataFrame({
        "Mes": diag["mes"],
        "2024": diag["participacion_2024"],
        "2025": diag["participacion_2025"],
        "Cierre 2026": diag["participacion_cierre_2026"],
        "2027 vigente": diag["participacion_2027_vigente"],
        "2027 redistribuido": diag["participacion_2027_redistribuida"],
    })
    fig = go.Figure()
    for col in ["2024", "2025", "Cierre 2026", "2027 vigente", "2027 redistribuido"]:
        fig.add_trace(go.Scatter(x=chart["Mes"], y=chart[col] * 100, mode="lines+markers", name=col))
    fig.update_layout(yaxis_title="Participación mensual (%)", xaxis_title="Mes", height=360, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, width="stretch")

    tabla = diag[[
        "mes", "participacion_ponderada_reciente", "participacion_2027_vigente",
        "participacion_2027_redistribuida", "afluencia_2027_vigente",
        "afluencia_2027_redistribuida", "diferencia_afluencia",
        "pasajeros_por_servicio_redistribuido", "observacion_metodologica",
    ]].rename(columns={
        "mes": "Mes",
        "participacion_ponderada_reciente": "Participación histórica reciente",
        "participacion_2027_vigente": "Participación 2027 vigente",
        "participacion_2027_redistribuida": "Participación 2027 redistribuida",
        "afluencia_2027_vigente": "Afluencia 2027 vigente",
        "afluencia_2027_redistribuida": "Afluencia 2027 redistribuida",
        "diferencia_afluencia": "Diferencia",
        "pasajeros_por_servicio_redistribuido": "Pasajeros por servicio redistribuido",
        "observacion_metodologica": "Observación metodológica",
    })
    st.dataframe(tabla.style.format({
        "Participación histórica reciente": "{:.4%}",
        "Participación 2027 vigente": "{:.4%}",
        "Participación 2027 redistribuida": "{:.4%}",
        "Afluencia 2027 vigente": "{:,.0f}",
        "Afluencia 2027 redistribuida": "{:,.0f}",
        "Diferencia": "{:+,.0f}",
        "Pasajeros por servicio redistribuido": "{:,.1f}",
    }), width="stretch", hide_index=True)
    with st.expander("Detalle técnico de diagnóstico mensual", expanded=False):
        st.write("Meses con mayor disminución: " + ", ".join(menores["mes"].astype(int).astype(str)))
        st.dataframe(diag.style.format({c: "{:.4%}" for c in diag.columns if "participacion" in c}), width="stretch", hide_index=True)


@st.cache_data(show_spinner=False)
def calcular_distribucion_biotren_linea_mod_cached(serie_dict):
    serie = pd.Series(serie_dict, dtype=float)
    return OD.distribuir_proyeccion_biotren_por_linea_mod(serie)


def _matriz_tarjeta(df, tipo_tarjeta, valor):
    tmp = df[df["tipo_tarjeta"].eq(tipo_tarjeta)]
    estaciones = list(dict.fromkeys(pd.concat([tmp["origen"], tmp["destino"]]).astype(str)))
    M = tmp.pivot_table(index="origen", columns="destino", values=valor, aggfunc="sum", fill_value=0.0)
    return M.reindex(index=estaciones, columns=estaciones, fill_value=0.0)



def render_incertidumbre_biotren(serv):
    st.markdown("### 9. Diagnósticos de incertidumbre")
    try:
        bt = BT.ejecutar_backtesting(params, mdf)
        bandas = INC.calcular_bandas_incertidumbre(serv.astype(float), bt.metricas_servicio)
    except Exception as e:
        st.warning(f"No fue posible calcular las bandas diagnósticas de Biotren: {e}")
        return

    fila = bandas.anual[bandas.anual["servicio"].eq("BIOTREN")].copy()
    if fila.empty:
        st.warning("No hay métricas de incertidumbre disponibles para Biotren.")
        return

    cols = {
        "total_banda_baja": "Banda baja",
        "total_base": "Base vigente",
        "total_banda_alta": "Banda alta",
        "total_ajustado_sesgo": "Ajuste por sesgo",
        "WMAPE_usado": "WMAPE usado (%)",
        "sesgo_usado": "Sesgo usado (%)",
        "advertencia_metodologica": "Advertencia metodológica",
    }
    st.dataframe(
        fila[list(cols)].rename(columns=cols).style.format({
            "Banda baja": "{:,.0f}",
            "Base vigente": "{:,.0f}",
            "Banda alta": "{:,.0f}",
            "Ajuste por sesgo": "{:,.0f}",
            "WMAPE usado (%)": "{:.2f}",
            "Sesgo usado (%)": "{:+.2f}",
        }),
        width="stretch",
        hide_index=True,
    )
    st.caption("Las bandas derivan del backtesting retrospectivo diagnóstico. No son intervalos estadísticos formales y no reemplazan la base operacional vigente de Biotren.")

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
    h2024 = hist_valor(s, 2024)
    h2025 = hist_valor(s, 2025)

    with st.expander("Justificación metodológica del resultado proyectado", expanded=True):
        st.markdown("""
El resultado proyectado 2027 corresponde al escenario operacional vigente y se construye con base histórica normalizada, calendario operacional, oferta de servicios, tratamiento de feriados y ajustes específicos por servicio. La proyección principal es mensual por servicio; en Biotren, las capas de línea, OD, tipo de tarjeta, ingresos y subsidios distribuyen e interpretan la demanda ya proyectada, sin recalcular la afluencia total.
""")

        resumen_servicios = []
        for servicio in O.SERVICIOS:
            pasajeros_servicio = float(serv[servicio].sum())
            if servicio == "BIOTREN":
                financiero = "Venta, subsidio normal y subsidio estudiante implementados"
                base = "Base histórica, calendario operacional, oferta L1/L2 y distribución posterior MOD/OD"
                ajuste = "Ajuste operacional vigente y distribución posterior de demanda"
                observacion = "Las capas OD/tarjeta/financieras no modifican la afluencia proyectada."
            elif servicio == "CORTO_LAJA":
                financiero = "Sin cálculo tarifario implementado"
                base = "Base histórica y recuperación de demanda"
                ajuste = "Confiabilidad operacional, oferta y supresión acotada"
                observacion = "El resultado se interpreta como recuperación operacional parcial."
            elif servicio == "TREN_ARAUCANIA":
                financiero = "Sin cálculo tarifario implementado"
                base = "Tramos operacionales y calendario 2027"
                ajuste = "Oferta efectiva por tramo y tratamiento de componente escolar"
                observacion = "La demanda se calcula por tipo de servicio, no con proporción fija agregada."
            else:
                financiero = "Sin cálculo tarifario implementado"
                base = "Referencia laboral, comportamiento observado y calendario"
                ajuste = "Moderación del efecto novedad y calibración laboral marzo-diciembre"
                observacion = "El resultado conserva variación mensual por estacionalidad y calendario."
            resumen_servicios.append({
                "Servicio": O.NOMBRE.get(servicio, servicio),
                "Pasajeros 2027": pasajeros_servicio,
                "Base metodológica": base,
                "Ajuste principal": ajuste,
                "Cálculo financiero implementado": financiero,
                "Observación": observacion,
            })
        st.dataframe(
            pd.DataFrame(resumen_servicios),
            width="stretch",
            hide_index=True,
            column_config={"Pasajeros 2027": st.column_config.NumberColumn("Pasajeros 2027", format="%d")},
        )

        st.markdown("#### Lectura del servicio seleccionado")
        st.dataframe(resumen_validacion_servicio(s, serv, uni, detalle), width="stretch", hide_index=True)

        if s == "BIOTREN":
            serie_biotren = serv["BIOTREN"].astype(float).copy()
            try:
                dist_linea = calcular_distribucion_biotren_linea_mod_cached(serie_biotren.to_dict())
                linea_anual = dist_linea.groupby("linea_od", as_index=False).agg(Pasajeros=("viajes_proyectados", "sum"))
                linea_anual["Participación"] = linea_anual["Pasajeros"] / linea_anual["Pasajeros"].sum()
                linea_anual = linea_anual.set_index("linea_od").reindex(["L1", "L2", "L1-L2"]).reset_index().rename(columns={"linea_od": "Línea"})
            except Exception:
                linea_anual = pd.DataFrame(columns=["Línea", "Pasajeros", "Participación"])
            try:
                ingresos_subsidio = calcular_resumen_anual_ingresos_subsidio_biotren_cached(serie_biotren.to_dict())
                anual = ingresos_subsidio["resumen_anual"]
                cobertura = ingresos_subsidio.get("cobertura_estudiante", {})
            except Exception:
                anual = {}
                cobertura = {}

            st.markdown("##### Biotren: proyección, distribución e ingresos")
            st.markdown(f"""
- **Proyección de afluencia:** el modelo estima **{fmt(total)} pasajeros** para Biotren en 2027 desde el escenario operacional vigente.
- **Distribución por línea:** la demanda se distribuye posteriormente entre L1, L2 y L1-L2 con matrices MOD históricas atribuibles.
- **Tipo de tarjeta e ingresos:** la distribución OD por tipo de tarjeta permite estimar venta de pasajes y subsidios sin alterar la demanda mensual.
- **Alcance financiero:** los ingresos y subsidios calculados corresponden sólo a Biotren, no al total del sistema EFE Sur.
""")
            if not linea_anual.empty:
                st.dataframe(
                    linea_anual,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Pasajeros": st.column_config.NumberColumn("Pasajeros", format="%d"),
                        "Participación": st.column_config.NumberColumn("Participación", format="%.2%%"),
                    },
                )

            financiero = pd.DataFrame([
                {
                    "Concepto": "Venta de pasajes",
                    "Grupo considerado": "monedero, media_superior, adulto_mayor",
                    "Base de cálculo": "Tarifas directas por tipo de tarjeta",
                    "Monto anual 2027": anual.get("ingreso_venta", 0.0),
                    "Observación metodológica": "Otros tipos mantienen ingreso directo cero.",
                },
                {
                    "Concepto": "Subsidio normal",
                    "Grupo considerado": "Todas excepto media_superior y adulto_mayor",
                    "Base de cálculo": "Monto_normal_base / (1 - tasa_descuento_normal) - Monto_normal_base",
                    "Monto anual 2027": anual.get("subsidio_normal", 0.0),
                    "Observación metodológica": "Tasa de descuento normal vigente y diagonal en cero.",
                },
                {
                    "Concepto": "Subsidio estudiante",
                    "Grupo considerado": "media_superior",
                    "Base de cálculo": "Ingreso teórico sin subsidio sin diagonal - venta media_superior con diagonal",
                    "Monto anual 2027": anual.get("subsidio_estudiante", 0.0),
                    "Observación metodológica": "No se usa brecha OD max(0, tarifa_sin_subsidio - tarifa_pagada) como fórmula final.",
                },
                {
                    "Concepto": "Subsidio total",
                    "Grupo considerado": "normal + media_superior",
                    "Base de cálculo": "Subsidio normal + subsidio estudiante",
                    "Monto anual 2027": anual.get("subsidio_total", 0.0),
                    "Observación metodológica": "adulto_mayor no integra subsidio normal ni estudiante.",
                },
                {
                    "Concepto": "Ingreso total Biotren",
                    "Grupo considerado": "Biotren",
                    "Base de cálculo": "Venta_pasajes + Subsidio_normal + Subsidio_estudiante",
                    "Monto anual 2027": anual.get("ingreso_total_biotren", 0.0),
                    "Observación metodológica": "Ingreso financiero estimado sólo para Biotren.",
                },
            ])
            st.dataframe(
                financiero,
                width="stretch",
                hide_index=True,
                column_config={"Monto anual 2027": st.column_config.NumberColumn("Monto anual 2027", format="$ %d")},
            )

            with st.expander("Detalle técnico de ingresos y subsidios Biotren", expanded=False):
                st.markdown("""
**Venta de pasajes.** `monedero` usa tarifa normal; `media_superior` usa tarifa estudiante pagada; `adulto_mayor` usa tarifa adulto mayor. `estudiante_basica`, `discapacitado`, `funcionario_normal`, `funcionario_especial` y `convenio_colectivo` no generan venta directa.

**Subsidio normal.** `Subsidio_normal = Monto_normal_base / (1 - tasa_descuento_normal) - Monto_normal_base`, con tarifa normal, grupo normal igual a todas las tarjetas excepto `media_superior` y `adulto_mayor`, y diagonal en cero.

**Subsidio estudiante.** `Subsidio_estudiante = Ingreso_teorico_estudiante_sin_subsidio_sin_diagonal - Venta_media_superior_con_diagonal`. `media_superior` es el único grupo estudiante considerado; la venta real estimada considera diagonal; el ingreso teórico sin subsidio excluye diagonal; esta diferencia de tratamiento es intencional. No se usa como fórmula final `max(0, tarifa_sin_subsidio - tarifa_pagada)` por par OD.

**Ingreso total.** `Ingreso_total_Biotren = Venta_pasajes + Subsidio_normal + Subsidio_estudiante`.
""")

            st.markdown("##### Limitaciones y advertencias")
            st.info("Las capas OD, línea y tipo de tarjeta distribuyen la demanda proyectada de Biotren; no recalculan la afluencia total.")
            st.warning("Los ingresos y subsidios están implementados sólo para Biotren; los otros servicios no tienen cálculo tarifario en el modelo.")
            if cobertura.get("sin_cobertura_modelo"):
                st.warning("Matriz estudiante BT sin subsidio con cobertura parcial; estaciones del modelo sin cobertura: " + ", ".join(cobertura.get("sin_cobertura_modelo", [])))
            if cobertura.get("estaciones_sin_tarifas"):
                st.warning("Estaciones en matriz sin tarifas disponibles hacia/desde otras estaciones: " + ", ".join(cobertura.get("estaciones_sin_tarifas", [])))
            st.info("La diagonal tiene tratamiento diferenciado en subsidio estudiante: venta media_superior con diagonal e ingreso teórico sin subsidio sin diagonal.")
        elif s == "CORTO_LAJA":
            st.markdown(f"""
**Resultado proyectado.** La proyección anual de Laja-Talcahuano alcanza **{fmt(total)} pasajeros**. El resultado combina base histórica, calendario operacional, oferta vigente y recuperación parcial de demanda asociada a confiabilidad operacional.

**Alcance financiero.** El modelo no implementa actualmente cálculo tarifario, ingresos ni subsidios para este servicio. La lectura financiera se limita a Biotren.

**Consistencia histórica.** El resultado queda {fmt_pct(var_pct(total, h2024)) if h2024 else 's/i'} respecto de 2024 y {fmt_pct(var_pct(total, h2025)) if h2025 else 's/i'} respecto de 2025, considerando la información histórica disponible.
""")
        elif s == "TREN_ARAUCANIA":
            tramos = {col: float(uni[col].sum()) for col in ["TA_TEMUCO_VICTORIA", "TA_TEMUCO_PITRUFQUEN", "TA_CLARET"] if col in uni.columns}
            st.markdown(f"""
**Resultado proyectado.** La proyección anual de Tren Araucanía alcanza **{fmt(total)} pasajeros**. El cálculo considera tramos operacionales y oferta efectiva por tipo de servicio.

**Tramos operacionales.** Temuco-Victoria proyecta **{fmt(tramos.get('TA_TEMUCO_VICTORIA', 0))}**, Temuco-Pitrufquén **{fmt(tramos.get('TA_TEMUCO_PITRUFQUEN', 0))}** y Claret **{fmt(tramos.get('TA_CLARET', 0))}** pasajeros. El componente Claret se trata como escolar cuando corresponde.

**Alcance financiero.** El modelo no implementa actualmente cálculo tarifario, ingresos ni subsidios para este servicio.
""")
        elif s == "LLANQUIHUE_PM":
            ene_feb = float(serv.loc[["2027-01", "2027-02"], s].sum())
            st.markdown(f"""
**Resultado proyectado.** La proyección anual de Llanquihue-Puerto Montt alcanza **{fmt(total)} pasajeros**, con **{fmt(ene_feb)}** pasajeros en enero-febrero. La proyección combina referencia laboral, comportamiento observado, calendario y moderación del efecto novedad.

**Perfil mensual.** Marzo-diciembre se calibra con una referencia laboral, sin forzar un valor idéntico en todos los meses. Enero y febrero incorporan menor efecto de novedad del servicio.

**Alcance financiero.** El modelo no implementa actualmente cálculo tarifario, ingresos ni subsidios para este servicio.
""")

        st.markdown("#### Componentes que explican el resultado mensual")
        tabla_comp = tabla_detalle_mes(detalle, s)
        if not tabla_comp.empty:
            vista_comp = tabla_comp[["periodo", "viajes_operados_plan", "demanda_proyectada", "var_oferta_operada_pct", "var_demanda_pct", "elasticidad_media"]].rename(columns={
                "periodo": "Periodo",
                "viajes_operados_plan": "Viajes operados",
                "demanda_proyectada": "Demanda proyectada",
                "var_oferta_operada_pct": "Variación oferta",
                "var_demanda_pct": "Variación demanda",
                "elasticidad_media": "Elasticidad media",
            })
            st.dataframe(
                vista_comp,
                width="stretch",
                hide_index=True,
                column_config={
                    "Viajes operados": st.column_config.NumberColumn("Viajes operados", format="%d"),
                    "Demanda proyectada": st.column_config.NumberColumn("Demanda proyectada", format="%d"),
                    "Variación oferta": st.column_config.NumberColumn("Variación oferta", format="%.2f"),
                    "Variación demanda": st.column_config.NumberColumn("Variación demanda", format="%.2f"),
                    "Elasticidad media": st.column_config.NumberColumn("Elasticidad media", format="%.2f"),
                },
            )
        st.caption("La elasticidad menor que 1 implica rendimiento marginal decreciente: un aumento de oferta eleva la demanda, pero no en la misma proporción que los servicios adicionales.")

def editor_oferta(unit, label, base_df=None):
    if base_df is None:
        sub = params[params.unit == unit].pivot(index="mes", columns="dt", values="servicios_dia")[O.DTYPES]
    else:
        sub = base_df[base_df.unit == unit].pivot(index="mes", columns="dt", values="servicios_dia")[O.DTYPES]
    sub.index.name = "Mes"
    st.caption(f"**{label}** — servicios por día. Cada modificación impacta directamente el mes editado.")
    cfg = {dt: st.column_config.NumberColumn(O.DTNOMBRE[dt], min_value=0.0, step=1.0, format="%.1f") for dt in O.DTYPES}
    ed = st.data_editor(sub, width="stretch", key=f"of_{unit}", column_config=cfg)
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
        st.dataframe((piv * 100).round(1), width="stretch")
        st.caption("Participación mensual ponderada con TA-Dist.xlsx. Claret queda en 0% para enero y febrero. La respuesta ante cambios de oferta se calcula tramo por tramo, no como redistribución estática 13/87.")
    return plan_tramos, plan_tramos


def _referencia_servicio_disponible(s):
    return s in set(REF_SERVICIO_TO_MODELO.values())


def _referencia_servicio_mensual(s, serv):
    if not _referencia_servicio_disponible(s):
        return pd.DataFrame()
    mensual = construir_referencia_mensual_visual(serv)
    return mensual[mensual["servicio_modelo"].eq(s)].copy().sort_values(["anio", "mes_num"])


def _referencia_servicio_anual(s, serv):
    if not _referencia_servicio_disponible(s):
        return pd.DataFrame()
    anual = construir_referencia_anual_visual(serv)
    return anual[anual["servicio_modelo"].eq(s)].copy().sort_values("anio")


def grafico_historico_y_proyeccion(s, serv):
    fig = go.Figure()
    ref = _referencia_servicio_mensual(s, serv)
    if not ref.empty:
        for tipo in ["Histórico observado", "Cierre 2026 estimado", "Proyección 2027 modelo"]:
            d = ref[ref["tipo_dato_label"].eq(tipo)].copy()
            if d.empty:
                continue
            fig.add_trace(go.Scatter(
                x=d["periodo"].astype(str),
                y=d["afluencia"].astype(float),
                name=tipo,
                mode="lines+markers" if tipo != "Histórico observado" else "lines",
                line=dict(
                    color=REF_TIPO_COLOR[tipo],
                    width=3 if tipo != "Histórico observado" else 2,
                    dash="dash" if tipo == "Proyección 2027 modelo" else "solid",
                ),
                marker=dict(size=7),
            ))
    else:
        st.info("La referencia histórica normalizada de cierre 2026 está disponible sólo para Biotren, Laja-Talcahuano y Tren Araucanía; no se extrapola histórico para este servicio.")
        fig.add_trace(go.Scatter(
            x=list(serv.index),
            y=serv[s].astype(float),
            name="Proyección 2027 modelo",
            mode="lines+markers",
            line=dict(color=REF_TIPO_COLOR["Proyección 2027 modelo"], width=3, dash="dash"),
        ))
    fig.update_layout(height=380, margin=dict(l=8, r=8, t=8, b=8), plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=1.15, x=0),
                      hovermode="x unified", font=dict(family="Segoe UI", color="#0f2740"))
    fig.update_xaxes(showgrid=False, title="Periodo")
    fig.update_yaxes(gridcolor="#eef2f7", title="pasajeros/mes")
    st.plotly_chart(fig, width="stretch")


def tabla_referencia_anual_servicio(s, serv):
    anual = _referencia_servicio_anual(s, serv)
    if anual.empty:
        return pd.DataFrame()
    tabla = anual[["anio", "tipo_dato_label", "afluencia_anual"]].rename(columns={
        "anio": "año",
        "tipo_dato_label": "tipo de dato",
        "afluencia_anual": "total anual",
    })
    tabla["observación metodológica"] = tabla["tipo de dato"].map({
        "Histórico observado": "Registro histórico observado normalizado desde el CSV de referencia.",
        "Cierre 2026 estimado": "Estimación de cierre anual 2026; no corresponde a observado definitivo.",
        "Proyección 2027 modelo": "Resultado vigente del motor operacional 2027; no recalibrado por el cierre 2026.",
    })
    return tabla


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
        st.caption(f"Biotren usa días operacionales sin feriados nacionales, elasticidad de oferta {e:.2f}, factor de nivel {fn:.3f} y fuerza estacional {fe:.2f}. La suma operacional se realiza sobre L1 y L2; Laja-Talcahuano se mantiene separado para evitar doble conteo. El perfil mensual incorpora un tratamiento estacional del bloque marzo-abril para mantener una trayectoria mensual coherente con la evidencia histórica disponible.")

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
<b>Propósito.</b> El modelo estima la afluencia mensual 2027 por servicio y permite analizar escenarios de oferta por mes y tipo de día.
<br><br>
<b>Escenario operacional vigente.</b> Biotren: 12.673.199; Tren Araucanía: 809.484; Llanquihue-Puerto Montt: 412.132; Laja-Talcahuano: 540.842; total sistema: 14.435.657 pasajeros.
<br><br>
<b>Separación metodológica.</b> La proyección base mensual, el backtesting histórico diagnóstico y las bandas de incertidumbre se mantienen como componentes diferenciados.
</div>
""", unsafe_allow_html=True)

    with st.expander("1. Secuencia metodológica", expanded=True):
        st.markdown("""
1. El modelo construye una proyección mensual por servicio.
2. La proyección considera calendario operacional, oferta, feriados, productividad, estacionalidad y supuestos específicos.
3. Cada servicio se trata de forma independiente según sus reglas operacionales.
4. Sólo Biotren incorpora módulos posteriores de distribución por línea OD, distribución OD por tipo de tarjeta, ingresos tarifarios preliminares y base referencial de subsidio.
5. El backtesting histórico es retrospectivo diagnóstico no holdout.
6. Las bandas de incertidumbre derivan del backtesting diagnóstico, no reemplazan el escenario base y se calculan sobre la base 2027 vigente.
""")

    with st.expander("2. Tratamiento por servicio", expanded=False):
        st.markdown("""
- **Biotren:** proyecta **12.673.199 pasajeros**. La proyección incorpora ajuste base progresivo hacia un nivel intermedio cercano a 12,8 millones, afectación operacional de Línea 2 en fines de semana de enero-febrero y ajuste residual en meses laborales. El resultado queda cercano al objetivo operacional de 12,7 millones.
- **Tren Araucanía:** proyecta **809.484 pasajeros**. Victoria-Temuco opera con 11 servicios lunes-viernes durante 2027. La metodología separa Temuco-Victoria, Temuco-Pitrufquén y Claret; Claret es un componente escolar específico de marzo-diciembre. El perfil mensual combina patrón histórico, calendario, oferta y control técnico de marzo.
- **Llanquihue-Puerto Montt:** proyecta **412.132 pasajeros**. Marzo-diciembre se calibra con un promedio laboral referencial cercano a 1.500 pasajeros por día laboral; el promedio del bloque es aproximadamente 1.499,85. Enero y febrero incorporan reducción por menor efecto de novedad.
- **Laja-Talcahuano:** proyecta **540.842 pasajeros**. No recibe ajuste operacional específico nuevo; mantiene su patrón histórico, oferta operacional, calendario y regla de feriados como operación de fin de semana.
""")
        st.info("Tren Araucanía, Llanquihue-Puerto Montt y Laja-Talcahuano no utilizan MOD Biotren, categorías L1/L2/L1-L2, tipo de tarjeta, ingresos ni base referencial de subsidio Biotren.")

    with st.expander("3. Calendario operacional, oferta y feriados", expanded=False):
        st.info("Para Biotren, Tren Araucanía y Llanquihue-Puerto Montt, los feriados nacionales tienen oferta efectiva cero. Para Laja-Talcahuano, los feriados operan con oferta de fin de semana; si el feriado cae lunes-viernes se imputa como domingo operacional.")
        st.markdown("La oferta de escenario se aplica por mes y tipo de día. Una modificación de oferta afecta el mes editado y el total anual por agregación de meses.")
        st.dataframe(tabla_feriados_2027(), width="stretch", height=240)
        st.markdown("**Resumen de días operacionales por unidad, mes y tipo de día**")
        st.dataframe(O.calendario_operacional_resumen(2027), width="stretch", height=280)

    with st.expander("4. Biotren: distribución por línea OD basada en MOD", expanded=False):
        st.markdown("""
La demanda total mensual de Biotren proviene del modelo temporal. La MOD histórica atribuible no genera ese total; sólo distribuye la demanda ya proyectada.

- **Categorías estándar:** `L1`, `L2` y `L1-L2`.
- **Concepción:** estación común/intercambio; `Concepción → Concepción` queda como control `No clasificado` y no recibe proyección estándar.
- **Criterio vigente:** el supuesto fijo 80/20 no corresponde a la metodología vigente; fue reemplazado por participaciones mensuales basadas en MOD histórica atribuible.
- **Validación:** la suma mensual `L1 + L2 + L1-L2` conserva el total mensual de Biotren.
""")

    with st.expander("5. Biotren: tipo de tarjeta, ingresos y subsidio", expanded=False):
        st.markdown("""
La distribución OD por tipo de tarjeta se recalcula sobre el total mensual vigente de Biotren.

**Tipos con ingreso tarifario directo:** `monedero`, `media_superior` y `adulto_mayor`.

**Tipos con tarifa cero:** `estudiante_basica`, `discapacitado`, `funcionario_normal`, `funcionario_especial` y `convenio_colectivo`.

Los ingresos son preliminares y no incorporan subsidios, evasión, ajustes contables ni reglas comerciales adicionales. La base de subsidio es referencial y no calcula montos monetarios.
""")

    with st.expander("6. Backtesting e incertidumbre", expanded=False):
        st.markdown("""
El backtesting histórico compara observado vs estimado en periodos conocidos. Es una validación retrospectiva diagnóstica no holdout y no reemplaza la proyección operacional 2027.

Las bandas de incertidumbre derivan de métricas históricas de error, especialmente WMAPE. No son intervalos estadísticos formales ni intervalos de confianza. El ajuste por sesgo es una sensibilidad diagnóstica. Las bandas se calculan sobre la base vigente: Biotren 12.673.199; Tren Araucanía 809.484; Llanquihue-Puerto Montt 412.132; Laja-Talcahuano 540.842.
""")

    with st.expander("7. Validaciones y limitaciones", expanded=False):
        st.markdown("""
**Validaciones:** conservación de totales mensuales, suma de participaciones MOD por línea, `No clasificado` sin proyección estándar, consistencia por tipo de tarjeta, ingresos sólo en tipos con tarifa aplicable, feriados por servicio, backtesting diagnóstico, bandas de incertidumbre sin valores negativos y ausencia de binarios versionados.

**Limitaciones:** elasticidades agregadas, OD dependiente de datos históricos disponibles, ingresos preliminares, ausencia de cálculo monetario de subsidios, capacidad, ocupación, tiempos de viaje y confiabilidad diaria detallada.
""")

    st.markdown("#### Bibliografía")
    st.markdown("""
- Transportation Research Board. *TCRP Report 95, Chapter 9: Transit Scheduling and Frequency*. Washington, D.C., 2004. https://trb.org/publications/tcrp/tcrp_rpt_95c9.pdf
- Balcombe, R. et al. *The Demand for Public Transport: A Practical Guide*. TRL Report TRL593, 2004. https://www.trl.co.uk/uploads/trl/documents/TRL593%20-%20The%20Demand%20for%20Public%20Transport.pdf
- Paulley, N. et al. *The demand for public transport: The effects of fares, quality of service, income and car ownership*. Transport Policy, 13(4), 295-306, 2006. https://eprints.whiterose.ac.uk/id/eprint/2034/1/ITS23_The_demand_for_public_transport_UPLOADABLE.pdf
- Berrebi, S., Joshi, S. & Watkins, K. *On Ridership and Frequency*. Transportation Research Part A, 2021. https://doi.org/10.48550/arXiv.2002.02493
- Feriados de Chile. *Feriados de Chile — Año 2027*. Fuente basada en Biblioteca del Congreso Nacional. https://www.feriados.cl/2027.htm
""")

def render_validacion_historica():
    st.markdown("### Validación histórica — backtesting")
    st.info("El backtesting compara observado vs estimado en periodos históricos conocidos. Es una validación retrospectiva diagnóstica, no un holdout estricto ni una garantía predictiva; no recalibra ni altera el escenario vigente 2027.")
    try:
        bt = BT.ejecutar_backtesting(params, mdf)
    except Exception as e:
        st.warning(f"No fue posible ejecutar el backtesting histórico: {e}")
        return

    anios_bt = sorted(bt.observado_estimado["anio"].dropna().astype(int).unique().tolist())
    meses_bt = int(len(bt.observado_estimado))
    with st.expander("Alcance metodológico del backtesting", expanded=True):
        st.markdown(f"""
- **Tipo:** `{BT.BACKTESTING_TIPO}`; corresponde a una revisión retrospectiva diagnóstica, no a una validación holdout fuera de muestra.
- **Periodos evaluados:** años {", ".join(map(str, anios_bt))}; se incluyen sólo meses con observación histórica disponible ({meses_bt} filas servicio-mes).
- **Observado:** afluencia mensual normalizada `pax_norm`, con columna de cobertura para advertir meses incompletos.
- **Estimado:** motor mensual-elástico y parámetros vigentes cargados por la aplicación; pueden incorporar información posterior al periodo evaluado.
- **Interpretación:** WMAPE es la métrica agregada principal; MAPE se muestra como referencia y puede ser inestable en servicios o meses de baja afluencia.
""")

    total = bt.resumen_total_sistema.iloc[0]
    k = st.columns(5)
    k[0].metric("MAE sistema", fmt(total["MAE"]))
    k[1].metric("RMSE sistema", fmt(total["RMSE"]))
    k[2].metric("MAPE sistema", f"{total['MAPE']:.1f}%")
    k[3].metric("WMAPE sistema", f"{total['WMAPE']:.1f}%")
    k[4].metric("Sesgo sistema", f"{total['sesgo']:+.1f}%")

    st.markdown("#### Métricas por servicio")
    ms = bt.metricas_servicio.copy()
    ms["servicio"] = ms["servicio"].map(lambda x: O.NOMBRE.get(x, x))
    st.dataframe(ms, width="stretch", hide_index=True)

    st.markdown("#### Tabla observado vs estimado por mes")
    comp = bt.observado_estimado.copy()
    comp["servicio"] = comp["servicio"].map(lambda x: O.NOMBRE.get(x, x))
    st.dataframe(comp[["servicio", "periodo", "observado", "estimado", "error", "error_abs", "error_pct", "cobertura"]], width="stretch", height=360)

    st.markdown("#### Errores mensuales agregados del sistema")
    err = comp.groupby("periodo", as_index=False).agg(observado=("observado", "sum"), estimado=("estimado", "sum"))
    err["error"] = err["estimado"] - err["observado"]
    err["error_abs"] = err["error"].abs()
    err["error_pct"] = err["error"] / err["observado"].replace(0, pd.NA)
    st.dataframe(err, width="stretch", height=260)

    st.markdown("#### Advertencias metodológicas")
    for warning in bt.advertencias:
        st.warning(warning)



def render_evolucion_historica_cierre_proyeccion(serv):
    st.markdown("#### Evolución histórica, cierre 2026 y proyección 2027")
    st.info(
        "Los CSV normalizados de cierre 2026 se usan exclusivamente como referencia visual. "
        "El cierre 2026 se rotula como estimado y no recalibra ni modifica la proyección operacional 2027 vigente."
    )
    anual = construir_referencia_anual_visual(serv)
    mensual = construir_referencia_mensual_visual(serv)

    servicios = list(REF_SERVICIO_TO_MODELO.values())
    servicio_sel = st.selectbox(
        "Servicio",
        servicios,
        format_func=lambda x: O.NOMBRE.get(x, x),
        key="ref_cierre_2026_servicio",
    )

    anual_s = anual[anual["servicio_modelo"].eq(servicio_sel)].copy().sort_values("anio")
    mensual_s = mensual[mensual["servicio_modelo"].eq(servicio_sel)].copy()

    fig = go.Figure()
    for tipo in ["Histórico observado", "Cierre 2026 estimado", "Proyección 2027 modelo"]:
        d = anual_s[anual_s["tipo_dato_label"].eq(tipo)].sort_values("anio")
        if d.empty:
            continue
        modo = "lines+markers" if tipo == "Histórico observado" else "markers"
        fig.add_trace(go.Scatter(
            x=d["anio"].astype(int),
            y=d["afluencia_anual"].astype(float),
            name=tipo,
            mode=modo,
            marker=dict(size=11),
            line=dict(color=REF_TIPO_COLOR[tipo], width=3, dash="dash" if tipo != "Histórico observado" else "solid"),
        ))
    fig.update_layout(height=360, margin=dict(l=8, r=8, t=8, b=8), plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=1.12, x=0),
                      hovermode="x unified", font=dict(family="Segoe UI", color="#0f2740"))
    fig.update_xaxes(dtick=1, showgrid=False, title="Año")
    fig.update_yaxes(gridcolor="#eef2f7", title="pasajeros/año")
    st.plotly_chart(fig, width="stretch")

    mensual_cmp = mensual_s[mensual_s["anio"].isin([2026, 2027])].copy().sort_values(["anio", "mes_num"])
    fig_m = go.Figure()
    for tipo in ["Cierre 2026 estimado", "Proyección 2027 modelo"]:
        d = mensual_cmp[mensual_cmp["tipo_dato_label"].eq(tipo)]
        if d.empty:
            continue
        fig_m.add_trace(go.Scatter(
            x=d["mes_num"].astype(int),
            y=d["afluencia"].astype(float),
            name=tipo,
            mode="lines+markers",
            line=dict(color=REF_TIPO_COLOR[tipo], width=3, dash="dash" if tipo == "Proyección 2027 modelo" else "solid"),
        ))
    fig_m.update_layout(height=320, margin=dict(l=8, r=8, t=8, b=8), plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=1.12, x=0),
                        hovermode="x unified", font=dict(family="Segoe UI", color="#0f2740"))
    fig_m.update_xaxes(dtick=1, range=[0.7, 12.3], showgrid=False, title="Mes")
    fig_m.update_yaxes(gridcolor="#eef2f7", title="pasajeros/mes")
    st.plotly_chart(fig_m, width="stretch")

    tabla = anual_s[["anio", "tipo_dato_label", "afluencia_anual"]].rename(columns={
        "anio": "año",
        "tipo_dato_label": "tipo de dato",
        "afluencia_anual": "afluencia",
    })
    tabla["observación metodológica"] = tabla["tipo de dato"].map({
        "Histórico observado": "Registro histórico observado normalizado desde el CSV de referencia.",
        "Cierre 2026 estimado": "Estimación de cierre anual 2026; no corresponde a observado definitivo.",
        "Proyección 2027 modelo": "Resultado vigente del motor operacional 2027; no recalibrado por el cierre 2026.",
    })
    st.dataframe(tabla.style.format({"afluencia": "{:,.0f}"}), width="stretch", hide_index=True, height=300)


def render_resumen():
    uni, serv, detalle = O.proyectar_mensual_elastico(params, mdf, return_detalle=True)
    st.markdown("### Resumen 2027 recalibrado")
    st.info("El total anual es la suma de los meses proyectados. El escenario 2027 recalibrado conserva trazabilidad contra el escenario anterior y aplica supuestos operacionales específicos por servicio.")

    kk = st.columns(4)
    for i, s in enumerate(O.SERVICIOS):
        viajes = detalle[detalle.servicio == s]["viajes_operados_plan"].sum()
        om = serv[s].sum() / max(viajes, 1)
        kk[i].metric(O.NOMBRE[s], fmt(serv[s].sum()), f"{fmt(om)} pax/viaje")


    st.markdown("#### Comparación contra escenario anterior")
    escenario_anterior = {"BIOTREN": 12991160.0, "CORTO_LAJA": 540842.0, "TREN_ARAUCANIA": 950258.0, "LLANQUIHUE_PM": 420853.0}
    motivos = {
        "BIOTREN": "Baja progresiva, afectación L2 fines de semana y ajuste residual laboral",
        "TREN_ARAUCANIA": "Victoria-Temuco 11 servicios L-V y suavizamiento de marzo",
        "LLANQUIHUE_PM": "Promedio laboral marzo-diciembre y menor efecto novedad estival",
        "CORTO_LAJA": "Sin ajuste específico nuevo",
    }
    comp = pd.DataFrame([{
        "servicio": O.NOMBRE[k],
        "total anterior": escenario_anterior[k],
        "total recalibrado": float(serv[k].sum()),
        "diferencia": float(serv[k].sum()) - escenario_anterior[k],
        "diferencia %": (float(serv[k].sum()) / escenario_anterior[k] - 1.0) * 100.0,
        "motivo principal": motivos[k],
    } for k in O.SERVICIOS])
    st.dataframe(comp.style.format({"total anterior":"{:,.0f}", "total recalibrado":"{:,.0f}", "diferencia":"{:,.0f}", "diferencia %":"{:+.2f}%"}), width="stretch", hide_index=True)

    diag_detalle = detalle.groupby(["servicio", "mes"], as_index=False)["afl"].sum()
    if not diag_detalle.empty:
        bt = serv["BIOTREN"].astype(float)
        st.caption(f"Biotren queda a {fmt(abs(bt.sum() - 12_700_000))} pasajeros del objetivo de 12,7 millones. Tren Araucanía usa 11 servicios L-V Victoria-Temuco; Laja-Talcahuano no recibe ajuste específico nuevo.")

    fig = go.Figure()
    for s in O.SERVICIOS:
        fig.add_trace(go.Scatter(x=list(serv.index), y=serv[s].astype(float), name=O.NOMBRE[s],
                                 mode="lines+markers", line=dict(color=PAL[s], width=3)))
    fig.update_layout(height=380, margin=dict(l=8, r=8, t=8, b=8), plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=1.1, x=0),
                      hovermode="x unified", font=dict(family="Segoe UI", color="#0f2740"))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#eef2f7", title="pax/mes")
    st.plotly_chart(fig, width="stretch")

    render_evolucion_historica_cierre_proyeccion(serv)

    st.markdown("#### Proyección mensual 2027")
    st.dataframe(serv, width="stretch")

    st.markdown("#### Calendario operacional 2027 aplicado")
    st.dataframe(O.calendario_operacional_resumen(2027), width="stretch", height=260)

    st.markdown("#### Comportamiento histórico anual observado")
    st.dataframe(hist_anual, width="stretch")

    tramos_ta = uni[[c for c in uni.columns if str(c).startswith("TA_")]].copy()
    c1, c2, c3, c4 = st.columns(4)
    c1.download_button("⬇ Resumen por servicio", serv.to_csv().encode(), "proyeccion_2027_resumen_mensual_elastico.csv")
    c2.download_button("⬇ Detalle por unidad", uni.to_csv().encode(), "proyeccion_2027_unidades_mensual_elastico.csv")
    c3.download_button("⬇ Tren Araucanía por tramo", tramos_ta.to_csv().encode(), "proyeccion_2027_tren_araucania_tramos.csv")
    c4.download_button("⬇ Detalle de cálculo", detalle.to_csv(index=False).encode(), "detalle_calculo_mensual_elastico.csv")



def _serie_biotren_vigente_pre_redistribucion(serv):
    mensual_recal = pd.DataFrame(serv.attrs.get("recalibracion_2027", {}).get("mensual", []))
    if mensual_recal.empty or "proyeccion_vigente_pre_redistribucion" not in mensual_recal.columns:
        return serv["BIOTREN"].astype(float)
    vigente = mensual_recal[mensual_recal["servicio"].eq("BIOTREN")].set_index("mes")["proyeccion_vigente_pre_redistribucion"].astype(float)
    vigente.index = [f"2027-{int(m):02d}" for m in vigente.index]
    return vigente.reindex(serv.index).astype(float)


def _tabla_financiera_biotren(anual_sub, venta_por_tipo):
    return pd.DataFrame([
        {
            "Concepto": "Venta de pasajes",
            "Grupo considerado": "Biotren",
            "Base de cálculo": "monedero normal + media_superior estudiante pagada + adulto_mayor",
            "Monto anual": anual_sub.get("ingreso_venta", sum(venta_por_tipo.values())),
            "Observación": "Corresponde sólo a Biotren; otros tipos de tarjeta mantienen ingreso directo cero.",
        },
        {
            "Concepto": "Subsidio normal",
            "Grupo considerado": "Todas las tarjetas excepto media_superior y adulto_mayor",
            "Base de cálculo": "Monto normal base / (1 - tasa_descuento_normal) - monto normal base",
            "Monto anual": anual_sub.get("subsidio_normal", 0.0),
            "Observación": "Usa tasa parametrizada; no modifica la afluencia mensual.",
        },
        {
            "Concepto": "Subsidio estudiante",
            "Grupo considerado": "media_superior",
            "Base de cálculo": "Ingreso teórico estudiante sin subsidio sin diagonal - venta media_superior con diagonal",
            "Monto anual": anual_sub.get("subsidio_estudiante", 0.0),
            "Observación": "Fórmula oficial agregada; la brecha OD se mantiene sólo como diagnóstico.",
        },
        {
            "Concepto": "Subsidio total",
            "Grupo considerado": "Biotren",
            "Base de cálculo": "Subsidio normal + subsidio estudiante",
            "Monto anual": anual_sub.get("subsidio_total", 0.0),
            "Observación": "No corresponde al total del sistema EFE Sur.",
        },
        {
            "Concepto": "Ingreso total Biotren",
            "Grupo considerado": "Biotren",
            "Base de cálculo": "Venta de pasajes + subsidio normal + subsidio estudiante",
            "Monto anual": anual_sub.get("ingreso_total_biotren", 0.0),
            "Observación": "Resultado financiero anual exclusivo de Biotren.",
        },
    ])


def render_biotren_ejecutivo(serv, uni, detalle):
    serie = serv["BIOTREN"].astype(float).copy()
    vigente = _serie_biotren_vigente_pre_redistribucion(serv)
    servicios_mensuales = O.servicios_comerciales_biotren_mensuales(2027)
    servicios_anuales = float(servicios_mensuales.sum())
    diag = O.diagnostico_redistribucion_biotren_2027(vigente, serie)
    resultado_anual = calcular_resultado_biotren_tarjeta_anual_cached(serie.to_dict())
    resumen_anual_tipo = resultado_anual["resumen_tipo_tarjeta"].copy()
    ingresos_subsidio = resultado_anual.get("ingresos_subsidio_biotren", {})
    anual_sub = ingresos_subsidio.get("resumen_anual", {})
    cobertura = ingresos_subsidio.get("cobertura_estudiante", {})
    pasajeros = float(anual_sub.get("viajes_biotren", serie.sum()))
    pasajeros_por_servicio = pasajeros / servicios_anuales if servicios_anuales else 0.0

    st.markdown("## Biotren 2027: afluencia, ocupación e ingresos")
    st.markdown(
        """
<div class="bt-panel">
  <p class="bt-note">Escenario redistribuido mensualmente con total anual conservado, validación por pasajeros por servicio comercial e ingresos/subsidios recalculados sobre la nueva distribución mensual. Las capas por línea, OD y tipo de tarjeta distribuyen la afluencia Biotren; no generan un nuevo total anual.</p>
  <span class="bt-chip">Afluencia redistribuida</span><span class="bt-chip">Ocupación promedio por servicio</span><span class="bt-chip">Ingresos y subsidios Biotren</span>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("### 1. Indicadores ejecutivos")
    fila_1 = st.columns(4)
    fila_1[0].metric("Pasajeros Biotren 2027", fmt(pasajeros))
    fila_1[1].metric("Servicios comerciales 2027", fmt(servicios_anuales))
    fila_1[2].metric("Pax/servicio comercial", f"{pasajeros_por_servicio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    fila_1[3].metric("Venta de pasajes", fmt_mm(anual_sub.get("ingreso_venta", 0.0)))
    fila_2 = st.columns(4)
    fila_2[0].metric("Subsidio total", fmt_mm(anual_sub.get("subsidio_total", 0.0)))
    fila_2[1].metric("Ingreso total Biotren", fmt_mm(anual_sub.get("ingreso_total_biotren", 0.0)))
    fila_2[2].metric("Subsidio normal", fmt_mm(anual_sub.get("subsidio_normal", 0.0)))
    fila_2[3].metric("Subsidio estudiante", fmt_mm(anual_sub.get("subsidio_estudiante", 0.0)))

    st.markdown("### 2. Evolución mensual y redistribución")
    mensual = pd.DataFrame({
        "Periodo": serie.index,
        "Mes": range(1, 13),
        "Afluencia vigente": vigente.values,
        "Afluencia redistribuida": serie.values,
        "Participación mensual": serie.values / pasajeros if pasajeros else 0.0,
        "Servicios comerciales": servicios_mensuales.values,
    })
    mensual["Diferencia"] = mensual["Afluencia redistribuida"] - mensual["Afluencia vigente"]
    mensual["Pasajeros por servicio"] = mensual["Afluencia redistribuida"] / mensual["Servicios comerciales"].replace(0, pd.NA)
    fig_afl = go.Figure()
    fig_afl.add_trace(go.Scatter(x=mensual["Periodo"], y=mensual["Afluencia vigente"], mode="lines+markers", name="2027 vigente"))
    fig_afl.add_trace(go.Scatter(x=mensual["Periodo"], y=mensual["Afluencia redistribuida"], mode="lines+markers", name="2027 redistribuido"))
    fig_afl.update_layout(height=360, yaxis_title="Pasajeros", xaxis_title="Mes", hovermode="x unified", margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig_afl, width="stretch")
    st.dataframe(
        mensual[["Mes", "Afluencia redistribuida", "Participación mensual", "Diferencia", "Pasajeros por servicio"]],
        width="stretch",
        hide_index=True,
        height=260,
        column_config={
            "Afluencia redistribuida": st.column_config.NumberColumn("Afluencia redistribuida", format="%d"),
            "Participación mensual": st.column_config.NumberColumn("Participación mensual", format="%.2%%"),
            "Diferencia": st.column_config.NumberColumn("Diferencia", format="%+d"),
            "Pasajeros por servicio": st.column_config.NumberColumn("Pasajeros por servicio", format="%.1f"),
        },
    )

    st.markdown("### 3. Participación mensual y redistribución 2027")
    chart = pd.DataFrame({
        "Mes": diag["mes"],
        "2024": diag["participacion_2024"],
        "2025": diag["participacion_2025"],
        "Cierre 2026": diag["participacion_cierre_2026"],
        "2027 vigente": diag["participacion_2027_vigente"],
        "2027 redistribuido": diag["participacion_2027_redistribuida"],
    })
    fig_part = go.Figure()
    for col in ["2024", "2025", "Cierre 2026", "2027 vigente", "2027 redistribuido"]:
        fig_part.add_trace(go.Scatter(x=chart["Mes"], y=chart[col] * 100, mode="lines+markers", name=col))
    fig_part.update_layout(yaxis_title="Participación mensual (%)", xaxis_title="Mes", height=360, margin=dict(l=10, r=10, t=20, b=10), hovermode="x unified")
    st.plotly_chart(fig_part, width="stretch")
    tabla_diag = diag[["mes", "participacion_ponderada_reciente", "participacion_2027_vigente", "participacion_2027_redistribuida", "afluencia_2027_redistribuida", "pasajeros_por_servicio_redistribuido"]].rename(columns={
        "mes": "Mes",
        "participacion_ponderada_reciente": "Histórica reciente",
        "participacion_2027_vigente": "2027 vigente",
        "participacion_2027_redistribuida": "2027 redistribuida",
        "afluencia_2027_redistribuida": "Afluencia redistribuida",
        "pasajeros_por_servicio_redistribuido": "Pasajeros por servicio",
    })
    st.dataframe(
        tabla_diag,
        width="stretch",
        hide_index=True,
        height=260,
        column_config={
            "Histórica reciente": st.column_config.NumberColumn("Histórica reciente", format="%.2%%"),
            "2027 vigente": st.column_config.NumberColumn("2027 vigente", format="%.2%%"),
            "2027 redistribuida": st.column_config.NumberColumn("2027 redistribuida", format="%.2%%"),
            "Afluencia redistribuida": st.column_config.NumberColumn("Afluencia redistribuida", format="%d"),
            "Pasajeros por servicio": st.column_config.NumberColumn("Pasajeros por servicio", format="%.1f"),
        },
    )
    with st.expander("Detalle metodológico de participación mensual", expanded=False):
        st.markdown("""
- Participación mensual = afluencia mensual / afluencia anual.
- Pesos del patrón reciente: 2024 = 25%, 2025 = 35%, cierre 2026 = 40%.
- Participación objetivo = 80% patrón histórico ponderado + 20% participación de servicios comerciales 2027.
- El redondeo se ajusta para que la suma mensual conserve exactamente el total anual Biotren.
""")
        st.dataframe(diag, width="stretch", hide_index=True, height=320)

    st.markdown("### 4. Composición de demanda")
    dist_linea = calcular_distribucion_biotren_linea_mod_cached(serie.to_dict())
    anual_linea = dist_linea.groupby("linea_od", as_index=False).agg(viajes=("viajes_proyectados", "sum"))
    anual_linea["participacion"] = anual_linea["viajes"] / anual_linea["viajes"].sum()
    anual_linea = anual_linea.set_index("linea_od").reindex(["L1", "L2", "L1-L2"]).reset_index()
    fig_linea = go.Figure(go.Bar(x=anual_linea["linea_od"], y=anual_linea["viajes"], marker_color=["#1f6feb", "#0e9f6e", "#d97706"], text=[fmt(v) for v in anual_linea["viajes"]], textposition="outside"))
    fig_linea.update_layout(title="Distribución anual por línea", height=320, yaxis_title="Pasajeros", xaxis_title="Línea", showlegend=False, margin=dict(l=10, r=10, t=45, b=10))
    st.plotly_chart(fig_linea, width="stretch")
    st.dataframe(
        anual_linea.rename(columns={"linea_od": "Línea", "viajes": "Pasajeros 2027", "participacion": "Participación"}),
        width="stretch",
        hide_index=True,
        column_config={"Pasajeros 2027": st.column_config.NumberColumn("Pasajeros 2027", format="%d"), "Participación": st.column_config.NumberColumn("Participación", format="%.2%%")},
    )

    resumen_tipo = resumen_anual_tipo.groupby(["tipo_tarjeta", "nombre_visual", "tipo_pasajero_tarifa"], as_index=False).agg(viajes=("viajes_proyectados", "sum"), venta_pasajes=("ingresos_tarifarios_proyectados", "sum"))
    total_viajes = float(resumen_tipo["viajes"].sum())
    resumen_tipo["participacion"] = resumen_tipo["viajes"] / total_viajes if total_viajes else 0.0
    resumen_tipo["rol_tarifario"] = resumen_tipo["tipo_tarjeta"].map(_rol_tarjetario)
    resumen_tipo["grupo_subsidio"] = resumen_tipo["tipo_tarjeta"].map(_grupo_subsidio_tarjeta)
    resumen_tipo = resumen_tipo.sort_values("viajes", ascending=False)
    fig_tarjetas = go.Figure(go.Bar(x=resumen_tipo["nombre_visual"], y=resumen_tipo["viajes"], marker_color=["#0e9f6e" if r == "Tarifa directa" else "#94a3b8" for r in resumen_tipo["rol_tarifario"]], text=[fmt(v) for v in resumen_tipo["viajes"]], textposition="outside"))
    fig_tarjetas.update_layout(title="Viajes anuales por tipo de tarjeta", height=360, yaxis_title="Viajes", xaxis_title="Tipo de tarjeta", showlegend=False, margin=dict(l=10, r=10, t=45, b=90))
    fig_tarjetas.update_xaxes(tickangle=-25)
    st.plotly_chart(fig_tarjetas, width="stretch")
    tabla_tarjetas = resumen_tipo.rename(columns={"tipo_tarjeta": "Tipo de tarjeta", "nombre_visual": "Nombre", "tipo_pasajero_tarifa": "Tarifa aplicada", "viajes": "Viajes 2027", "participacion": "Participación", "rol_tarifario": "Rol tarifario", "grupo_subsidio": "Grupo subsidio"})
    st.dataframe(
        tabla_tarjetas[["Tipo de tarjeta", "Nombre", "Rol tarifario", "Grupo subsidio", "Tarifa aplicada", "Viajes 2027", "Participación"]],
        width="stretch",
        hide_index=True,
        height=300,
        column_config={"Viajes 2027": st.column_config.NumberColumn("Viajes 2027", format="%d"), "Participación": st.column_config.NumberColumn("Participación", format="%.2%%")},
    )
    with st.expander("Detalle mensual de conservación por línea", expanded=False):
        mensual_linea = dist_linea.pivot_table(index="periodo", columns="linea_od", values="viajes_proyectados", aggfunc="sum", fill_value=0.0).reindex(columns=["L1", "L2", "L1-L2"], fill_value=0.0)
        mensual_linea["Total líneas"] = mensual_linea.sum(axis=1)
        mensual_linea["Total Biotren"] = serie.reindex(mensual_linea.index).astype(float)
        mensual_linea["Diferencia"] = mensual_linea["Total líneas"] - mensual_linea["Total Biotren"]
        st.dataframe(mensual_linea.reset_index().rename(columns={"periodo": "Periodo"}), width="stretch", hide_index=True, height=280)

    st.markdown("### 5. Resultados financieros Biotren")
    venta_por_tipo = resumen_tipo.set_index("tipo_tarjeta")["venta_pasajes"].to_dict()
    tabla_financiera = _tabla_financiera_biotren(anual_sub, venta_por_tipo)
    st.dataframe(
        tabla_financiera,
        width="stretch",
        hide_index=True,
        column_config={"Monto anual": st.column_config.NumberColumn("Monto anual", format="$ %d")},
    )

    st.markdown("### 6. Advertencias y cobertura tarifaria")
    advertencias = []
    if cobertura.get("sin_cobertura_modelo"):
        advertencias.append("Concepción Centro sin cobertura en matriz estudiante sin subsidio: " + ", ".join(cobertura.get("sin_cobertura_modelo", [])))
    if cobertura.get("estaciones_sin_tarifas"):
        advertencias.append("Pasajero Lota sin tarifas disponibles: " + ", ".join(cobertura.get("estaciones_sin_tarifas", [])))
    advertencias.append("La diagonal tiene tratamiento diferenciado: venta media_superior con diagonal e ingreso teórico estudiante sin subsidio sin diagonal.")
    advertencias.append(f"Matriz estudiante sin subsidio: {fmt(cobertura.get('estaciones_matriz', 0))} estaciones; las capas OD/tarjeta distribuyen la afluencia y no generan el total anual.")
    for adv in advertencias:
        st.info(adv)

    with st.expander("Detalle OD mensual por tipo de tarjeta", expanded=False):
        periodos = list(serie.index)
        periodo = st.selectbox("Mes proyectado", periodos, format_func=lambda x: f"{str(x)[5:7]} - 2027", key="od_biotren_periodo_compacto")
        tipo_tarjeta = st.selectbox("Tipo de tarjeta", OD.TIPOS_TARJETA_ESPERADOS, key="od_biotren_tipo_tarjeta_compacto")
        resultado_mes = calcular_od_biotren_tarjeta_mes_cached(periodo, float(serie.loc[periodo]))
        viajes_long = resultado_mes["viajes_tipo_tarjeta_long"]
        resumen_mes = resultado_mes["resumen_tipo_tarjeta"].copy()
        M = _matriz_tarjeta(viajes_long, tipo_tarjeta, "viajes_proyectados")
        R = _matriz_tarjeta(viajes_long, tipo_tarjeta, "ingresos_tarifarios_proyectados")
        st.caption("Detalle técnico en memoria: distribuye el total mensual seleccionado por tipo de tarjeta y par OD.")
        t1, t2, t3 = st.tabs(["Matriz OD viajes", "Matriz OD ingresos", "Resumen mensual"])
        with t1:
            st.dataframe(M.round(0).astype(int).copy(deep=True), width="stretch", height=420)
        with t2:
            st.dataframe(R.round(0).astype(int).copy(deep=True), width="stretch", height=420)
        with t3:
            st.dataframe(resumen_mes, width="stretch", height=260)

    with st.expander("Justificación metodológica Biotren", expanded=False):
        st.markdown("""
- La redistribución mensual usa participación anual reciente y conserva el total anual Biotren.
- La validación operacional se expresa como pasajeros por servicio comercial = pasajeros anuales / servicios comerciales anuales.
- Las capas por línea, OD, tipo de tarjeta, ingresos y subsidios se recalculan después de la afluencia mensual redistribuida.
- Subsidio normal: `Monto_normal_base / (1 - tasa_descuento_normal) - Monto_normal_base`.
- Subsidio estudiante: `Ingreso_teorico_estudiante_sin_subsidio_sin_diagonal - Venta_media_superior_con_diagonal`.
""")

    with st.expander("Diagnóstico de incertidumbre", expanded=False):
        render_incertidumbre_biotren(serv)

def render_servicio(s):
    cf = CONF[s]
    st.markdown(f"### {O.NOMBRE[s]} &nbsp;<span class='badge' style='background:{CONF_C[cf]}'>Confianza {cf}</span>", unsafe_allow_html=True)

    st.markdown("#### Oferta 2027")
    ce = {}
    plan_tramos = None
    if s == "BIOTREN":
        with st.expander("Parámetros de oferta Biotren", expanded=False):
            st.info("Biotren se edita por línea. L1 considera 47 servicios L-V durante 2027; L2 mantiene 110 servicios L-V todo el año. Desde mayo, 3 servicios L2 L-V operan acoplados dentro de esos 110 y se registran sólo como capacidad efectiva.")
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

    if s == "BIOTREN":
        render_biotren_ejecutivo(serv, uni, detalle)
        return

    st.markdown("#### Evolución mensual histórica, cierre 2026 y proyección 2027")
    grafico_historico_y_proyeccion(s, serv)
    tabla_ref = tabla_referencia_anual_servicio(s, serv)
    if not tabla_ref.empty:
        st.dataframe(tabla_ref.style.format({"total anual": "{:,.0f}"}), width="stretch", hide_index=True, height=300)

    st.markdown("#### Total operacional 2027 vigente")
    k = st.columns(4)
    k[0].metric("Total anual 2027", fmt(serv[s].dropna().sum()))
    k[1].metric("Pax/servicio comercial", fmt(ocup_proy))
    k[2].metric("Mes peak", pk, fmt(serv[s].max()))
    k[3].metric("Mes menor", serv[s].astype(float).idxmin(), fmt(serv[s].min()))

    g, t = st.columns([3, 2])
    with g:
        render_justificacion_servicio(s, serv, uni, detalle)
        render_ecuacion_servicio(s)
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
        st.dataframe(out, width="stretch", height=330)

    st.markdown("#### Detalle mensual del cálculo oferta-demanda")
    st.dataframe(tabla_detalle_mes(detalle, s), width="stretch")

    with st.expander("Calendario operacional aplicado al servicio"):
        st.dataframe(tabla_calendario_servicio(s), width="stretch")
    st.caption("La columna impacto_mes_vs_base permite verificar que un cambio de oferta afecta el mes modificado y que el total anual resulta de la suma mensual.")

    if s == "CORTO_LAJA":
        st.warning("Oferta base: 8 servicios todos los días; sólo sábados y domingos de enero-febrero tienen 10 servicios. El escenario incorpora recuperación parcial de confiabilidad, supresión base acotada y mayor peso del patrón histórico de mejor desempeño.")
    if s == "TREN_ARAUCANIA":
        st.warning("Claret se considera servicio escolar: enero y febrero quedan sin oferta ni demanda proyectada para este tipo de servicio. Las modificaciones de oferta se evalúan por tramo con elasticidad diferenciada.")
    if s == "LLANQUIHUE_PM":
        st.warning("Enero y febrero se reducen por menor efecto novedad; marzo-diciembre se calibran hacia un promedio laboral cercano a 1.500 pasajeros, sin forzar exactamente el mismo valor cada mes.")

    if s == "LLANQUIHUE_PM":
        cal = O.dias_operacionales_por_tipo(2027, units=["LLANQUIHUE_PM"])
        lv = cal[(cal.unit.eq("LLANQUIHUE_PM")) & (cal.dt.eq("LV"))].set_index("mes")["n_dias"]
        t = pd.DataFrame({"periodo": serv.index, "pasajeros": serv[s].astype(float).values})
        t["mes"] = range(1, 13)
        t["dias_laborales_operacionales"] = t["mes"].map(lv.to_dict()).astype(float)
        t["promedio_laboral"] = t["pasajeros"] / t["dias_laborales_operacionales"].replace(0, pd.NA)
        st.markdown("#### Promedio laboral mensual")
        st.dataframe(t[["periodo", "pasajeros", "dias_laborales_operacionales", "promedio_laboral"]].style.format({"pasajeros":"{:,.0f}", "dias_laborales_operacionales":"{:,.0f}", "promedio_laboral":"{:,.1f}"}), width="stretch", hide_index=True)
    st.download_button(f"⬇ Descargar proyección {O.NOMBRE[s]} (CSV)", out.to_csv().encode(),
                       f"proyeccion_2027_{s}.csv", key=f"dl_{s}")


tabs = st.tabs(["📘 Metodología", "📊 Resumen", "🧪 Validación histórica"] + [O.NOMBRE[s] for s in O.SERVICIOS])
with tabs[0]:
    render_metodologia()
with tabs[1]:
    render_resumen()
with tabs[2]:
    render_validacion_historica()
for i, s in enumerate(O.SERVICIOS):
    with tabs[i + 3]:
        render_servicio(s)
