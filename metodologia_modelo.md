# Metodología del modelo predictivo de afluencia EFE Sur 2027

## 1. Propósito del modelo

El modelo estima la afluencia mensual proyectada de pasajeros para los servicios de EFE Sur durante 2027. Su objetivo es apoyar planificación operacional y evaluación de escenarios de oferta por servicio, unidad operacional, mes y tipo de día.

Para Biotren, el modelo incorpora además una capa espacial origen-destino (OD) que distribuye la demanda mensual proyectada por par de estaciones y tipo de tarjeta. Esta capa permite obtener matrices de viajes e ingresos preliminares, sin modificar la proyección temporal de demanda.

## 2. Alcance del modelo

La metodología se organiza en tres componentes complementarios:

1. **Modelo temporal de afluencia mensual:** estima la demanda mensual total por servicio.
2. **Módulo espacial OD de Biotren:** asigna la demanda mensual de Biotren a pares origen-destino y tipos de pasajero.
3. **Módulo preliminar de ingresos OD:** calcula ingresos referenciales multiplicando viajes OD por tarifas disponibles.

El módulo OD no reemplaza el modelo temporal. La demanda total mensual se calcula primero y luego se distribuye espacialmente.

## 3. Insumos principales

Los insumos principales son la afluencia diaria histórica consolidada, parámetros de oferta por servicio, calendario operacional 2027, feriados nacionales, matrices OD históricas procesadas de Biotren, mapeos de estación-línea, participaciones históricas por tipo de tarjeta, tarifas 2026 por tipo de pasajero y distancias entre estaciones. Los CSV procesados versionados permiten ejecutar el modelo sin depender de archivos Excel binarios.

## 4. Modelo temporal mensual de afluencia

El cálculo se realiza por unidad operacional `u`, mes `m` y tipo de día `d`, distinguiendo lunes-viernes, sábado y domingo. Cada mes se calcula de manera independiente. El total anual corresponde a la suma de los doce meses, por lo que una modificación de oferta afecta el mes editado y el total anual por agregación.

### 4.1 Ecuaciones generales

```text
V0(u,m,d) = S0(u,m,d) × N_op(u,m,d) × (1 - tau(u,m,d))
D0(u,m,d) = V0(u,m,d) × q(u,m,d) × F_nivel(s) × F_est(s,m)
V1(u,m,d) = S1(u,m,d) × N_op(u,m,d) × (1 - tau(u,m,d) - c(u))
D1(u,m,d) = D0(u,m,d) × (V1(u,m,d) / V0(u,m,d)) ^ epsilon(s)
```

Donde:

- `S0` es la oferta base del escenario.
- `S1` es la oferta de escenario editable.
- `N_op` es la cantidad de días operacionales efectivos del tipo respectivo en el mes.
- `tau` es la tasa de supresión histórica incorporada al cálculo.
- `q` es la productividad media por servicio, construida desde datos históricos disponibles.
- `F_nivel` ajusta el nivel general del servicio.
- `F_est` representa el perfil estacional mensual.
- `epsilon` es la elasticidad de demanda respecto de la oferta.
- `c` es una contingencia adicional de supresión para análisis de sensibilidad.

La elasticidad es menor que 1 para representar una respuesta parcial de demanda ante cambios de oferta. Un aumento de servicios puede mejorar frecuencia y accesibilidad, pero no implica necesariamente un aumento proporcional de pasajeros.

## 5. Tratamiento de calendario, feriados y oferta

El calendario 2027 se transforma en días operacionales efectivos por servicio, mes y tipo de día. Las reglas implementadas son:

- **Biotren, Tren Araucanía y Llanquihue-Puerto Montt:** feriados nacionales con oferta efectiva cero.
- **Laja-Talcahuano:** feriados nacionales con oferta de fin de semana. Si el feriado cae lunes-viernes, se imputa como día operacional tipo domingo.

Los feriados nacionales utilizados se encuentran en `data/feriados_chile_2027.csv`. El conteo operacional resultante se exporta en `data/calendario_operacional_2027.csv` y `outputs/calendario_operacional_2027.csv`.

## 6. Proyección por servicio

### 6.1 Biotren

Biotren se modela separando L1 y L2. La oferta se edita por línea, mes y tipo de día. El escenario base considera L1 con 48 servicios lunes-viernes durante 2027 y L2 con 106 servicios lunes-viernes entre enero y abril, aumentando a 109 servicios lunes-viernes desde mayo.

La proyección mensual utiliza días operacionales efectivos, feriados sin operación, productividad histórica, estacionalidad mensual y elasticidad parcial de oferta. Laja-Talcahuano se mantiene como servicio independiente para evitar doble conteo dentro del corredor L1.

