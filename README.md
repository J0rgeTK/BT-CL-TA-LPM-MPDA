# Metodología del modelo predictivo de afluencia EFE Sur 2027

## 1. Propósito y alcance del modelo

El modelo estima la afluencia mensual proyectada de pasajeros para los servicios de EFE Sur durante 2027. Su objetivo es apoyar planificación operacional y evaluación de escenarios de oferta por servicio, unidad operacional, mes y tipo de día.

La metodología separa tres componentes:

1. **Modelo temporal mensual:** estima la demanda mensual total por servicio.
2. **Módulos OD de Biotren:** distribuyen la demanda mensual ya proyectada por línea OD, pares origen-destino y tipo de tarjeta.
3. **Ingresos preliminares y base referencial:** calculan ingresos tarifarios sólo donde existe tarifa directa y preparan una base referencial de subsidio sin calcular montos.

Los módulos OD, ingresos y subsidio referencial son específicos de Biotren. No reemplazan la proyección temporal, no generan el total mensual de demanda y no se aplican a Tren Araucanía, Llanquihue-Puerto Montt ni Laja-Talcahuano.

## 2. Insumos y fuentes de información

Los insumos principales son la afluencia diaria histórica consolidada, parámetros de oferta por servicio, calendario operacional 2027, feriados nacionales, matrices OD históricas procesadas de Biotren, mapeos de estación-línea, participaciones históricas por tipo de tarjeta, tarifas 2026 por tipo de pasajero y distancias entre estaciones. Los CSV procesados versionados permiten ejecutar el modelo sin depender de archivos Excel binarios.

## 3. Modelo temporal mensual de proyección

El cálculo se realiza por unidad operacional `u`, mes `m` y tipo de día `d`, distinguiendo lunes-viernes, sábado y domingo. Cada mes se calcula de manera independiente. El total anual corresponde a la suma de los doce meses, por lo que una modificación de oferta afecta el mes editado y el total anual por agregación.

```text
V0(u,m,d) = S0(u,m,d) × N_op(u,m,d) × (1 - tau(u,m,d))
D0(u,m,d) = V0(u,m,d) × q(u,m,d) × F_nivel(s) × F_est(s,m)
V1(u,m,d) = S1(u,m,d) × N_op(u,m,d) × (1 - tau(u,m,d) - c(u))
D1(u,m,d) = D0(u,m,d) × (V1(u,m,d) / V0(u,m,d)) ^ epsilon(s)
```

Donde `S0` es la oferta base del escenario, `S1` es la oferta editable, `N_op` corresponde a días operacionales efectivos, `tau` es la tasa de supresión histórica, `q` es productividad media, `F_nivel` es el factor de nivel, `F_est` representa estacionalidad mensual, `epsilon` es elasticidad de demanda respecto de oferta y `c` es una contingencia adicional de supresión para análisis de sensibilidad.

La elasticidad es menor que 1 para representar respuesta parcial de demanda ante cambios de oferta.

## 4. Calendario operacional, oferta y feriados

El calendario 2027 se transforma en días operacionales efectivos por servicio, mes y tipo de día. Las reglas implementadas son:

- **Biotren, Tren Araucanía y Llanquihue-Puerto Montt:** feriados nacionales con oferta efectiva cero.
- **Laja-Talcahuano:** feriados nacionales con oferta de fin de semana. Si el feriado cae lunes-viernes, se imputa como día operacional tipo domingo.

Los feriados nacionales utilizados se encuentran en `data/feriados_chile_2027.csv`. El conteo operacional resultante se exporta en `data/calendario_operacional_2027.csv` y `outputs/calendario_operacional_2027.csv`.

## 5. Tratamiento por servicio

### 5.1 Biotren

Biotren se modela separando L1 y L2 en el motor temporal. La oferta se edita por línea, mes y tipo de día. El escenario operacional 2027 considera L1 con 48 servicios lunes-viernes durante el año y L2 con 106 servicios lunes-viernes entre enero y abril, aumentando a 109 servicios lunes-viernes desde mayo.

La proyección mensual utiliza días operacionales efectivos, feriados sin operación, productividad histórica, estacionalidad mensual y elasticidad parcial de oferta. Laja-Talcahuano se mantiene como servicio independiente para evitar doble conteo dentro del corredor L1.

El escenario operacional vigente proyecta **12.673.199 pasajeros** para Biotren. La proyección incorpora una baja operacional progresiva respecto del escenario de referencia inicial y se estructura en tres componentes metodológicos: ajuste base progresivo hacia un total intermedio cercano a 12,8 millones, afectación operacional de Línea 2 en fines de semana concentrada en enero y febrero, y ajuste residual distribuido en meses laborales. El resultado se mantiene cercano al objetivo operacional de 12,7 millones de pasajeros.

La distribución por línea OD, la distribución OD por tipo de tarjeta y los ingresos tarifarios preliminares se recalculan después de obtener el total mensual vigente de Biotren. La base referencial de subsidio no calcula montos monetarios.

