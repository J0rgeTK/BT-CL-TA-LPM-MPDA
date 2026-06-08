"""
regenerar_datos.py -- reconstruye los CSV procesados desde la base de datos cruda.
Solo necesario si cambian los datos fuente. La app NO lo necesita en runtime.

Uso:
  1) Coloca la base cruda en:
       data/raw_bbdd/{BT,CL,LP,TA}/*.xlsx
       data/raw_rroo/Consolidado.xlsx
  2) python regenerar_datos.py
Genera: data/afluencia_diaria_consolidada.csv y data/oferta_params.csv
"""
import pipeline_afluencia as P
import oferta as O

BBDD = "data/raw_bbdd"
RROO = "data/raw_rroo/Consolidado.xlsx"
AF = "data/afluencia_diaria_consolidada.csv"

if __name__ == "__main__":
    diario = P.etl_afluencia_diaria(BBDD)
    diario.to_csv(AF, index=False)
    print(f"afluencia: {len(diario)} filas -> {AF}")
    params = O.construir_parametros(RROO, AF)
    params.to_csv("data/oferta_params.csv", index=False)
    print(f"oferta_params: {len(params)} filas -> data/oferta_params.csv")
