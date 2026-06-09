"""
oferta.py -- motor de OFERTA del modelo de afluencia (v8, oferta vigente + calibracion mayo 2026).

El modelo NO usa clima. Base: fechas (estacionalidad) + reporte operacional (RROO).
La oferta de trenes es la VARIABLE de planificacion, editable por el usuario y
diferenciada por TIPO DE DIA (Lunes-Viernes 'LV', Sabado 'Sab', Domingo 'Dom') y mes.

Unidades: BIOTREN_L1, BIOTREN_L2, CORTO_LAJA, TREN_ARAUCANIA, LLANQUIHUE_PM.
La afluencia de Biotren se reparte 20/80 (L1/L2, matriz OD; supuesto).

Estaciones Llanquihue-PM (XP-NQ): XP=La Paloma, NQ=Llanquihue, AL=Alerce, EV=Puerto Varas.
Nota operacional: los servicios Laja-Talcahuano circulan sobre el corredor de L1,
pero se proyectan como CORTO_LAJA para no duplicar afluencia ni oferta. Por eso
BIOTREN_L1 se parametriza como oferta propia de Biotren L1, excluyendo los
servicios Laja-Talcahuano ya contabilizados en CORTO_LAJA.

Modelo por unidad/mes:
  proy_oferta = SUMA_tipo_dia [ servicios_por_dia x n_dias_2027 x pax_por_viaje x (1-supresion) ]
  Biotren y Tren Araucania: escenario recomendado = referencia estacional + factor parcial x (proy_oferta - referencia estacional)
"""
import numpy as np
import pandas as pd
from pathlib import Path

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

DATA_DIR = Path(__file__).resolve().parent / 'data'


# ---------------------------------------------------------------------------
# Oferta vigente informada para el escenario base del modelo.
#
# Criterio de no doble conteo:
# - L1 operacional total informada: 48 LV, 16 Sab, 8 Dom, incluyendo servicios
#   Laja-Talcahuano en un mes tipo.
# - Como CORTO_LAJA se modela por separado, BIOTREN_L1 queda sólo con la oferta
#   propia de Biotren: 40 LV, 8 Sab, 0 Dom.
# - CORTO_LAJA incorpora 8 servicios base y 2 cortos LV Hualqui-Talcamavida /
#   Talcamavida-Hualqui: 10 LV. En sábado y domingo usa 8 servicios en un mes
#   tipo, con excepción enero-febrero, donde se consideran 10 servicios.
# - Tren Araucania tiene diferencias L-J / viernes; el modelo usa tipo LV, por
#   lo que se usa promedio ponderado semanal: (4*19 + 1*17) / 5 = 18.6.
# ---------------------------------------------------------------------------
OFERTA_ACTUAL_MODELO = {
    'BIOTREN_L1': {'LV': 40.0, 'Sab': 8.0, 'Dom': 0.0},
    'BIOTREN_L2': {'LV': 106.0, 'Sab': 53.0, 'Dom': 32.0},
    'CORTO_LAJA': {'LV': 10.0, 'Sab': 8.0, 'Dom': 8.0},
    'TREN_ARAUCANIA': {'LV': 18.6, 'Sab': 12.0, 'Dom': 6.0},
    'LLANQUIHUE_PM': {'LV': 20.0, 'Sab': 0.0, 'Dom': 0.0},
}

# Excepciones mensuales respecto a la oferta tipo anterior. Se aplican sobre
# servicios_dia para que el resultado predictivo quede acorde con la oferta
# efectivamente informada por mes.
OFERTA_ACTUAL_EXCEPCIONES = [
    {'unit': 'CORTO_LAJA', 'mes': 1, 'dt': 'Sab', 'servicios_dia': 10.0,
     'detalle': 'Enero: 10 servicios sabado y domingo en lugar de 8'},
    {'unit': 'CORTO_LAJA', 'mes': 1, 'dt': 'Dom', 'servicios_dia': 10.0,
     'detalle': 'Enero: 10 servicios sabado y domingo en lugar de 8'},
    {'unit': 'CORTO_LAJA', 'mes': 2, 'dt': 'Sab', 'servicios_dia': 10.0,
     'detalle': 'Febrero: 10 servicios sabado y domingo en lugar de 8'},
    {'unit': 'CORTO_LAJA', 'mes': 2, 'dt': 'Dom', 'servicios_dia': 10.0,
     'detalle': 'Febrero: 10 servicios sabado y domingo en lugar de 8'},
]

