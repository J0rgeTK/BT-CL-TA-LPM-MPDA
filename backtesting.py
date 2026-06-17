"""Backtesting histórico del modelo predictivo EFE Sur.

El módulo compara, por servicio y mes, la afluencia observada histórica contra
la estimación generada con el mismo motor mensual-elástico vigente. No modifica
la lógica de proyección 2027, no escribe outputs masivos y no toca insumos OD.

Alcance metodológico:
- Es una validación retrospectiva diagnóstica, no un holdout estricto.
- Por defecto evalúa todos los años con observación histórica disponibles antes
  de 2027 y sólo compara meses efectivamente observados.
- Usa la afluencia mensual normalizada (`pax_norm`) producida por
  `pipeline_afluencia.mensualizar`, conservando la cobertura mensual como señal
  de meses incompletos.
- Usa los parámetros vigentes recibidos por el llamador y el motor
  mensual-elástico vigente. Si esos parámetros incorporan información posterior
  al periodo evaluado, el resultado debe leerse como diagnóstico retrospectivo y
  no como prueba predictiva fuera de muestra.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

import oferta as O


METRIC_COLUMNS = ["MAE", "RMSE", "MAPE", "WMAPE", "sesgo"]
BACKTESTING_TIPO = "retrospectivo_diagnostico_no_holdout"


@dataclass(frozen=True)
class BacktestResult:
    """Contenedor de resultados de backtesting."""

    observado_estimado: pd.DataFrame
    errores_mensuales: pd.DataFrame
    metricas_servicio: pd.DataFrame
    resumen_total_sistema: pd.DataFrame
    advertencias: list[str]
    diagnosticos: dict[str, pd.DataFrame]


def _as_prepared_mdf(mdf: pd.DataFrame) -> pd.DataFrame:
    g = O._preparar_mdf(mdf)  # reutiliza normalización histórica del motor vigente
    required = {"servicio", "anio", "m", "pax_norm"}
    missing = required - set(g.columns)
    if missing:
        raise ValueError(f"mdf no contiene columnas requeridas: {sorted(missing)}")
    return g


def observed_monthly(mdf: pd.DataFrame, anios: list[int] | tuple[int, ...]) -> pd.DataFrame:
    """Retorna observado mensual histórico por servicio para los años solicitados."""
    years = {int(y) for y in anios}
    g = _as_prepared_mdf(mdf)
    obs = (
        g[g["anio"].isin(years)]
        .groupby(["servicio", "anio", "m"], as_index=False)
        .agg(observado=("pax_norm", "sum"), cobertura=("cobertura", "mean"))
    )
    obs["periodo"] = obs.apply(lambda r: f"{int(r.anio)}-{int(r.m):02d}", axis=1)
    return obs[["servicio", "anio", "m", "periodo", "observado", "cobertura"]].sort_values(["servicio", "periodo"])


def estimate_for_year(params: pd.DataFrame, mdf: pd.DataFrame, anio: int) -> pd.DataFrame:
    """Genera estimación mensual por servicio para un año histórico con el motor vigente."""
    _, serv, _ = O.proyectar_mensual_elastico(params, mdf, anio=int(anio), return_detalle=True)
    est = serv.reset_index(names="periodo").melt(id_vars="periodo", var_name="servicio", value_name="estimado")
    est["anio"] = int(anio)
    est["m"] = est["periodo"].str[-2:].astype(int)
    return est[["servicio", "anio", "m", "periodo", "estimado"]]


def comparar_observado_estimado(params: pd.DataFrame, mdf: pd.DataFrame, anios: list[int] | tuple[int, ...]) -> pd.DataFrame:
    """Construye tabla observado vs estimado por servicio, año y mes."""
    obs = observed_monthly(mdf, anios)
    est = pd.concat([estimate_for_year(params, mdf, int(y)) for y in sorted(set(anios))], ignore_index=True)
    out = obs.merge(est, on=["servicio", "anio", "m", "periodo"], how="left")
    out["estimado"] = pd.to_numeric(out["estimado"], errors="coerce")
    out["observado"] = pd.to_numeric(out["observado"], errors="coerce")
    out["error"] = out["estimado"] - out["observado"]
    out["error_abs"] = out["error"].abs()
    out["error_pct"] = np.where(out["observado"].abs() > 0, out["error"] / out["observado"], np.nan)
    return out.sort_values(["servicio", "periodo"]).reset_index(drop=True)


def calcular_metricas(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Calcula MAE, RMSE, MAPE, WMAPE y sesgo para los grupos indicados."""
    rows = []
    for keys, d in df.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        obs = d["observado"].astype(float)
        err = d["error"].astype(float)
        denom = obs.abs().sum()
        rows.append({
            **dict(zip(group_cols, keys)),
            "n_meses": int(len(d)),
            "n_meses_mape": int(obs.abs().gt(0).sum()),
            "n_meses_observado_cero": int(obs.abs().eq(0).sum()),
            "observado_total": float(obs.sum()),
            "estimado_total": float(d["estimado"].astype(float).sum()),
            "MAE": float(err.abs().mean()),
            "RMSE": float(np.sqrt(np.mean(np.square(err)))),
            "MAPE": float((err.abs() / obs.abs().replace(0, np.nan)).mean() * 100),
            "WMAPE": float(err.abs().sum() / denom * 100) if denom else np.nan,
            "sesgo": float(err.sum() / denom * 100) if denom else np.nan,
        })
    return pd.DataFrame(rows)


