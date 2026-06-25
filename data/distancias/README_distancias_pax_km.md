# Matrices de distancia y cálculo pax-km

Fuente: `Libro1 2.xlsx`, primera matriz de cada hoja:

- `PAX KM BT`: Biotren.
- `PAX KM CL`: Laja-Talcahuano.
- `PAX KM VT`: Tren Araucanía.
- `PAX KM LL-LP`: Llanquihue-Puerto Montt.

Archivos normalizados:

- `distancias_od_servicio_long.csv`: matriz long consolidada por servicio.
- `distancias_biotren_long.csv`.
- `distancias_corto_laja_long.csv`.
- `distancias_tren_araucania_long.csv`.
- `distancias_llanquihue_pm_long.csv`.
- `validacion_distancias_od.csv`.

Criterios metodológicos:

- Los nombres de estaciones se homologan a los nombres usados por el modelo.
- Para Laja-Talcahuano se fuerza `Los Acacios ↔ Manquimávida = 33 km`.
- En Tren Araucanía, `Coleg. Claret` se mantiene como estación de matriz porque el servicio Claret opera sólo entre Claret y Temuco; la matriz conserva las distancias disponibles y los OD no operacionales permanecen sin uso al cruzarse con las matrices de demanda/tarifa.
- El pax-km se calcula como `viajes_proyectados_OD × distancia_km_OD`.
- Llanquihue-Puerto Montt cuenta con matriz de distancias normalizada, pero el pax-km queda pendiente hasta incorporar MOD/distribución OD del servicio.