El bloque marzo-abril incorpora un tratamiento estacional para mantener una trayectoria mensual consistente con la evidencia histórica disponible, sin transformar el modelo en una distribución anual fija.

### 6.2 Laja-Talcahuano

Laja-Talcahuano se proyecta como servicio propio. La oferta base considera 8 servicios diarios durante el año, con excepción de sábados y domingos de enero y febrero, donde se consideran 10 servicios. Los feriados nacionales se modelan con oferta de fin de semana.

El escenario representa una recuperación operacional parcial mediante supresión acotada, elasticidad parcial de oferta y mayor peso del patrón histórico de mejor desempeño.

### 6.3 Tren Araucanía

Tren Araucanía se modela por tipo de servicio:

- Temuco - Victoria.
- Temuco - Pitrufquén.
- Claret.

Cada tramo responde a su propia oferta y elasticidad. Temuco-Victoria tiene mayor respuesta marginal esperada que Pitrufquén y Claret. Claret se restringe a marzo-diciembre por su carácter escolar, por lo que enero y febrero no generan oferta ni demanda para este componente.

### 6.4 Llanquihue-Puerto Montt

Llanquihue-Puerto Montt se modela con operación de lunes a viernes. En el escenario base no se consideran servicios planificados de fin de semana ni operación en feriados nacionales. Enero y febrero conservan una señal estival dentro del perfil mensual.

## 7. Biotren: proyección total mensual

El modelo mensual estima la demanda total de Biotren y, posteriormente, el módulo OD distribuye dicha demanda según estructura histórica de viajes. La MOD no genera el total mensual de Biotren; se usa para distribuir espacialmente o por línea la demanda total proyectada.

## 8. Biotren: distribución OD por tipo de tarjeta

El modelo temporal mensual sigue proyectando la demanda total de Biotren. El módulo OD no modifica esa proyección: distribuye la demanda mensual ya estimada entre tipos de tarjeta y pares origen-destino. La estructura implementada es:

```text
Proyección mensual Biotren
→ distribución por tipo de tarjeta
→ patrón OD histórico mensual por tarjeta
→ matriz OD de viajes por mes y tipo de tarjeta
→ ingreso tarifario preliminar según tarifa aplicable
→ base referencial de subsidio futuro, sin cálculo de montos
```

### 8.1 Tipos de tarjeta

La segmentación mensual se calcula con participaciones históricas por tipo de tarjeta:

```text
Demanda(t,m) = Demanda(Biotren,m) × Participación(t,m)
```

Se consideran ocho tipos de tarjeta:

| Tipo de tarjeta | Regla de ingreso tarifario preliminar |
|---|---|
| `monedero` | Usa tarifa normal/adulto. |
| `media_superior` | Usa tarifa estudiante. |
| `adulto_mayor` | Usa tarifa adulto mayor. |
| `estudiante_basica` | Tarifa 0. |
| `discapacitado` | Tarifa 0. |
| `funcionario_normal` | Tarifa 0. |
| `funcionario_especial` | Tarifa 0. |
| `convenio_colectivo` | Tarifa 0. |

Los tipos con tarifa 0 conservan viajes proyectados en la distribución de afluencia, pero no generan ingreso tarifario directo.

### 8.2 Distribución OD por tipo de tarjeta

Para cada mes y tipo de tarjeta se utiliza la participación OD histórica del mismo segmento para asignar viajes a pares origen-destino:

```text
Viajes_ij,t,m = Demanda(t,m) × ParticipaciónOD_ij,t,m
```

La suma de todos los tipos de tarjeta conserva la demanda mensual total de Biotren. La vista de la aplicación está acotada al mes y tipo seleccionados para evitar cargar o producir matrices long completas.


## 9. Biotren: distribución por línea OD basada en MOD

Como criterio estándar, la distribución mensual de Biotren por línea OD se prepara a partir de MOD histórica atribuible por línea OD. El supuesto fijo 80/20 fue reemplazado como criterio estándar por esta distribución basada en MOD histórica atribuible y no modifica la proyección mensual total de Biotren calculada por el motor mensual-elástico.

Cada par origen-destino se clasifica con el mapeo estación-línea versionado en `data/od_biotren/processed/mapeo_estacion_linea_biotren.csv`. Las categorías estándar proyectadas son:

| Categoría OD | Interpretación |
|---|---|
| `L1` | Origen y destino atribuibles al corredor L1, incluyendo viajes desde/hacia estación común cuando el otro extremo es L1. |
| `L2` | Origen y destino atribuibles al corredor L2, incluyendo viajes desde/hacia estación común cuando el otro extremo es L2. |
| `L1-L2` | Viajes entre corredores o que implican combinación entre líneas. |

