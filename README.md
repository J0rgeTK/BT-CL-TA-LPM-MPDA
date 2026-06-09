# Modelo de predicción de afluencia EFE Sur — versión calibrada mayo 2026

Esta versión actualiza el modelo de proyección 2027 incorporando los resultados reales de afluencia de mayo 2026 para Biotren, Laja-Talcahuano, Tren Araucanía y Llanquihue-Puerto Montt.

## Cambios metodológicos principales

1. **Biotren**
   - Se corrige la lectura del archivo diario para usar la columna oficial `Afluencias + Multas +SSE`.
   - El total mensual de mayo 2026 utilizado por el modelo es 1.039.422 pasajeros.
   - Se calibra la productividad por viaje considerando que la mayor oferta no implica crecimiento proporcional.

2. **Llanquihue-Puerto Montt**
   - Se corrige la mensualización de series incompletas: el servicio se normaliza contra días lunes-viernes, no contra fines de semana sin operación planificada.
   - Esto evita sobreestimar meses con cobertura parcial.

3. **Calibración de productividad**
   - Se crea `data/calibracion_mayo_2026.csv`.
   - La calibración ajusta parcialmente los pasajeros por viaje por servicio y tipo de día.
   - No reemplaza toda la historia por mayo; usa pesos y límites para mantener un resultado conservador.

4. **Respuesta conservadora a la oferta**
   - La proyección final combina referencia estacional y proyección por oferta calibrada.
   - Si la oferta genera un resultado superior a la referencia, solo se reconoce una fracción del diferencial.

## Resultados principales 2027

| Servicio | Referencia estacional | Solo oferta calibrada | Escenario conservador mayo 2026 |
|---|---:|---:|---:|
| Biotren | 11.089.501 | 12.907.596 | 11.528.639 |
| Laja-Talcahuano | 438.014 | 501.607 | 459.278 |
| Llanquihue-Puerto Montt | 433.606 | 436.992 | 420.526 |
| Tren Araucanía | 652.783 | 807.179 | 709.763 |

## Archivos relevantes

- `data/afluencia_diaria_consolidada.csv`: base diaria consolidada actualizada con mayo 2026.
- `data/afluencia_mayo_2026_cargada.csv`: registros diarios incorporados desde los archivos de mayo.
- `data/resumen_mayo_2026.csv`: control de afluencia, días y productividad de mayo 2026.
- `data/calibracion_mayo_2026.csv`: factores de calibración de pasajeros por viaje.
- `data/afluencia_mensual_modelo.csv`: base mensual usada por la referencia estacional.
- `outputs/proyeccion_2027_resumen_conservador.csv`: proyección final por servicio.
- `outputs/proyeccion_2027_unidades_conservador.csv`: detalle por unidad, incluyendo Biotren L1 y L2.
- `outputs/comparativo_escenarios_2027.csv`: comparación entre referencia, oferta calibrada y escenario conservador.
- `outputs/validacion_mayo_2026_vs_proyeccion.csv`: control de coherencia contra mayo 2026.

## Ejecución

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Para regenerar los datos y salidas desde los archivos de mayo dentro del entorno de trabajo:

```bash
python actualizar_mayo2026.py
```

