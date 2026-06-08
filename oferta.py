"""
oferta.py -- motor de OFERTA del modelo de afluencia (v3, por tipo de dia).

El modelo NO usa clima. Base: fechas (estacionalidad) + reporte operacional (RROO).
La oferta de trenes es la VARIABLE de planificacion, editable por el usuario y
diferenciada por TIPO DE DIA (Lunes-Viernes 'LV', Sabado 'Sab', Domingo 'Dom') y mes.

Unidades: BIOTREN_L1, BIOTREN_L2, CORTO_LAJA, TREN_ARAUCANIA, LLANQUIHUE_PM.
La afluencia de Biotren se reparte 20/80 (L1/L2, matriz OD; supuesto).

Estaciones Llanquihue-PM (XP-NQ): XP=La Paloma, NQ=Llanquihue, AL=Alerce, EV=Puerto Varas.
Nota: los servicios Laja-Talcahuano circulan por L1 (Hualqui-Talcahuano) pero en el RROO
figuran como linea propia (CORTO LJ); no se duplican con L1.

Modelo por unidad/mes:
  afluencia = SUMA_tipo_dia [ servicios_por_dia x n_dias_2027 x pax_por_viaje x (1-supresion) ]
"""
import numpy as np
import pandas as pd

STATIONS = {"XP": "La Paloma", "NQ": "Llanquihue", "AL": "Alerce", "EV": "Puerto Varas"}
UNIT = {'BIOTREN L1': 'BIOTREN_L1', 'BIOTREN L2': 'BIOTREN_L2', 'CORTO LJ': 'CORTO_LAJA',
        'XP - NQ': 'LLANQUIHUE_PM', 'XP-NQ': 'LLANQUIHUE_PM',
        'VI - TM': 'TREN_ARAUCANIA', 'VI-TM': 'TREN_ARAUCANIA'}
SERVICIOS = ['BIOTREN', 'CORTO_LAJA', 'TREN_ARAUCANIA', 'LLANQUIHUE_PM']
UNIDADES_DE = {'BIOTREN': ['BIOTREN_L1', 'BIOTREN_L2'], 'CORTO_LAJA': ['CORTO_LAJA'],
               'TREN_ARAUCANIA': ['TREN_ARAUCANIA'], 'LLANQUIHUE_PM': ['LLANQUIHUE_PM']}
NOMBRE = {'BIOTREN': 'Biotren', 'CORTO_LAJA': 'Laja-Talcahuano',
          'TREN_ARAUCANIA': 'Tren Araucania', 'LLANQUIHUE_PM': 'Llanquihue-Puerto Montt'}
DTYPES = ['LV', 'Sab', 'Dom']
DTNOMBRE = {'LV': 'Lunes a Viernes', 'Sab': 'Sabado', 'Dom': 'Domingo'}


def _dt(dow):
    return 'LV' if dow < 5 else ('Sab' if dow == 5 else 'Dom')


