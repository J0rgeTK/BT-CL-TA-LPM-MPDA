# Cierre 2026 EFE Sur - datos normalizados para visualización

Fuente: `Cierre-2026-EFESur.xlsx`.

Uso previsto:
- Enriquecer visualizaciones históricas y diagramas de proyección.
- Distinguir histórico observado, cierre 2026 estimado y proyección 2027 del modelo.
- No recalibrar ni modificar resultados del escenario 2027.

Archivos:
- `afluencia_historica_cierre_2026_long.csv`: serie mensual normalizada.
- `afluencia_historica_cierre_2026_resumen_anual.csv`: resumen anual por servicio.

Columnas del archivo mensual:
- `servicio`
- `anio`
- `mes_num`
- `mes`
- `afluencia`
- `tipo_dato`: `historico_observado` o `cierre_2026_estimado`
- `fuente`

Servicios incluidos:
- Biotren
- Laja Talcahuano
- Tren Araucanía

Nota metodológica:
El dato 2026 se etiqueta como `cierre_2026_estimado`. No debe tratarse como observado definitivo salvo validación posterior.
