"""Validación técnica del modelo predictivo de afluencia EFE Sur.

El script ejecuta controles básicos de consistencia sobre el motor mensual,
el módulo OD híbrido de Biotren, las matrices de ingresos, el calendario
operacional y las salidas exportadas. Genera un resumen auditable en /outputs.
"""
from __future__ import annotations

from pathlib import Path
import compileall
import subprocess
import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

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

    # 2. Verificación de que no queden binarios/caches versionados.
    git_files = subprocess.run(
        ["git", "ls-files"],
        cwd=BASE,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    patrones_binarios = (".pyc", ".pyo", ".pyd", ".zip", ".xlsx", ".xlsm", ".xls")
    versionados_no_permitidos = [
        f for f in git_files
        if "/__pycache__/" in f
        or f.startswith("__pycache__/")
        or "/_Pycache_/" in f
        or f.startswith("_Pycache_/")
        or f.lower().endswith(patrones_binarios)
    ]
    rows.append(_ok(
        "Sin binarios/cache versionados",
        len(versionados_no_permitidos) == 0,
        "Faltantes: ninguno" if not versionados_no_permitidos else ", ".join(versionados_no_permitidos[:5]),
    ))

    # 3. Ejecución del motor mensual.
    params = O.aplicar_oferta_actual(pd.read_csv(DATA / "oferta_params.csv"))
    diario = pd.read_csv(DATA / "afluencia_diaria_consolidada.csv", parse_dates=["fecha"])
    mdf = P.mensualizar(diario)
    uni, serv, detalle = O.proyectar_mensual_elastico(params, mdf, return_detalle=True)
    total_servicios = serv.sum().sum()
    rows.append(_ok("Ejecución del motor mensual-elástico", total_servicios > 0, f"Total sistema: {total_servicios:,.0f}"))

    # 4. Consistencia de totales mensuales/anuales entre detalle y resumen.
    serv_desde_detalle = detalle.groupby(["periodo", "servicio"])["afl"].sum().unstack()[serv.columns]
    dif_mensual = (serv_desde_detalle - serv).abs().max().max()
    dif_anual = (serv_desde_detalle.sum() - serv.sum()).abs().max()
    rows.append(_ok(
        "Consistencia mensual/anual del motor",
        bool(dif_mensual <= 0.5 and dif_anual <= 6.0),
        f"Diferencia mensual máxima: {dif_mensual:.6f}; anual máxima: {dif_anual:.6f}",
    ))

    # 5. Sensibilidad mensual: cambio en marzo L2 debe afectar marzo y no todos los meses.
    plan = O.oferta_actual_df(mensual=True)
    plan.loc[(plan.unit == "BIOTREN_L2") & (plan.mes == 3) & (plan.dt == "LV"), "servicios_dia"] += 10
    _, serv_alt, _ = O.proyectar_mensual_elastico(params, mdf, plan=plan, return_detalle=True)
    dif = (serv_alt["BIOTREN"] - serv["BIOTREN"]).astype(float)
    meses_con_cambio = dif[dif.abs() > 1e-6].index.tolist()
    rows.append(_ok("Sensibilidad mensual por oferta", meses_con_cambio == ["2027-03"], f"Meses con cambio: {meses_con_cambio}"))

    # 6. Feriados: Biotren sin operación, Laja opera como fin de semana.
    cal = O.calendario_diario_operacional(2027, units=["BIOTREN_L2", "CORTO_LAJA"])
    fer = cal[cal["es_feriado"]]
    biotren_fer_ok = bool((fer[fer.unit == "BIOTREN_L2"]["opera"] == False).all())
    laja_fer_ok = bool((fer[fer.unit == "CORTO_LAJA"]["opera"] == True).all())
    rows.append(_ok("Regla de feriados Biotren", biotren_fer_ok, "Biotren queda sin operación en feriados nacionales"))
    rows.append(_ok("Regla de feriados Laja-Talcahuano", laja_fer_ok, "Laja-Talcahuano opera feriados con regla fin de semana"))

    # 7. OD híbrido: ejecución y consistencia de totales.
    resultado = ODH.distribuir_proyeccion_biotren(serv["BIOTREN"].astype(float))
    od_resumen = resultado["resumen"].copy()
    od_total_mes = od_resumen.groupby("periodo")["viajes_tipo_proyectados"].sum()
    dif_od = od_total_mes.sub(serv["BIOTREN"].astype(float), fill_value=0).abs().max()
    rows.append(_ok("Consistencia OD mensual vs Biotren", dif_od < 1e-5, f"Diferencia máxima: {dif_od:.8f}"))

    # 8. Matrices por tipo: orden, dimensiones e ingresos.
    station_order = resultado["station_order"]
    dim_ok = True
    ingreso_dim_ok = True
    for key, M in resultado["matrices_viajes"].items():
        dim_ok = dim_ok and list(M.index) == station_order and list(M.columns) == station_order
        R = resultado["matrices_ingresos"][key]
        ingreso_dim_ok = ingreso_dim_ok and list(R.index) == station_order and list(R.columns) == station_order and R.shape == M.shape
    rows.append(_ok("Orden original de estaciones en matrices OD", bool(dim_ok), f"Estaciones: {len(station_order)}"))
    rows.append(_ok("Dimensión matriz ingresos vs viajes", bool(ingreso_dim_ok), "Índices, columnas y dimensiones coinciden"))

    # 9. Tarifas e ingresos para pares con viajes proyectados.
    viajes = resultado["viajes_long"]
    ingresos = resultado["ingresos_long"]
    merged = viajes.merge(ingresos, on=["periodo", "mes", "tipo_pasajero", "origen", "destino"], how="left")
    zero_income = int(((merged["viajes_proyectados"] > 1e-9) & (merged["ingresos_proyectados"].fillna(0) <= 0)).sum())
    rows.append(_ok("Viajes proyectados con ingreso no positivo", zero_income == 0, f"Pares detectados: {zero_income}"))

    # 10. Validación explícita de arreglos NumPy/Pandas no escribibles en el balance OD.
    seed_ro = np.array([[1.0, 2.0], [3.0, 4.0]])
    row_ro = np.array([30.0, 70.0])
    col_ro = np.array([45.0, 55.0])
    seed_ro.flags.writeable = False
    row_ro.flags.writeable = False
    col_ro.flags.writeable = False
    M_ro, conv_ro, _, err_ro = ODH.ipf(seed_ro, row_ro, col_ro)
    readonly_ok = bool(conv_ro and np.isfinite(err_ro) and np.allclose(M_ro.sum(axis=1), [30.0, 70.0]) and np.allclose(M_ro.sum(axis=0), [45.0, 55.0]))
    rows.append(_ok("OD compatible con arreglos read-only", readonly_ok, f"Converge: {conv_ro}; error: {err_ro:.2e}"))

    # 11. Insumos OD por tipo de tarjeta: estructura y consistencia.
    val_tipo_tarjeta = ODH.validar_insumos_tipo_tarjeta()
    for _, row in val_tipo_tarjeta.iterrows():
        rows.append(_ok(str(row["control"]), row["estado"] == "OK", str(row["detalle"])))

    # 11A. Clasificación OD por línea Biotren preparada para análisis MOD.
    mapeo_linea = ODH.cargar_mapeo_estacion_linea()
    od_historica_tarjeta = pd.read_csv(ODH.PROCESSED_FILES["od_historica_tipo_tarjeta"])
    estaciones_sin_mapeo = ODH.validar_estaciones_od_en_mapeo(od_historica_tarjeta, mapeo_linea)
    rows.append(_ok(
        "Estaciones OD con registro en mapeo línea",
        len(estaciones_sin_mapeo) == 0,
        "Sin registro: " + (", ".join(estaciones_sin_mapeo) if estaciones_sin_mapeo else "ninguna"),
    ))
    duplicadas_mapeo = mapeo_linea[mapeo_linea["estacion"].duplicated(keep=False)]["estacion"].tolist()
    rows.append(_ok(
        "Mapeo estación-línea sin duplicados",
        len(duplicadas_mapeo) == 0,
        "Duplicadas: " + (", ".join(duplicadas_mapeo) if duplicadas_mapeo else "ninguna"),
    ))
    lineas_invalidas = sorted(set(mapeo_linea["linea_base"].astype(str)) - ODH.LINEAS_BASE_BIOTREN_VALIDAS)
    rows.append(_ok(
        "Valores válidos de linea_base",
        len(lineas_invalidas) == 0,
        "Inválidos: " + (", ".join(lineas_invalidas) if lineas_invalidas else "ninguno"),
    ))
    concepcion = mapeo_linea[mapeo_linea["estacion"].map(ODH.canon) == "Concepción"]
    concepcion_ok = bool(
        len(concepcion) == 1
        and concepcion.iloc[0]["linea_base"] == "L1_L2"
        and int(concepcion.iloc[0]["es_estacion_comun"]) == 1
    )
    rows.append(_ok(
        "Concepción marcada como estación común/intercambio",
        concepcion_ok,
        "Registro: " + (concepcion[["estacion", "linea_base", "es_estacion_comun"]].to_dict("records").__str__() if len(concepcion) else "no encontrado"),
    ))
    conteo_lineas = mapeo_linea["linea_base"].value_counts().reindex(sorted(ODH.LINEAS_BASE_BIOTREN_VALIDAS), fill_value=0)
    rows.append(_ok(
        "Cantidad de estaciones por línea base",
        True,
        "; ".join(f"{k}: {int(v)}" for k, v in conteo_lineas.items()),
    ))
    od_clasificada = ODH.clasificar_od_por_linea(od_historica_tarjeta, mapeo_linea)
    viajes_col = "viajes_observados"
    total_original = float(od_historica_tarjeta[viajes_col].sum())
    total_clasificado = float(od_clasificada[viajes_col].sum())
    no_clasificados = float(od_clasificada.loc[od_clasificada["clasificacion_linea_od"] == "No clasificado", viajes_col].sum())
    pct_no_clasificado = no_clasificados / total_clasificado if total_clasificado else 0.0
    rows.append(_ok(
        "Proporción de viajes OD No clasificado",
        True,
        f"Viajes No clasificado: {no_clasificados:,.0f}; proporción: {pct_no_clasificado:.4%}",
    ))
    rows.append(_ok(
        "Clasificación OD por línea conserva total observado",
        abs(total_original - total_clasificado) <= 1e-8,
        f"Original: {total_original:,.0f}; clasificado: {total_clasificado:,.0f}; diferencia: {total_clasificado - total_original:.8f}",
    ))
    resumen_no_clasificado = ODH.resumir_od_no_clasificada(od_historica_tarjeta, mapeo_linea)
    top_no_clasificado = resumen_no_clasificado[resumen_no_clasificado["viajes_observados_totales"] > 0].head(20)
    pares_cero_no_clasificado = int((resumen_no_clasificado["viajes_observados_totales"] == 0).sum())
    motivos_no_clasificado = resumen_no_clasificado.groupby("motivo_probable")["viajes_observados_totales"].sum().sort_values(ascending=False)
    rows.append(_ok(
        "Top pares OD No clasificado por motivo probable",
        True,
        (
            "Motivos: "
            + "; ".join(f"{k}: {v:,.0f}" for k, v in motivos_no_clasificado.items())
            + f". Pares No clasificado sin viajes observados: {pares_cero_no_clasificado}"
            + ". Top: "
            + "; ".join(
                (
                    f"{r.origen}->{r.destino}: {r.viajes_observados_totales:,.0f} "
                    f"({r.porcentaje_sobre_total_no_clasificado:.4%} No clas.; "
                    f"{r.porcentaje_sobre_total_od_historico:.4%} total; {r.motivo_probable})"
                )
                for r in top_no_clasificado.itertuples(index=False)
            )
        ),
    ))

    # 12. Paso 2B mínimo: distribución por tipo de tarjeta e ingresos agregados en memoria.
    resultado_tarjetas = ODH.distribuir_proyeccion_biotren_por_tipo_tarjeta(serv["BIOTREN"].astype(float))
    resumen_tarjetas = resultado_tarjetas["resumen_tipo_tarjeta"]
    total_tarjetas_mes = resumen_tarjetas.groupby("periodo")["viajes_proyectados"].sum()
    dif_tarjetas = total_tarjetas_mes.sub(serv["BIOTREN"].astype(float), fill_value=0).abs().max()
    rows.append(_ok("Consistencia tarjeta mensual vs Biotren", dif_tarjetas < 1e-5, f"Diferencia máxima: {dif_tarjetas:.8f}"))

    ingresos_por_tarifa = resumen_tarjetas.groupby("tipo_pasajero_tarifa")["ingresos_tarifarios_proyectados"].sum()
    ingresos_con_tarifa_ok = bool((ingresos_por_tarifa.drop(labels=["Sin ingreso tarifario"], errors="ignore") > 0).all())
    ingreso_cero_ok = bool(ingresos_por_tarifa.get("Sin ingreso tarifario", 0.0) == 0.0)
    rows.append(_ok(
        "Ingreso tarifario agregado por tipo de tarjeta",
        ingresos_con_tarifa_ok and ingreso_cero_ok,
        "; ".join(f"{k}: {v:,.0f}" for k, v in ingresos_por_tarifa.items()),
    ))

    subsidio_ref = resultado_tarjetas["subsidio_referencial_base"]
    subsidio_ok = bool({"mes", "grupo_subsidio_referencial", "viajes_observados_base_referencial"}.issubset(subsidio_ref.columns) and len(subsidio_ref) > 0)
    rows.append(_ok("Base referencial de subsidio en memoria", subsidio_ok, f"Filas agregadas: {len(subsidio_ref)}; sin cálculo de montos"))

    # 13. Exportación controlada en modo muestra: un mes/tipo, sin escribir
    # outputs completos. Valida la ruta operativa sin generar archivos masivos.
    muestra_export = ODH.exportar_salidas_tipo_tarjeta(
        serv["BIOTREN"].astype(float),
        meses=[1],
        tipos_tarjeta=["monedero"],
        escribir_archivos=False,
    )
    muestra_ok = bool(
        len(muestra_export["viajes_tipo_tarjeta_long"]) > 0
        and len(muestra_export["ingresos_tipo_tarjeta_long"]) == len(muestra_export["viajes_tipo_tarjeta_long"])
        and len(muestra_export["base_subsidio_referencial_long"]) > 0
        and muestra_export["archivos"] == {}
    )
    rows.append(_ok(
        "Exportación tipo tarjeta en modo muestra sin outputs completos",
        muestra_ok,
        (
            f"Viajes: {len(muestra_export['viajes_tipo_tarjeta_long'])}; "
            f"ingresos: {len(muestra_export['ingresos_tipo_tarjeta_long'])}; "
            f"archivos escritos: {len(muestra_export['archivos'])}"
        ),
    ))

    # 14. Carga real de Streamlit mediante AppTest.
    app = AppTest.from_file(str(BASE / "streamlit_app.py"), default_timeout=30)
    app.run()
    rows.append(_ok("Carga de Streamlit", len(app.exception) == 0, f"Excepciones detectadas: {len(app.exception)}"))

    # 15. Cobertura de archivos exportados.
    expected = [
        OUT / "proyeccion_2027_resumen_mensual_elastico.csv",
        OUT / "proyeccion_2027_unidades_mensual_elastico.csv",
        OUT / "detalle_calculo_mensual_elastico.csv",
        OD_OUT / "od_2027_viajes_por_tipo_long.csv",
        OD_OUT / "od_2027_ingresos_por_tipo_long.csv",
        ODH.PROCESSED_FILES["orden_estaciones"],
        ODH.PROCESSED_FILES["od_historica"],
        ODH.PROCESSED_FILES["tarifas"],
        ODH.PROCESSED_FILES["distancias"],
        ODH.PROCESSED_FILES["validacion"],
        ODH.PROCESSED_FILES["od_historica_tipo_tarjeta"],
        ODH.PROCESSED_FILES["participacion_mensual_tipo_tarjeta"],
        ODH.PROCESSED_FILES["participacion_od_tipo_tarjeta"],
        ODH.PROCESSED_FILES["mapeo_tipo_tarjeta"],
        ODH.PROCESSED_FILES["base_subsidio_referencial"],
    ]
    missing = [p.name for p in expected if not p.exists()]
    rows.append(_ok("Archivos de salida principales", len(missing) == 0, "Faltantes: " + (", ".join(missing) if missing else "ninguno")))

    out = pd.DataFrame(rows)
    out.to_csv(OUT / "resumen_validacion_tecnica.csv", index=False)
    return out


if __name__ == "__main__":
    print(ejecutar_validacion().to_string(index=False))
