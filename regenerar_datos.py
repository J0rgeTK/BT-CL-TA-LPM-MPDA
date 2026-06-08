"""
regenerar_datos.py -- reconstruye los CSV procesados desde la base cruda.
Solo necesario si cambian los datos fuente. La app NO lo necesita en runtime.

Pasos: coloca la base cruda en data/raw_bbdd/{BT,CL,LP,TA}/*.xlsx y
data/raw_rroo/Consolidado.xlsx ; luego: python regenerar_datos.py
"""
import pandas as pd
import pipeline_afluencia as P
import oferta as O

BBDD = "data/raw_bbdd"
RROO = "data/raw_rroo/Consolidado.xlsx"
AF = "data/afluencia_diaria_consolidada.csv"
CALIB_BIOTREN = 1.07          # ETL vs Resumen oficial (factor estable 1.070 +- 0.006)
VENTANA_MESES = 12            # ancla parametros de oferta en el desempenio reciente

if __name__ == "__main__":
    diario = P.etl_afluencia_diaria(BBDD)
    # calibracion de nivel Biotren al Resumen oficial
    m = diario["servicio"] == "BIOTREN"
    diario.loc[m, "pasajeros"] = (diario.loc[m, "pasajeros"] * CALIB_BIOTREN).round(0)
    diario.to_csv(AF, index=False)
    print(f"afluencia: {len(diario)} filas -> {AF} (Biotren x{CALIB_BIOTREN})")
    params = O.construir_parametros(RROO, AF, ventana_meses=VENTANA_MESES)
    params.to_csv("data/oferta_params.csv", index=False)
    print(f"oferta_params: {len(params)} filas -> data/oferta_params.csv (ventana {VENTANA_MESES}m)")
