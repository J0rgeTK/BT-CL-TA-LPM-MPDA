# Metodología del modelo predictivo de afluencia EFE Sur 2027

## 1. Propósito del modelo

El modelo estima la afluencia mensual proyectada de pasajeros para los servicios de EFE Sur durante 2027. Su objetivo es apoyar planificación operacional y evaluación de escenarios de oferta por servicio, unidad operacional, mes y tipo de día.

Para Biotren, el modelo incorpora además una capa espacial origen-destino (OD) que distribuye la demanda mensual proyectada por par de estaciones y tipo de pasajero. Esta capa permite obtener matrices de viajes e ingresos preliminares, sin modificar la proyección temporal de demanda.

## 2. Separación metodológica

La metodología se organiza en tres componentes complementarios:

1. **Modelo temporal de afluencia mensual:** estima la demanda mensual total por servicio.
2. **Módulo espacial OD de Biotren:** asigna la demanda mensual de Biotren a pares origen-destino y tipos de pasajero.
3. **Módulo preliminar de ingresos OD:** calcula ingresos referenciales multiplicando viajes OD por tarifas disponibles.

El módulo OD no reemplaza el modelo temporal. La demanda total mensual se calcula primero y luego se distribuye espacialmente.

## 3. Modelo temporal de afluencia mensual

El cálculo se realiza por unidad operacional `u`, mes `m` y tipo de día `d`, distinguiendo lunes-viernes, sábado y domingo. Cada mes se calcula de manera independiente. El total anual corresponde a la suma de los doce meses, por lo que una modificación de oferta afecta el mes editado y el total anual por agregación.

### 3.1 Ecuaciones generales

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

## 4. Calendario operacional y feriados

El calendario 2027 se transforma en días operacionales efectivos por servicio, mes y tipo de día. Las reglas implementadas son:

- **Biotren, Tren Araucanía y Llanquihue-Puerto Montt:** feriados nacionales con oferta efectiva cero.
- **Laja-Talcahuano:** feriados nacionales con oferta de fin de semana. Si el feriado cae lunes-viernes, se imputa como día operacional tipo domingo.

Los feriados nacionales utilizados se encuentran en `data/feriados_chile_2027.csv`. El conteo operacional resultante se exporta en `data/calendario_operacional_2027.csv` y `outputs/calendario_operacional_2027.csv`.

## 5. Tratamiento por servicio

### 5.1 Biotren

Biotren se modela separando L1 y L2. La oferta se edita por línea, mes y tipo de día. El escenario base considera L1 con 48 servicios lunes-viernes durante 2027 y L2 con 106 servicios lunes-viernes entre enero y abril, aumentando a 109 servicios lunes-viernes desde mayo.

La proyección mensual utiliza días operacionales efectivos, feriados sin operación, productividad histórica, estacionalidad mensual y elasticidad parcial de oferta. Laja-Talcahuano se mantiene como servicio independiente para evitar doble conteo dentro del corredor L1.

El bloque marzo-abril incorpora un tratamiento estacional para mantener una trayectoria mensual consistente con la evidencia histórica disponible, sin transformar el modelo en una distribución anual fija.

### 5.2 Laja-Talcahuano

Laja-Talcahuano se proyecta como servicio propio. La oferta base considera 8 servicios diarios durante el año, con excepción de sábados y domingos de enero y febrero, donde se consideran 10 servicios. Los feriados nacionales se modelan con oferta de fin de semana.

El escenario representa una recuperación operacional parcial mediante supresión acotada, elasticidad parcial de oferta y mayor peso del patrón histórico de mejor desempeño.

### 5.3 Tren Araucanía

Tren Araucanía se modela por tipo de servicio:

- Temuco - Victoria.
- Temuco - Pitrufquén.
- Claret.

Cada tramo responde a su propia oferta y elasticidad. Temuco-Victoria tiene mayor respuesta marginal esperada que Pitrufquén y Claret. Claret se restringe a marzo-diciembre por su carácter escolar, por lo que enero y febrero no generan oferta ni demanda para este componente.