Concepción se marca como estación común/intercambio (`L1_L2`). El par `Concepción → Concepción` se mantiene como control `No clasificado`, porque corresponde a diagonal común-común y no debe asignarse artificialmente a L1, L2 ni L1-L2. Las estaciones `SIN_CLASIFICAR` no registran viajes observados históricos asociados en el diagnóstico vigente.

Para cada mes, las participaciones se calculan sólo sobre viajes atribuibles:

```text
Participación_linea_m = Viajes_observados_linea_m / (Viajes_L1_m + Viajes_L2_m + Viajes_L1-L2_m)
Proyección_linea_m = Proyección_Biotren_m × Participación_linea_m
```

El `No clasificado` se reporta como control diagnóstico histórico y no recibe proyección estándar. La suma mensual `L1 + L2 + L1-L2` conserva el total mensual de Biotren, salvo diferencias numéricas de redondeo.

Con la proyección vigente, la distribución anual resultante es: `L1`: 1.503.779 viajes (11,5754%); `L2`: 10.496.944 viajes (80,8007%); `L1-L2`: 990.437 viajes (7,6239%); Total Biotren: 12.991.160 viajes.

### 9.1 Costo generalizado e impedancia

El costo generalizado se calcula con tarifa y distancia normalizadas:

```text
C_ij,p = alpha × Tarifa_normalizada_ij,p + beta × Distancia_normalizada_ij
```

Luego se aplica función de impedancia exponencial:

```text
f(C_ij,p) = exp(-lambda × C_ij,p)
```

### 9.2 Balance IPF/Furness

La matriz final se balancea para conservar producciones por origen, atracciones por destino y total mensual por tipo:

```text
T_ij,p,m = IPF(K_ij,p,m, O_i,p,m, D_j,p,m)
```

Este procedimiento mantiene consistencia entre la demanda mensual proyectada y la estructura espacial utilizada.

### 9.3 Orden de estaciones

Las matrices OD visualizadas y exportadas conservan el orden original de estaciones de los insumos procesados. La homologación de nombres se utiliza para integrar OD, tarifas y distancias, sin ordenar estaciones alfabéticamente.

## 10. Ingresos tarifarios preliminares

Los ingresos OD preliminares se calculan en memoria multiplicando la matriz de viajes por la tarifa aplicable a cada tipo de tarjeta:

```text
Ingreso_ij,t,m = Viajes_ij,t,m × Tarifa_ij,t
```

Las reglas aplicadas son: `monedero` usa tarifa normal/adulto; `media_superior` usa tarifa estudiante; `adulto_mayor` usa tarifa adulto mayor; `estudiante_basica`, `discapacitado`, `funcionario_normal`, `funcionario_especial` y `convenio_colectivo` usan tarifa 0. Los ingresos deben interpretarse como una estimación preliminar. No incorporan subsidios, ajustes contables, evasión, reglas comerciales adicionales ni variación tarifaria dinámica por periodo.

## 11. Base referencial de subsidio

La base referencial de subsidio se prepara para trazabilidad metodológica, sin calcular montos. El grupo `subsidio_normal_base` agrupa todas las matrices OD excepto `media_superior` y `adulto_mayor`; `subsidio_estudiante_media_superior` considera sólo `media_superior`; y `adulto_mayor` no considera subsidio referencial. Esta base no debe interpretarse como liquidación, compensación ni estimación monetaria implementada.

## 12. Validaciones

El modelo genera controles para revisar:

- consistencia entre totales mensuales proyectados y matrices OD por tipo;
- suma de tipos de tarjeta respecto del total mensual Biotren distribuido;
- participaciones mensuales MOD por línea OD atribuible (`L1`, `L2`, `L1-L2`) suman 1;
- conservación del total mensual Biotren al distribuir por línea OD;
- reporte de `No clasificado` como control sin proyección estándar;
- cobertura de tarifas para tipos con ingreso tarifario directo;
- conservación del orden original de estaciones;
- igualdad de dimensión y orden entre matrices de viajes e ingresos;
- sensibilidad de demanda ante cambios de oferta mensual;
- aplicación de feriados por servicio;
- ejecución del módulo OD con arreglos NumPy/Pandas no escribibles;
- disponibilidad de insumos OD procesados en CSV;
- generación de salidas CSV principales.

## 13. Limitaciones

- El modelo es una herramienta de proyección operacional y espacial; no corresponde a un modelo causal completo de demanda.
- Las elasticidades son agregadas por servicio o tramo y no capturan heterogeneidad individual.
- Tarifa y distancia no representan todos los determinantes de movilidad.
- Los ingresos OD son preliminares y dependen de la cobertura tarifaria disponible.
- Los tipos con tarifa 0 conservan viajes proyectados, pero no generan ingreso tarifario directo en esta etapa.
- No se calculan montos de subsidio.
- No se incorporan capacidad máxima, ocupación, tiempos de viaje, regularidad diaria ni confiabilidad operacional detallada.
- Los resultados están condicionados por la calidad, cobertura y consistencia de los datos históricos disponibles.

