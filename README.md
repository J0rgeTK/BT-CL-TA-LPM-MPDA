# Modelo de afluencia EFE/Fesur — proyeccion 2027

App Streamlit que proyecta la afluencia mensual 2027 por servicio, con la **oferta de
trenes como variable de planificacion editable**. Base del comportamiento: estacionalidad
(fechas) + reporte operacional (RROO). **No usa variable climatica.**

Repo liviano, listo para GitHub y Streamlit Cloud: la app corre solo con los CSV
procesados en `data/` (no requiere los Excel crudos en runtime).

## Servicios (4 secciones)
1. **Biotren** — oferta separada **Linea 1 / Linea 2** (cargas por viaje L1~236, L2~345).
2. **Laja-Talcahuano** (Corto Laja).
3. **Tren Araucania** (Victoria-Temuco).
4. **Llanquihue-Puerto Montt** (linea XP-NQ; estaciones XP=La Paloma, NQ=Llanquihue,
   AL=Alerce, EV=Puerto Varas).

## Estructura
```
modelo_afluencia_efe/
├── streamlit_app.py            # punto de entrada de la app
├── pipeline_afluencia.py       # ETL afluencia + pronostico estacional (referencia)
├── oferta.py                   # motor de oferta (unidades, supresion, pax/viaje)
├── regenerar_datos.py          # reconstruye los CSV desde la base cruda (opcional)
├── data/
│   ├── afluencia_diaria_consolidada.csv   # afluencia diaria por servicio
│   └── oferta_params.csv                  # parametros de oferta por unidad y mes
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
git init
git add .
git commit -m "Modelo afluencia EFE/Fesur 2027"
git branch -M main
git remote add origin https://github.com/<usuario>/modelo_afluencia_efe.git
git push -u origin main
```

## Desplegar en Streamlit Cloud
1. Entrar a https://share.streamlit.io y conectar la cuenta de GitHub.
2. "New app" -> elegir el repo y la rama `main`.
3. **Main file path:** `streamlit_app.py`
4. Deploy. Las dependencias se instalan desde `requirements.txt`.

No se requieren secrets ni variables de entorno.

## Regenerar los datos (opcional)
Los Excel crudos NO se versionan (ver `.gitignore`) porque no son necesarios para el
despliegue. Si cambian los datos fuente:
```bash
# colocar la base cruda en data/raw_bbdd/{BT,CL,LP,TA}/ y data/raw_rroo/Consolidado.xlsx
python regenerar_datos.py
```
Esto regenera `data/afluencia_diaria_consolidada.csv` y `data/oferta_params.csv`.

## Modelo
Por unidad (BIOTREN_L1, BIOTREN_L2, CORTO_LAJA, TREN_ARAUCANIA, LLANQUIHUE_PM) y mes:
```
afluencia = servicios_planificados x pax_por_viaje(mes) x (1 - supresion)
```
- `servicios_planificados`: editable en la app (default = oferta historica operada).
- `pax_por_viaje`: carga media por viaje operado, por mes.
- `supresion`: tasa historica del RROO + contingencia extra opcional.
- Biotren: afluencia repartida 20/80 (L1/L2, matriz OD); total = L1 + L2.
Se muestra ademas una **referencia estacional** (descomposicion por fechas) para contraste.

## Caveats (leer antes de presupuestar)
- **Corto Laja**: oferta plana (corr~0); el modo por oferta sobreestima (ignora tendencia).
  Usar la referencia estacional como base.
- **Llanquihue-PM**: 13 meses, confianza BAJA; meses abr-may imputados (solape RROO delgado).
- **Biotren**: el reparto L1/L2 (20/80) es un supuesto de matriz OD, no medicion por linea.
- **Biotren** nivel ETL ~5-13% bajo el Resumen oficial (definicion de "Pasajeros").

## Roadmap
- v3: modelo de confiabilidad operacional (supresiones/atrasos por causa) sobre el RROO.
