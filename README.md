# Modelo de afluencia EFE/Fesur — proyeccion 2027

App Streamlit que proyecta la afluencia mensual 2027 por servicio. La **oferta de trenes
es la variable de planificacion**, editable **por tipo de dia** (Lunes-Viernes / Sabado /
Domingo) y mes. Base: estacionalidad (fechas) + reporte operacional (RROO). Sin clima.

Repo liviano, listo para GitHub y Streamlit Cloud: corre con los CSV procesados en `data/`.

## Servicios (pestanias)
- **Resumen** + 4 secciones: **Biotren** (oferta L1 / L2 por separado), **Laja-Talcahuano**,
  **Tren Araucania**, **Llanquihue-Puerto Montt** (XP=La Paloma, NQ=Llanquihue, AL=Alerce, EV=Puerto Varas).

## Estructura
```
modelo_afluencia_efe/
├── streamlit_app.py        # app (pestanias por servicio, editores por tipo de dia, Plotly, ocupacion)
├── pipeline_afluencia.py   # ETL afluencia + pronostico estacional (referencia)
├── oferta.py               # motor de oferta por unidad/mes/tipo-de-dia
├── regenerar_datos.py      # reconstruye los CSV desde la base cruda (opcional)
├── data/
│   ├── afluencia_diaria_consolidada.csv
│   └── oferta_params.csv
├── .streamlit/config.toml
├── requirements.txt        # streamlit fijado a version validada
├── .gitignore
└── README.md
```

## Correr / desplegar
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```
GitHub: `git init && git add . && git commit -m "modelo afluencia 2027" && git push`.
Streamlit Cloud: New app -> repo + rama main -> **Main file: streamlit_app.py** -> Deploy.

## Modelo
Por unidad (BIOTREN_L1, BIOTREN_L2, CORTO_LAJA, TREN_ARAUCANIA, LLANQUIHUE_PM), mes y tipo de dia:
```
afluencia[mes] = SUMA_tipo_dia [ servicios_por_dia x n_dias_2027 x pax_por_viaje x (1 - supresion) ]
```
- `servicios_por_dia`: EDITABLE (default = oferta historica reciente).
- `pax_por_viaje`: carga media por viaje operado (= "ocupacion media", pax por servicio).
- `n_dias_2027`: dias reales de cada tipo por mes en 2027.
- `supresion`: tasa historica del RROO + contingencia extra opcional.

**Calibraciones aplicadas (v4):**
- **Biotren x1.07**: el ETL subcontaba 7% vs el Resumen oficial (factor estable 1.070 +- 0.006);
  se calibra al nivel oficial de "Pasajeros".
- **Anclaje reciente (12 meses)**: servicios_dia y pax_por_viaje se estiman con los ultimos
  12 meses, para reflejar el desempenio actual (2026) y no diluirlo con la historia mas debil.

## Ocupacion media
Cada seccion muestra los **pasajeros promedio por viaje** (carga media) por mes y por tipo de
dia. Es un proxy de ocupacion; la ocupacion real (pax/asientos) requiere la capacidad por tren,
no disponible en los datos.

## Caveats
- **Corto Laja**: oferta plana (corr~0); el modo por oferta sobreestima. Usar la referencia estacional.
- **Llanquihue-PM**: 13 meses, confianza BAJA; algunos meses imputados (solape RROO delgado).
- **Biotren**: el reparto L1/L2 (20/80) es un supuesto de matriz OD, no medicion por linea.

## Verificacion (mes a mes vs ultimo actual del mismo mes)
Biotren 1.04 · Tren Araucania 0.97 · Corto Laja 0.99 · Llanquihue-PM 1.18. El modelo
sigue de cerca el desempenio reciente; no subestima.

## Roadmap
- v5: modelo de confiabilidad operacional (supresiones/atrasos por causa) sobre el RROO.
