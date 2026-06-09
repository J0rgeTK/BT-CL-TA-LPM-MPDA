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

## Fórmulas específicas por servicio

Las siguientes expresiones son las que se presentan en la aplicación dentro de cada sección de servicio. Todas derivan de la fórmula general, pero incorporan las unidades operacionales, factores de nivel y elasticidades de cada caso.

### Biotren

```text
D_BT,m = Σ_{u∈{L1,L2}} Σ_d [ S1,u,m,d · N_m,d · (1 - τ_u,m,d - c_u) · q_u,m,d · 0,972 · F_est,BT,m · (V1,u,m,d / V0,u,m,d)^0,55 ]
```

### Laja-Talcahuano

```text
D_LT,m = Σ_d [ S1,LT,m,d · N_m,d · (1 - τ*_LT,m,d - c) · q_LT,m,d · 1,133 · F_est,LT,m · (V1,LT,m,d / V0,LT,m,d)^0,38 ]
τ*_LT,m,d = min(τ_LT,m,d, 0,01)
```

### Tren Araucanía

```text
S_eq,m,d = S_base,m,d · [Σ_{r∈{VT,PT,CL}} w_r · S_r,m,d] / [Σ_{r∈{VT,PT,CL}} w_r · S_base,r,m,d]
D_TA,m = Σ_d [ S_eq,1,m,d · N_m,d · (1 - τ_TA,m,d - c) · q_TA,m,d · 1,000 · F_est,TA,m · (V1,TA,m,d / V0,TA,m,d)^0,42 ]
```

### Llanquihue-Puerto Montt

```text
D_LLPM,m = Σ_d [ S1,LLPM,m,d · N_m,d · (1 - τ_LLPM,m,d - c) · q_LLPM,m,d · 1,000 · F_est,LLPM,m · (V1,LLPM,m,d / V0,LLPM,m,d)^0,35 ]
```

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
| Laja-Talcahuano | 0,38 | 1,133 | 0,55 |
| Tren Araucanía | 0,42 | 1,000 | 0,50 |
| Llanquihue-Puerto Montt | 0,35 | 1,000 | 0,85 |

## Tratamiento por servicio

### Biotren
Se modela separando Biotren L1 y Biotren L2. El escenario base queda en torno a 12,5 millones de pasajeros anuales, pero la distribución mensual no se obtiene repartiendo ese total. Cada mes se calcula desde su oferta y productividad mensual.

### Laja-Talcahuano
La oferta base queda corregida y se incorpora recuperación parcial de confiabilidad y productividad:

- 8 servicios todos los días.
- Sólo sábados y domingos de enero y febrero consideran 10 servicios.
- No se aplican 10 servicios a lunes-viernes.
- Para 2027 se asume menor afectación operacional que en 2025-2026, por lo que la tasa de supresión histórica se acota a 1% en el escenario base.
- Se aumenta el peso del patrón mensual 2024 para capturar un año con mejor comportamiento relativo, sin copiar directamente su nivel anual de afluencia.
- Se aplica un factor de recuperación de nivel de 1,133. Este factor representa una recuperación operacional y de confiabilidad parcial, llevando la proyección a aproximadamente 540 mil pasajeros anuales.
- La calibración de mayo 2026 se mantiene, pero con menor peso para no sobrerrepresentar un mes afectado por menor confiabilidad reciente.
- El resultado queda metodológicamente entre el desempeño 2025 y el máximo observado de 2024: supone recuperación respecto de 2025-2026, pero no una recuperación plena al nivel 2024.

### Tren Araucanía
La oferta se edita por tipo de servicio:

- Temuco - Victoria.
- Temuco - Pitrufquén.
- Claret.

El modelo ya no usa una relación fija 13/87 ni una oferta equivalente única como mecanismo principal. La demanda se calcula por tramo usando la distribución mensual observada en `TA-Dist.xlsx`, disponible como `data/tren_araucania_distribucion_tramos.csv`. La serie contiene participación mensual por tipo de servicio entre mayo 2024 y mayo 2026.

La fórmula aplicada es:

```text
D_TA,m = Σ_r D_r,m
D_r,m = D_base_TA,m × α_hist_r,m × (V_plan_r,m / V_base_r,m) ^ ε_r
V_r,m = Σ_d S_r,m,d × N_m,d × (1 - τ_TA,m,d - c)
```

Donde `α_hist_r,m` corresponde a la participación histórica mensual del tramo `r`, ponderada con los datos 2024-2026 del archivo TA-Dist. Para Claret, `α_hist = 0` en enero y febrero y la oferta se fuerza a cero en esos meses por corresponder a un servicio escolar.

Elasticidades específicas por tramo:

| Tramo | Elasticidad de oferta | Criterio operacional |
|---|---:|---|
| Temuco - Victoria | 0,46 | Tramo principal, mayor respuesta marginal esperada |
| Temuco - Pitrufquén | 0,28 | Menor peso relativo de demanda |
| Claret | 0,12 | Servicio escolar, activo sólo marzo-diciembre; respuesta acotada por calendario escolar |

Con esto, un aumento de servicios en Victoria-Temuco tiene mayor impacto esperado que un aumento equivalente en Pitrufquén o Claret, y cualquier cambio de oferta afecta únicamente el mes y tramo editado.

### Llanquihue-Puerto Montt
Enero y febrero conservan una señal estival similar a 2026. El servicio se mantiene sin operación planificada de fines de semana.

## Resultados base 2027

| Servicio | Proyección 2027 |
|---|---:|
| Biotren | 12.546.182 |
| Laja-Talcahuano | 540.166 |
| Tren Araucanía | 807.180 |
| Llanquihue-Puerto Montt | 436.992 |
| Total sistema modelado | 14.330.520 |

## Archivos relevantes

- `oferta.py`: motor mensual-elástico.
- `streamlit_app.py`: aplicación Streamlit con metodología, resumen y detalle por servicio.
- `outputs/proyeccion_2027_resumen_mensual_elastico.csv`: proyección mensual por servicio.
- `outputs/proyeccion_2027_unidades_mensual_elastico.csv`: detalle por unidad operacional.
- `outputs/detalle_calculo_mensual_elastico.csv`: detalle de cálculo por unidad, mes y tipo de día.
- `outputs/factores_estacionalidad_mensual.csv`: factores mensuales usados para productividad.
- `data/tren_araucania_distribucion_tramos.csv`: distribución mensual observada por tipo de servicio de Tren Araucanía.
- `outputs/tren_araucania_distribucion_historica_tramos.csv`: participaciones mensuales usadas por el modelo para Tren Araucanía.
- `outputs/validacion_sensibilidad_tren_araucania_tramos.csv`: comparación del impacto de modificar oferta en Victoria-Temuco, Pitrufquén-Temuco y Claret.
- `outputs/validacion_sensibilidad_cambio_oferta_marzo_l2.csv`: prueba de sensibilidad que demuestra que un cambio en marzo sólo modifica marzo.
- `outputs/validacion_laja_recuperacion.csv`: contraste del ajuste Laja-Talcahuano frente al histórico disponible.

## Bibliografía verificable

1. Transportation Research Board. *TCRP Report 95, Chapter 9: Transit Scheduling and Frequency*. Washington, D.C., 2004. https://trb.org/publications/tcrp/tcrp_rpt_95c9.pdf
2. Balcombe, R., Mackett, R., Paulley, N., Preston, J., Shires, J., Titheridge, H., Wardman, M. & White, P. *The Demand for Public Transport: A Practical Guide*. TRL Report TRL593, 2004. https://www.trl.co.uk/uploads/trl/documents/TRL593%20-%20The%20Demand%20for%20Public%20Transport.pdf
3. Paulley, N., Balcombe, R., Mackett, R., Titheridge, H., Preston, J., Wardman, M., Shires, J. & White, P. *The demand for public transport: The effects of fares, quality of service, income and car ownership*. Transport Policy, 13(4), 295-306, 2006. https://eprints.whiterose.ac.uk/id/eprint/2034/1/ITS23_The_demand_for_public_transport_UPLOADABLE.pdf
4. Berrebi, S., Joshi, S. & Watkins, K. *On Ridership and Frequency*. Transportation Research Part A, 2021. https://doi.org/10.48550/arXiv.2002.02493