OFERTA_ACTUAL_DETALLE = [
    {'servicio': 'Biotren L2', 'unit': 'BIOTREN_L2', 'dt': 'LV', 'servicios_dia': 106.0,
     'detalle': '106 servicios de lunes a viernes'},
    {'servicio': 'Biotren L2', 'unit': 'BIOTREN_L2', 'dt': 'Sab', 'servicios_dia': 53.0,
     'detalle': '53 servicios sabado'},
    {'servicio': 'Biotren L2', 'unit': 'BIOTREN_L2', 'dt': 'Dom', 'servicios_dia': 32.0,
     'detalle': '32 servicios domingo'},
    {'servicio': 'Biotren L1 operacional total', 'unit': 'BIOTREN_L1_TOTAL_OPERACIONAL', 'dt': 'LV', 'servicios_dia': 48.0,
     'detalle': 'Incluye 8 servicios Laja-Talcahuano'},
    {'servicio': 'Biotren L1 operacional total', 'unit': 'BIOTREN_L1_TOTAL_OPERACIONAL', 'dt': 'Sab', 'servicios_dia': 16.0,
     'detalle': 'Mes tipo: 8 servicios Biotren L1 propios + 8 Laja-Talcahuano'},
    {'servicio': 'Biotren L1 operacional total', 'unit': 'BIOTREN_L1_TOTAL_OPERACIONAL', 'dt': 'Dom', 'servicios_dia': 8.0,
     'detalle': 'Mes tipo: corresponde a 8 servicios Laja-Talcahuano'},
    {'servicio': 'Biotren L1 operacional total', 'unit': 'BIOTREN_L1_TOTAL_OPERACIONAL', 'dt': 'Sab', 'servicios_dia': 18.0,
     'detalle': 'Enero-febrero: 8 servicios Biotren L1 propios + 10 Laja-Talcahuano'},
    {'servicio': 'Biotren L1 operacional total', 'unit': 'BIOTREN_L1_TOTAL_OPERACIONAL', 'dt': 'Dom', 'servicios_dia': 10.0,
     'detalle': 'Enero-febrero: corresponde a 10 servicios Laja-Talcahuano'},
    {'servicio': 'Biotren L1 propia del modelo', 'unit': 'BIOTREN_L1', 'dt': 'LV', 'servicios_dia': 40.0,
     'detalle': '48 L1 operacional total - 8 Laja-Talcahuano para evitar doble conteo'},
    {'servicio': 'Biotren L1 propia del modelo', 'unit': 'BIOTREN_L1', 'dt': 'Sab', 'servicios_dia': 8.0,
     'detalle': 'Oferta propia no contabilizada en CORTO_LAJA'},
    {'servicio': 'Biotren L1 propia del modelo', 'unit': 'BIOTREN_L1', 'dt': 'Dom', 'servicios_dia': 0.0,
     'detalle': 'Sin oferta propia dominical; la oferta dominical del corredor se contabiliza en CORTO_LAJA'},
    {'servicio': 'Laja-Talcahuano', 'unit': 'CORTO_LAJA', 'dt': 'LV', 'servicios_dia': 10.0,
     'detalle': '8 servicios base + 2 cortos Hualqui-Talcamavida / Talcamavida-Hualqui'},
    {'servicio': 'Laja-Talcahuano', 'unit': 'CORTO_LAJA', 'dt': 'Sab', 'servicios_dia': 10.0,
     'detalle': 'Enero-febrero: 10 servicios sabado'},
    {'servicio': 'Laja-Talcahuano', 'unit': 'CORTO_LAJA', 'dt': 'Dom', 'servicios_dia': 10.0,
     'detalle': 'Enero-febrero: 10 servicios domingo'},
    {'servicio': 'Laja-Talcahuano', 'unit': 'CORTO_LAJA', 'dt': 'Sab', 'servicios_dia': 8.0,
     'detalle': 'Marzo-diciembre: 8 servicios sabado'},
    {'servicio': 'Laja-Talcahuano', 'unit': 'CORTO_LAJA', 'dt': 'Dom', 'servicios_dia': 8.0,
     'detalle': 'Marzo-diciembre: 8 servicios domingo'},
    {'servicio': 'Tren Araucania', 'unit': 'TREN_ARAUCANIA', 'dt': 'LV', 'servicios_dia': 18.6,
     'detalle': 'Promedio ponderado: lunes-jueves 19; viernes 17'},
    {'servicio': 'Tren Araucania', 'unit': 'TREN_ARAUCANIA', 'dt': 'Sab', 'servicios_dia': 12.0,
     'detalle': '8 Victoria-Temuco + 4 Pitrufquen-Temuco'},
    {'servicio': 'Tren Araucania', 'unit': 'TREN_ARAUCANIA', 'dt': 'Dom', 'servicios_dia': 6.0,
     'detalle': '6 Victoria-Temuco'},
    {'servicio': 'Llanquihue-Puerto Montt', 'unit': 'LLANQUIHUE_PM', 'dt': 'LV', 'servicios_dia': 20.0,
     'detalle': '20 servicios de lunes a viernes'},
    {'servicio': 'Llanquihue-Puerto Montt', 'unit': 'LLANQUIHUE_PM', 'dt': 'Sab', 'servicios_dia': 0.0,
     'detalle': 'Sin servicios planificados de fin de semana'},
    {'servicio': 'Llanquihue-Puerto Montt', 'unit': 'LLANQUIHUE_PM', 'dt': 'Dom', 'servicios_dia': 0.0,
     'detalle': 'Sin servicios planificados de fin de semana'},
]