def agregar_diagnosticos_mensuales(comp: pd.DataFrame) -> pd.DataFrame:
    """Agrega sesgo mensual y contribución al error absoluto total del sistema."""
    out = comp.copy()
    total_error_abs = float(out["error_abs"].sum())
    out["sesgo_mensual"] = out["error_pct"]
    out["contribucion_error_total_sistema"] = out["error_abs"] / total_error_abs if total_error_abs else np.nan
    out["mes_calendario"] = out["m"].astype(int)
    out["bloque_calendario"] = np.select(
        [
            out["mes_calendario"].isin([1, 2]),
            out["mes_calendario"].isin([3, 4, 5, 6, 7, 8, 9, 10, 11, 12]),
        ],
        ["estival", "no_estival"],
        default="sin_clasificar",
    )
    out["bloque_escolar_ta"] = np.where(out["mes_calendario"].isin([3, 4, 5, 6, 7, 8, 9, 10, 11, 12]), "escolar", "no_escolar")
    return out


def diagnostico_componentes_estimados(params: pd.DataFrame, mdf: pd.DataFrame, anios: list[int] | tuple[int, ...],
                                      comp: pd.DataFrame) -> pd.DataFrame:
    """Resume componentes internos estimados cuando el motor los expone.

    La base observada mensual disponible es por servicio agregado; por eso este
    diagnóstico no asigna observado a componentes. Se usa para localizar cuánto
    aporta cada componente interno a la estimación del servicio.
    """
    frames = []
    for anio in sorted(set(int(y) for y in anios)):
        _, _, detalle = O.proyectar_mensual_elastico(params, mdf, anio=anio, return_detalle=True)
        d = detalle.copy()
        d["anio"] = anio
        d["mes_calendario"] = d["mes"].astype(int)
        d["periodo"] = d["mes_calendario"].map(lambda m: f"{anio}-{int(m):02d}")
        d["componente"] = d["unit"].map(O.TA_TRAMO_NOMBRE).fillna(d["unit"])
        frames.append(
            d.groupby(["servicio", "anio", "mes_calendario", "periodo", "unit", "componente"], as_index=False)
            .agg(estimado_componente=("afl", "sum"), viajes_operados_plan=("viajes_operados_plan", "sum"))
        )
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    periodos_observados = comp[["servicio", "periodo"]].drop_duplicates()
    out = out.merge(periodos_observados, on=["servicio", "periodo"], how="inner")
    total = out.groupby(["servicio", "anio", "mes_calendario", "periodo"], as_index=False)["estimado_componente"].sum()
    total = total.rename(columns={"estimado_componente": "estimado_servicio"})
    out = out.merge(total, on=["servicio", "anio", "mes_calendario", "periodo"], how="left")
    out["participacion_estimado_servicio"] = out["estimado_componente"] / out["estimado_servicio"].replace(0, np.nan)
    out["bloque_escolar_ta"] = np.where(out["mes_calendario"].isin([3, 4, 5, 6, 7, 8, 9, 10, 11, 12]), "escolar", "no_escolar")
    return out


