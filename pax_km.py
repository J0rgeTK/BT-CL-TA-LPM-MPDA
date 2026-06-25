"""Cálculo de pax-km por servicio a partir de matrices OD proyectadas.

La demanda mensual proyectada se conserva en los módulos OD de cada servicio.
Este módulo sólo incorpora la matriz de distancias por par OD para estimar:

- pax-km mensual y anual;
- distancia media por pasajero;
- detalle OD mensual con distancia y pax-km.

Para Llanquihue-Puerto Montt se normaliza la matriz de distancias, pero el
pax-km queda no disponible hasta incorporar una MOD/distribución OD del servicio.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
import unicodedata

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "distancias"
DISTANCIAS_LONG = DATA_DIR / "distancias_od_servicio_long.csv"
VALIDACION_DISTANCIAS = DATA_DIR / "validacion_distancias_od.csv"

SERVICIOS_CON_OD_PAXKM = {"BIOTREN", "CORTO_LAJA", "TREN_ARAUCANIA"}


def _strip_accents(value) -> str:
    value = "" if value is None else str(value).strip()
    return "".join(ch for ch in unicodedata.normalize("NFKD", value) if not unicodedata.combining(ch))


def estacion_key(value) -> str:
    value = _strip_accents(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


@lru_cache(maxsize=1)
def cargar_distancias() -> pd.DataFrame:
    if not DISTANCIAS_LONG.exists():
        raise FileNotFoundError(f"No existe archivo de distancias OD: {DISTANCIAS_LONG}")
    df = pd.read_csv(DISTANCIAS_LONG)
    df["distancia_km"] = pd.to_numeric(df["distancia_km"], errors="coerce").fillna(0.0)
    df["origen_key"] = df["origen"].map(estacion_key)
    df["destino_key"] = df["destino"].map(estacion_key)
    return df


@lru_cache(maxsize=1)
def cargar_validacion_distancias() -> pd.DataFrame:
    if VALIDACION_DISTANCIAS.exists():
        return pd.read_csv(VALIDACION_DISTANCIAS)
    return pd.DataFrame()


def anexar_distancia_y_pax_km(servicio: str, viajes_long: pd.DataFrame, viajes_col: str = "viajes_proyectados") -> pd.DataFrame:
    """Devuelve detalle OD con distancia y pax-km.

    Requiere columnas `origen`, `destino` y `viajes_col` en `viajes_long`.
    Si un par OD no tiene distancia, se marca `sin_distancia=True` y se imputa 0 km
    para no romper el flujo del dashboard; el control queda visible en el resumen.
    """
    servicio = str(servicio)
    if viajes_long is None or viajes_long.empty:
        return pd.DataFrame()
    required = {"origen", "destino", viajes_col}
    missing = required - set(viajes_long.columns)
    if missing:
        raise ValueError(f"Faltan columnas para pax-km {servicio}: {sorted(missing)}")

    dist = cargar_distancias()
    dist = dist[dist["servicio"].eq(servicio)][["origen_key", "destino_key", "distancia_km"]].copy()
    out = viajes_long.copy()
    out["origen_key"] = out["origen"].map(estacion_key)
    out["destino_key"] = out["destino"].map(estacion_key)
    out = out.merge(dist, on=["origen_key", "destino_key"], how="left")
    out["sin_distancia"] = out["distancia_km"].isna()
    out["distancia_km"] = out["distancia_km"].fillna(0.0).astype(float)
    out["viajes_pax_km_base"] = pd.to_numeric(out[viajes_col], errors="coerce").fillna(0.0)
    out["pax_km"] = out["viajes_pax_km_base"] * out["distancia_km"]
    return out.drop(columns=["origen_key", "destino_key"], errors="ignore")


def resumen_pax_km(servicio: str, viajes_long: pd.DataFrame, viajes_col: str = "viajes_proyectados") -> dict[str, pd.DataFrame | dict]:
    servicio = str(servicio)
    if servicio not in SERVICIOS_CON_OD_PAXKM:
        return {
            "detalle": pd.DataFrame(),
            "resumen_mensual": pd.DataFrame(),
            "resumen_anual": {
                "servicio": servicio,
                "pax_km_total": np.nan,
                "distancia_media_km": np.nan,
                "viajes_total": np.nan,
                "pares_sin_distancia": np.nan,
                "disponible": False,
                "observacion": "Sin MOD/distribución OD incorporada al modelo.",
            },
        }
    detalle = anexar_distancia_y_pax_km(servicio, viajes_long, viajes_col=viajes_col)
    if detalle.empty:
        return {
            "detalle": detalle,
            "resumen_mensual": pd.DataFrame(),
            "resumen_anual": {
                "servicio": servicio,
                "pax_km_total": 0.0,
                "distancia_media_km": np.nan,
                "viajes_total": 0.0,
                "pares_sin_distancia": 0,
                "disponible": True,
                "observacion": "Sin viajes OD para calcular pax-km.",
            },
        }
    periodo_col = "periodo" if "periodo" in detalle.columns else None
    if periodo_col:
        mensual = detalle.groupby(periodo_col, as_index=False).agg(
            viajes_total=("viajes_pax_km_base", "sum"),
            pax_km_total=("pax_km", "sum"),
            pares_sin_distancia=("sin_distancia", "sum"),
        )
        mensual["distancia_media_km"] = np.where(
            mensual["viajes_total"] > 0,
            mensual["pax_km_total"] / mensual["viajes_total"],
            np.nan,
        )
    else:
        mensual = pd.DataFrame()
    viajes_total = float(detalle["viajes_pax_km_base"].sum())
    pax_km_total = float(detalle["pax_km"].sum())
    resumen = {
        "servicio": servicio,
        "pax_km_total": pax_km_total,
        "distancia_media_km": pax_km_total / viajes_total if viajes_total else np.nan,
        "viajes_total": viajes_total,
        "pares_sin_distancia": int(detalle["sin_distancia"].sum()),
        "disponible": True,
        "observacion": "Calculado sobre MOD/distribución OD proyectada.",
    }
    return {"detalle": detalle, "resumen_mensual": mensual, "resumen_anual": resumen}


def matriz_pax_km(detalle_pax_km: pd.DataFrame, filtro_col: str | None = None, filtro_valor: str | None = None) -> pd.DataFrame:
    if detalle_pax_km is None or detalle_pax_km.empty:
        return pd.DataFrame()
    df = detalle_pax_km.copy()
    if filtro_col and filtro_valor is not None and filtro_col in df.columns:
        df = df[df[filtro_col].astype(str).eq(str(filtro_valor))].copy()
    if df.empty:
        return pd.DataFrame()
    return df.pivot_table(index="origen", columns="destino", values="pax_km", aggfunc="sum", fill_value=0.0)
