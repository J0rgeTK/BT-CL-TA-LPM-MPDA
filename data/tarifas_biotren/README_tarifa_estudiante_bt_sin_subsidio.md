# Tarifa estudiante BT sin subsidio - matriz normalizada corregida

Fuente original: `Estudiante BT sin subsidio.xlsx`, hoja `Hoja1`.

Uso previsto:
- Insumo para calcular el subsidio asociado a la MOD `media_superior` de Biotren.
- No reemplaza la tarifa estudiante pagada usada para ingresos por venta de pasajes.
- No modifica la proyección de afluencia 2027.

Archivos:
- `tarifa_estudiante_bt_sin_subsidio_wide_raw.csv`: matriz fuente en formato ancho.
- `tarifa_estudiante_bt_sin_subsidio_long.csv`: matriz en formato largo para consumo del modelo.

Columnas del archivo largo:
- `origen`, `destino`: estaciones de la matriz fuente.
- `tarifa_estudiante_bt_sin_subsidio`: tarifa estudiante BT sin subsidio por par OD.
- `es_diagonal`: 1 si origen y destino son la misma estación; 0 en caso contrario.
- `origen_en_modelo`, `destino_en_modelo`: validación contra `data/od_biotren/processed/orden_estaciones_original.csv`.
- `tarifa_disponible`: 1 si existe tarifa en la matriz fuente; 0 si está vacía.
- `fuente`: nombre del archivo original.

Diagnóstico de cobertura:
- Estaciones en matriz fuente: 26.
- Estaciones en orden OD del modelo revisado: 27.
- Pares OD totales en formato largo: 676.
- Pares no diagonales con tarifa disponible: 600.
- Pares no diagonales sin tarifa: 50.
- Estaciones del modelo no presentes en la matriz fuente: Concepcion Centro.
- Estaciones de la matriz fuente no presentes en el modelo: ninguna.

Advertencias metodológicas:
- La diagonal de la matriz debe tratarse como cero para el cálculo de subsidio.
- `Concepcion Centro` no aparece en la matriz fuente y debe mantenerse como caso sin cobertura tarifaria salvo definición explícita.
- `Pasajero Lota` aparece en la matriz, pero no posee tarifas disponibles hacia/desde otras estaciones en la fuente recibida.
- No se debe imputar tarifa faltante sin regla metodológica validada.

Regla de cálculo propuesta para subsidio estudiante:
- Grupo estudiante: sólo `media_superior`.
- `subsidio_estudiante = suma(MOD_media_superior_ij × max(0, tarifa_estudiante_bt_sin_subsidio_ij - tarifa_estudiante_pagada_ij))`, con diagonal en cero. La venta de pasajes de `media_superior` usa la tarifa estudiante pagada; el subsidio cubre sólo la brecha tarifaria y no modifica la afluencia proyectada.

Regla de cálculo propuesta para subsidio normal:
- Grupo normal: todas las tarjetas excepto `media_superior` y `adulto_mayor`.
- `monto_tarifa_normal = suma(MOD_normal_base_ij × tarifa_normal_ij)`, con diagonal en cero.
- `subsidio_normal = monto_tarifa_normal / (1 - tasa_descuento) - monto_tarifa_normal`.
- La `tasa_descuento` debe quedar parametrizada y validada como valor mayor que 0 y menor que 1.
