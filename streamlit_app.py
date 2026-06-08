"""
streamlit_app.py -- Modelo de afluencia EFE/Fesur 2027.
Punto de entrada para Streamlit Cloud. Ejecutar local:  streamlit run streamlit_app.py

4 secciones (una por servicio). La OFERTA de trenes es la variable de planificacion
editable. Base del comportamiento: estacionalidad (fechas) + reporte operacional (RROO,
ya precalculado en data/oferta_params.csv). Sin variable climatica.
"""
import os
import numpy as np
import pandas as pd
import streamlit as st

import pipeline_afluencia as P
import oferta as O

st.set_page_config(page_title="Afluencia EFE/Fesur 2027", layout="wide")
st.title("Modelo de afluencia 2027 — EFE/Fesur")
st.caption("La oferta de trenes es la variable de planificacion. Base: estacionalidad "
           "(fechas) + reporte operacional (RROO). Sin variable climatica.")

CONF = {"BIOTREN": "ALTA", "CORTO_LAJA": "ALTA",
        "TREN_ARAUCANIA": "MEDIA", "LLANQUIHUE_PM": "BAJA"}

DATA = os.path.join(os.path.dirname(__file__), "data")


@st.cache_data
def cargar():
    diario = pd.read_csv(os.path.join(DATA, "afluencia_diaria_consolidada.csv"),
                         parse_dates=["fecha"])
    params = pd.read_csv(os.path.join(DATA, "oferta_params.csv"))
    mdf = P.mensualizar(diario)
    base, meta = P.proyectar_2027(mdf)
    return diario, params, mdf, base, meta


try:
    diario, params, mdf, base, meta = cargar()
except Exception as e:
    st.error(f"No se pudieron cargar los datos en /data: {e}")
    st.stop()

seccion = st.sidebar.radio("Seccion",
                           ["Resumen general"] + [O.NOMBRE[s] for s in O.SERVICIOS])
INV = {v: k for k, v in O.NOMBRE.items()}


def editor_oferta(unit, label):
    sub = params[params.unit == unit][["mes", "operados_hist"]].set_index("mes")
    sub.columns = ["servicios"]
    st.caption(f"Oferta {label} (servicios/mes). Editable — default = oferta historica operada.")
    ed = st.data_editor(sub.T, use_container_width=True, key=f"of_{unit}")
    plan = ed.T.reset_index()
    plan.columns = ["mes", "servicios"]
    plan["unit"] = unit
    return plan[["unit", "mes", "servicios"]]


def render_servicio(s):
    st.header(O.NOMBRE[s])
    st.caption(f"Confianza del pronostico: {CONF[s]}")
    h = mdf[mdf.servicio == s].sort_values("mes")
    h["mes_str"] = h["mes"].astype(str)
    st.subheader("Afluencia mensual historica")
    st.line_chart(h.set_index("mes_str")["pax_norm"])

    st.subheader("Oferta 2027 (variable de planificacion)")
    planes = []
    if s == "BIOTREN":
        st.info("Biotren: edite L1 y L2 por separado. La afluencia se reparte 20/80 (L1/L2, "
                "matriz OD); cada linea tiene su carga por viaje (L1~236, L2~345). Nota: los "
                "servicios Laja-Talcahuano circulan por L1 en HQ-TH pero figuran como linea "
                "propia en el RROO (no se duplican aqui).")
        c1, c2 = st.columns(2)
        with c1:
            planes.append(editor_oferta("BIOTREN_L1", "Linea 1"))
        with c2:
            planes.append(editor_oferta("BIOTREN_L2", "Linea 2"))
    else:
        planes.append(editor_oferta(O.UNIDADES_DE[s][0], O.NOMBRE[s]))

    st.subheader("Contingencia extra (sobre la supresion historica)")
    ce = {}
    cols = st.columns(len(O.UNIDADES_DE[s]))
    for i, u in enumerate(O.UNIDADES_DE[s]):
        ce[u] = cols[i].number_input(f"{u} (+% supresion)", 0.0, 30.0, 0.0, 1.0) / 100.0

    plan = pd.concat(planes, ignore_index=True)
    uni, serv = O.proyectar(params, plan=plan, contingencia_extra=ce)

    st.subheader("Proyeccion 2027")
    out = pd.DataFrame(index=serv.index)
    if s == "BIOTREN":
        out["Linea 1"] = uni["BIOTREN_L1"]
        out["Linea 2"] = uni["BIOTREN_L2"]
    out["Total (por oferta)"] = serv[s]
    out["Referencia estacional"] = base[s].values
    st.dataframe(out, use_container_width=True)
    a, b = st.columns(2)
    a.metric(f"Total anual 2027 — {O.NOMBRE[s]} (por oferta)", f"{int(serv[s].dropna().sum()):,}")
    b.metric("Referencia estacional", f"{int(base[s].sum()):,}")
    if s == "CORTO_LAJA":
        st.warning("Laja-Talcahuano: oferta plana (CV 3%), casi sin correlacion con la "
                   "demanda. El modo por oferta sobreestima (ignora la tendencia a la baja). "
                   "Usar la referencia estacional como base; la oferta solo para escenarios.")
    if s == "LLANQUIHUE_PM":
        st.warning("Llanquihue-PM: 13 meses, solape RROO delgado (abr-may imputados). "
                   "corr(oferta,demanda)=+0.76 (prometedor pero fragil). Confianza BAJA.")
    st.download_button(f"Descargar proyeccion {O.NOMBRE[s]} (CSV)",
                       out.to_csv().encode(), f"proyeccion_2027_{s}.csv")


if seccion == "Resumen general":
    st.subheader("Proyeccion 2027 — escenario base (oferta = historica)")
    uni, serv = O.proyectar(params)
    st.dataframe(serv, use_container_width=True)
    st.write("**Totales anuales (por oferta):**",
             {s: int(serv[s].dropna().sum()) for s in serv.columns})
    st.write("**Totales anuales (referencia estacional):**",
             {c: int(base[c].sum()) for c in base.columns})
    st.caption("Entra a cada seccion para editar la oferta y ver el efecto. "
               "Biotren se desglosa en Linea 1 / Linea 2.")
    st.download_button("Descargar resumen por servicio (CSV)",
                       serv.to_csv().encode(), "proyeccion_2027_resumen.csv")
    st.download_button("Descargar detalle por unidad (incl. L1/L2)",
                       uni.to_csv().encode(), "proyeccion_2027_unidades.csv")
else:
    render_servicio(INV[seccion])
