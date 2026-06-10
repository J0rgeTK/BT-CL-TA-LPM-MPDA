# Modelo de predicción de afluencia EFE Sur 2027

## Versión
Modelo mensual-elástico con oferta editable por mes, servicio y tipo de día, incorporando calendario operacional 2027 con feriados nacionales y escenario de oferta 2027 actualizado para Biotren y Tren Araucanía.

## Cambio estructural principal
La versión anterior calculaba un total anual y luego lo distribuía mes a mes con un perfil mensual. Esa estructura hacía que una modificación de oferta en un mes alterara la distribución completa del año.

Esta versión cambia totalmente la lógica: cada mes se calcula de forma independiente en función de su oferta, su cantidad de días operacionales, productividad histórica, calibración reciente, supresión y elasticidad de demanda respecto de oferta. El total anual es sólo la suma de los meses.

## Fórmula general

Para cada unidad operacional `u`, mes `m` y tipo de día `d`:

```text
V0(u,m,d) = S0(u,m,d) * N_op(u,m,d) * (1 - tau(u,m,d))
D0(u,m,d) = V0(u,m,d) * q(u,m,d) * F_nivel(s) * F_est(s,m)
V1(u,m,d) = S1(u,m,d) * N_op(u,m,d) * (1 - tau(u,m,d) - c(u))
D1(u,m,d) = D0(u,m,d) * (V1(u,m,d) / V0(u,m,d)) ^ epsilon(s)
```

Donde:

- `S0`: oferta vigente base.
- `S1`: oferta editada por el usuario.
- `N_op`: número de días operacionales del tipo correspondiente en el mes, después de aplicar feriados nacionales y reglas por servicio.
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
D_BT,m = Σ_{u∈{L1,L2}} Σ_d [ S1,u,m,d · N_op,u,m,d · (1 - τ_u,m,d - c_u) · q_u,m,d · 1,004 · F_est,BT,m · (V1,u,m,d / V0,u,m,d)^0,55 ]