def generar_advertencias_servicio(metricas_servicio: pd.DataFrame, umbral_wmape: float = 25.0) -> pd.DataFrame:
    """Genera advertencias diagnósticas livianas por servicio."""
    rows = []
    for r in metricas_servicio.itertuples(index=False):
        mensajes = []
        if float(r.WMAPE) >= umbral_wmape:
            mensajes.append(f"WMAPE sobre umbral {umbral_wmape:.0f}%")
        if abs(float(r.sesgo)) >= 10.0:
            direccion = "sobreestimación" if float(r.sesgo) > 0 else "subestimación"
            mensajes.append(f"sesgo agregado relevante ({direccion})")
        if not mensajes:
            mensajes.append("sin alerta cuantitativa principal")
        rows.append({
            "servicio": r.servicio,
            "WMAPE": float(r.WMAPE),
            "sesgo": float(r.sesgo),
            "advertencia": "; ".join(mensajes),
        })
    return pd.DataFrame(rows).sort_values(["WMAPE", "servicio"], ascending=[False, True])


def ejecutar_backtesting(params: pd.DataFrame, mdf: pd.DataFrame, anios: list[int] | tuple[int, ...] | None = None) -> BacktestResult:
    """Ejecuta backtesting por servicio y total sistema.

    Si no se entregan años, usa años históricos con datos disponibles excluyendo
    2027 para no interferir con el escenario vigente.
    """
    g = _as_prepared_mdf(mdf)
    if anios is None:
        anios = sorted(int(y) for y in g.loc[g["anio"] < 2027, "anio"].dropna().unique())
    comp = comparar_observado_estimado(params, mdf, anios)
    comp = agregar_diagnosticos_mensuales(comp)
    metricas_servicio = calcular_metricas(comp, ["servicio"])
    resumen_servicio_anio = calcular_metricas(comp, ["servicio", "anio"])
    resumen_servicio_mes_calendario = calcular_metricas(comp, ["servicio", "mes_calendario"])
    contribucion_servicio = (
        comp.groupby("servicio", as_index=False)
        .agg(
            error_abs=("error_abs", "sum"),
            error_neto=("error", "sum"),
            contribucion_error_total_sistema=("contribucion_error_total_sistema", "sum"),
            observado_total=("observado", "sum"),
            estimado_total=("estimado", "sum"),
        )
        .sort_values("contribucion_error_total_sistema", ascending=False)
    )
    contribucion_anio = calcular_metricas(comp, ["anio"])
    componentes = diagnostico_componentes_estimados(params, mdf, anios, comp)
    advertencias_servicio = generar_advertencias_servicio(metricas_servicio)

    sistema = comp.groupby(["anio", "m", "periodo"], as_index=False).agg(observado=("observado", "sum"), estimado=("estimado", "sum"))
    sistema["servicio"] = "TOTAL_SISTEMA"
    sistema["error"] = sistema["estimado"] - sistema["observado"]
    sistema["error_abs"] = sistema["error"].abs()
    sistema["error_pct"] = np.where(sistema["observado"].abs() > 0, sistema["error"] / sistema["observado"], np.nan)
    resumen_total = calcular_metricas(sistema, ["servicio"])

    advertencias = [
        "Tipo de backtesting: retrospectivo diagnóstico, no holdout estricto fuera de muestra.",
        "Años evaluados por defecto: todos los años históricos disponibles antes de 2027; sólo se comparan meses con observación.",
        "Dato observado: afluencia mensual normalizada pax_norm de pipeline_afluencia.mensualizar; la cobertura se reporta para identificar meses incompletos.",
        "Parámetros estimadores: parámetros vigentes entregados al módulo y motor mensual-elástico vigente; pueden incorporar información posterior al periodo evaluado.",
        "Backtesting diagnóstico: evalúa desempeño histórico y no recalibra ni altera el escenario vigente 2027.",
        "Las estimaciones usan el motor mensual-elástico vigente; los feriados parametrizados explícitamente corresponden al horizonte 2027.",
        "MAPE excluye meses con observado cero y puede ser inestable cuando el observado mensual es bajo; WMAPE se usa como métrica agregada principal.",
        "La comparación se limita a meses con observación histórica disponible y no genera outputs masivos ni modifica data/od_biotren/processed/.",
        "Los componentes internos se reportan sólo para estimados cuando no existe observado desagregado comparable por componente.",
    ]
    diagnosticos = {
        "resumen_servicio_anio": resumen_servicio_anio,
        "resumen_servicio_mes_calendario": resumen_servicio_mes_calendario,
        "contribucion_servicio": contribucion_servicio,
        "contribucion_anio": contribucion_anio,
        "componentes_estimados": componentes,
        "advertencias_servicio": advertencias_servicio,
    }
    return BacktestResult(comp, comp.copy(), metricas_servicio, resumen_total, advertencias, diagnosticos)