### 5.4 Llanquihue-Puerto Montt

Llanquihue-Puerto Montt se modela con operación de lunes a viernes. En el escenario base no se consideran servicios planificados de fin de semana ni operación en feriados nacionales. Enero y febrero conservan una señal estival dentro del perfil mensual.

## 6. Módulo OD híbrido de Biotren

El módulo OD distribuye la demanda mensual proyectada de Biotren entre pares origen-destino y tipos de pasajero. La estructura implementada es:

```text
Proyección mensual Biotren
→ segmentación por tipo de pasajero
→ patrón OD histórico mensual
→ componente gravitacional parcial
→ balance IPF/Furness
→ matriz OD proyectada
```

### 6.1 Tipos de pasajero

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

### 6.2 Distribución OD híbrida

Para cada mes y tipo de pasajero se construye una matriz base histórica `S_ij,p,m` y una matriz gravitacional `G_ij,p,m`. La matriz semilla combina ambos componentes:

```text
K_ij,p,m = w_p × S_ij,p,m + (1 - w_p) × G_ij,p,m
```

Donde:

- `S_ij,p,m` es la estructura OD histórica mensual por tipo de pasajero.
- `G_ij,p,m` es la estructura gravitacional estimada con tarifa y distancia.
- `w_p` es el peso asignado a la matriz histórica.

La matriz histórica tiene mayor peso porque representa la estructura espacial observada. El componente gravitacional se utiliza como ajuste parcial de sensibilidad, no como distribuidor final autónomo.

### 6.3 Costo generalizado e impedancia

El costo generalizado se calcula con tarifa y distancia normalizadas:

```text
C_ij,p = alpha × Tarifa_normalizada_ij,p + beta × Distancia_normalizada_ij
```

Luego se aplica función de impedancia exponencial:

```text
f(C_ij,p) = exp(-lambda × C_ij,p)
```

### 6.4 Balance IPF/Furness

La matriz final se balancea para conservar producciones por origen, atracciones por destino y total mensual por tipo:

```text
T_ij,p,m = IPF(K_ij,p,m, O_i,p,m, D_j,p,m)
```

Este procedimiento mantiene consistencia entre la demanda mensual proyectada y la estructura espacial utilizada.

### 6.5 Orden de estaciones

Las matrices OD visualizadas y exportadas conservan el orden original de estaciones de los insumos procesados. La homologación de nombres se utiliza para integrar OD, tarifas y distancias, sin ordenar estaciones alfabéticamente.

## 7. Ingresos OD preliminares

Los ingresos OD se calculan multiplicando la matriz de viajes por la matriz tarifaria disponible:

```text
Ingreso_ij,p,m = T_ij,p,m × Tarifa_ij,p,2026
```

Los ingresos deben interpretarse como una estimación preliminar. No incorporan subsidios, ajustes contables, evasión, reglas comerciales adicionales ni variación tarifaria dinámica por periodo.

## 8. Validaciones implementadas

El modelo genera controles para revisar:

- consistencia entre totales mensuales proyectados y matrices OD por tipo;
- suma de Normal, Estudiante y Adulto Mayor respecto del total Biotren distribuido;
- cobertura de tarifas y distancias;
- conservación del orden original de estaciones;
- igualdad de dimensión y orden entre matrices de viajes e ingresos;
- sensibilidad de demanda ante cambios de oferta mensual;
- aplicación de feriados por servicio;
- ejecución del módulo OD con arreglos NumPy/Pandas no escribibles;
- disponibilidad de insumos OD procesados en CSV;
- generación de salidas CSV y Excel.

## 9. Limitaciones

