# Modelo de prediccion de afluencia EFE Sur 2027

Version ajustada con calibracion de mayo 2026, oferta vigente y distribucion mensual basada en comportamiento historico 2024-2026.

## Criterio general

El escenario principal del programa usa la oferta vigente como base operacional, calibra la productividad por viaje con mayo 2026 y distribuye el resultado anual mediante perfiles mensuales observados por servicio. El objetivo es evitar una proyeccion proporcional simple donde cada aumento de servicios genera el mismo crecimiento de pasajeros.

## Ajustes principales

- **Interfaz sin contraste externo:** la app muestra la proyeccion final, la oferta editable, el historico mensual y los indicadores de productividad. No se muestra una columna de contraste contra otra base de calculo.
- **Biotren:** se mantiene un resultado anual en torno a 12,5-12,6 millones de pasajeros, pero la distribucion mensual se reajusta con el comportamiento 2024, 2025 y enero-mayo 2026. Esto evita una curva mensual poco consistente con la historia reciente.
- **Laja-Talcahuano:** la oferta se corrige a 8 servicios por dia durante el ano, salvo sabados y domingos de enero-febrero, donde se consideran 10 servicios.
- **Tren Araucania:** la oferta se puede editar por tramo: Temuco-Victoria, Temuco-Pitrufquen y Claret. Para demanda se usa una oferta equivalente ponderada, reconociendo que un servicio adicional en Pitrufquen o Claret no genera el mismo efecto que uno en Victoria-Temuco.
- **Llanquihue-Puerto Montt:** enero y febrero mantienen niveles similares al comportamiento estival observado en 2026. El resto de meses se distribuye segun la serie disponible, considerando que no existen servicios planificados de fin de semana.

## Resultado anual 2027 del escenario base ajustado

| Servicio | Pasajeros proyectados 2027 |
|---|---:|
| Biotren | 12.546.183 |
| Laja-Talcahuano | 468.631 |
| Tren Araucania | 807.179 |
| Llanquihue-Puerto Montt | 436.992 |
| **Total sistema modelado** | **14.258.985** |

## Archivos de salida principales

- `outputs/proyeccion_2027_resumen_base_ajustada.csv`: proyeccion mensual por servicio.
- `outputs/proyeccion_2027_unidades_base_ajustada.csv`: detalle mensual por unidad de calculo.
- `outputs/proyeccion_2027_tren_araucania_tramos.csv`: desagregacion mensual de Tren Araucania por tramo.
- `outputs/perfil_mensual_utilizado_2027.csv`: participacion mensual usada para distribuir el total anual.
- `outputs/analisis_mensual_historico_servicio.csv`: comportamiento mensual por servicio y ano.
- `outputs/validacion_mayo_2026_vs_proyeccion.csv`: validacion de mayo 2026 y resultado anual del escenario.

## Uso

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Para regenerar datos y salidas:

```bash
python actualizar_mayo2026.py
```
