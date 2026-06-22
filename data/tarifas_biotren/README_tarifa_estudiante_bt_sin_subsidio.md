# Tarifa estudiante BT sin subsidio normalizada

## Fuente

Archivo base: `Presupuesto 2026 Biotren v4.xlsx`  
Hoja: `Tarifa Escolar Feb-sep`  
Bloque utilizado: `Estudiante Sin subsidio 2026`  
Rango de referencia del bloque fuente: encabezados en `B30:AA30`, matriz en `B31:AA56`.

Estos archivos normalizan la matriz que debe utilizarse para calcular el ingreso teórico estudiante sin subsidio de Biotren.

## Archivos

- `tarifa_estudiante_bt_sin_subsidio_long.csv`: matriz en formato largo para uso del modelo.
- `tarifa_estudiante_bt_sin_subsidio_wide_raw.csv`: matriz ancha normalizada.
- `validacion_comparacion_tarifa_estudiante_sin_subsidio.csv`: comparación contra la matriz versionada previamente, para control de auditoría.
- `README_tarifa_estudiante_bt_sin_subsidio.md`: descripción metodológica.

## Esquema del archivo largo

Columnas:

- `origen`: estación de origen homologada al modelo.
- `destino`: estación de destino homologada al modelo.
- `tarifa_estudiante_bt_sin_subsidio`: tarifa estudiante sin subsidio proveniente del presupuesto base.
- `es_diagonal`: 1 si origen = destino, 0 en caso contrario.
- `origen_en_modelo`: 1 si la estación de origen está en el universo de estaciones Biotren del modelo.
- `destino_en_modelo`: 1 si la estación de destino está en el universo de estaciones Biotren del modelo.
- `tarifa_disponible`: 1 si existe tarifa disponible; 0 si la tarifa está vacía.
- `fuente`: identificación del archivo, hoja y bloque fuente.

## Cobertura

- Estaciones en matriz fuente normalizada: 26.
- Pares OD totales: 676.
- Pares con tarifa disponible: 600.
- Pares sin tarifa: 76.
- Diagonal: sin tarifa disponible, tratada como cero para el ingreso teórico sin subsidio.
- `Pasajero Lota`: sin tarifas disponibles hacia/desde otras estaciones.
- `Concepción Centro`: no forma parte de esta matriz fuente y debe reportarse como estación del modelo sin cobertura tarifaria estudiante sin subsidio, si aparece en el universo de 27 estaciones del modelo.

## Homologación aplicada

| Nombre en presupuesto | Nombre normalizado |
|---|---|
| Manquimavida | Manquimávida |
| Concepcion | Concepción |
| Los Condores | Los Cóndores |
| Arenal / El Arenal | El Arenal |
| Diagonal Bio Bio | Diagonal Biobío |
| Megacentro | El Parque |
| Conavicoop | C. Raúl Silva H. |
| Escuadron | Hito Galvarino |
| Los Molles | Huinca |
| Los Chiflones | Cristo Redentor |
| Yobilo | Laguna Quiñenco |

## Controles de validación

Valores esperados desde el presupuesto base:

| OD | Tarifa |
|---|---:|
| Hualqui → La Leonera | 320 |
| Hualqui → Concepción | 330 |
| Hualqui → UTFSM | 340 |
| Concepción → UTFSM | 300 |
| Hualqui → Los Canelos | 560 |
| Hito Galvarino → Hualqui | 370 |

## Uso metodológico

Esta matriz debe usarse únicamente para calcular:

`Ingreso_teorico_estudiante_sin_subsidio_sin_diagonal`

La fórmula oficial de subsidio estudiante Biotren es:

`Subsidio_estudiante = Ingreso_teorico_estudiante_sin_subsidio_sin_diagonal - Venta_media_superior_con_diagonal`

donde:

- `Ingreso_teorico_estudiante_sin_subsidio_sin_diagonal = Σ_{i≠j}(MOD_media_superior_ij × tarifa_estudiante_BT_sin_subsidio_ij)`
- `Venta_media_superior_con_diagonal = Σ_{todos i,j}(MOD_media_superior_ij × tarifa_estudiante_pagada_ij)`

No debe usarse como fórmula final la brecha OD `max(0, tarifa_sin_subsidio - tarifa_pagada)` por par OD.

## Observación de auditoría

La comparación contra la matriz versionada anteriormente indica que la matriz previa tenía valores superiores. En los 600 pares comparables con tarifa disponible:

- Diferencia promedio nueva - anterior: -247.13
- Diferencia mediana nueva - anterior: -220.00
- Diferencia mínima nueva - anterior: -540
- Diferencia máxima nueva - anterior: -70

Esta normalización debe reemplazar los archivos de tarifa estudiante BT sin subsidio existentes en `data/tarifas_biotren/`.
