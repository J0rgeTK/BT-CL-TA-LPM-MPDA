# Modelo de predicción de afluencia EFE Sur 2027

## Versión
Modelo mensual-elástico con oferta editable por mes, servicio y tipo de día.

## Cambio estructural principal
La versión anterior calculaba un total anual y luego lo distribuía mes a mes con un perfil mensual. Esa estructura hacía que una modificación de oferta en un mes alterara la distribución completa del año.

Esta versión cambia totalmente la lógica: cada mes se calcula de forma independiente en función de su oferta, su cantidad de días, productividad histórica, calibración reciente, supresión y elasticidad de demanda respecto de oferta. El total anual es sólo la suma de los meses.

## Fórmula general

Para cada unidad operacional `u`, mes `m` y tipo de día `d`:

```text
V0(u,m,d) = S0(u,m,d) * N(m,d) * (1 - tau(u,m,d))
D0(u,m,d) = V0(u,m,d) * q(u,m,d) * F_nivel(s) * F_est(s,m)
V1(u,m,d) = S1(u,m,d) * N(m,d) * (1 - tau(u,m,d) - c(u))
D1(u,m,d) = D0(u,m,d) * (V1(u,m,d) / V0(u,m,d)) ^ epsilon(s)
```

Donde:

- `S0`: oferta vigente base.
- `S1`: oferta editada por el usuario.
- `N`: número de días del tipo correspondiente en el mes.
- `tau`: tasa de supresión histórica.
- `q`: pasajeros promedio por servicio, calibrado con mayo 2026.
- `F_nivel`: factor de calibración de nivel por servicio.
- `F_est`: factor de productividad mensual construido con histórico 2024, 2025 y 2026.
- `epsilon`: elasticidad de demanda respecto de oferta.
- `c`: contingencia adicional de supresión definida por el usuario.

## Fundamento metodológico

El modelo usa una formulación de elasticidad parcial porque en transporte público el aumento de frecuencia/oferta puede aumentar demanda, pero el efecto marginal no suele ser proporcional. En términos prácticos, un aumento de 10% en servicios no debe traducirse automáticamente en 10% más pasajeros si la demanda latente, la ocupación previa, la localización del tramo, el horario o la estacionalidad no lo respaldan.

La metodología se apoya en tres criterios:

1. **Desagregación mensual:** cada mes tiene cálculo propio; no existe redistribución anual posterior.
2. **Elasticidad menor que 1:** los cambios de oferta tienen efecto parcial y decreciente.
3. **Calibración histórica y reciente:** se usan patrones 2024-2025 y enero-mayo 2026, con calibración específica de mayo 2026.

## Parámetros principales

| Servicio | Elasticidad oferta | Factor nivel | Fuerza estacionalidad |
|---|---:|---:|---:|
| Biotren | 0,55 | 0,972 | 0,55 |
| Laja-Talcahuano | 0,38 | 1,000 | 0,45 |
| Tren Araucanía | 0,42 | 1,000 | 0,50 |
| Llanquihue-Puerto Montt | 0,35 | 1,000 | 0,85 |

## Tratamiento por servicio

### Biotren
Se modela separando Biotren L1 y Biotren L2. El escenario base queda en torno a 12,5 millones de pasajeros anuales, pero la distribución mensual no se obtiene repartiendo ese total. Cada mes se calcula desde su oferta y productividad mensual.

### Laja-Talcahuano
La oferta base queda corregida:

- 8 servicios todos los días.
- Sólo sábados y domingos de enero y febrero consideran 10 servicios.
- No se aplican 10 servicios a lunes-viernes.

### Tren Araucanía
La oferta se edita por tramo:

- Temuco - Victoria.
- Temuco - Pitrufquén.
- Claret.

Para demanda, no todos los servicios tienen igual efecto marginal. Se usa una oferta equivalente ponderada:

| Tramo | Peso relativo |
|---|---:|
| Temuco - Victoria | 1,00 |
| Temuco - Pitrufquén | 0,16 |
| Claret | 0,08 |

### Llanquihue-Puerto Montt
Enero y febrero conservan una señal estival similar a 2026. El servicio se mantiene sin operación planificada de fines de semana.

## Resultados base 2027

| Servicio | Proyección 2027 |
|---|---:|
| Biotren | 12.546.182 |
| Laja-Talcahuano | 468.631 |
| Tren Araucanía | 807.180 |
| Llanquihue-Puerto Montt | 436.992 |
| Total sistema modelado | 14.259.985 |

## Archivos relevantes

- `oferta.py`: motor mensual-elástico.
- `streamlit_app.py`: aplicación Streamlit con metodología, resumen y detalle por servicio.
- `outputs/proyeccion_2027_resumen_mensual_elastico.csv`: proyección mensual por servicio.
- `outputs/proyeccion_2027_unidades_mensual_elastico.csv`: detalle por unidad operacional.
- `outputs/detalle_calculo_mensual_elastico.csv`: detalle de cálculo por unidad, mes y tipo de día.
- `outputs/factores_estacionalidad_mensual.csv`: factores mensuales usados para productividad.
- `outputs/validacion_sensibilidad_cambio_oferta_marzo_l2.csv`: prueba de sensibilidad que demuestra que un cambio en marzo sólo modifica marzo.

## Bibliografía verificable

1. Transportation Research Board. *TCRP Report 95, Chapter 9: Transit Scheduling and Frequency*. Washington, D.C., 2004. https://trb.org/publications/tcrp/tcrp_rpt_95c9.pdf
2. Balcombe, R., Mackett, R., Paulley, N., Preston, J., Shires, J., Titheridge, H., Wardman, M. & White, P. *The Demand for Public Transport: A Practical Guide*. TRL Report TRL593, 2004. https://www.trl.co.uk/uploads/trl/documents/TRL593%20-%20The%20Demand%20for%20Public%20Transport.pdf
3. Paulley, N., Balcombe, R., Mackett, R., Titheridge, H., Preston, J., Wardman, M., Shires, J. & White, P. *The demand for public transport: The effects of fares, quality of service, income and car ownership*. Transport Policy, 13(4), 295-306, 2006. https://eprints.whiterose.ac.uk/id/eprint/2034/1/ITS23_The_demand_for_public_transport_UPLOADABLE.pdf
4. Berrebi, S., Joshi, S. & Watkins, K. *On Ridership and Frequency*. Transportation Research Part A, 2021. https://doi.org/10.48550/arXiv.2002.02493
