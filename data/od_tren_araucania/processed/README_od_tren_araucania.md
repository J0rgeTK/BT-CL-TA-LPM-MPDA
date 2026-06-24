# OD Tren Araucanía normalizado

Insumos:
- MOD base: enero-mayo 2026 y junio-diciembre 2024.
- Tarifas venta: `Alza Tarifaria 2026.xlsx`, hoja `TA Tarifas`.
- Tarifa estudiante sin subsidio: `Tarifa Sin Subsidio.xlsx`.

Criterios de ingreso:
- Normal: 100% tarifa normal.
- Delegación: 70% tarifa normal.
- Adulto Mayor: tarifa adulto mayor.
- Estudiante y Claret: tarifa estudiante.
- Discapacitado, Estudiante Básica, Funcionario y Sindicato: tarifa cero.

Criterios de subsidio:
- Normal: tasa de descuento 12,7% sobre venta normal.
- Estudiante/Claret: diferencia entre tarifa estudiante sin subsidio y tarifa estudiante pagada.
- Adulto Mayor, Delegación y tipos sin pago: sin subsidio modelado.

Controles:
- Registros MOD long positivos: 5,658
- Viajes observados base: 715,653
- Registros tarifa: 784
- OD/tipo con tarifa de venta faltante: 0
- OD/tipo estudiante sin tarifa sin subsidio faltante: 0
