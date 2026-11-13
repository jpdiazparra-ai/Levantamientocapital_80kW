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

En **Estrategia de Capital y Costos → Caja pendiente de cubrir**, el selector **Turbina para comparar** permite revisar **10 kW**, **80 kW** o **Ambas turbinas**. Aplica a las tres pestañas (proyecto, hito y sistema), los totales, el detalle y los CSV. La vista conjunta distingue los sistemas e hitos de cada turbina y conserva los filtros superiores.

En **Detalle de capital por sistema**, selecciona una fila para abrir las líneas o paquetes y registros de caja de ese sistema. Cada paquete ocupa una fila con los montos agregados y conserva sus IDs de origen. La tabla muestra participación y cobertura de referencias; el desglose conserva IDs, presupuesto, responsables, validación y evidencia. Las referencias indican la fila original de Plan y Costos cuando está disponible. Los CSV de líneas/paquetes y caja mantienen sus alcances separados para evitar duplicar presupuestos al existir varios registros de caja por actividad.

La plataforma inicia en **USD**. El botón **Actualizar todo** recarga las fuentes, restablece **USD** y conserva la vista y los filtros activos. La selección de moneda también se aplica a los PDF descargables.

El panel lateral muestra la versión del código en ejecución. `dashboard_runtime.py` comprueba los archivos del Bloque 2 y recarga sus módulos cuando cambia el código, para que una sesión activa no conserve funciones anteriores después de actualizar el repositorio. Las recargas ordinarias de datos conservan los selectores.

`analysis_option.py` implementa el Bloque 2, `timeline_scroll.py` su cronograma y `capital_charts.py` las comparaciones de capital, el calendario mensual y los fondos por responsable. Los estilos se encuentran en `assets/`. La propuesta de análisis y los criterios de validación están en [ANALISIS_BLOQUE4.md](ANALISIS_BLOQUE4.md).

El entorno virtual, las credenciales y el historial PMO local no se publican. La aplicación permite comenzar sin un archivo de historial y lo crea al guardar el primer corte.

El Bloque 2 orienta la lectura en cinco vistas: **Estrategia de Capital y Costos**, **Ejecución Técnica y Ruta de Hitos**, **Gobernanza de Costos y Control PMO**, **Caso de Inversión · 10 kW**, y **Caso de Inversión · 80 kW**. El **subbloque 4** consulta exclusivamente el [modelo independiente de 10 kW](https://docs.google.com/spreadsheets/d/e/2PACX-1vR8FDvZc18fkzHLW2Pcy5Z9WMRE_JWfdN9RfXDgojcr87S5jGYYvtC-l5302cwZRw/pubhtml). Replica el análisis y diseño del subbloque 5 en violeta: Evaluación 10 kW, Datos y supuestos, Inversión y socios, Resultados y caja, Ventas y fabricación, Gastos operativos, Activos y desarrollo, Controles y fuentes, y Estudio de mercado. Incluye resumen quinquenal, proyección decenal, caja mensual, economía unitaria, simuladores DCF, volumen y LCOE, y PDF ejecutivo de siete páginas. El estudio de mercado conserva el documento VAWT compartido y su alcance original (10 y 80 kW).

`valuation10_data.py` consulta las once hojas y ejecuta 19 conciliaciones sin modificar la fuente. `valuation10_unit.py` y `valuation10_lcoe.py` usan 10 kW para los indicadores por potencia y la generación. Los módulos `valuation10_project.py`, `valuation10_costs.py` y `valuation10_report.py` vinculan exclusivamente los costos e hitos de 10 kW con el PDF. La paleta se aplica por sesión y se restablece al salir de la vista; 80 kW mantiene su paleta azul. Ambas vistas tienen claves de controles y cachés financieras independientes. La fuente 10 kW consultada el 13-11-2026 presenta diferencias de conciliación en inversión económica inicial y activos aportados; se muestran como pendientes de revisión. Los archivos `valuation_data.py` y `valuation_view.py` conservan los componentes compartidos y el analizador histórico del modelo conjunto.

El **subbloque 5** usa exclusivamente el [modelo independiente de 80 kW](https://docs.google.com/spreadsheets/d/e/2PACX-1vRtQHrMkPa0wA7KpcUf_foYsbIpmh4gC4UuppPkWWIpFGPPhs3lxtRmzwB8D21sXw/pubhtml) y organiza ocho pestañas según su contenido: Evaluación 80 kW, Datos y supuestos, Inversión y socios, Resultados y caja, Ventas y fabricación, Gastos operativos, Activos y desarrollo, y Controles y fuentes. La evaluación presenta las cuatro áreas de 00 en una vista ejecutiva continua con gráficos, cifras publicadas y proyección quinquenal, sin pestañas internas. Los análisis de LCOE, volumen y DCF conservan sus controles en las áreas de fabricación y supuestos. `valuation80_data.py` lee las once hojas (incluida 10 Controles), contrasta 19 conciliaciones y conserva referencias de celda; `valuation80_view.py` comparte los estilos y gráficos existentes, y `valuation80_report.py` exporta seis páginas e incorpora costos y calendario de desembolsos del subbloque 1. Consulta sus reglas en [VALORIZACION_80KW.md](VALORIZACION_80KW.md).

La comparación de capital y el detalle por sistema usan **Caja pendiente de cubrir = Caja validada + Caja por validar**, a partir de los saldos incluidos y no pagados/parciales de Costos. El gráfico total, sus porcentajes, las líneas/paquetes y los registros de caja concilian sobre esa misma base. El presupuesto de referencia publicado se conserva en los datos de origen y no se usa como sustituto de saldo pendiente.

El **Calendario de desembolsos** incluye el selector **Turbina del calendario** (10 kW, 80 kW o ambas). Los totales, la programación mensual, los hitos y las tablas de saldos usan esa misma selección.

Las tarjetas y sistemas usan **Saldo pendiente caja CLP**, distribuido por Validación caja y limitado a No pagado/Parcial con Incluir en caja activo. El calendario mensual y las páginas PDF de desembolsos conservan **Caja programada CLP / Caja por validar CLP** de la fuente, incluso cuando sus alertas impiden programar un saldo. El panel **Conciliación · no pagados, saldo pendiente y caja programada** explica presupuesto, pagos, inclusión y diferencias; permite descargar los registros fuera de programación.
