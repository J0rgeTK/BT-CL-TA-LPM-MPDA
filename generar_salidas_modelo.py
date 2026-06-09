"""Regenera las salidas principales del modelo mensual-elástico."""
from pathlib import Path
import pandas as pd
import pipeline_afluencia as P
import oferta as O

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
OUT = BASE / "outputs"
OUT.mkdir(exist_ok=True)

params = O.aplicar_oferta_actual(pd.read_csv(DATA / "oferta_params.csv"))
diario = pd.read_csv(DATA / "afluencia_diaria_consolidada.csv", parse_dates=["fecha"])
mdf = P.mensualizar(diario)
uni, serv, detalle = O.proyectar_mensual_elastico(params, mdf, return_detalle=True)

serv.to_csv(OUT / "proyeccion_2027_resumen_mensual_elastico.csv")
uni.to_csv(OUT / "proyeccion_2027_unidades_mensual_elastico.csv")
detalle.to_csv(OUT / "detalle_calculo_mensual_elastico.csv", index=False)
O.analisis_mensual_historico(mdf).to_csv(OUT / "analisis_mensual_historico_servicio.csv", index=False)
O.resumen_historico_anual(mdf).to_csv(OUT / "resumen_historico_anual_servicio.csv", index=False)
O.factores_estacionalidad_mensual(params, mdf).to_csv(OUT / "factores_estacionalidad_mensual.csv", index=False)
uni[[c for c in uni.columns if str(c).startswith("TA_")]].to_csv(OUT / "proyeccion_2027_tren_araucania_tramos.csv")
O.perfil_distribucion_tren_araucania_por_tramo().to_csv(OUT / "tren_araucania_distribucion_historica_tramos.csv", index=False)

# Validación específica del ajuste de recuperación Laja-Talcahuano.
hist_laja = O.resumen_historico_anual(mdf)
hist_laja = hist_laja[hist_laja['servicio'] == 'CORTO_LAJA'].copy()
hist_laja['tipo_registro'] = 'historico_observado_normalizado'
hist_laja = hist_laja[['tipo_registro', 'anio', 'meses_observados', 'primer_mes', 'ultimo_mes', 'afluencia_observada_normalizada']]
proy_laja = pd.DataFrame([{
    'tipo_registro': 'proyeccion_2027_recuperacion_540k',
    'anio': 2027,
    'meses_observados': 12,
    'primer_mes': 1,
    'ultimo_mes': 12,
    'afluencia_observada_normalizada': int(serv['CORTO_LAJA'].sum()),
}])
pd.concat([hist_laja, proy_laja], ignore_index=True).to_csv(OUT / 'validacion_laja_recuperacion.csv', index=False)

plan = O.oferta_actual_df(mensual=True)
plan.loc[(plan.unit == "BIOTREN_L2") & (plan.mes == 3) & (plan.dt == "LV"), "servicios_dia"] += 10
_, serv2, _ = O.proyectar_mensual_elastico(params, mdf, plan=plan, return_detalle=True)
(serv2 - serv).reset_index().rename(columns={"index": "periodo"}).to_csv(
    OUT / "validacion_sensibilidad_cambio_oferta_marzo_l2.csv", index=False
)


# Validación específica de sensibilidad por tramo en Tren Araucanía.
base_ta = O.oferta_tren_araucania_tramos_df(mensual=True)
_, serv_base_ta, _ = O.proyectar_mensual_elastico(params, mdf, plan=base_ta, return_detalle=True)
registros_ta = []
for unit, dt, mes, delta in [
    ("TA_TEMUCO_VICTORIA", "LV", 3, 1.0),
    ("TA_TEMUCO_PITRUFQUEN", "LV", 3, 1.0),
    ("TA_CLARET", "LV", 3, 1.0),
    ("TA_CLARET", "LV", 1, 1.0),
]:
    plan_ta = base_ta.copy()
    m = (plan_ta.unit == unit) & (plan_ta.mes == mes) & (plan_ta.dt == dt)
    plan_ta.loc[m, "servicios_dia"] += delta
    _, serv_alt_ta, _ = O.proyectar_mensual_elastico(params, mdf, plan=plan_ta, return_detalle=True)
    periodo = f"2027-{mes:02d}"
    registros_ta.append({
        "unit": unit,
        "tramo": O.TA_TRAMO_NOMBRE.get(unit, unit),
        "mes": mes,
        "dt": dt,
        "delta_servicios_dia": delta,
        "impacto_mes": int(serv_alt_ta.loc[periodo, "TREN_ARAUCANIA"] - serv_base_ta.loc[periodo, "TREN_ARAUCANIA"]),
        "impacto_anual": int(serv_alt_ta["TREN_ARAUCANIA"].sum() - serv_base_ta["TREN_ARAUCANIA"].sum()),
    })
pd.DataFrame(registros_ta).to_csv(OUT / "validacion_sensibilidad_tren_araucania_tramos.csv", index=False)

print(serv.sum().to_string())
