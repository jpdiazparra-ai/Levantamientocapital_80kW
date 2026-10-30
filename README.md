# Levantamiento de capital · 10 kW y 80 kW

Dashboard Streamlit para validación tecnológica, CAPEX y ejecución, valor financiero y análisis alternativo del proyecto eólico.

El **Bloque 4 · Opción de análisis** usa el documento publicado de control del proyecto y contiene capital y desembolsos, hitos técnicos y control PMO. Separa importes de referencia, por validar y validados. El cronograma incluye filtros por hito, sistema, paquete y estado, orden cronológico, fin previsto actual, línea de hoy y desplazamiento continuo con encabezados fijos.

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

El panel lateral muestra la versión del código en ejecución. `dashboard_runtime.py` comprueba los archivos del Bloque 4 y recarga sus módulos cuando cambia el código, para que una sesión activa no conserve funciones anteriores después de actualizar el repositorio. Las recargas ordinarias de datos conservan los selectores.

`analysis_option.py` implementa el Bloque 4, `timeline_scroll.py` su cronograma y `capital_charts.py` las comparaciones de capital, el calendario mensual y los fondos por responsable. Los estilos se encuentran en `assets/`. La propuesta de análisis y los criterios de validación están en [ANALISIS_BLOQUE4.md](ANALISIS_BLOQUE4.md).

El entorno virtual, las credenciales y el historial PMO local no se publican. La aplicación permite comenzar sin un archivo de historial y lo crea al guardar el primer corte.
