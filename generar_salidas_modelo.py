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
O.desagregar_tren_araucania_por_tramo(serv["TREN_ARAUCANIA"]).to_csv(OUT / "proyeccion_2027_tren_araucania_tramos.csv")

plan = O.oferta_actual_df(mensual=True)
plan.loc[(plan.unit == "BIOTREN_L2") & (plan.mes == 3) & (plan.dt == "LV"), "servicios_dia"] += 10
_, serv2, _ = O.proyectar_mensual_elastico(params, mdf, plan=plan, return_detalle=True)
(serv2 - serv).reset_index().rename(columns={"index": "periodo"}).to_csv(
    OUT / "validacion_sensibilidad_cambio_oferta_marzo_l2.csv", index=False
)

print(serv.sum().to_string())