def oferta_actual_df(detalle=False, mensual=True):
    """Devuelve la oferta vigente informada.

    detalle=True retorna filas explicativas de respaldo operacional.
    mensual=True retorna la oferta usada por el modelo para cada mes y tipo de dia,
    incluyendo excepciones como Laja-Talcahuano en enero-febrero.
    mensual=False retorna la oferta tipo sin excepciones mensuales.
    """
    if detalle:
        return pd.DataFrame(OFERTA_ACTUAL_DETALLE)

    rows = []
    for unit, vals in OFERTA_ACTUAL_MODELO.items():
        for mes in range(1, 13):
            for dt, servicios_dia in vals.items():
                rows.append({'unit': unit, 'mes': mes, 'dt': dt, 'servicios_dia': float(servicios_dia)})
    df = pd.DataFrame(rows)

    if mensual:
        exc = pd.DataFrame(OFERTA_ACTUAL_EXCEPCIONES)
        if not exc.empty:
            for _, x in exc.iterrows():
                m = (df['unit'] == x['unit']) & (df['mes'] == int(x['mes'])) & (df['dt'] == x['dt'])
                df.loc[m, 'servicios_dia'] = float(x['servicios_dia'])
        return df

    return df.drop(columns='mes').drop_duplicates().reset_index(drop=True)


def aplicar_oferta_actual(params, oferta=None, excepciones=None):
    """Reemplaza servicios_dia por la oferta vigente, manteniendo pax_x_viaje y tasa_sup.

    La asignacion se define por unidad, mes y tipo de dia. Esto permite representar
    modificaciones mensuales especificas sin cambiar la estimacion historica de
    pax_x_viaje ni las tasas de supresion.
    """
    p = params.copy()
    p['mes'] = p['mes'].astype(int)

    if oferta is None:
        oferta_df = oferta_actual_df(mensual=True)
    elif isinstance(oferta, pd.DataFrame):
        oferta_df = oferta.copy()
        if 'mes' not in oferta_df.columns:
            base = []
            for mes in range(1, 13):
                x = oferta_df.copy()
                x['mes'] = mes
                base.append(x)
            oferta_df = pd.concat(base, ignore_index=True)
    else:
        rows = []
        for unit, vals in oferta.items():
            for mes in range(1, 13):
                for dt, servicios_dia in vals.items():
                    rows.append({'unit': unit, 'mes': mes, 'dt': dt, 'servicios_dia': float(servicios_dia)})
        oferta_df = pd.DataFrame(rows)

    if excepciones is not None:
        exc = pd.DataFrame(excepciones)
        if not exc.empty:
            for _, x in exc.iterrows():
                m = (oferta_df['unit'] == x['unit']) & (oferta_df['mes'] == int(x['mes'])) & (oferta_df['dt'] == x['dt'])
                oferta_df.loc[m, 'servicios_dia'] = float(x['servicios_dia'])

    oferta_df = oferta_df[['unit', 'mes', 'dt', 'servicios_dia']].rename(columns={'servicios_dia': 'servicios_dia_actual'})
    p = p.merge(oferta_df, on=['unit', 'mes', 'dt'], how='left')
    p['servicios_dia'] = pd.to_numeric(p['servicios_dia_actual'], errors='coerce').fillna(p['servicios_dia'])
    return p.drop(columns='servicios_dia_actual')

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

    # La oferta historica del RROO se utiliza para estimar pax_x_viaje y tasa_sup.
    # El escenario base predictivo se recalibra a la oferta vigente informada.
    params = aplicar_oferta_actual(params)
    return params.sort_values(['unit', 'mes', 'dt']).reset_index(drop=True)


