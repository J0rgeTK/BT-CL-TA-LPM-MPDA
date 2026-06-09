# Modelo de predicción de afluencia EFE Sur — versión base calibrada ajustada

Esta versión actualiza el modelo de proyección 2027 incorporando los resultados reales de afluencia de mayo 2026 y dejando como escenario principal una **base calibrada por oferta**, con ajuste específico para Biotren.

## Criterio del escenario recomendado

El resultado anterior de **solo oferta calibrada** se considera más coherente con la evolución esperada del servicio durante 2026 que el escenario conservador original. Por lo tanto, esta versión usa ese enfoque como base para los servicios regionales y aplica una corrección puntual a Biotren.

- **Laja-Talcahuano:** mantiene la proyección por oferta calibrada.
- **Tren Araucanía:** mantiene la proyección por oferta calibrada.
- **Llanquihue-Puerto Montt:** mantiene la proyección por oferta calibrada, con la corrección metodológica de días lunes-viernes.
- **Biotren:** se ajusta a la baja respecto de la oferta calibrada, reconociendo el 80% del diferencial entre referencia estacional y oferta calibrada. Esto deja la proyección anual en torno a 12,5-12,6 millones de pasajeros, permitiendo simular posteriormente aumentos leves de servicios sin partir desde una base excesivamente alta.

## Resultados principales 2027

| Servicio | Referencia estacional | Solo oferta calibrada | Escenario base calibrado ajustado |
|---|---:|---:|---:|
| Biotren | 11.089.501 | 12.907.596 | 12.543.975 |
| Laja-Talcahuano | 438.014 | 501.607 | 501.607 |
| Llanquihue-Puerto Montt | 433.606 | 436.992 | 436.992 |
| Tren Araucanía | 652.783 | 807.179 | 807.179 |

## Lectura técnica

El modelo mantiene la productividad calibrada con mayo 2026, pero evita que Biotren quede completamente anclado al escenario más alto de oferta calibrada. La corrección aplicada no elimina el efecto de la mayor oferta; solo reduce el diferencial positivo frente a la referencia estacional para dejar margen a futuras simulaciones de incremento de servicios.

## Archivos relevantes

- `data/afluencia_diaria_consolidada.csv`: base diaria consolidada actualizada con mayo 2026.
- `data/afluencia_mayo_2026_cargada.csv`: registros diarios incorporados desde los archivos de mayo.
- `data/resumen_mayo_2026.csv`: control de afluencia, días y productividad de mayo 2026.
- `data/calibracion_mayo_2026.csv`: factores de calibración de pasajeros por viaje.
- `data/afluencia_mensual_modelo.csv`: base mensual usada por la referencia estacional.
- `outputs/proyeccion_2027_resumen_base_ajustada.csv`: proyección final recomendada por servicio.
- `outputs/proyeccion_2027_unidades_base_ajustada.csv`: detalle por unidad, incluyendo Biotren L1 y L2.
- `outputs/comparativo_escenarios_2027.csv`: comparación entre referencia, oferta calibrada y escenario base ajustado.
- `outputs/validacion_mayo_2026_vs_proyeccion.csv`: control de coherencia contra mayo 2026.

Por compatibilidad con versiones previas, también se conservan los archivos `outputs/proyeccion_2027_resumen_conservador.csv` y `outputs/proyeccion_2027_unidades_conservador.csv`, con el mismo resultado del escenario base ajustado.

## Ejecución

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Para regenerar los datos y salidas desde los archivos de mayo dentro del entorno de trabajo:

```bash
python actualizar_mayo2026.py
```
