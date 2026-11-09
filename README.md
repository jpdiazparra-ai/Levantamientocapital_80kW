# Levantamiento de capital · 10 kW y 80 kW

Dashboard Streamlit para validación tecnológica, CAPEX y ejecución, valor financiero y análisis alternativo del proyecto eólico.

El **Bloque 2 · Ingeniería de Proyecto y Evaluación Financiera** usa el documento publicado de control del proyecto y contiene capital y desembolsos, hitos técnicos, control PMO y valorización financiera. La valorización consulta de forma independiente su documento publicado de pestañas 00–09. Separa importes de referencia, por validar y validados. El cronograma incluye filtros por hito, sistema, paquete y estado, orden cronológico, fin previsto actual, línea de hoy y desplazamiento continuo con encabezados fijos.

## Ejecutar local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py --server.address 127.0.0.1
```

## Desplegar aparte

Usa esta carpeta como servicio independiente en Render.

- `buildCommand`: `pip install -r requirements.txt`
- `startCommand`: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`

El botón **Actualizar todo** recarga las fuentes y conserva la vista y los filtros activos.

El panel lateral muestra la versión del código en ejecución. `dashboard_runtime.py` comprueba los archivos del Bloque 2 y recarga sus módulos cuando cambia el código, para que una sesión activa no conserve funciones anteriores después de actualizar el repositorio. Las recargas ordinarias de datos conservan los selectores.

`analysis_option.py` implementa el Bloque 2, `timeline_scroll.py` su cronograma y `capital_charts.py` las comparaciones de capital, el calendario mensual y los fondos por responsable. Los estilos se encuentran en `assets/`. La propuesta de análisis y los criterios de validación están en [ANALISIS_BLOQUE4.md](ANALISIS_BLOQUE4.md).

El entorno virtual, las credenciales y el historial PMO local no se publican. La aplicación permite comenzar sin un archivo de historial y lo crea al guardar el primer corte.

El Bloque 2 orienta la lectura en cinco vistas: **Estrategia de Capital y Costos**, **Ejecución Técnica y Ruta de Hitos**, **Gobernanza de Costos y Control PMO**, **Valor del Negocio · 10 y 80 kW**, y **Caso de Inversión · 80 kW**. El subbloque 4 reúne seis pestañas de análisis, con diagnóstico financiero, comparación unitaria 10/80 kW, proyección por período y laboratorios de mix y DCF interactivos en el resumen, lectura íntegra de las once hojas 00–09 y catorce conciliaciones propias; sus criterios están en [VALORIZACION_BLOQUE4.md](VALORIZACION_BLOQUE4.md).

El **subbloque 5** usa exclusivamente el [modelo independiente de 80 kW](https://docs.google.com/spreadsheets/d/e/2PACX-1vRtQHrMkPa0wA7KpcUf_foYsbIpmh4gC4UuppPkWWIpFGPPhs3lxtRmzwB8D21sXw/pubhtml) y organiza ocho pestañas según su contenido: Evaluación 80 kW, Datos y supuestos, Inversión y socios, Resultados y caja, Ventas y fabricación, Gastos operativos, Activos y desarrollo, y Controles y fuentes. La evaluación presenta las cuatro áreas de 00 en una vista ejecutiva continua con gráficos, cifras publicadas y proyección quinquenal, sin pestañas internas. Los análisis de LCOE, volumen y DCF conservan sus controles en las áreas de fabricación y supuestos. `valuation80_data.py` lee las once hojas (incluida 10 Controles), contrasta 19 conciliaciones y conserva referencias de celda; `valuation80_view.py` comparte los estilos y gráficos existentes, y `valuation80_report.py` exporta seis páginas e incorpora costos y calendario de desembolsos del subbloque 1. Consulta sus reglas en [VALORIZACION_80KW.md](VALORIZACION_80KW.md).
