# Insumos OD Biotren procesados por tipo de tarjeta

Estos archivos CSV fueron generados desde las matrices OD anuales por tipo de tarjeta de Biotren.

## Archivos generados

- `orden_estaciones_original.csv`: orden maestro de estaciones, preservado desde la matriz original.
- `od_historica_tipo_tarjeta_long.csv`: matrices OD mensuales en formato largo para los 8 tipos de tarjeta.
- `participacion_mensual_tipo_tarjeta.csv`: participación mensual de cada tipo de tarjeta sobre el total observado.
- `participacion_od_tipo_tarjeta_mensual.csv`: participación OD dentro de cada tipo de tarjeta y mes.
- `mapeo_tipo_tarjeta.csv`: reglas de ingreso tarifario y agrupación referencial de subsidio.
- `validacion_extraccion_tipo_tarjeta.csv`: controles de lectura, dimensiones, orden de estaciones, totales y advertencias.
- `base_subsidio_referencial_historica_long.csv`: base histórica agrupada para una futura formulación de subsidio.
- `resumen_mensual_total_tipo_tarjeta.csv`: total observado mensual agregado de los tipos disponibles.

## Regla tarifaria prevista para el modelo

- `monedero`: tarifa adulto/normal.
- `media_superior`: tarifa estudiante.
- `adulto_mayor`: tarifa adulto mayor.
- Resto de tipos: tarifa 0 en la proyección preliminar de ingresos.

## Regla referencial para subsidio

- `subsidio_normal_base`: suma de todos los tipos excepto `media_superior` y `adulto_mayor`.
- `subsidio_estudiante_media_superior`: sólo `media_superior`.
- `sin_subsidio_adulto_mayor`: sólo `adulto_mayor`.

El monto de subsidio no se calcula en estos CSV; sólo se deja preparada la base OD referencial.

## Dimensiones

- Estaciones: 27
- Tipos de tarjeta: 8
- Meses por tipo: 12
- Registros OD esperados: 8 × 12 × 27 × 27 = 69,984

## Advertencias detectadas

En algunos archivos, el texto interno de la celda descriptiva del tipo de pasajero no coincide con el nombre del archivo. Para evitar ambigüedades, la clasificación usada en los CSV se basa en el nombre del archivo externo y en `mapeo_tipo_tarjeta.csv`. La advertencia queda documentada en `validacion_extraccion_tipo_tarjeta.csv`.
