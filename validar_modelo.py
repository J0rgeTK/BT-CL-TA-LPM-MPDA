"""Validación técnica del modelo predictivo de afluencia EFE Sur.

El script ejecuta controles básicos de consistencia sobre el motor mensual,
el módulo OD híbrido de Biotren, las matrices de ingresos, el calendario
operacional y las salidas exportadas. Genera un resumen auditable en /outputs.
"""
from __future__ import annotations

from pathlib import Path
import compileall
import numpy as np
import pandas as pd

import pipeline_afluencia as P
import oferta as O
import od_biotren_hibrido as ODH

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
OUT = BASE / "outputs"
OD_OUT = OUT / "od_biotren_hibrido"


def _ok(nombre: str, ok: bool, detalle: str = "") -> dict:
    return {"control": nombre, "estado": "OK" if ok else "REVISAR", "detalle": detalle}


def ejecutar_validacion() -> pd.DataFrame:
    rows = []

    # 1. Compilación del proyecto.
    compiled = compileall.compile_dir(str(BASE), quiet=1, force=False)
    rows.append(_ok("Compilación Python del proyecto", bool(compiled), "compileall sobre el directorio del modelo"))

    # 2. Ejecución del motor mensual.
    params = O.aplicar_oferta_actual(pd.read_csv(DATA / "oferta_params.csv"))
    diario = pd.read_csv(DATA / "afluencia_diaria_consolidada.csv", parse_dates=["fecha"])
    mdf = P.mensualizar(diario)
    uni, serv, detalle = O.proyectar_mensual_elastico(params, mdf, return_detalle=True)
    total_servicios = serv.sum().sum()
    rows.append(_ok("Ejecución del motor mensual-elástico", total_servicios > 0, f"Total sistema: {total_servicios:,.0f}"))

    # 3. Sensibilidad mensual: cambio en marzo L2 debe afectar marzo y no todos los meses.
    plan = O.oferta_actual_df(mensual=True)
    plan.loc[(plan.unit == "BIOTREN_L2") & (plan.mes == 3) & (plan.dt == "LV"), "servicios_dia"] += 10
    _, serv_alt, _ = O.proyectar_mensual_elastico(params, mdf, plan=plan, return_detalle=True)
    dif = (serv_alt["BIOTREN"] - serv["BIOTREN"]).astype(float)
    meses_con_cambio = dif[dif.abs() > 1e-6].index.tolist()
    rows.append(_ok("Sensibilidad mensual por oferta", meses_con_cambio == ["2027-03"], f"Meses con cambio: {meses_con_cambio}"))

    # 4. Feriados: Biotren sin operación, Laja opera como fin de semana.
    cal = O.calendario_diario_operacional(2027, units=["BIOTREN_L2", "CORTO_LAJA"])
    fer = cal[cal["es_feriado"]]
    biotren_fer_ok = bool((fer[fer.unit == "BIOTREN_L2"]["opera"] == False).all())
    laja_fer_ok = bool((fer[fer.unit == "CORTO_LAJA"]["opera"] == True).all())
    rows.append(_ok("Regla de feriados Biotren", biotren_fer_ok, "Biotren queda sin operación en feriados nacionales"))
    rows.append(_ok("Regla de feriados Laja-Talcahuano", laja_fer_ok, "Laja-Talcahuano opera feriados con regla fin de semana"))

    # 5. OD híbrido: ejecución y consistencia de totales.
    resultado = ODH.distribuir_proyeccion_biotren(serv["BIOTREN"].astype(float))
    od_resumen = resultado["resumen"].copy()
    od_total_mes = od_resumen.groupby("periodo")["viajes_tipo_proyectados"].sum()
    dif_od = od_total_mes.sub(serv["BIOTREN"].astype(float), fill_value=0).abs().max()
    rows.append(_ok("Consistencia OD mensual vs Biotren", dif_od < 1e-5, f"Diferencia máxima: {dif_od:.8f}"))

    # 6. Matrices por tipo: orden, dimensiones e ingresos.
    station_order = resultado["station_order"]
    dim_ok = True
    ingreso_dim_ok = True
    for key, M in resultado["matrices_viajes"].items():
        dim_ok = dim_ok and list(M.index) == station_order and list(M.columns) == station_order
        R = resultado["matrices_ingresos"][key]
        ingreso_dim_ok = ingreso_dim_ok and list(R.index) == station_order and list(R.columns) == station_order and R.shape == M.shape
    rows.append(_ok("Orden original de estaciones en matrices OD", bool(dim_ok), f"Estaciones: {len(station_order)}"))
    rows.append(_ok("Dimensión matriz ingresos vs viajes", bool(ingreso_dim_ok), "Índices, columnas y dimensiones coinciden"))

    # 7. Tarifas y distancias para pares con viajes proyectados.
    viajes = resultado["viajes_long"]
    ingresos = resultado["ingresos_long"]
    merged = viajes.merge(ingresos, on=["periodo", "mes", "tipo_pasajero", "origen", "destino"], how="left")
    zero_income = int(((merged["viajes_proyectados"] > 1e-9) & (merged["ingresos_proyectados"].fillna(0) <= 0)).sum())
    rows.append(_ok("Viajes proyectados con ingreso no positivo", zero_income == 0, f"Pares detectados: {zero_income}"))

    # 8. Cobertura de archivos exportados.
    expected = [
        OUT / "proyeccion_2027_resumen_mensual_elastico.csv",
        OUT / "proyeccion_2027_unidades_mensual_elastico.csv",
        OUT / "detalle_calculo_mensual_elastico.csv",
        OD_OUT / "od_2027_viajes_por_tipo_long.csv",
        OD_OUT / "od_2027_ingresos_por_tipo_long.csv",
        OD_OUT / "od_biotren_2027_hibrido_por_tipo.xlsx",
    ]
    missing = [p.name for p in expected if not p.exists()]
    rows.append(_ok("Archivos de salida principales", len(missing) == 0, "Faltantes: " + (", ".join(missing) if missing else "ninguno")))

    out = pd.DataFrame(rows)
    out.to_csv(OUT / "resumen_validacion_tecnica.csv", index=False)
    return out


if __name__ == "__main__":
    print(ejecutar_validacion().to_string(index=False))
