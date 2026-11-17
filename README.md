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

En **Lo que deja cada turbina entregada** (10 y 80 kW), el selector de alcance filtra el costo informado y su desglose: **Turbina + instalación** incluye todas las partidas Aplica; **Solo equipo turbina** excluye fundaciones y anclajes, montaje y logística. Estos nombres también aparecen en Costo comercial de las turbinas, la comparación y sus informes de alcance. El OPEX de la hoja 07 y la proyección financiera conservan sus bases de origen; el precio de venta y el LCOE del panel siguen el alcance seleccionado.

En **Lo que deja cada turbina entregada**, las cuatro filas muestran **Costo equipamiento turbina**, **OPEX por turbina**, **Precio de venta · sin IVA** y **Precio de venta · con IVA**. El OPEX procede de Opex total de la hoja 07 (E82 en la estructura actual). Precio sin IVA = equipamiento del alcance seleccionado + OPEX por turbina; precio con IVA = ese total × (1 + IVA referencial de 03). La tabla y la curva de LCOE del panel comparten ese precio sin IVA, con conversión de moneda una sola vez. Un importe ausente impide completar el precio; la cobertura de equipamiento informa los subtotales parciales.

En **Costo comercial de las turbinas**, el informe completo se puede descargar en **PDF** o **Excel** mediante botones contiguos. El Excel incluye Resumen por sistema y Detalle de todas las partidas del alcance seleccionado, con moneda activa, referencias de fuente, filtros, gráfico y totales vinculados al detalle; conserva los importes no informados como celdas vacías.

En el **subbloque 5**, **Costo comercial de la turbina de 80 kW** permanece visible como panel abierto. Incluye los selectores **Turbina + instalación** y **Solo equipo turbina**, sincronizados con el selector superior que determina equipamiento, precio y LCOE. Toda la sección Lo que deja cada turbina entregada de 80 kW utiliza la paleta azul de referencia (#003366, #00509E, #007ACC, #66A3FF y #CCE0FF): costos y precios, LCOE, Monte Carlo y detalle comercial. Las demás secciones conservan sus colores.

El subbloque 5 inicia con **Solo equipo turbina** en ambos selectores sincronizados de 80 kW. La actualización aplica esa selección una vez a las sesiones existentes; después respeta los cambios voluntarios de alcance. La tabla conserva los importes por equipo y por kW (importe dividido por 80 kW).

En **Lo que deja cada turbina entregada · 80 kW**, el panel **Monte Carlo · incertidumbre del LCOE** permite enviar rangos mínimo/más probable/máximo para CAPEX por kW (% de la base), O&M anual (% del CAPEX), factor de planta y tasa real. Usa distribuciones triangulares y 1.000–25.000 escenarios (10.000 por defecto; semilla fija 2026), con la vida útil del LCOE de referencia. El precio sin IVA del alcance seleccionado determina la inversión inicial; el OPEX comercial incluido en el precio no se añade al mantenimiento anual. Los resultados incluyen histograma, P10/P50/P90 y CSV con muestras, parámetros y contexto. Los rangos iniciales son exploratorios y editables, no calibrados con datos del proyecto. Un cambio de base, factor o alcance invalida los resultados anteriores; cambiar solo la moneda o la hora de consulta conserva las muestras y los rangos. `monte_carlo_lcoe.py` aplica la fórmula vectorizada equivalente al flujo descontado constante de `lcoe_finance.py`; `monte_carlo_view.py` implementa el formulario y sus resultados.

Las tarjetas **P10, P50 y P90** muestran costo por **kWh** y su equivalente por **MWh** (× 1.000), en la moneda activa. El Bloque 2 conserva las actualizaciones por interacción y el botón **Actualizar todo**, sin el temporizador anterior de 60 segundos. Monte Carlo no descarta escenarios únicamente porque la fuente se consultó a otra hora.

Los importes monetarios de tarjetas, tablas, gráficos y reportes PDF/Excel se presentan como enteros, con separador de miles y sin parte decimal (ej.: US$ 165.200.682). El LCOE y las tarifas pequeñas conservan su precisión. El redondeo es visual: no modifica los valores de cálculo ni los datos numéricos del Excel. Los porcentajes y tipos de cambio mantienen su formato propio.

Las matrices de proyección anual y primeros cinco años de 10 y 80 kW se presentan agrupadas en **Producción y capacidad**, **Resultados del negocio** y **Flujo y posición de caja**. La vista usa encabezados e indicadores fijos al desplazar la tabla, valores alineados, moneda en cada indicador y énfasis en ventas, EBITDA, flujo libre y caja final; la columna final resalta el último año seleccionado. La tabla nativa con herramientas para copiar y descargar queda en **Tabla completa · copiar y descargar**. `projection_matrix.py` presenta exclusivamente los valores del período elegido, sin recalcularlos ni sumar saldos de cierre.

La pestaña **Resultados y caja · 80 kW** utiliza la misma paleta azul de la matriz anual en gráficos, tarjetas, selectores y avisos. Ventas conserva #003366; EBITDA #007ACC; flujo libre #66A3FF; caja al cierre #00509E. La leyenda superior presenta esa relación y los gráficos mantienen el color de cada indicador en las distintas vistas. El tema se limita a esta pestaña mediante un contexto de renderizado y se restablece al salir.

**Gastos operativos** y **Activos y desarrollo** de 80 kW comparten el diseño azul de Resultados y caja: tarjetas con acentos coherentes con sus gráficos, leyendas, filtros y tablas con filas alternadas. Estructura y Entrega/flota conservan sus colores; el gráfico de activos coincide con los colores de sus cuatro tarjetas. Los temas se restablecen al salir de cada panel.