def construir_parametros(rroo_path, afluencia_csv, sheet='2024-2025-Mar2026',
                         biotren_split=(0.20, 0.80), ventana_meses=12):
    """ventana_meses: usa solo los ultimos N meses para estimar servicios_dia y
    pax_por_viaje (refleja el desempenio reciente). None => toda la historia."""
    r = pd.read_excel(rroo_path, sheet_name=sheet)
    r.columns = [c.strip() for c in r.columns]
    r['Fecha'] = pd.to_datetime(r['Fecha'])
    _af_fechas = pd.read_csv(afluencia_csv, parse_dates=['fecha'])['fecha']
    if ventana_meses:
        maxd = min(r['Fecha'].max(), _af_fechas.max())
        corte = maxd - pd.DateOffset(months=ventana_meses)
        r = r[r['Fecha'] >= corte]
    r['unit'] = r['LINEA'].map(UNIT)
    col = [c for c in r.columns if c.startswith('Atraso') and 'Salida' in c][0]
    r['sup'] = r['Salida Real'].isna() | r[col].astype(str).str.contains('SUP', case=False, na=False)
    r = r.dropna(subset=['unit'])
    r['mes'] = r['Fecha'].dt.month
    r['dt'] = r['Fecha'].dt.dayofweek.map(_dt)
    r['d'] = r['Fecha'].dt.date

    perday = r.groupby(['unit', 'd', 'mes', 'dt']).agg(prog=('sup', 'size'), sup=('sup', 'sum')).reset_index()
    perday['oper'] = perday['prog'] - perday['sup']
    sd = perday.groupby(['unit', 'mes', 'dt']).agg(servicios_dia=('prog', 'mean'),
                                                   sup=('sup', 'sum'), prog=('prog', 'sum')).reset_index()
    sd['tasa_sup'] = (sd['sup'] / sd['prog']).round(4)
    sd = sd[['unit', 'mes', 'dt', 'servicios_dia', 'tasa_sup']]
    sd['servicios_dia'] = sd['servicios_dia'].round(1)

    af = pd.read_csv(afluencia_csv, parse_dates=['fecha'])
    if ventana_meses:
        af = af[af['fecha'] >= corte]
    recs = []
    for _, x in af.iterrows():
        if x['servicio'] == 'BIOTREN':
            recs.append(('BIOTREN_L1', x['fecha'], x['pasajeros'] * biotren_split[0]))
            recs.append(('BIOTREN_L2', x['fecha'], x['pasajeros'] * biotren_split[1]))
        else:
            recs.append((x['servicio'], x['fecha'], x['pasajeros']))
    afu = pd.DataFrame(recs, columns=['unit', 'fecha', 'afluencia'])
    afu['d'] = afu['fecha'].dt.date
    j = afu.merge(perday[['unit', 'd', 'oper']], on=['unit', 'd'])
    j = j[j['oper'] > 0]
    j['mes'] = pd.to_datetime(j['fecha']).dt.month
    j['dt'] = pd.to_datetime(j['fecha']).dt.dayofweek.map(_dt)
    j['pxv'] = j['afluencia'] / j['oper']
    pxv = j.groupby(['unit', 'mes', 'dt'])['pxv'].mean().reset_index(name='pax_x_viaje')

    params = sd.merge(pxv, on=['unit', 'mes', 'dt'], how='left')
    full = pd.MultiIndex.from_product([params['unit'].unique(), range(1, 13), DTYPES],
                                      names=['unit', 'mes', 'dt'])
    params = params.set_index(['unit', 'mes', 'dt']).reindex(full).reset_index()
    for c in ['servicios_dia', 'pax_x_viaje', 'tasa_sup']:
        params[c] = params.groupby(['unit', 'dt'])[c].transform(lambda s: s.fillna(s.mean()))
        params[c] = params.groupby('unit')[c].transform(lambda s: s.fillna(s.mean()))
    params['servicios_dia'] = params['servicios_dia'].round(1)
    params['pax_x_viaje'] = params['pax_x_viaje'].round(1)
    params['tasa_sup'] = params['tasa_sup'].round(4)
    return params.sort_values(['unit', 'mes', 'dt']).reset_index(drop=True)


def dias_por_tipo(anio=2027):
    d = pd.date_range(f'{anio}-01-01', f'{anio}-12-31')
    df = pd.DataFrame({'mes': d.month, 'dt': d.dayofweek.map(_dt)})
    return df.groupby(['mes', 'dt']).size().reset_index(name='n_dias')


def proyectar(params, plan=None, contingencia_extra=None, anio=2027):
    p = params.copy()
    if plan is not None:
        pl = plan[['unit', 'mes', 'dt', 'servicios_dia']].rename(columns={'servicios_dia': 'sd_plan'})
        pl['mes'] = pl['mes'].astype(int)
        p = p.merge(pl, on=['unit', 'mes', 'dt'], how='left')
        p['servicios_dia'] = pd.to_numeric(p['sd_plan'], errors='coerce').fillna(p['servicios_dia'])
        p = p.drop(columns='sd_plan')
    p = p.merge(dias_por_tipo(anio), on=['mes', 'dt'], how='left')
    ce = contingencia_extra or {}
    p['f_sup'] = (1 - p['tasa_sup'] - p['unit'].map(ce).fillna(0)).clip(0, 1)
    p['afl'] = p['servicios_dia'] * p['n_dias'] * p['pax_x_viaje'] * p['f_sup']
    uni = p.groupby(['unit', 'mes'])['afl'].sum().reset_index()
    uni_w = uni.pivot(index='mes', columns='unit', values='afl')
    uni_w.index = [f'{anio}-{m:02d}' for m in uni_w.index]
    serv = pd.DataFrame(index=uni_w.index)
    for s, us in UNIDADES_DE.items():
        cols = [u for u in us if u in uni_w.columns]
        if cols:
            serv[s] = uni_w[cols].sum(axis=1)
    return uni_w.round(0).astype('Int64'), serv.round(0).astype('Int64')
