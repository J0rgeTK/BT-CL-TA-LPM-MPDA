# Metodología del modelo predictivo de afluencia EFE Sur 2027

## 1. Propósito del modelo

El modelo estima la afluencia mensual proyectada de pasajeros para los servicios de EFE Sur y permite evaluar escenarios de oferta por mes, unidad operacional y tipo de día. Para Biotren, el modelo incorpora además una capa espacial OD que distribuye la demanda mensual proyectada por par origen-destino, tipo de pasajero e ingresos preliminares.

La estructura metodológica separa tres componentes:

1. **Modelo temporal de afluencia mensual:** estima la demanda total mensual por servicio.
2. **Módulo espacial OD de Biotren:** distribuye la demanda mensual entre pares origen-destino y tipo de pasajero.
3. **Módulo preliminar de ingresos OD:** multiplica viajes OD proyectados por tarifas 2026 disponibles.

El módulo OD complementa al modelo temporal; no lo reemplaza.

## 2. Modelo temporal de afluencia mensual

El cálculo se realiza por unidad operacional `u`, mes `m` y tipo de día `d`, distinguiendo lunes-viernes, sábado y domingo. Cada mes se calcula de forma independiente y el total anual corresponde a la suma de los meses. Por lo tanto, una modificación de oferta en un mes afecta principalmente ese mes y no redistribuye automáticamente el resto del año.

### 2.1 Ecuaciones generales

```text
V0(u,m,d) = S0(u,m,d) × N_op(u,m,d) × (1 - tau(u,m,d))
D0(u,m,d) = V0(u,m,d) × q(u,m,d) × F_nivel(s) × F_est(s,m)
V1(u,m,d) = S1(u,m,d) × N_op(u,m,d) × (1 - tau(u,m,d) - c(u))
D1(u,m,d) = D0(u,m,d) × (V1(u,m,d) / V0(u,m,d)) ^ epsilon(s)
```

Donde:

- `S0` es la oferta base del escenario.
- `S1` es la oferta editada por el usuario.
- `N_op` es la cantidad de días operacionales efectivos del tipo respectivo en el mes.
- `tau` es la tasa de supresión histórica incorporada al cálculo.
- `q` es la productividad media por servicio, construida desde los datos históricos disponibles.
- `F_nivel` ajusta el nivel general del servicio.
- `F_est` incorpora el comportamiento mensual observado.
- `epsilon` es la elasticidad de demanda respecto de la oferta.
- `c` es una contingencia adicional de supresión definida por el usuario.

La elasticidad es menor que 1, porque un aumento de servicios mejora frecuencia y accesibilidad, pero no necesariamente genera pasajeros en la misma proporción que la oferta adicional.

## 3. Calendario operacional y feriados

El modelo transforma el calendario 2027 en días operacionales efectivos por servicio, mes y tipo de día. La regla incorporada es:

- **Biotren, Tren Araucanía y Llanquihue-Puerto Montt:** feriados nacionales con oferta efectiva cero.
- **Laja-Talcahuano:** feriados nacionales operan con oferta de fin de semana. Si el feriado cae lunes-viernes, se imputa como día operacional tipo domingo.

Los feriados nacionales utilizados se encuentran en `data/feriados_chile_2027.csv`. El conteo operacional resultante se encuentra en `data/calendario_operacional_2027.csv` y `outputs/calendario_operacional_2027.csv`.

## 4. Tratamiento por servicio

### 4.1 Biotren

Biotren se modela separando L1 y L2. La oferta se edita por línea, mes y tipo de día. El escenario base considera L1 con 48 servicios lunes-viernes durante todo 2027 y L2 con 106 servicios lunes-viernes entre enero y abril, aumentando a 109 servicios lunes-viernes desde mayo.

La proyección mensual utiliza días operacionales efectivos, feriados sin operación, productividad histórica, estacionalidad mensual y elasticidad parcial de oferta. Laja-Talcahuano se mantiene como servicio independiente para evitar doble conteo dentro del corredor L1.

El perfil de marzo y abril se regulariza para evitar peaks mensuales no respaldados por el comportamiento histórico observado. Esta regularización conserva la suma del bloque marzo-abril y no transforma el modelo en una distribución anual fija.

### 4.2 Laja-Talcahuano

Laja-Talcahuano se proyecta como servicio propio. La oferta base considera 8 servicios diarios durante el año, con excepción de sábados y domingos de enero y febrero, donde se consideran 10 servicios. Los feriados nacionales se modelan con oferta de fin de semana.

El escenario considera recuperación parcial de confiabilidad operacional. Para ello, la supresión base se acota y se otorga mayor peso al patrón histórico de mejor desempeño, sin asumir una recuperación plena al máximo histórico observado.

### 4.3 Tren Araucanía

Tren Araucanía se modela por tipo de servicio:

- Temuco - Victoria.
- Temuco - Pitrufquén.
- Claret.