## 14. Próximos pasos

- Profundizar la formulación de subsidios a partir de la base referencial preparada.
- Integrar tiempos de viaje, capacidad, ocupación y regularidad operacional.
- Mejorar el módulo de ingresos con reglas tarifarias, descuentos, subsidios y validación contable.
- Incorporar variables operacionales complementarias, como atrasos, cancelaciones y niveles de servicio.
- Contrastar las proyecciones con observaciones futuras y actualizar parámetros cuando exista nueva evidencia.

## 15. Insumos OD Biotren sin binarios versionados

El módulo OD híbrido de Biotren se ejecuta por defecto desde CSV procesados versionados en `data/od_biotren/processed/`. Esto permite usar la app y las validaciones sin mantener archivos Excel binarios dentro del repositorio.

### 15.1 Archivos obligatorios versionados

Para ejecutar `od_biotren_hibrido.py`, `streamlit_app.py` y `validar_modelo.py` deben existir los siguientes CSV procesados:

- `data/od_biotren/processed/orden_estaciones_original.csv`.
- `data/od_biotren/processed/od_historica_por_tipo_long.csv`.
- `data/od_biotren/processed/od_historica_tipo_tarjeta_long.csv`.
- `data/od_biotren/processed/participacion_mensual_tipo_tarjeta.csv`.
- `data/od_biotren/processed/participacion_od_tipo_tarjeta_mensual.csv`.
- `data/od_biotren/processed/mapeo_tipo_tarjeta.csv`.
- `data/od_biotren/processed/mapeo_estacion_linea_biotren.csv`.
- `data/od_biotren/processed/base_subsidio_referencial_historica_long.csv`.
- `data/od_biotren/processed/tarifas_2026_por_tipo_long.csv`.
- `data/od_biotren/processed/distancia_biotren_km_long.csv`.
- `data/od_biotren/processed/validacion_extraccion_od.csv`.

Estos archivos contienen el orden original de estaciones, matrices OD históricas, participaciones por tipo de tarjeta, mapeos tarifarios, base referencial de subsidio futuro, tarifas 2026 por tipo, distancia Biotren y validación de extracción/homologación.

### 15.2 Archivos externos opcionales

Los Excel originales son insumos externos opcionales y están ignorados por Git. Sólo se necesitan para regenerar los CSV procesados:

- `data/od_biotren/input/0. Matrices Biotren may_2026.xlsx`.
- `data/od_biotren/input/0. Matrices Biotren mar_2026.xlsx`.
- `data/od_biotren/input/0. Matrices Biotren abr_2026.xlsx`.
- `data/od_biotren/input/Consolidado Tarifas EFE Sur 2026.xlsx`.
- `data/od_biotren/input/Libro1.xlsx`.

La regla general es: los Excel originales no se versionan; los CSV procesados sí se versionan cuando son necesarios para reproducir la ejecución del módulo OD. La aplicación muestra matrices por mes y tipo de tarjeta seleccionados, evitando cargar o producir matrices long completas en la visualización.

### 15.3 Regeneración de insumos OD

Si se actualizan los Excel originales o faltan los CSV procesados, ejecutar:

```bash
python preparar_insumos_od_biotren.py
```

El script lee los Excel disponibles en `data/od_biotren/input/`, homologa estaciones con la misma lógica del módulo OD y vuelve a generar los CSV en `data/od_biotren/processed/`.

Si los CSV procesados faltan, `od_biotren_hibrido.py` muestra un error indicando que se debe ejecutar `python preparar_insumos_od_biotren.py` con los Excel originales disponibles.

## 16. Bibliografía de referencia

1. Transportation Research Board. *TCRP Report 95, Chapter 9: Transit Scheduling and Frequency*. Washington, D.C., 2004.
2. Balcombe, R. et al. *The Demand for Public Transport: A Practical Guide*. TRL Report TRL593, 2004.
3. Paulley, N. et al. *The demand for public transport: The effects of fares, quality of service, income and car ownership*. Transport Policy, 13(4), 295-306, 2006.
4. Berrebi, S., Joshi, S. & Watkins, K. *On Ridership and Frequency*. Transportation Research Part A, 2021.
5. Wilson, A. G. *Entropy in Urban and Regional Modelling*. Pion, 1970.
6. Ortúzar, J. de D. & Willumsen, L. G. *Modelling Transport*. 4th edition. Wiley, 2011.
7. Feriados de Chile. *Feriados de Chile — Año 2027*. Fuente basada en Biblioteca del Congreso Nacional.