def dias_por_tipo(anio=2027):
    d = pd.date_range(f'{anio}-01-01', f'{anio}-12-31')
    df = pd.DataFrame({'mes': d.month, 'dt': d.dayofweek.map(_dt)})
    return df.groupby(['mes', 'dt']).size().reset_index(name='n_dias')


def _aplicar_plan_y_contingencia(params, plan=None, contingencia_extra=None, anio=2027, calibracion_productividad=True):
    """Base comun de calculo por unidad/mes/tipo de dia.

    Retorna el detalle antes de agregar por servicio. Se deja separado para que
    el escenario conservador pueda reutilizar los viajes ofertados y ajustar la
    respuesta de demanda sin modificar la oferta visible al usuario.
    """
    p = params.copy()
    if calibracion_productividad:
        p = calibrar_productividad_reciente(p)
    if plan is not None:
        pl = plan[['unit', 'mes', 'dt', 'servicios_dia']].rename(columns={'servicios_dia': 'sd_plan'})
        pl['mes'] = pl['mes'].astype(int)
        p = p.merge(pl, on=['unit', 'mes', 'dt'], how='left')
        p['servicios_dia'] = pd.to_numeric(p['sd_plan'], errors='coerce').fillna(p['servicios_dia'])
        p = p.drop(columns='sd_plan')
    p = p.merge(dias_por_tipo(anio), on=['mes', 'dt'], how='left')
    ce = contingencia_extra or {}
    p['f_sup'] = (1 - p['tasa_sup'] - p['unit'].map(ce).fillna(0)).clip(0, 1)
    p['viajes_programados_mes'] = p['servicios_dia'] * p['n_dias']
    p['viajes_operados_mes'] = p['viajes_programados_mes'] * p['f_sup']
    p['afl'] = p['viajes_operados_mes'] * p['pax_x_viaje']
    return p


def _agregar_servicios(p, anio=2027):
    uni = p.groupby(['unit', 'mes'])['afl'].sum().reset_index()
    uni_w = uni.pivot(index='mes', columns='unit', values='afl')
    uni_w.index = [f'{anio}-{m:02d}' for m in uni_w.index]
    serv = pd.DataFrame(index=uni_w.index)
    for s, us in UNIDADES_DE.items():
        cols = [u for u in us if u in uni_w.columns]
        if cols:
            serv[s] = uni_w[cols].sum(axis=1)
    return uni_w, serv


def proyectar(params, plan=None, contingencia_extra=None, anio=2027, calibracion_productividad=True):
    """Proyeccion directa por oferta.

    Esta version mantiene la formula original: cada servicio adicional conserva
    la productividad historica por viaje. Se conserva para trazabilidad y para
    analizar escenarios expansivos, pero el escenario recomendado para Biotren
    y Tren Araucania usa `proyectar_conservador`.
    """
    p = _aplicar_plan_y_contingencia(params, plan=plan, contingencia_extra=contingencia_extra, anio=anio, calibracion_productividad=calibracion_productividad)
    uni_w, serv = _agregar_servicios(p, anio=anio)
    return uni_w.round(0).astype('Int64'), serv.round(0).astype('Int64')


AJUSTE_CONSERVADOR = {
    # Factores revisados con datos reales de mayo 2026.
    # factor_alza < 1 evita traducir mecanicamente mas oferta en mas pasajeros.
    # factor_baja suaviza caidas cuando la proyeccion por oferta queda por debajo
    # de la referencia estacional.
    'BIOTREN': {'factor_alza': 0.25, 'factor_baja': 0.60},
    'CORTO_LAJA': {'factor_alza': 0.35, 'factor_baja': 0.60},
    'TREN_ARAUCANIA': {'factor_alza': 0.40, 'factor_baja': 0.70},
    'LLANQUIHUE_PM': {'factor_alza': 0.25, 'factor_baja': 0.60},
}


