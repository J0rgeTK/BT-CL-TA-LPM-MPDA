"""
oferta.py -- motor de OFERTA del modelo de afluencia (v2, reformulado).

El modelo NO usa clima. Se basa en: fechas (estacionalidad, via mes-calendario) +
reporte operacional RROO (oferta operada y supresiones). La oferta 2027 es una
VARIABLE editable por el usuario (plan de servicios), por servicio y mes; para Biotren
se separa en Linea 1 y Linea 2 como dos unidades con su propia carga por viaje.

Unidades del modelo:
  BIOTREN_L1, BIOTREN_L2, CORTO_LAJA, TREN_ARAUCANIA, LLANQUIHUE_PM
La afluencia de Biotren se reparte L1/L2 con split fijo de matriz OD (20/80, supuesto).

Diccionario de estaciones Llanquihue-Puerto Montt (linea XP-NQ en RROO):
  XP=La Paloma, NQ=Llanquihue, AL=Alerce, EV=Puerto Varas.
Nota operacional: los servicios de Laja-Talcahuano (CORTO_LAJA) circulan dentro de la
operacion diaria de Linea 1 SOLO en el tramo Hualqui-Talcahuano (HQ-TH/TH-HQ), pero en
el RROO figuran como linea propia (CORTO LJ), por lo que NO se duplican con L1.
"""
import numpy as np
import pandas as pd

STATIONS = {"XP": "La Paloma", "NQ": "Llanquihue", "AL": "Alerce", "EV": "Puerto Varas"}

UNIT = {
    'BIOTREN L1': 'BIOTREN_L1', 'BIOTREN L2': 'BIOTREN_L2',
    'CORTO LJ': 'CORTO_LAJA',
    'XP - NQ': 'LLANQUIHUE_PM', 'XP-NQ': 'LLANQUIHUE_PM',
    'VI - TM': 'TREN_ARAUCANIA', 'VI-TM': 'TREN_ARAUCANIA',
}
SERVICIOS = ['BIOTREN', 'CORTO_LAJA', 'TREN_ARAUCANIA', 'LLANQUIHUE_PM']
UNIDADES_DE = {
    'BIOTREN': ['BIOTREN_L1', 'BIOTREN_L2'],
    'CORTO_LAJA': ['CORTO_LAJA'],
    'TREN_ARAUCANIA': ['TREN_ARAUCANIA'],
    'LLANQUIHUE_PM': ['LLANQUIHUE_PM'],
}
NOMBRE = {'BIOTREN': 'Biotren', 'CORTO_LAJA': 'Laja-Talcahuano',
          'TREN_ARAUCANIA': 'Tren Araucania', 'LLANQUIHUE_PM': 'Llanquihue-Puerto Montt'}