S0_L1,LV,m = 48 para todo 2027
S0_L2,LV,m = 106 para enero-abril; 109 desde mayo-diciembre
```

### Laja-Talcahuano

```text
D_LT,m = Σ_d [ S1,LT,m,d · N_op,LT,m,d · (1 - τ*_LT,m,d - c) · q_LT,m,d · 1,133 · F_est,LT,m · (V1,LT,m,d / V0,LT,m,d)^0,38 ]
τ*_LT,m,d = min(τ_LT,m,d, 0,01)
```

### Tren Araucanía

```text
D_TA,m = Σ_{r∈{VT,PT,CL}} D_r,m
D_r,m = D_base_TA,m × α_hist_r,m × (V_plan_r,m / V_base_r,m) ^ ε_r
V_r,m = Σ_d S_r,m,d × N_op,r,m,d × (1 - τ_TA,m,d - c)
S0_VT,LV,m = 15 para todo 2027; S0_PT,LV,m = 6,6; S0_CL,LV,m = 3 sólo marzo-diciembre
```

### Llanquihue-Puerto Montt

```text
D_LLPM,m = Σ_d [ S1,LLPM,m,d · N_op,LLPM,m,d · (1 - τ_LLPM,m,d - c) · q_LLPM,m,d · 1,000 · F_est,LLPM,m · (V1,LLPM,m,d / V0,LLPM,m,d)^0,35 ]
```

## Fundamento metodológico

El modelo usa una formulación de elasticidad parcial porque en transporte público el aumento de frecuencia/oferta puede aumentar demanda, pero el efecto marginal no suele ser proporcional. En términos prácticos, un aumento de 10% en servicios no debe traducirse automáticamente en 10% más pasajeros si la demanda latente, la ocupación previa, la localización del tramo, el horario o la estacionalidad no lo respaldan.

La metodología se apoya en tres criterios:

1. **Desagregación mensual:** cada mes tiene cálculo propio; no existe redistribución anual posterior.
2. **Elasticidad menor que 1:** los cambios de oferta tienen efecto parcial y decreciente.
3. **Calibración histórica y reciente:** se usan patrones 2024-2025 y enero-mayo 2026, con calibración específica de mayo 2026.
4. **Calendario operacional:** los feriados nacionales 2027 se descuentan de Biotren, Tren Araucanía y Llanquihue-Puerto Montt. Laja-Talcahuano mantiene operación en feriados con oferta de fin de semana.

## Parámetros principales

| Servicio | Elasticidad oferta | Factor nivel | Fuerza estacionalidad |
|---|---:|---:|---:|
| Biotren | 0,55 | 1,004 | 0,55 |
| Laja-Talcahuano | 0,38 | 1,133 | 0,55 |
| Tren Araucanía | 0,42 | 0,955 | 0,50 |
| Llanquihue-Puerto Montt | 0,35 | 1,000 | 0,85 |

## Tratamiento por servicio

### Biotren
Se modela separando Biotren L1 y Biotren L2. El escenario actualizado incorpora 48 servicios L-V para L1 durante todo 2027 y mejora L2 de 106 a 109 servicios L-V desde mayo en adelante. La distribución mensual no se obtiene repartiendo un total anual: cada mes se calcula desde su oferta, días operacionales, feriados, productividad mensual y elasticidad de oferta. El resultado anual actualizado queda en torno a 13,0 millones de pasajeros. El ajuste responde al comportamiento reciente 2026 y al aumento de oferta 2027, manteniendo elasticidad parcial para evitar una extrapolación proporcional.

Adicionalmente, sólo para Biotren se aplica una corrección puntual marzo-abril. La proyección previa dejaba abril artificialmente por sobre marzo; sin embargo, el dato 2026 disponible muestra marzo levemente mayor que abril. Por ello, el modelo redistribuye únicamente el bloque marzo-abril manteniendo constante su suma conjunta y el total anual, asignando 50,2% a marzo y 49,8% a abril. Esta regla no altera otros meses ni elimina la sensibilidad a cambios de oferta: si se modifica la oferta de marzo o abril, el cambio sigue afectando el mes intervenido.

### Laja-Talcahuano
La oferta base queda corregida y se incorpora recuperación parcial de confiabilidad y productividad:

- 8 servicios todos los días.
- Sólo sábados y domingos de enero y febrero consideran 10 servicios.
- En feriados nacionales opera con oferta de fin de semana; si el feriado cae lunes-viernes se imputa como domingo operacional para efectos de oferta.
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

El modelo ya no usa una relación fija 13/87 ni una oferta equivalente única como mecanismo principal. Además, descuenta feriados nacionales como días sin operación para sus tramos. La demanda se calcula por tramo usando la distribución mensual observada en `TA-Dist.xlsx`, disponible como `data/tren_araucania_distribucion_tramos.csv`. La serie contiene participación mensual por tipo de servicio entre mayo 2024 y mayo 2026. En el escenario actualizado, el tramo Temuco - Victoria aumenta de 9 a 15 servicios L-V, mientras Pitrufquén y Claret mantienen su parametrización base. El nivel anual se modera mediante un factor 0,955, dejando el resultado cercano a 950 mil pasajeros y evitando que el incremento de oferta Victoria-Temuco produzca una sobrerrespuesta agregada.

La fórmula aplicada es:

```text
D_TA,m = Σ_r D_r,m
D_r,m = D_base_TA,m × α_hist_r,m × (V_plan_r,m / V_base_r,m) ^ ε_r
V_r,m = Σ_d S_r,m,d × N_op,r,m,d × (1 - τ_TA,m,d - c)
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
Enero y febrero conservan una señal estival similar a 2026. El servicio se mantiene sin operación planificada de fines de semana ni feriados nacionales.

## Resultados base 2027

| Servicio | Proyección 2027 |
|---|---:|
| Biotren | 12.991.160 |
| Laja-Talcahuano | 540.842 |
| Tren Araucanía | 950.258 |
| Llanquihue-Puerto Montt | 420.853 |
| Total sistema modelado | 14.488.013 |

## Calendario operacional 2027

El modelo incorpora feriados nacionales 2027 como regla de operación, no sólo como nota metodológica. Para Biotren, Tren Araucanía y Llanquihue-Puerto Montt, los feriados nacionales tienen oferta efectiva cero. Para Laja-Talcahuano, los feriados nacionales se modelan con oferta de fin de semana.

Los feriados nacionales usados se encuentran en `data/feriados_chile_2027.csv` y el conteo mensual aplicado por unidad, mes y tipo de día está en `data/calendario_operacional_2027.csv` y `outputs/calendario_operacional_2027.csv`. Se excluyen feriados regionales o comunales para mantener un calendario común de modelación.



## Justificación metodológica por servicio en la aplicación

La aplicación incorpora en cada sección de servicio una pestaña desplegable denominada **Justificación metodológica del resultado proyectado**. Esta sección está vinculada a la salida activa del modelo, por lo que sus valores se actualizan cuando se modifica la oferta mensual o se incorpora contingencia adicional de supresión.

El propósito de esta pestaña es hacer auditable el resultado de cada servicio, mostrando:

