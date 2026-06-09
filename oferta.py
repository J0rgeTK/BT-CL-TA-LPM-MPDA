"""
oferta.py -- motor de OFERTA del modelo de afluencia (v8, oferta vigente + calibracion mayo 2026).

El modelo NO usa clima. Base: fechas (estacionalidad) + reporte operacional (RROO).
La oferta de trenes es la VARIABLE de planificacion, editable por el usuario y
diferenciada por TIPO DE DIA (Lunes-Viernes 'LV', Sabado 'Sab', Domingo 'Dom') y mes.

Unidades: BIOTREN_L1, BIOTREN_L2, CORTO_LAJA, TREN_ARAUCANIA, LLANQUIHUE_PM.
Para Tren Araucania se mantiene TREN_ARAUCANIA como unidad agregada de demanda
y se agrega una desagregacion auxiliar de oferta por tramo: TA_TEMUCO_VICTORIA,
TA_TEMUCO_PITRUFQUEN y TA_CLARET.
La afluencia de Biotren se reparte 20/80 (L1/L2, matriz OD; supuesto).

Estaciones Llanquihue-PM (XP-NQ): XP=La Paloma, NQ=Llanquihue, AL=Alerce, EV=Puerto Varas.
Nota operacional: los servicios Laja-Talcahuano circulan sobre el corredor de L1,
pero se proyectan como CORTO_LAJA para no duplicar afluencia ni oferta. Por eso
BIOTREN_L1 se parametriza como oferta propia de Biotren L1, excluyendo los
servicios Laja-Talcahuano ya contabilizados en CORTO_LAJA.

Modelo por unidad/mes:
  proy_oferta = SUMA_tipo_dia [ servicios_por_dia x n_dias_2027 x pax_por_viaje x (1-supresion) ]
  Escenario recomendado 2027 = oferta calibrada con mayo 2026.
  Ajuste especifico Biotren: se aplica un factor anual prudencial sobre la
  oferta calibrada para situar la proyeccion en torno a 12,5-12,6 MM antes
  de simular aumentos leves de oferta futura.
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

TA_TRAMOS = ['TA_TEMUCO_VICTORIA', 'TA_TEMUCO_PITRUFQUEN', 'TA_CLARET']
TA_TRAMO_NOMBRE = {
    'TA_TEMUCO_VICTORIA': 'Temuco - Victoria',
    'TA_TEMUCO_PITRUFQUEN': 'Temuco - Pitrufquen',
    'TA_CLARET': 'Claret',
}
# Peso relativo de demanda: un servicio adicional en Pitrufquen o Claret no se
# transforma en la misma demanda que un servicio adicional Victoria-Temuco.
TA_TRAMO_PESO_DEMANDA = {
    'TA_TEMUCO_VICTORIA': 1.00,
    'TA_TEMUCO_PITRUFQUEN': 0.16,
    'TA_CLARET': 0.08,
}
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
# - CORTO_LAJA usa 8 servicios base todos los dias. La excepcion operacional
#   corresponde solo a sabado y domingo de enero-febrero, donde se consideran
#   10 servicios. No se aplica 10 servicios a lunes-viernes.
# - Tren Araucania tiene diferencias L-J / viernes; el modelo usa tipo LV, por
#   lo que se usa promedio ponderado semanal: (4*19 + 1*17) / 5 = 18.6.
# ---------------------------------------------------------------------------
OFERTA_ACTUAL_MODELO = {
    'BIOTREN_L1': {'LV': 40.0, 'Sab': 8.0, 'Dom': 0.0},
    'BIOTREN_L2': {'LV': 106.0, 'Sab': 53.0, 'Dom': 32.0},
    'CORTO_LAJA': {'LV': 8.0, 'Sab': 8.0, 'Dom': 8.0},
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
    {'servicio': 'Laja-Talcahuano', 'unit': 'CORTO_LAJA', 'dt': 'LV', 'servicios_dia': 8.0,
     'detalle': '8 servicios lunes a viernes; los 10 servicios aplican solo a fines de semana de enero-febrero'},
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



def unidad_a_servicio():
    rows = {}
    for s, units in UNIDADES_DE.items():
        for u in units:
            rows[u] = s
    return rows


# Elasticidades de respuesta de demanda ante cambios de oferta programada.
# Se usan valores inferiores a 1 para representar rendimientos marginales decrecientes:
# un aumento de servicios mejora accesibilidad/frecuencia, pero no genera pasajeros
# en la misma proporción que la oferta adicional.
ELASTICIDAD_OFERTA_SERVICIO = {
    'BIOTREN': 0.55,
    'CORTO_LAJA': 0.38,
    'TREN_ARAUCANIA': 0.42,
    'LLANQUIHUE_PM': 0.35,
}

# Ajuste de nivel calibrado con mayo 2026 y revisión de coherencia histórica.
# No es una comparación visible; funciona como calibrador de productividad base.
AJUSTE_NIVEL_SERVICIO = {
    'BIOTREN': 0.972,
    'CORTO_LAJA': 1.000,
    'TREN_ARAUCANIA': 1.000,
    'LLANQUIHUE_PM': 1.000,
}

# Intensidad con que se corrige la productividad mensual hacia el patrón histórico.
# 0 = sólo productividad/oferta observada; 1 = calza completamente la estacionalidad histórica.
# Se deja por debajo de 1 para no volver a un modelo de simple distribución anual.
FUERZA_ESTACIONALIDAD = {
    'BIOTREN': 0.55,
    'CORTO_LAJA': 0.45,
    'TREN_ARAUCANIA': 0.50,
    'LLANQUIHUE_PM': 0.85,
}

RAMP_NUEVA_OFERTA = {
    'BIOTREN': 0.55,
    'CORTO_LAJA': 0.45,
    'TREN_ARAUCANIA': 0.45,
    'LLANQUIHUE_PM': 0.40,
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


def oferta_tren_araucania_tramos_df(mensual=True):
    """Oferta vigente de Tren Araucania desagregada por tramo."""
    base = {
        # Promedio LV: lunes-jueves 9/7/3 y viernes 9/5/3.
        'TA_TEMUCO_VICTORIA': {'LV': 9.0, 'Sab': 8.0, 'Dom': 6.0},
        'TA_TEMUCO_PITRUFQUEN': {'LV': 6.6, 'Sab': 4.0, 'Dom': 0.0},
        'TA_CLARET': {'LV': 3.0, 'Sab': 0.0, 'Dom': 0.0},
    }
    rows = []
    for unit, vals in base.items():
        meses = range(1, 13) if mensual else [None]
        for mes in meses:
            for dt, servicios_dia in vals.items():
                row = {'unit': unit, 'dt': dt, 'servicios_dia': float(servicios_dia)}
                if mensual:
                    row['mes'] = mes
                rows.append(row)
    cols = ['unit', 'mes', 'dt', 'servicios_dia'] if mensual else ['unit', 'dt', 'servicios_dia']
    return pd.DataFrame(rows)[cols]


def plan_tren_araucania_agregado(plan_tramos):
    """Convierte oferta por tramo de Tren Araucania en oferta equivalente agregada.

    La oferta equivalente conserva el nivel actual cuando se usan los valores base.
    Si el usuario aumenta servicios en Victoria-Temuco, el efecto en demanda es
    mayor que si aumenta servicios en Pitrufquen o Claret.
    """
    base = oferta_tren_araucania_tramos_df(mensual=True)
    df = plan_tramos.copy()
    df['mes'] = df['mes'].astype(int)
    idx = base[['unit', 'mes', 'dt']].copy()
    df = idx.merge(df[['unit', 'mes', 'dt', 'servicios_dia']], on=['unit', 'mes', 'dt'], how='left')
    df = df.merge(base.rename(columns={'servicios_dia': 'servicios_base'}), on=['unit', 'mes', 'dt'], how='left')
    df['servicios_dia'] = pd.to_numeric(df['servicios_dia'], errors='coerce').fillna(df['servicios_base'])
    df['peso'] = df['unit'].map(TA_TRAMO_PESO_DEMANDA).fillna(0.0)
    df['ponderado'] = df['servicios_dia'] * df['peso']

    base2 = base.copy()
    base2['peso'] = base2['unit'].map(TA_TRAMO_PESO_DEMANDA).fillna(0.0)
    base2['ponderado_base'] = base2['servicios_dia'] * base2['peso']
    cur = df.groupby(['mes', 'dt'])['ponderado'].sum().reset_index()
    bas = base2.groupby(['mes', 'dt']).agg(ponderado_base=('ponderado_base', 'sum'),
                                           total_base=('servicios_dia', 'sum')).reset_index()
    out = cur.merge(bas, on=['mes', 'dt'], how='left')
    out['servicios_dia'] = out['total_base'] * out['ponderado'] / out['ponderado_base'].replace(0, np.nan)
    out['servicios_dia'] = out['servicios_dia'].fillna(0.0)
    out['unit'] = 'TREN_ARAUCANIA'
    return out[['unit', 'mes', 'dt', 'servicios_dia']]


def _preparar_mdf(mdf):
    g = mdf.copy()
    if not pd.api.types.is_period_dtype(g['mes']):
        g['mes'] = pd.PeriodIndex(g['mes'], freq='M')
    g['anio'] = g['mes'].dt.year
    g['m'] = g['mes'].dt.month
    return g


def analisis_mensual_historico(mdf):
    """Tabla auditable de comportamiento mensual por servicio y anio."""
    g = _preparar_mdf(mdf)
    rows = []
    for (servicio, anio), d in g.groupby(['servicio', 'anio']):
        total_obs = d['pax_norm'].sum()
        meses_obs = d['m'].nunique()
        media_obs = d['pax_norm'].mean()
        for _, r in d.iterrows():
            rows.append({
                'servicio': servicio,
                'anio': int(anio),
                'mes': int(r['m']),
                'afluencia_mensual_normalizada': round(float(r['pax_norm']), 0),
                'meses_observados_anio': int(meses_obs),
                'participacion_sobre_periodo_observado': float(r['pax_norm'] / total_obs) if total_obs else np.nan,
                'indice_mensual_vs_media_observada': float(r['pax_norm'] / media_obs) if media_obs else np.nan,
                'cobertura': float(r.get('cobertura', np.nan)),
            })
    return pd.DataFrame(rows).sort_values(['servicio', 'anio', 'mes']).reset_index(drop=True)


def resumen_historico_anual(mdf):
    g = _preparar_mdf(mdf)
    out = (g.groupby(['servicio', 'anio'])
             .agg(meses_observados=('m', 'nunique'),
                  afluencia_observada_normalizada=('pax_norm', 'sum'),
                  promedio_mensual=('pax_norm', 'mean'),
                  primer_mes=('m', 'min'), ultimo_mes=('m', 'max'))
             .reset_index())
    out['afluencia_observada_normalizada'] = out['afluencia_observada_normalizada'].round(0)
    out['promedio_mensual'] = out['promedio_mensual'].round(0)
    return out


def _share_full_years(g, servicio):
    weights_by_service = {
        'BIOTREN': {2024: 0.40, 2025: 0.45, 2026: 0.15},
        'CORTO_LAJA': {2024: 0.35, 2025: 0.45, 2026: 0.20},
        'TREN_ARAUCANIA': {2025: 0.70, 2026: 0.30},
        'LLANQUIHUE_PM': {2025: 0.30, 2026: 0.70},
    }
    weights = weights_by_service.get(servicio, {})
    out = pd.Series(0.0, index=range(1, 13), dtype=float)
    tw = 0.0

    # Años completos: uso directo de participación anual.
    for y, d in g.groupby('anio'):
        y = int(y)
        if d['m'].nunique() >= 12:
            sh = d.set_index('m')['pax_norm'].astype(float).reindex(range(1, 13))
            sh = sh / sh.sum()
            w = float(weights.get(y, 1.0))
            out = out.add(sh * w, fill_value=0.0)
            tw += w

    if tw > 0:
        out = out / tw
    else:
        piv = g.sort_values('mes').groupby('m')['pax_norm'].last()
        mean_val = float(piv.mean()) if len(piv) else 1.0
        out = pd.Series({m: float(piv.get(m, mean_val)) for m in range(1, 13)}, dtype=float)
        out = out / out.sum()

    # Año parcial 2026: se incorpora sólo en meses observados, sin inferir el año completo.
    obs26 = g[g['anio'] == 2026].set_index('m')['pax_norm'].astype(float)
    if not obs26.empty:
        denom = max(out.loc[obs26.index].sum(), 1e-9)
        anual_implicito = obs26.sum() / denom
        sh26 = obs26 / anual_implicito
        peso_2026 = {'BIOTREN': 0.45, 'CORTO_LAJA': 0.30, 'TREN_ARAUCANIA': 0.45, 'LLANQUIHUE_PM': 0.70}.get(servicio, 0.35)
        for m, v in sh26.items():
            out.loc[m] = (1 - peso_2026) * out.loc[m] + peso_2026 * v

    out = out.reindex(range(1, 13)).fillna(out.mean())
    return out / out.sum()


def perfil_mensual_historico(mdf, servicio, total_anual=None):
    """Perfil mensual histórico utilizado como corrección de productividad.

    Este perfil NO se usa para repartir un total anual fijo. Se usa para construir
    factores de productividad mensual que luego se aplican al cálculo mes a mes.
    """
    g_all = _preparar_mdf(mdf)
    g = g_all[g_all['servicio'] == servicio].copy()
    if g.empty:
        return pd.Series(1 / 12, index=[f'2027-{m:02d}' for m in range(1, 13)])

    if servicio == 'LLANQUIHUE_PM':
        # Mantener enero-febrero 2026 como señal estival cuando existen datos.
        vals = {}
        for m in range(1, 13):
            d = g[g['m'] == m].sort_values('anio')
            vals[m] = float(d.iloc[-1]['pax_norm']) if not d.empty else np.nan
        available = [v for v in vals.values() if pd.notna(v)]
        fill = float(np.mean(available)) if available else 1.0
        raw = pd.Series({m: (fill if pd.isna(v) else v) for m, v in vals.items()}, dtype=float).reindex(range(1, 13))
        share = raw / raw.sum()
    else:
        share = _share_full_years(g, servicio)

    share.index = [f'2027-{m:02d}' for m in range(1, 13)]
    return share.astype(float)


def _base_detalle(params, anio=2027, calibracion_productividad=True):
    p = params.copy()
    p['mes'] = p['mes'].astype(int)
    if calibracion_productividad:
        p = calibrar_productividad_reciente(p)
    p = p.merge(dias_por_tipo(anio), on=['mes', 'dt'], how='left')
    p['servicio'] = p['unit'].map(unidad_a_servicio())
    p['nivel_factor'] = p['servicio'].map(AJUSTE_NIVEL_SERVICIO).fillna(1.0)
    p['elasticidad'] = p['servicio'].map(ELASTICIDAD_OFERTA_SERVICIO).fillna(0.45)
    p['f_sup_base'] = (1 - p['tasa_sup']).clip(0, 1)
    p['viajes_programados_base'] = p['servicios_dia'] * p['n_dias']
    p['viajes_operados_base'] = p['viajes_programados_base'] * p['f_sup_base']
    p['afl_base_sin_estacionalidad'] = p['viajes_operados_base'] * p['pax_x_viaje'] * p['nivel_factor']
    return p


def factores_estacionalidad_mensual(params, mdf, anio=2027, calibracion_productividad=True):
    """Calcula factores mensuales de productividad por servicio.

    El factor se obtiene comparando la proyección directa por oferta actual con
    el patrón histórico mensual. Luego se aplica con una fuerza menor o igual a 1
    y se normaliza para que el escenario base conserve el nivel anual calibrado.
    """
    p0 = _base_detalle(params, anio=anio, calibracion_productividad=calibracion_productividad)
    base_serv = (p0.groupby(['servicio', 'mes'])['afl_base_sin_estacionalidad'].sum()
                   .reset_index())
    rows = []
    for s, d in base_serv.groupby('servicio'):
        total_base = float(d['afl_base_sin_estacionalidad'].sum())
        hist_share = perfil_mensual_historico(mdf, s)
        raw = d.set_index('mes')['afl_base_sin_estacionalidad'].astype(float).reindex(range(1, 13)).fillna(0.0)
        target = pd.Series({m: total_base * float(hist_share.get(f'{anio}-{m:02d}', 1/12)) for m in range(1, 13)}, dtype=float)
        ratio = (target / raw.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(1.0)
        fuerza = float(FUERZA_ESTACIONALIDAD.get(s, 0.5))
        f = ratio.pow(fuerza)
        annual_after = float((raw * f).sum())
        normalizador = total_base / annual_after if annual_after > 0 else 1.0
        for m in range(1, 13):
            rows.append({
                'servicio': s,
                'mes': int(m),
                'factor_estacionalidad': float(f.loc[m] * normalizador),
                'participacion_historica_utilizada': float(hist_share.get(f'{anio}-{m:02d}', 1/12)),
                'fuerza_estacionalidad': fuerza,
            })
    return pd.DataFrame(rows)


def _aplicar_plan(detalle_base, plan=None, contingencia_extra=None):
    p = detalle_base.copy()
    if plan is not None:
        pl = plan[['unit', 'mes', 'dt', 'servicios_dia']].rename(columns={'servicios_dia': 'servicios_dia_plan'})
        pl['mes'] = pl['mes'].astype(int)
        p = p.merge(pl, on=['unit', 'mes', 'dt'], how='left')
        p['servicios_dia_plan'] = pd.to_numeric(p['servicios_dia_plan'], errors='coerce').fillna(p['servicios_dia'])
    else:
        p['servicios_dia_plan'] = p['servicios_dia']

    ce = contingencia_extra or {}
    p['f_sup_plan'] = (1 - p['tasa_sup'] - p['unit'].map(ce).fillna(0)).clip(0, 1)
    p['viajes_programados_plan'] = p['servicios_dia_plan'] * p['n_dias']
    p['viajes_operados_plan'] = p['viajes_programados_plan'] * p['f_sup_plan']
    return p


def proyectar_mensual_elastico(params, mdf, plan=None, contingencia_extra=None,
                               anio=2027, calibracion_productividad=True,
                               return_detalle=False):
    """Proyección mensual oferta-demanda con elasticidad parcial.

    Fórmula principal por unidad u, mes m y tipo de día d:
      D1 = D0 * (V1 / V0) ** e

    donde:
      D0 = demanda base mensual calibrada,
      V0 = viajes operados base,
      V1 = viajes operados con la oferta editada,
      e  = elasticidad de demanda respecto de oferta, con 0 < e < 1.

    Si el usuario modifica la oferta de un mes, sólo cambian las filas de ese mes.
    El total anual ya no se reparte posteriormente: resulta de sumar los meses.
    """
    base = _base_detalle(params, anio=anio, calibracion_productividad=calibracion_productividad)
    fest = factores_estacionalidad_mensual(params, mdf, anio=anio,
                                           calibracion_productividad=calibracion_productividad)
    p = _aplicar_plan(base, plan=plan, contingencia_extra=contingencia_extra)
    p = p.merge(fest[['servicio', 'mes', 'factor_estacionalidad', 'participacion_historica_utilizada', 'fuerza_estacionalidad']],
                on=['servicio', 'mes'], how='left')
    p['factor_estacionalidad'] = p['factor_estacionalidad'].fillna(1.0)
    p['demanda_base_mensual'] = p['afl_base_sin_estacionalidad'] * p['factor_estacionalidad']

    ratio = p['viajes_operados_plan'] / p['viajes_operados_base'].replace(0, np.nan)
    p['ratio_oferta_operada'] = ratio.replace([np.inf, -np.inf], np.nan)
    p['afl'] = p['demanda_base_mensual'] * p['ratio_oferta_operada'].pow(p['elasticidad'])

    # Fallback para oferta nueva donde no existe V0: productividad base reducida por etapa de maduración.
    m_new = p['viajes_operados_base'].le(0) & p['viajes_operados_plan'].gt(0)
    if m_new.any():
        ramp = p.loc[m_new, 'servicio'].map(RAMP_NUEVA_OFERTA).fillna(0.45)
        p.loc[m_new, 'afl'] = (p.loc[m_new, 'viajes_operados_plan'] *
                               p.loc[m_new, 'pax_x_viaje'] *
                               p.loc[m_new, 'nivel_factor'] *
                               p.loc[m_new, 'factor_estacionalidad'] * ramp)
    p['afl'] = p['afl'].fillna(0.0).clip(lower=0)
    p['pax_por_viaje_resultante'] = p['afl'] / p['viajes_operados_plan'].replace(0, np.nan)
    p['pax_por_viaje_base'] = p['demanda_base_mensual'] / p['viajes_operados_base'].replace(0, np.nan)
    p['variacion_servicios_dia'] = p['servicios_dia_plan'] - p['servicios_dia']
    p['variacion_pct_oferta_operada'] = (p['viajes_operados_plan'] / p['viajes_operados_base'].replace(0, np.nan) - 1) * 100
    p['variacion_pct_demanda'] = (p['afl'] / p['demanda_base_mensual'].replace(0, np.nan) - 1) * 100

    uni = p.groupby(['unit', 'mes'])['afl'].sum().reset_index()
    uni_w = uni.pivot(index='mes', columns='unit', values='afl').fillna(0.0)
    uni_w.index = [f'{anio}-{m:02d}' for m in uni_w.index]
    serv = pd.DataFrame(index=uni_w.index)
    for s, us in UNIDADES_DE.items():
        cols = [u for u in us if u in uni_w.columns]
        if cols:
            serv[s] = uni_w[cols].sum(axis=1)

    uni_w = uni_w.round(0).astype('Int64')
    serv = serv.round(0).astype('Int64')
    detalle = p.copy()
    detalle['periodo'] = detalle['mes'].map(lambda m: f'{anio}-{int(m):02d}')
    if return_detalle:
        return uni_w, serv, detalle
    return uni_w, serv


def proyectar(params, plan=None, contingencia_extra=None, anio=2027, calibracion_productividad=True):
    """Compatibilidad: proyección directa mensual por oferta y productividad constante."""
    p = _base_detalle(params, anio=anio, calibracion_productividad=calibracion_productividad)
    p = _aplicar_plan(p, plan=plan, contingencia_extra=contingencia_extra)
    p['afl'] = p['viajes_operados_plan'] * p['pax_x_viaje'] * p['nivel_factor']
    uni = p.groupby(['unit', 'mes'])['afl'].sum().reset_index()
    uni_w = uni.pivot(index='mes', columns='unit', values='afl').fillna(0.0)
    uni_w.index = [f'{anio}-{m:02d}' for m in uni_w.index]
    serv = pd.DataFrame(index=uni_w.index)
    for s, us in UNIDADES_DE.items():
        cols = [u for u in us if u in uni_w.columns]
        if cols:
            serv[s] = uni_w[cols].sum(axis=1)
    return uni_w.round(0).astype('Int64'), serv.round(0).astype('Int64')


def proyectar_base_ajustada(params, mdf, plan=None, contingencia_extra=None,
                            anio=2027, calibracion_productividad=True,
                            factores_total=None):
    """Compatibilidad: ahora usa el motor mensual elástico, no distribución anual."""
    uni, serv, detalle = proyectar_mensual_elastico(params, mdf, plan=plan,
                                                    contingencia_extra=contingencia_extra,
                                                    anio=anio,
                                                    calibracion_productividad=calibracion_productividad,
                                                    return_detalle=True)
    perfiles = detalle.groupby(['servicio', 'periodo']).agg(
        afluencia_proyectada_mes=('afl', 'sum'),
        viajes_operados_plan=('viajes_operados_plan', 'sum'),
        viajes_operados_base=('viajes_operados_base', 'sum'),
        ratio_oferta_operada=('ratio_oferta_operada', 'mean'),
        elasticidad=('elasticidad', 'mean')
    ).reset_index().rename(columns={'periodo': 'mes'})
    return uni, serv, perfiles


def desagregar_tren_araucania_por_tramo(serie_total, plan_tramos=None, anio=2027):
    """Distribuye la proyeccion agregada de Tren Araucania por tramo según oferta ponderada."""
    if plan_tramos is None:
        tr = oferta_tren_araucania_tramos_df(mensual=True)
    else:
        base = oferta_tren_araucania_tramos_df(mensual=True)
        tr = base[['unit', 'mes', 'dt']].merge(plan_tramos[['unit', 'mes', 'dt', 'servicios_dia']],
                                               on=['unit', 'mes', 'dt'], how='left')
        tr = tr.merge(base.rename(columns={'servicios_dia': 'servicios_base'}), on=['unit', 'mes', 'dt'], how='left')
        tr['servicios_dia'] = pd.to_numeric(tr['servicios_dia'], errors='coerce').fillna(tr['servicios_base'])
        tr = tr[['unit', 'mes', 'dt', 'servicios_dia']]
    nd = dias_por_tipo(anio)
    tr = tr.merge(nd, on=['mes', 'dt'], how='left')
    tr['peso'] = tr['unit'].map(TA_TRAMO_PESO_DEMANDA).fillna(0.0)
    tr['servicios_mes_ponderados'] = tr['servicios_dia'] * tr['n_dias'] * tr['peso']
    w = tr.groupby(['mes', 'unit'])['servicios_mes_ponderados'].sum().reset_index()
    total = w.groupby('mes')['servicios_mes_ponderados'].transform('sum').replace(0, np.nan)
    w['participacion_demanda'] = (w['servicios_mes_ponderados'] / total).fillna(0.0)
    out = w.pivot(index='mes', columns='unit', values='participacion_demanda').fillna(0.0)
    out.index = [f'{anio}-{m:02d}' for m in out.index]
    total_series = pd.Series(serie_total, index=out.index).astype(float)
    for c in out.columns:
        out[c] = out[c] * total_series
    return out.round(0).astype('Int64')


def viajes_anuales(params, plan=None, contingencia_extra=None, anio=2027, units=None,
                   mdf=None, usar_motor_elastico=False):
    """Viajes operados anuales estimados, util para calcular pax/viaje proyectado."""
    p = _base_detalle(params, anio=anio, calibracion_productividad=True)
    p = _aplicar_plan(p, plan=plan, contingencia_extra=contingencia_extra)
    if units is not None:
        p = p[p['unit'].isin(units)]
    return float(p['viajes_operados_plan'].sum())


def sensibilidad_oferta_mensual(params, mdf, servicio, unit, mes, dt, delta_servicios=1.0, anio=2027):
    """Calcula efecto marginal de cambiar la oferta de un mes/tipo de día."""
    base_plan = oferta_actual_df(mensual=True)
    plan = base_plan.copy()
    m = (plan['unit'] == unit) & (plan['mes'] == mes) & (plan['dt'] == dt)
    if not m.any():
        return pd.DataFrame()
    uni0, serv0 = proyectar_mensual_elastico(params, mdf, plan=base_plan, anio=anio)
    plan.loc[m, 'servicios_dia'] = plan.loc[m, 'servicios_dia'] + float(delta_servicios)
    uni1, serv1 = proyectar_mensual_elastico(params, mdf, plan=plan, anio=anio)
    periodo = f'{anio}-{mes:02d}'
    return pd.DataFrame([{
        'servicio': servicio,
        'unit': unit,
        'mes': mes,
        'dt': dt,
        'delta_servicios_dia': delta_servicios,
        'afluencia_base_mes': int(serv0.loc[periodo, servicio]),
        'afluencia_con_cambio_mes': int(serv1.loc[periodo, servicio]),
        'impacto_mes': int(serv1.loc[periodo, servicio] - serv0.loc[periodo, servicio]),
        'impacto_anual': int(serv1[servicio].sum() - serv0[servicio].sum()),
    }])