def construir_parametros(rroo_path, afluencia_csv, sheet='2024-2025-Mar2026',
                         biotren_split=(0.20, 0.80)):
    """Devuelve params por UNIDAD y mes: operados_hist, tasa_sup, pax_x_viaje."""
    r = pd.read_excel(rroo_path, sheet_name=sheet)
    r.columns = [c.strip() for c in r.columns]
    r['Fecha'] = pd.to_datetime(r['Fecha'])
    r['mes'] = r['Fecha'].dt.month
    r['ym'] = r['Fecha'].dt.to_period('M').astype(str)
    r['unit'] = r['LINEA'].map(UNIT)
    col = [c for c in r.columns if c.startswith('Atraso') and 'Salida' in c][0]
    r['sup'] = r['Salida Real'].isna() | r[col].astype(str).str.contains('SUP', case=False, na=False)
    r = r.dropna(subset=['unit'])

    # operados/mes-calendario y tasa de supresion
    nm = r.groupby(['unit', 'mes'])['ym'].nunique().reset_index(name='nm')
    agg = r.groupby(['unit', 'mes']).agg(prog=('sup', 'size'), sup=('sup', 'sum')).reset_index()
    agg = agg.merge(nm, on=['unit', 'mes'])
    agg['operados_hist'] = ((agg['prog'] - agg['sup']) / agg['nm']).round(0)
    agg['tasa_sup'] = (agg['sup'] / agg['prog']).round(4)

    # operados por ym (para pax_x_viaje)
    op_ym = r.groupby(['unit', 'ym']).apply(lambda d: (~d['sup']).sum()).reset_index(name='operados')

    # afluencia por unidad (Biotren split 20/80)
    af = pd.read_csv(afluencia_csv, parse_dates=['fecha'])
    af['ym'] = af['fecha'].dt.to_period('M').astype(str)
    afm = af.groupby(['servicio', 'ym'])['pasajeros'].sum().reset_index()
    recs = []
    for _, x in afm.iterrows():
        if x['servicio'] == 'BIOTREN':
            recs.append(('BIOTREN_L1', x['ym'], x['pasajeros'] * biotren_split[0]))
            recs.append(('BIOTREN_L2', x['ym'], x['pasajeros'] * biotren_split[1]))
        else:
            recs.append((x['servicio'], x['ym'], x['pasajeros']))
    afu = pd.DataFrame(recs, columns=['unit', 'ym', 'afluencia'])

    j = afu.merge(op_ym, on=['unit', 'ym'])
    j['mes'] = pd.to_datetime(j['ym'] + '-01').dt.month
    j['pxv'] = j['afluencia'] / j['operados'].replace(0, np.nan)
    pxv = j.groupby(['unit', 'mes'])['pxv'].mean().reset_index(name='pax_x_viaje')

    params = agg[['unit', 'mes', 'operados_hist', 'tasa_sup']].merge(pxv, on=['unit', 'mes'], how='left')
    # reindexar a 12 meses por unidad e imputar huecos (p.ej. LP meses sin RROO) con media del servicio
    full = pd.MultiIndex.from_product([params['unit'].unique(), range(1, 13)], names=['unit', 'mes'])
    params = params.set_index(['unit', 'mes']).reindex(full).reset_index()
    for col in ['operados_hist', 'tasa_sup', 'pax_x_viaje']:
        params[col] = params.groupby('unit')[col].transform(lambda s: s.fillna(s.mean()))
    params['operados_hist'] = params['operados_hist'].round(0)
    params['pax_x_viaje'] = params['pax_x_viaje'].round(1)
    params['tasa_sup'] = params['tasa_sup'].round(4)
    return params.sort_values(['unit', 'mes']).reset_index(drop=True)


def proyectar(params, plan=None, contingencia_extra=None):
    """Proyeccion 2027 por unidad y servicio.
    plan : df [unit, mes, servicios] (oferta planificada). None => operados_hist.
    contingencia_extra : dict unit->fraccion extra de supresion (0=como historico).
    Devuelve (por_unidad_df, por_servicio_df) en formato ancho (index 2027-MM).
    """
    p = params.copy()
    if plan is not None:
        p = p.merge(plan, on=['unit', 'mes'], how='left')
        p['servicios'] = p['servicios'].fillna(p['operados_hist'])
    else:
        p['servicios'] = p['operados_hist']
    ce = contingencia_extra or {}
    p['f_sup'] = (1 - p['tasa_sup'] - p['unit'].map(ce).fillna(0)).clip(0, 1)
    p['afluencia'] = (p['servicios'] * p['pax_x_viaje'] * p['f_sup']).round(0)

    uni = p.pivot(index='mes', columns='unit', values='afluencia')
    uni.index = [f'2027-{m:02d}' for m in uni.index]
    # agregar a servicio
    serv = pd.DataFrame(index=uni.index)
    for s, us in UNIDADES_DE.items():
        cols = [u for u in us if u in uni.columns]
        if cols:
            serv[s] = uni[cols].sum(axis=1)
    return uni.round(0).astype('Int64'), serv.round(0).astype('Int64')