def cargar_calibracion_productividad(path=None):
    """Carga factores de calibracion de pax/viaje observados en mayo 2026.

    El archivo esperado contiene, al menos:
      unit, dt, factor_objetivo, peso_calibracion, factor_min, factor_max.
    Si el archivo no existe, retorna DataFrame vacio y no modifica parametros.
    """
    if path is None:
        path = DATA_DIR / 'calibracion_mayo_2026.csv'
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def calibrar_productividad_reciente(params, calibracion=None):
    """Ajusta pax_x_viaje con el comportamiento observado en mayo 2026.

    La calibracion es parcial: no reemplaza toda la historia por mayo, sino que
    aproxima la productividad historica a la productividad reciente usando un
    peso configurable y limites de variacion. Esto permite representar que un
    aumento de servicios puede reducir pasajeros promedio por viaje.
    """
    p = params.copy()
    if calibracion is None:
        cal = cargar_calibracion_productividad()
    elif isinstance(calibracion, pd.DataFrame):
        cal = calibracion.copy()
    else:
        cal = pd.read_csv(calibracion)

    if cal.empty:
        return p

    required = {'unit', 'dt', 'factor_objetivo'}
    if not required.issubset(set(cal.columns)):
        return p

    for _, r in cal.iterrows():
        unit = r['unit']
        dt = r['dt']
        peso = float(r.get('peso_calibracion', 1.0))
        f_obj = float(r['factor_objetivo'])
        f_min = float(r.get('factor_min', 0.65))
        f_max = float(r.get('factor_max', 1.45))
        f_aplicado = np.clip(1 + peso * (f_obj - 1), f_min, f_max)
        m = (p['unit'] == unit) & (p['dt'] == dt)
        p.loc[m, 'pax_x_viaje'] = p.loc[m, 'pax_x_viaje'] * f_aplicado
    p['pax_x_viaje'] = p['pax_x_viaje'].round(1)
    return p



def proyectar_conservador(params, base_servicios, plan=None, contingencia_extra=None,
                          anio=2027, ajustes=None, calibracion_productividad=True):
    """Proyeccion recomendada para escenario base conservador.

    Combina dos senales:
    1) proyeccion directa por oferta vigente/editada;
    2) referencia estacional historica, que recoge el comportamiento observado
       hasta 2026 sin asumir que mas servicios generan demanda proporcional.

    Para los servicios con calibracion reciente se aplica una respuesta parcial:
      final = referencia + factor * (oferta - referencia)
    con factores menores a 1. El resultado conserva el efecto de la oferta,
    pero evita incrementos mecanicos de afluencia por cada tren adicional.

    `base_servicios` debe tener indice mensual YYYY-MM y columnas por servicio
    iguales a SERVICIOS, como la salida de pipeline_afluencia.proyectar_2027.
    """
    ajustes = ajustes or AJUSTE_CONSERVADOR
    p = _aplicar_plan_y_contingencia(params, plan=plan, contingencia_extra=contingencia_extra, anio=anio, calibracion_productividad=calibracion_productividad)
    uni_w, serv_oferta = _agregar_servicios(p, anio=anio)

    serv_final = serv_oferta.copy()
    base = base_servicios.copy()
    base.index = serv_oferta.index

    for s, cfg in ajustes.items():
        if s not in serv_final.columns or s not in base.columns:
            continue
        oferta = serv_oferta[s].astype(float)
        referencia = base[s].astype(float)
        factor_alza = float(cfg.get('factor_alza', 1.0))
        factor_baja = float(cfg.get('factor_baja', 1.0))
        factor = pd.Series(np.where(oferta >= referencia, factor_alza, factor_baja), index=serv_final.index)
        serv_final[s] = referencia + factor * (oferta - referencia)

        # Redistribucion a unidades: mantiene la proporcion mensual de la
        # proyeccion por oferta. Para servicios de una unidad equivale a reemplazar
        # directamente esa unidad.
        unidades = [u for u in UNIDADES_DE[s] if u in uni_w.columns]
        if unidades:
            total_unidades = uni_w[unidades].sum(axis=1).replace(0, np.nan)
            ratio = (serv_final[s] / total_unidades).replace([np.inf, -np.inf], np.nan).fillna(0)
            for u in unidades:
                uni_w[u] = uni_w[u] * ratio

    return uni_w.round(0).astype('Int64'), serv_final.round(0).astype('Int64')


def viajes_anuales(params, plan=None, contingencia_extra=None, anio=2027, units=None):
    """Viajes operados anuales estimados, util para calcular pax/viaje proyectado."""
    p = _aplicar_plan_y_contingencia(params, plan=plan, contingencia_extra=contingencia_extra, anio=anio)
    if units is not None:
        p = p[p['unit'].isin(units)]
    return float(p['viajes_operados_mes'].sum())