Cada tramo responde a su propia oferta y elasticidad. El tramo Temuco-Victoria tiene mayor respuesta marginal esperada que Pitrufquén y Claret. Claret se restringe a marzo-diciembre por su carácter escolar, por lo que enero y febrero no generan oferta ni demanda para ese componente.

### 4.4 Llanquihue-Puerto Montt

Llanquihue-Puerto Montt se modela con operación de lunes a viernes. En el escenario base no se consideran servicios planificados de fin de semana ni feriados nacionales. Enero y febrero conservan una señal estival dentro del perfil mensual.

## 5. Módulo OD híbrido de Biotren

El módulo OD toma la demanda mensual proyectada de Biotren y la distribuye espacialmente entre pares origen-destino y tipo de pasajero. La estructura implementada es:

```text
Proyección mensual Biotren
→ segmentación por tipo de pasajero
→ distribución OD histórica mensual
→ ajuste gravitacional parcial
→ balance IPF/Furness
→ matriz OD proyectada
→ ingresos OD preliminares
```

### 5.1 Tipos de pasajero

Se consideran tres segmentos:

| Tipo final | Bloque OD utilizado |
|---|---|
| Normal | T. Monedero |
| Estudiante | T. Estudiante |
| Adulto Mayor | T. Tercera Edad |

La segmentación mensual se calcula con participaciones históricas por tipo de pasajero:

```text
Demanda(p,m) = Demanda(Biotren,m) × Participación(p,m)
```

### 5.2 Distribución OD híbrida

Para cada mes y tipo de pasajero se construye una matriz base histórica `S_ij,p,m` y una matriz gravitacional `G_ij,p,m`. La matriz final combina ambos componentes:

```text
K_ij,p,m = w_p × S_ij,p,m + (1 - w_p) × G_ij,p,m
```

Donde:

- `S_ij,p,m` es la estructura OD histórica mensual por tipo de pasajero.
- `G_ij,p,m` es la estructura gravitacional estimada con tarifa y distancia.
- `w_p` es el peso de la matriz histórica.

La matriz histórica tiene mayor peso porque la validación muestra una estructura OD estable. El gravitacional se mantiene como ajuste parcial y capa de sensibilidad espacial, no como distribuidor final puro.

### 5.3 Costo generalizado e impedancia

El costo generalizado se calcula con tarifa y distancia normalizadas:

```text
C_ij,p = alpha × Tarifa_normalizada_ij,p + beta × Distancia_normalizada_ij
```

Luego se aplica función de impedancia exponencial:

```text
f(C_ij,p) = exp(-lambda × C_ij,p)
```

### 5.4 Balance IPF/Furness

La matriz final se balancea para conservar producciones por origen, atracciones por destino y total mensual por tipo:

```text
T_ij,p,m = IPF(K_ij,p,m, O_i,p,m, D_j,p,m)
```

Este procedimiento asegura que la matriz final mantenga consistencia con la demanda mensual proyectada y con la estructura espacial observada.

### 5.5 Orden de estaciones

Las matrices OD visualizadas y exportadas conservan el orden original de estaciones de los archivos fuente. La homologación de nombres se usa sólo para cruzar OD, tarifas y distancias. No se ordenan estaciones alfabéticamente.

## 6. Módulo preliminar de ingresos OD

Los ingresos OD se calculan multiplicando la matriz de viajes por la matriz tarifaria disponible:

```text
Ingreso_ij,p,m = T_ij,p,m × Tarifa_ij,p,2026
```

Los ingresos deben interpretarse como una estimación preliminar, porque dependen de la cobertura y nivel de desagregación de la matriz tarifaria disponible. Si una futura versión incorpora matrices mensuales-anuales por tipo de tarjeta, el cálculo de ingresos podrá diferenciar mejor tipos de pago, descuentos y subsidios.

## 7. Validaciones incorporadas

El modelo genera salidas de validación para revisar:

- consistencia entre totales mensuales proyectados y matrices OD por tipo;
- suma de Normal, Estudiante y Adulto Mayor respecto del total Biotren distribuido;
- cobertura de tarifas y distancias;
- conservación del orden original de estaciones;
- sensibilidad de la demanda ante cambios de oferta mensual;
- aplicación de feriados por servicio;
- generación de archivos CSV y Excel;
- ejecución del módulo OD sin errores por arreglos NumPy/Pandas no editables.

## 8. Resultados base 2027

| Servicio | Proyección 2027 |
|---|---:|
| Biotren | 12.991.160 |
| Laja-Talcahuano | 540.842 |
| Tren Araucanía | 950.258 |
| Llanquihue-Puerto Montt | 420.853 |
| Total sistema modelado | 14.903.113 |

## 9. Ingresos OD preliminares Biotren