### 5.2 Tren Araucanía

Tren Araucanía se modela por componente de servicio:

- Temuco - Victoria.
- Temuco - Pitrufquén.
- Claret.

El escenario operacional vigente proyecta **809.484 pasajeros** para Tren Araucanía. La oferta Victoria-Temuco considera 11 servicios lunes-viernes durante todo 2027; esta condición operacional reduce la proyección respecto de escenarios de mayor oferta.

Cada componente responde a su propia oferta y elasticidad. Temuco-Victoria tiene mayor respuesta marginal esperada que Pitrufquén y Claret. Claret se trata como componente escolar específico y se restringe a marzo-diciembre; enero y febrero no generan oferta ni demanda para este componente. La distribución mensual combina patrón histórico, calendario operacional, oferta mensual y tratamiento escolar. El control de marzo evita concentración artificial mediante suavizamiento técnico cuando la relación frente al promedio abril-diciembre supera el umbral definido.

Tren Araucanía no utiliza MOD Biotren, categorías L1/L2/L1-L2, distribución OD Biotren, tipo de tarjeta Biotren, ingresos Biotren ni base referencial de subsidio Biotren.

### 5.3 Llanquihue-Puerto Montt

Llanquihue-Puerto Montt se modela con operación de lunes a viernes. En el escenario base no se consideran servicios planificados de fin de semana ni operación en feriados nacionales.

El escenario operacional vigente proyecta **412.132 pasajeros** para Llanquihue-Puerto Montt. Marzo-diciembre se calibra con un promedio laboral referencial cercano a 1.500 pasajeros por día laboral; el promedio reportado para el bloque es aproximadamente **1.499,85 pasajeros por día laboral**. Esta referencia opera como ancla metodológica y no como restricción rígida idéntica para todos los meses. Enero y febrero consideran una reducción por menor efecto de novedad del servicio.

El servicio mantiene independencia metodológica respecto de módulos OD Biotren, categorías L1/L2/L1-L2, tipo de tarjeta, ingresos Biotren y base referencial de subsidio Biotren.

### 5.4 Laja-Talcahuano / Corto Laja

Laja-Talcahuano se proyecta como servicio propio. La oferta base considera 8 servicios diarios durante el año, con excepción de sábados y domingos de enero y febrero, donde se consideran 10 servicios. Los feriados nacionales se modelan con oferta de fin de semana.

El escenario operacional vigente proyecta **540.842 pasajeros** para Laja-Talcahuano. El servicio no recibe ajuste operacional específico nuevo dentro de la recalibración; su tratamiento sigue asociado a patrón histórico, oferta operacional, calendario y regla de feriados como operación de fin de semana.

Laja-Talcahuano no utiliza MOD Biotren, categorías L1/L2/L1-L2, distribución OD Biotren, tipo de tarjeta Biotren, ingresos Biotren ni base referencial de subsidio Biotren.

## 6. Escenario operacional 2027 vigente

| Servicio | Proyección anual vigente 2027 |
|---|---:|
| Biotren | 12.673.199 |
| Tren Araucanía | 809.484 |
| Llanquihue-Puerto Montt | 412.132 |
| Laja-Talcahuano / Corto Laja | 540.842 |
| **Total sistema** | **14.435.657** |

Estos valores corresponden a la base operacional vigente sobre la cual se ejecutan los módulos OD de Biotren, el backtesting diagnóstico y las bandas de incertidumbre.

## 7. Biotren: distribución por línea OD basada en MOD

La demanda total mensual de Biotren proviene del modelo temporal. La MOD histórica atribuible no genera ese total; sólo distribuye la demanda ya proyectada por línea OD.

Cada par origen-destino se clasifica con el mapeo estación-línea versionado en `data/od_biotren/processed/mapeo_estacion_linea_biotren.csv`. Las categorías estándar proyectadas son:

| Categoría OD | Interpretación |
|---|---|
| `L1` | Origen y destino atribuibles al corredor L1, incluyendo viajes desde/hacia estación común cuando el otro extremo es L1. |
| `L2` | Origen y destino atribuibles al corredor L2, incluyendo viajes desde/hacia estación común cuando el otro extremo es L2. |
| `L1-L2` | Viajes entre corredores o que implican combinación entre líneas. |

Concepción se marca como estación común/intercambio (`L1_L2`). El par `Concepción → Concepción` se mantiene como control `No clasificado`, porque corresponde a diagonal común-común y no debe asignarse artificialmente a L1, L2 ni L1-L2. El `No clasificado` se reporta como control diagnóstico histórico y no recibe proyección estándar.

```text
Participación_linea_m = Viajes_observados_linea_m / (Viajes_L1_m + Viajes_L2_m + Viajes_L1-L2_m)
Proyección_linea_m = Proyección_Biotren_m × Participación_linea_m
```