- El modelo es una herramienta de proyección operacional y espacial; no corresponde a un modelo causal completo de demanda.
- Las elasticidades son agregadas por servicio o tramo y no capturan heterogeneidad individual.
- Tarifa y distancia no representan todos los determinantes de movilidad.
- Los ingresos OD son preliminares y dependen de la cobertura tarifaria disponible.
- No se incorporan subsidios, capacidad máxima, ocupación, tiempos de viaje, regularidad diaria ni confiabilidad operacional detallada.
- Los resultados están condicionados por la calidad, cobertura y consistencia de los datos históricos disponibles.

## 10. Próximos pasos recomendados

- Incorporar matrices OD mensuales más completas por tipo de tarjeta y periodo.
- Integrar tiempos de viaje, capacidad, ocupación y regularidad operacional.
- Mejorar el módulo de ingresos con reglas tarifarias, descuentos, subsidios y validación contable.
- Incorporar variables operacionales complementarias, como atrasos, cancelaciones y niveles de servicio.
- Contrastar las proyecciones con observaciones futuras y actualizar parámetros cuando exista nueva evidencia.

## 11. Insumos OD Biotren sin binarios versionados

El módulo OD híbrido de Biotren se ejecuta por defecto desde CSV procesados versionados en `data/od_biotren/processed/`. Esto permite usar la app y las validaciones sin mantener archivos Excel binarios dentro del repositorio.

### 11.1 Archivos obligatorios versionados

Para ejecutar `od_biotren_hibrido.py`, `streamlit_app.py` y `validar_modelo.py` deben existir los siguientes CSV procesados:

- `data/od_biotren/processed/orden_estaciones_original.csv`.
- `data/od_biotren/processed/od_historica_por_tipo_long.csv`.
- `data/od_biotren/processed/tarifas_2026_por_tipo_long.csv`.
- `data/od_biotren/processed/distancia_biotren_km_long.csv`.
- `data/od_biotren/processed/validacion_extraccion_od.csv`.

Estos archivos contienen el orden original de estaciones, las matrices OD históricas por tipo de pasajero en formato largo, las tarifas 2026 por tipo, la distancia Biotren y la validación de extracción/homologación.

### 11.2 Archivos externos opcionales

Los Excel originales son insumos externos y están ignorados por Git. Sólo se necesitan para regenerar los CSV procesados:

- `data/od_biotren/input/0. Matrices Biotren may_2026.xlsx`.
- `data/od_biotren/input/Consolidado Tarifas EFE Sur 2026.xlsx`.
- `data/od_biotren/input/Libro1.xlsx`.

La regla general es: los Excel originales no se versionan; los CSV procesados sí se versionan cuando son necesarios para reproducir la ejecución del módulo OD.

### 11.3 Regeneración de insumos OD

Si se actualizan los Excel originales o faltan los CSV procesados, ejecutar:

```bash
python preparar_insumos_od_biotren.py
```

El script lee los Excel disponibles en `data/od_biotren/input/`, homologa estaciones con la misma lógica del módulo OD y vuelve a generar los CSV en `data/od_biotren/processed/`.

Si los CSV procesados faltan, `od_biotren_hibrido.py` muestra un error indicando que se debe ejecutar `python preparar_insumos_od_biotren.py` con los Excel originales disponibles.

## 12. Bibliografía de referencia

1. Transportation Research Board. *TCRP Report 95, Chapter 9: Transit Scheduling and Frequency*. Washington, D.C., 2004.
2. Balcombe, R. et al. *The Demand for Public Transport: A Practical Guide*. TRL Report TRL593, 2004.
3. Paulley, N. et al. *The demand for public transport: The effects of fares, quality of service, income and car ownership*. Transport Policy, 13(4), 295-306, 2006.
4. Berrebi, S., Joshi, S. & Watkins, K. *On Ridership and Frequency*. Transportation Research Part A, 2021.
5. Wilson, A. G. *Entropy in Urban and Regional Modelling*. Pion, 1970.
6. Ortúzar, J. de D. & Willumsen, L. G. *Modelling Transport*. 4th edition. Wiley, 2011.
7. Feriados de Chile. *Feriados de Chile — Año 2027*. Fuente basada en Biblioteca del Congreso Nacional.