| Tipo de pasajero | Viajes proyectados | Ingresos proyectados |
|---|---:|---:|
| Normal | 9.438.455 | $6.181.205.133 |
| Estudiante | 2.754.612 | $639.943.678 |
| Adulto Mayor | 798.093 | $274.666.957 |
| Total Biotren | 12.991.160 | $7.095.815.768 |

## 10. Limitaciones

- El modelo no debe interpretarse como causal completo de demanda.
- Tarifa y distancia no capturan todos los determinantes de movilidad.
- La distribución OD depende de la estabilidad histórica observada.
- Los ingresos son preliminares si la tarifa disponible no está completamente desagregada por tipo de tarjeta.
- El subsidio no está incorporado en esta versión.
- Variables como tiempos de viaje, capacidad, ocupación, atrasos, cancelaciones y contingencias deben incorporarse desde bases operacionales complementarias.

## 11. Próximos pasos recomendados

- Preparar matrices OD mensuales-anuales por tipo de tarjeta.
- Mejorar ingresos por tipo de pago y descuento.
- Incorporar estimación de subsidio.
- Agregar tiempos de viaje, capacidad y ocupación.
- Incorporar atrasos, cancelaciones y contingencias desde reportes operacionales.
- Validar la distribución OD proyectada con datos reales futuros.

## 12. Bibliografía verificable

1. Transportation Research Board. *TCRP Report 95, Chapter 9: Transit Scheduling and Frequency*. Washington, D.C., 2004. https://trb.org/publications/tcrp/tcrp_rpt_95c9.pdf
2. Balcombe, R., Mackett, R., Paulley, N., Preston, J., Shires, J., Titheridge, H., Wardman, M. & White, P. *The Demand for Public Transport: A Practical Guide*. TRL Report TRL593, 2004. https://www.trl.co.uk/uploads/trl/documents/TRL593%20-%20The%20Demand%20for%20Public%20Transport.pdf
3. Paulley, N., Balcombe, R., Mackett, R., Titheridge, H., Preston, J., Wardman, M., Shires, J. & White, P. *The demand for public transport: The effects of fares, quality of service, income and car ownership*. Transport Policy, 13(4), 295-306, 2006. https://eprints.whiterose.ac.uk/id/eprint/2034/1/ITS23_The_demand_for_public_transport_UPLOADABLE.pdf
4. Berrebi, S., Joshi, S. & Watkins, K. *On Ridership and Frequency*. Transportation Research Part A, 2021. https://doi.org/10.48550/arXiv.2002.02493
5. Wilson, A. G. *Entropy in Urban and Regional Modelling*. Pion, 1970.
6. Ortúzar, J. de D. & Willumsen, L. G. *Modelling Transport*. 4th edition. Wiley, 2011.
7. Feriados de Chile. *Feriados de Chile — Año 2027*. Fuente basada en Biblioteca del Congreso Nacional. https://www.feriados.cl/2027.htm

## 11. Insumos OD Biotren sin binarios versionados

El módulo OD híbrido de Biotren se ejecuta por defecto desde CSV procesados versionados en `data/od_biotren/processed/`. Esto permite usar la app y las validaciones sin mantener archivos Excel binarios dentro del repositorio.

### Archivos obligatorios versionados

Para ejecutar `od_biotren_hibrido.py`, `streamlit_app.py` y `validar_modelo.py` deben existir los siguientes CSV procesados:

- `data/od_biotren/processed/orden_estaciones_original.csv`.
- `data/od_biotren/processed/od_historica_por_tipo_long.csv`.
- `data/od_biotren/processed/tarifas_2026_por_tipo_long.csv`.
- `data/od_biotren/processed/distancia_biotren_km_long.csv`.
- `data/od_biotren/processed/validacion_extraccion_od.csv`.

Estos archivos contienen el orden original de estaciones, las matrices OD históricas por bloque/tipo de pasajero en formato largo, las tarifas 2026 por tipo, la distancia Biotren y la validación de extracción/homologación.

### Archivos externos opcionales

Los Excel originales se consideran insumos externos y están ignorados por Git. Sólo se necesitan para regenerar los CSV procesados:

- `data/od_biotren/input/0. Matrices Biotren may_2026.xlsx`.
- `data/od_biotren/input/Consolidado Tarifas EFE Sur 2026.xlsx`.
- `data/od_biotren/input/Libro1.xlsx`.

La regla general es: los Excel originales no se versionan; los CSV procesados sí se versionan cuando son necesarios para reproducir la ejecución del módulo OD.

### Regeneración de insumos OD

Si se actualizan los Excel originales o faltan los CSV procesados, ejecutar:

```bash
python preparar_insumos_od_biotren.py
```

El script lee los Excel disponibles en `data/od_biotren/input/`, homologa estaciones con la misma lógica del módulo OD y vuelve a generar los CSV en `data/od_biotren/processed/`.

Si los CSV procesados faltan, `od_biotren_hibrido.py` muestra un error claro indicando que se debe ejecutar `python preparar_insumos_od_biotren.py` con los Excel originales disponibles.