El supuesto fijo 80/20 no corresponde al criterio metodológico vigente; fue reemplazado por participaciones mensuales calculadas con MOD histórica atribuible. La suma mensual `L1 + L2 + L1-L2` conserva el total mensual de Biotren, salvo diferencias numéricas de redondeo.

## 8. Biotren: distribución OD por tipo de tarjeta

El módulo OD por tipo de tarjeta distribuye el total mensual vigente de Biotren entre tipos de tarjeta y pares origen-destino. La suma de todos los tipos de tarjeta conserva la demanda mensual total de Biotren.

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

## 9. Ingresos tarifarios preliminares

Los ingresos OD preliminares se calculan en memoria multiplicando la matriz de viajes por la tarifa aplicable a cada tipo de tarjeta:

```text
Ingreso_ij,t,m = Viajes_ij,t,m × Tarifa_ij,t
```

Los ingresos tarifarios preliminares aplican sólo donde existe tarifa directa: `monedero`, `media_superior` y `adulto_mayor`. Los tipos `estudiante_basica`, `discapacitado`, `funcionario_normal`, `funcionario_especial` y `convenio_colectivo` usan tarifa 0. Los ingresos no incorporan subsidios, evasión, ajustes contables, reglas comerciales adicionales ni variación tarifaria dinámica por periodo.

## 10. Base referencial de subsidio

La base referencial de subsidio se prepara para trazabilidad metodológica, sin calcular montos. El grupo `subsidio_normal_base` agrupa todas las matrices OD excepto `media_superior` y `adulto_mayor`; `subsidio_estudiante_media_superior` considera sólo `media_superior`; y `adulto_mayor` no considera subsidio referencial. Esta base no corresponde a liquidación, compensación ni estimación monetaria implementada.

## 11. Backtesting histórico diagnóstico

El modelo incluye un módulo de backtesting histórico para contrastar periodos observados conocidos contra estimaciones producidas por el mismo motor mensual-elástico utilizado en el escenario vigente. El backtesting es retrospectivo diagnóstico no holdout: audita consistencia, escala y perfil mensual, pero no reemplaza ni recalibra la proyección operacional 2027.

El backtesting entrega métricas por servicio y para el total sistema: MAE, RMSE, MAPE, WMAPE y sesgo. WMAPE es la referencia agregada principal porque pondera por volumen observado.

## 12. Bandas de incertidumbre diagnósticas

Las bandas de incertidumbre derivan de métricas históricas de error del backtesting, especialmente WMAPE. No son intervalos estadísticos formales ni intervalos de confianza. El ajuste por sesgo es una sensibilidad diagnóstica.

Las bandas se calculan sobre la proyección base 2027 vigente:

| Servicio | Base 2027 usada por incertidumbre |
|---|---:|
| Biotren | 12.673.199 |
| Tren Araucanía | 809.484 |
| Llanquihue-Puerto Montt | 412.132 |
| Laja-Talcahuano | 540.842 |

## 13. Validaciones, limitaciones y próximos pasos

El modelo genera controles de consistencia mensual/anual, feriados por servicio, sensibilidad de oferta, conservación de totales OD de Biotren, suma de participaciones MOD por línea, consistencia por tipo de tarjeta, ingresos sólo para tipos con tarifa aplicable, base referencial de subsidio sin montos, backtesting diagnóstico y bandas de incertidumbre sin valores negativos.

La sección **Validación histórica** de Streamlit muestra los resultados agregados, el detalle observado vs estimado y las advertencias. El proceso se ejecuta en memoria: no genera archivos binarios, no modifica outputs masivos y no altera `data/od_biotren/processed/`.

## Escenario 2027 recalibrado

El escenario 2027 incorpora una recalibración operacional trazable sin modificar los datos históricos procesados. Biotren aplica una baja progresiva del total mensual, una afectación operacional adicional en Línea 2 durante fines de semana de enero-febrero y un ajuste residual distribuido en meses laborales, de modo que la demanda anual se ubica en el entorno de 12,7 millones de pasajeros.

Tren Araucanía se calcula por componente de servicio. Victoria-Temuco opera con 11 servicios de lunes a viernes durante todo 2027, Temuco-Pitrufquén se mantiene separado y Claret conserva su tratamiento escolar específico de marzo a diciembre. El perfil mensual incluye diagnóstico y suavizamiento de marzo cuando corresponde para evitar concentración artificial.

Llanquihue-Puerto Montt se calibra con un promedio de día laboral cercano a 1.500 pasajeros entre marzo y diciembre, permitiendo variación mensual por estacionalidad y calendario. Enero y febrero incorporan una reducción por menor efecto novedad del servicio y no se fuerzan al promedio laboral de meses ancla.

Laja-Talcahuano no recibe una modificación específica nueva en la recalibración y mantiene su regla operacional de feriados como fin de semana. Las bandas de incertidumbre se calculan sobre la nueva proyección base 2027, conservando las métricas históricas de WMAPE y sesgo del backtesting.