- Proyección anual 2027 calculada por el modelo.
- Viajes operados proyectados y pasajeros por viaje resultantes.
- Mes de mayor y menor afluencia proyectada.
- Comparación contra años históricos completos cuando existen 12 meses observados.
- Comparación parcial contra 2026 usando los mismos meses observados disponibles, evitando comparar un año parcial como si fuera anual.
- Componentes mensuales del cálculo: viajes operados, demanda proyectada, variación de oferta, variación de demanda y elasticidad media.
- Lectura técnica personalizada por servicio, coherente con la oferta, la estacionalidad, los feriados 2027 y los ajustes específicos de cada caso.

Esta mejora evita que la justificación quede como texto fijo desconectado del cálculo. Si el usuario cambia, por ejemplo, la oferta de Biotren en un mes específico, la tabla de justificación y el detalle mensual reflejan el nuevo total anual y el impacto mensual correspondiente.

Las justificaciones se respaldan además en `outputs/justificacion_metodologica_servicios.csv`, que resume por servicio la proyección anual, viajes operados, pasajeros por viaje, comparaciones históricas válidas y criterio técnico utilizado.

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
- `data/feriados_chile_2027.csv` y `outputs/feriados_chile_2027.csv`: feriados nacionales usados por el modelo.
- `data/calendario_operacional_2027.csv` y `outputs/calendario_operacional_2027.csv`: conteo de días operacionales por unidad, mes y tipo de día.

## Bibliografía verificable

1. Transportation Research Board. *TCRP Report 95, Chapter 9: Transit Scheduling and Frequency*. Washington, D.C., 2004. https://trb.org/publications/tcrp/tcrp_rpt_95c9.pdf
2. Balcombe, R., Mackett, R., Paulley, N., Preston, J., Shires, J., Titheridge, H., Wardman, M. & White, P. *The Demand for Public Transport: A Practical Guide*. TRL Report TRL593, 2004. https://www.trl.co.uk/uploads/trl/documents/TRL593%20-%20The%20Demand%20for%20Public%20Transport.pdf
3. Paulley, N., Balcombe, R., Mackett, R., Titheridge, H., Preston, J., Wardman, M., Shires, J. & White, P. *The demand for public transport: The effects of fares, quality of service, income and car ownership*. Transport Policy, 13(4), 295-306, 2006. https://eprints.whiterose.ac.uk/id/eprint/2034/1/ITS23_The_demand_for_public_transport_UPLOADABLE.pdf
4. Berrebi, S., Joshi, S. & Watkins, K. *On Ridership and Frequency*. Transportation Research Part A, 2021. https://doi.org/10.48550/arXiv.2002.02493
5. Feriados de Chile. *Feriados de Chile — Año 2027*. Fuente basada en Biblioteca del Congreso Nacional. https://www.feriados.cl/2027.htm

# Complemento metodológico: distribución OD gravitacional Biotren

El modelo mensual de afluencia mantiene la responsabilidad de proyectar el total mensual de pasajeros. El módulo gravitacional incorporado agrega una segunda etapa espacial, cuyo objetivo es distribuir el total mensual de Biotren entre pares origen-destino.

La formulación doblemente restringida utilizada es:

`T_ij = A_i × O_i × B_j × D_j × f(C_ij)`

Donde `O_i` representa producciones por estación de origen, `D_j` atracciones por estación de destino, `C_ij` el costo generalizado y `A_i`, `B_j` factores de balance. El costo generalizado se construye con tarifa y distancia normalizadas:

`C_ij = α × Tarifa_norm_ij + β × Distancia_norm_ij`

Se evaluaron funciones exponencial y potencial de impedancia. El procedimiento Furness/IPF ajusta iterativamente la matriz estimada para respetar los márgenes de origen y destino. La calibración se basa en matrices OD observadas 2023-2025 y se valida con marzo, abril y mayo de 2026.

El módulo no debe interpretarse como un modelo causal completo, porque las matrices de entrada no contienen tiempos de viaje, frecuencia efectiva por estación, capacidad, atrasos, cancelaciones ni contingencias. Estas variables deben incorporarse desde el modelo predictivo principal o desde bases operacionales complementarias.

## Módulo OD híbrido Biotren por tipo de pasajero

El módulo OD de Biotren se incorpora como una capa posterior a la proyección mensual de afluencia. El modelo temporal mantiene la responsabilidad de estimar la demanda total mensual del servicio, mientras que el módulo OD distribuye esa demanda entre pares origen-destino y por tipo de pasajero.

### Criterio metodológico adoptado

La validación preliminar mostró que la matriz OD histórica proporcional presenta un mejor desempeño práctico que un modelo gravitacional puro. En consecuencia, el módulo implementado utiliza un enfoque híbrido:

- matriz histórica OD mensual por tipo de pasajero como estructura principal;
- modelo gravitacional como corrección parcial y control de sensibilidad espacial;
- balance IPF/Furness para conservar producciones y atracciones.

Esta decisión evita que tarifa y distancia, por sí solas, generen redistribuciones espaciales no observadas en Biotren. El modelo gravitacional se mantiene como componente metodológico de sensibilidad y no como sustituto de la estructura OD histórica.

### Segmentación por tipo de pasajero

La demanda mensual proyectada de Biotren se distribuye en tres segmentos:

- Normal: bloque `T. Monedero`.
- Estudiante: bloque `T. Estudiante`.
- Adulto Mayor: bloque `T. Tercera Edad`.

La participación mensual de cada tipo de pasajero se estima desde las matrices OD observadas, ponderando los años disponibles por mes. Cuando existe información 2026 para el mes, esta recibe mayor peso; para meses sin 2026 se ponderan principalmente 2025 y 2024.

\[
Demanda_{p,m}=Demanda_{Biotren,m}\times Participacion_{p,m}
\]

### Costo generalizado

El costo generalizado se construye con la matriz tarifaria Biotren 2026 por estación y la matriz de distancia `PAX KM BT`:

\[
C_{ij,p}=\alpha\cdot TarifaNormalizada_{ij,p}+\beta\cdot DistanciaNormalizada_{ij}
\]

Parámetros actuales:

- \(\alpha=0,75\): peso tarifario.
- \(\beta=0,25\): peso de distancia.
- \(\lambda=0,05\): impedancia exponencial.

### Combinación histórica-gravitacional

Para cada mes y tipo de pasajero, se construye una matriz histórica proporcional \(S_{ij,p,m}\) y una matriz gravitacional balanceada \(G_{ij,p,m}\). La matriz semilla final es:

\[
K_{ij,p,m}=w_p\cdot S_{ij,p,m}+(1-w_p)\cdot G_{ij,p,m}
\]

Pesos vigentes:

- Normal: 80% histórico y 20% gravitacional.
- Estudiante: 85% histórico y 15% gravitacional.
- Adulto Mayor: 85% histórico y 15% gravitacional.

### Balance final

La matriz OD final se obtiene mediante IPF/Furness:

\[
T_{ij,p,m}=IPF(K_{ij,p,m},O_{i,p,m},D_{j,p,m})
\]

Esto asegura que la matriz final respete:

- demanda total mensual proyectada por tipo de pasajero;
- producciones por origen;
- atracciones por destino;
- estructura espacial histórica;
- sensibilidad parcial a tarifa y distancia.

### Ingresos proyectados por OD

Los ingresos se estiman multiplicando la matriz OD proyectada por la matriz tarifaria 2026 correspondiente al tipo de pasajero:

\[
Ingreso_{ij,p,m}=T_{ij,p,m}\times Tarifa_{ij,p,2026}
\]

Esta estimación debe interpretarse como una primera aproximación de ingresos por OD y tipo de pasajero. En próximas iteraciones se recomienda preparar matrices OD mensuales-anuales por tipo de tarjeta para mejorar la precisión de ingresos y habilitar posteriormente la estimación de subsidio recibido.

### Orden de estaciones

Todas las matrices exportadas conservan el orden original de estaciones del archivo `0. Matrices Biotren may_2026.xlsx`. La homologación de nombres se utiliza sólo para cruzar matrices OD, tarifas y distancias, pero no para reordenar alfabéticamente la salida.

### Limitaciones

- No se incorporan aún tiempos de viaje, frecuencias por tramo, capacidad, congestión, regularidad operacional ni confiabilidad estación-tramo dentro del módulo OD.
- La estimación de ingresos se realiza con tarifas 2026 por estación y no con una desagregación completa por tipo de tarjeta.
- El modelo gravitacional representa distribución espacial condicionada por producciones, atracciones y costo generalizado; no debe interpretarse como un modelo causal completo de generación de demanda.


### Cobertura tarifaria y estaciones sin tarifa explícita

Cuando una estación o par OD aparece en la matriz OD original, pero no cuenta con tarifa positiva en la matriz tarifaria 2026 por estación, el programa conserva la estación en la matriz exportada para no alterar el orden ni la estructura original. Sin embargo, no asigna demanda proyectada a esos pares mientras no exista tarifa verificable. Esta regla evita estimar ingresos sobre tarifas inexistentes y deja trazable la necesidad de completar o validar la matriz tarifaria en futuras iteraciones.

