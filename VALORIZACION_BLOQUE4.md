# Sub bloque 4 · Valorización y viabilidad financiera

El Bloque 4 incorpora una cuarta vista que consulta exclusivamente el modelo publicado de valorización:

[Modelo 00–09](https://docs.google.com/spreadsheets/d/e/2PACX-1vSLGE7e12WDJ2MiiGFqFOieTuXl4ilhBgbLv2I3sQEAJCOVpVeRTjxK-lmdUZ5gjg/pubhtml).

## Cobertura y navegación

Se leen once pestañas: **00 Evaluación**, **00 Datos de entrada**, **01 Resumen**, **02 Inversión y socios**, **03 Supuestos**, **04 Resultados y flujo**, **05 Balance y cobros**, **06 Caja mensual**, **07 Ventas y producción**, **08 Gastos operativos** y **09 Activos y arranque**. Las hojas 10 y 11 se consultaron durante el análisis inicial para entender los criterios de la fuente; las vistas y conciliaciones de la aplicación usan 00–09.

La interfaz organiza el contenido en seis pestañas:

| Vista | Contenido |
|---|---|
| Resumen y valorización | DCF antes de capital nuevo, VAN/TIR económicos, puente de valor, precios negociados, sensibilidad nativa y condiciones pendientes. |
| Inversión y socios | Capital primario, compra secundaria, propiedad implícita y puente de caja del arranque. |
| Resultados y operación | Curvas anuales, puente al EBITDA, demanda/capacidad, economía unitaria de 10/80 kW y flujo completo. |
| Caja y cobros | Calendario mensual, caja antes/después de aportes, anticipos, balance y año de apoyo terminal separado. |
| OPEX y activos | Presupuesto por área, partidas y ajustes, inventario valorizado, referencias históricas y depreciación. |
| Supuestos y trazabilidad | Conciliaciones propias, supuestos publicados, referencias de indicadores, caso activo/base V6 y lectura íntegra de las once pestañas. |

El año operativo actualiza resultados unitarios, balance y presupuesto OPEX. El DCF y las curvas completas mantienen los diez años de la fuente. La sensibilidad nativa conserva los nueve resultados publicados. El resumen incorpora además cuatro vistas interactivas descritas abajo; sus simulaciones analíticas se distinguen del caso publicado y no recalculan el libro completo.

## Convenciones y trazabilidad

- El modelo publica importes en USD nominales y presupuestos de origen en CLP. La visualización respeta el selector CLP/USD del panel; para CLP multiplica USD por el tipo de cambio de visualización. El tipo de cambio interno de la fuente se conserva por separado y sirve para conciliar las partidas OPEX en CLP con sus salidas en USD.
- Los ceros contables `-`, `–` y `—` son cero. Las celdas vacías y los valores no disponibles se conservan como faltantes.
- Las tasas de TIR y peso terminal se leen desde **00 Evaluación**, donde se publican como porcentajes. Algunas celdas auxiliares de 04 presentan valores redondeados como enteros y no se usan para mostrar esas tasas.
- El DCF de 00 C21 no incluye el capital nuevo. El VAN económico de 00 C19 resta el valor de los activos aportados al VAN de caja explícito. El precio previo/posterior de 02 se mantiene como valor negociado separado.
- El capital primario entra en FW. La compra secundaria se paga a fundadores; no se agrega como ingreso operativo ni como caja de la empresa. El estado Propuesta se muestra tal como aparece en la fuente.
- `Caja sin puente` de 06 ya contiene el aporte primario. La caja anterior a aportes se deriva del acumulado de `Flujo neto USD` y se identifica como derivada.
- El año mensual 11 sirve de apoyo al terminal/anticipos. No se mezcla con los diez años del DCF ni con la ventana mensual predeterminada.
- El OPEX usa el detalle anual J:S de OP-01 a OP-30, convertido con el tipo de cambio del modelo, más los ajustes en USD de filas 65–67, una sola vez.
- Los activos se valorizan con **Costo aplicado USD**, columna P de 09. La asignación proporcional del inventario a los activos en especie se identifica como provisional. El CT histórico se muestra como referencia separada y se excluye del gráfico de inversión y del inventario filtrado por defecto.

## Conciliaciones y actualización

`valuation_data.py` contrasta catorce controles: completitud, puente del DCF, VAN económico, Gordon, coincidencia con resumen, destino de fondos, precio previo/posterior, inversión inicial, activos en especie, caja inicial, balance, EBITDA, OPEX y flujo mensual/anual. Las tolerancias se muestran en su unidad y reconocen que el CSV redondea importes; no acreditan presupuestos ni contratos. Las discrepancias y errores de fórmula se señalan y se localizan en la pestaña de trazabilidad.

La caché dura 60 segundos y participa en Actualizar todo mediante el mismo nonce de refresco. Los filtros tienen claves estables. La vista se carga antes del documento Plan/Costos de los otros sub bloques: un error de IDs en ese documento no impide revisar valorización. La revisión visual y las pruebas verificaron ambas monedas, navegación, cambios de año, los once orígenes y conservación de selecciones.

## Resumen financiero interactivo

El resumen mantiene sus cuatro KPI publicados y añade estas vistas:

- **Valorización y retorno:** construcción del DCF, comparación con precio negociado y, después, DCF/ventas y DCF/EBITDA del primer año, índice de rentabilidad económico, payback simple y descontado, spread tasa–crecimiento y relación entre precio previo negociado y DCF. Los múltiplos describen el modelo; no son comparables de mercado ni múltiplos EV. El índice descuenta entradas y salidas económicas, incluidos activos aportados, sin terminal. El payback interpola flujos anuales y no representa un calendario mensual ni el retorno del socio.
- **Economía por turbina:** año independiente, selección de 10/80 kW, gráfico por equipo o por kW, matriz de precios, fabricación, margen bruto, OPEX específico y contribución antes de OPEX común. Los adicionales de terceros se asignan por producto únicamente si concilian con fabricación consolidada; una discrepancia material deja el margen sin cálculo. El laboratorio de mix usa ambos productos a costos/precios unitarios constantes, volumen editable y OPEX común fijo: muestra EBITDA aproximado, punto de equilibrio en equipos equivalentes, margen de seguridad y apalancamiento operativo. No recalcula economías de escala, impuestos, capital de trabajo ni capacidad de proveedores.
- **Proyección financiera:** intervalo de años seleccionable, ventas y EBITDA, flujo libre/caja y entregas/capacidad. Los ratios incluyen margen EBITDA ponderado, CAGR de ventas y conversión FCFF/EBITDA. Los flujos se suman; la caja es el saldo del último año seleccionado. La tabla transpuesta muestra demanda, capacidad, entregas, externalización, sobrecostos, resultados y caja.
- **Escenarios de valorización:** tasa de descuento y crecimiento perpetuo editables, inclusión/exclusión del terminal y restauración de los supuestos publicados. Conserva los FCFF de años 0–10 y el FCFF normalizado publicado del año 11. La tasa modifica el descuento y el crecimiento solo el denominador de Gordon: no recalcula el flujo normalizado ni los resultados operativos. Exige r > g para usar terminal. Incluye mapa de sensibilidad y detalle de descuento anual.

Las variaciones del laboratorio se comparan con una base reconstruida usando los mismos importes CSV, que pueden estar redondeados. Los datos faltantes se conservan sin cálculo. `valuation_finance.py` contiene las fórmulas puras; `valuation_interactive.py`, los controles y gráficos. La conversión de moneda afecta la presentación, no los cálculos en USD de la fuente. Los controles conservan sus selecciones al actualizar.

## Presentación como reporte ejecutivo

La vista utiliza una paleta de azul pizarra, blanco y acentos verde azulado. Los KPI se agrupan en bandas compactas; los indicadores derivados tienen menor jerarquía que los resultados publicados. La fuente, moneda y año de detalle están en un panel plegable. Los importes exactos y notas se mantienen visibles.

La economía unitaria usa barras horizontales apiladas con precio de referencia; ventas y EBITDA se presentan en paneles alineados con escalas monetarias identificadas. Los mapas de sensibilidad muestran celdas separadas y valores rotulados. El diseño adapta los KPI a dos columnas en pantallas estrechas y conserva filtros, fórmulas y criterios de conciliación.

## Inversión y socios: condiciones completas de la operación

La vista incorpora las cuatro secciones de **02 Inversión y socios**: condiciones de la operación, precio y participación accionaria, aplicación de fondos y comparación entre negociación y DCF. Actualmente son 26 campos y cinco criterios de lectura, incluyendo mes/año del desembolso, estado, emisión primaria, compra secundaria, accionistas actuales, fracción vendida de acciones antiguas, aporte adicional para caja objetivo y patrimonio contable inicial.

Las tablas conservan las observaciones publicadas, unidades y referencias de celda. Los importes USD se convierten con el selector de visualización; porcentajes, estado y coordenadas del calendario mantienen sus unidades originales. Los ceros contables se muestran como cero, incluido un desembolso en año 0. La diferencia negociación–DCF y el cociente precio/DCF se muestran tal como se publican, respetando sus redondeos. Los gráficos complementan las tablas con destino del pago, estructura accionaria, puente de caja y contraste precio/DCF.

El estado Propuesta no acredita fondos. La compra secundaria se mantiene fuera de la caja de FW. No se infiere el reparto individual entre accionistas ni se convierte mes/año del modelo en una fecha de cierre confirmada. La trazabilidad incluye los valores originales en USD y los criterios completos de la fuente.

## PDF ejecutivo para comité financiero

A la derecha de **Valor indicativo y fundamentos del caso** se descarga un PDF vectorial en A4 horizontal de **exactamente cinco páginas**:

1. Alcance técnico documentado de la turbina de 80 kW, con referencias por ID a Plan.
2. Tesis financiera: DCF a diez años más terminal; VAN y TIR económicos a diez años sin terminal; activos fijos aportados como valor inicial y CAPEX pagado por FW acumulado en diez años. Una banda independiente resume ventas, EBITDA, margen ponderado y FCFF de los primeros cinco años. La economía por turbina conserva el primer año operativo como referencia explícita.
3. Proyección anual completa a diez años y clasificación del capital inicial.
4. Cifras exactas, supuestos, condiciones pendientes y enlaces a las fuentes.
5. Estructura técnica de costos de 80 kW, usando Plan y Costos del subbloque 1: sistemas, principales líneas, montos, variaciones, HH y cobertura de datos.

El margen EBITDA quinquenal es **suma de EBITDA / suma de ventas**; no es un promedio simple ni el margen del primer año. Ventas, EBITDA y FCFF son acumulados del período; activos fijos iniciales no se suman por año. Los horizontes se identifican en títulos y notas y siguen el calendario publicado del modelo. La TIR no se atribuye al socio ni a la turbina de 80 kW de forma aislada.

Se eliminan los anexos técnicos extensos; la quinta página es exclusivamente el nuevo resumen de costos. Las descripciones resumidas de la página 1 remiten al texto completo de Plan mediante sus IDs y el enlace de la página 4. La composición fija no añade anexos automáticos. Las pruebas verifican cinco páginas tanto en CLP como en USD y conservación del contenido de las cuatro primeras.

El informe sigue la moneda y tipo de cambio de presentación y usa el caso publicado, sin exportar las simulaciones locales del laboratorio. Distingue fabricación y contribución por equipo de EBITDA, VAN económico de VAN de caja y activos fijos en especie de inventario/preoperacionales. Los puntos financieros se generan con los datos vigentes, incluidos márgenes negativos cuando existen.

La fuente técnica se consulta de forma independiente en Plan, sin cruce obligatorio con Costos. No se extrapola una ficha de 10 kW a 80 kW ni se presenta una norma citada como certificación obtenida. Estado de la operación, fecha de consulta y fuentes acompañan al reporte.

`valuation_report.py` construye las cinco páginas con ReportLab. La caché versionada dura 60 segundos y la descarga usa `on_click='ignore'` para conservar la vista y filtros. Si no puede prepararse el informe, solo el botón queda deshabilitado con una explicación; el análisis financiero sigue disponible.

### Página 5: costos de la turbina de 80 kW

`valuation_costs.py` consulta Plan y Costos y reutiliza las reglas comerciales del subbloque 1. Se selecciona **Hito objetivo de Costos = 80 kW** y **Costo para producto = Aplica**; la vista es **Total**, incluidas fundaciones y montaje. Las dimensiones Sistema/Línea y el criterio HH proceden del mismo cruce por ID que usa el panel; Cantidad procede de Costos. Los IDs duplicados y las partidas elegibles sin correspondencia en Plan impiden exportar un agregado incompleto.

La tabla de sistemas concilia con el subtotal directo de Costos. La tabla de líneas muestra las seis de mayor Comercial anterior y agrega las restantes, conservando el total. Se incluyen Presupuesto vigente, variación `(presupuesto − comercial) / comercial`, participación comercial, costo por kW, HH informadas y cobertura de registros. Los vacíos se mantienen como faltantes; HH no suma insumos y señala cantidades pendientes. Una variación de importes informados no se presenta como sobrecosto validado.

Esta fuente es **CLP nativa**, a diferencia del modelo de valorización, que es USD nativo. Los importes de la página 5 se convierten una sola vez con el tipo de cambio de visualización. La base de partidas no reemplaza ni se incorpora automáticamente al costo de fabricación proyectado de la página 2. Se identifica su fecha de consulta por separado. La caché del PDF pasa a versión 3 para invalidar descargas anteriores de cuatro páginas.

## LCOE interactivo en Economía por turbina

Después de la economía unitaria y antes de Equilibrio y sensibilidad del mix se incorpora un escenario LCOE del propietario. Respeta el año y los productos seleccionados. La tabla editable incluye CAPEX del equipo, otros CAPEX instalados, O&M fijo anual y O&M variable por kWh; el precio de venta es la referencia inicial y puede alternarse por fabricación como aproximación interna. Los costos de sitio deben agregarse solo si no están incluidos en el equipo.

Los supuestos iniciales **ilustrativos**, no extraídos de una ficha certificada, son factor de planta neto 30 %, vida útil 20 años, tasa real 8 % y O&M fijo anual 2 % de la referencia del equipo. El porcentaje inicializa el valor de referencia: no multiplica los CAPEX editados; una cifra anual manual tiene prioridad. Otros CAPEX y O&M variable parten de cero, pendientes de completar. El OPEX específico del fabricante se muestra como referencia y no se utiliza automáticamente como mantenimiento del activo instalado.

`lcoe_finance.py` calcula **VP de todos los costos / VP de energía neta**. La energía inicial es `kW × 8760 × FP neto`, con degradación geométrica desde el segundo año. No se restan otra vez disponibilidad ni pérdidas. La tasa real descuenta costos y energía al cierre de cada año, con CAPEX en año 0. Se incluyen crecimiento real del O&M fijo, reposición única en un año editable y retiro al final de la vida útil. No se incluyen impuestos, subsidios, ingresos, intereses de deuda, combustible ni valor residual.

La tabla de resultados presenta CAPEX, O&M, energía anual, VP de costos/energía, contribución de cada componente al LCOE y total por kWh y MWh. El gráfico muestra sensibilidad al factor de planta y el detalle anual permite auditar cada flujo. Fórmula de costos/energía descontados: [documentación NLR/NREL](https://www.nlr.gov/pv/lcoe-calculator/documentation); se utiliza el principio financiero general, sin importar supuestos fotovoltaicos ni parámetros técnicos de otra turbina.

`valuation_lcoe.py` conserva las ediciones como USD nativos por año, referencia y potencia. La conversión CLP/USD, los cambios de tipo de cambio y los filtros no alteran el escenario guardado. Se puede restaurar la tabla del contexto actual. Los cambios de vida útil mantienen válida la reposición; entradas incompletas, factor cero y costos no finitos no producen un LCOE. La simulación es independiente del DCF publicado y del PDF de cinco páginas.

### Tabla y seguimiento técnico LCOE

La tabla de supuestos utiliza formato numérico localizado con separadores de miles, columnas monetarias más amplias y filas de 52 px. La identificación de turbina queda fijada al desplazar la tabla horizontalmente. Los importes siguen siendo numéricos editables; el formato de presentación no altera los valores del escenario ni su conversión de moneda.

Después de la sensibilidad al factor de planta se incorporan tres vistas de líneas, con 80 kW como selección inicial cuando está disponible:

- **Generación neta:** producción anual y acumulada en paneles alineados; acumulación de energía física, sin descuento.
- **O&M y reposiciones:** O&M anual, reposición/retiro y total operativo por año. El CAPEX del año 0 se identifica por separado y sigue incluido en el LCOE.
- **LCOE por horizonte:** VP acumulado de costos desde año 0 dividido por VP acumulado de energía hasta cada año. Su último punto concilia con el LCOE de vida completa.

`lcoe_profiles` deriva las curvas de los mismos flujos del cálculo, sin modificar sus entradas. Todos los gráficos responden a factor neto, vida útil, tasa, degradación, O&M y eventos de reposición/retiro. El selector permite revisar otras turbinas del comparativo y conserva una selección válida al interactuar. Los valores cero en los eventos producen curvas planas; la generación depende del factor y degradación ingresados, no de una curva de viento certificada.

## Orden de lectura de Resumen y valorización

Los cuatro KPI publicados y el botón PDF permanecen como resumen común del caso. La navegación secundaria se organiza en **Valorización y retorno**, **Economía por turbina**, **Proyección financiera** y **Escenarios de valorización**.

Valorización y retorno sigue esta secuencia: construcción del DCF y comparación con precio negociado; lectura del valor; indicadores complementarios de rentabilidad; sensibilidad publicada; condiciones pendientes y definiciones plegadas al final. Los dos gráficos iniciales forman un grupo y se apilan en pantallas estrechas. Las fórmulas, fuentes y claves de los controles de economía, LCOE, proyección y escenarios se conservan.
