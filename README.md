# Modelo de afluencia EFE/Fesur — proyeccion 2027

App Streamlit que proyecta la afluencia mensual 2027 por servicio. La **oferta de trenes
es la variable de planificacion**, editable **por tipo de dia** (Lunes-Viernes / Sabado /
Domingo) y mes. Base del comportamiento: estacionalidad (fechas) + reporte operacional
(RROO). **No usa variable climatica.**

Repo liviano, listo para GitHub y Streamlit Cloud: corre solo con los CSV procesados en
`data/` (no requiere los Excel crudos en runtime).

## Servicios (4 secciones)
1. **Biotren** — oferta **Linea 1 / Linea 2** por separado (cargas por viaje distintas).
2. **Laja-Talcahuano** (Corto Laja).
3. **Tren Araucania** (Victoria-Temuco).
4. **Llanquihue-Puerto Montt** (XP-NQ; XP=La Paloma, NQ=Llanquihue, AL=Alerce, EV=Puerto Varas).

## Estructura
```
modelo_afluencia_efe/
├── streamlit_app.py        # app (4 secciones, editores por tipo de dia, graficos Plotly)
├── pipeline_afluencia.py   # ETL afluencia + pronostico estacional (referencia)
├── oferta.py               # motor de oferta por unidad/mes/tipo-de-dia
├── regenerar_datos.py      # reconstruye los CSV desde la base cruda (opcional)
├── data/
│   ├── afluencia_diaria_consolidada.csv
│   └── oferta_params.csv               # servicios_dia, pax/viaje y supresion por unidad/mes/tipo-dia
├── .streamlit/config.toml
├── requirements.txt
├── .gitignore
└── README.md
```

## Correr en local
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Subir a GitHub
```bash
git init && git add . && git commit -m "Modelo afluencia EFE/Fesur 2027"
git branch -M main
git remote add origin https://github.com/<usuario>/<repo>.git
git push -u origin main
```

## Desplegar en Streamlit Cloud
1. https://share.streamlit.io -> conectar GitHub.
2. New app -> repo + rama `main`.
3. **Main file path:** `streamlit_app.py`
4. Deploy (instala dependencias desde requirements.txt). No requiere secrets.

## Regenerar datos (opcional)
Los Excel crudos no se versionan (no se necesitan para el despliegue). Para regenerarlos:
```bash
# colocar data/raw_bbdd/{BT,CL,LP,TA}/ y data/raw_rroo/Consolidado.xlsx
python regenerar_datos.py
```

## Modelo
Por unidad (BIOTREN_L1, BIOTREN_L2, CORTO_LAJA, TREN_ARAUCANIA, LLANQUIHUE_PM), mes y tipo de dia:
```
afluencia[mes] = SUMA_tipo_dia [ servicios_por_dia x n_dias_2027 x pax_por_viaje x (1 - supresion) ]
```
- `servicios_por_dia`: EDITABLE en la app (default = oferta historica operada del RROO).
- `n_dias_2027`: dias reales de cada tipo (L-V/Sab/Dom) por mes en 2027 (del calendario).
- `pax_por_viaje`: carga media por viaje operado, por mes y tipo de dia (de la afluencia historica).
- `supresion`: tasa historica del RROO + contingencia extra opcional.
- Biotren: afluencia repartida 20/80 (L1/L2, matriz OD); total = L1 + L2.
Se muestra ademas una **referencia estacional** (descomposicion por fechas) para contraste.

## Caveats (leer antes de presupuestar)
- **Corto Laja**: oferta plana (corr~0); el modo por oferta sobreestima. Usar la referencia estacional.
- **Llanquihue-PM**: 13 meses, confianza BAJA; algunos meses imputados (solape RROO delgado).
- **Biotren**: el reparto L1/L2 (20/80) es un supuesto de matriz OD, no medicion por linea.
  Nivel ETL ~5-13% bajo el Resumen oficial (definicion de "Pasajeros").

## Roadmap
- v3: modelo de confiabilidad operacional (supresiones/atrasos por causa) sobre el RROO.
