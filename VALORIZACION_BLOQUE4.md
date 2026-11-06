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

- **Diagnóstico financiero:** DCF/ventas y DCF/EBITDA del primer año, índice de rentabilidad económico, payback simple y descontado, spread tasa–crecimiento y relación entre precio previo negociado y DCF. Los múltiplos describen el modelo; no son comparables de mercado ni múltiplos EV. El índice descuenta entradas y salidas económicas, incluidos activos aportados, sin terminal. El payback interpola flujos anuales y no representa un calendario mensual ni el retorno del socio.
- **Economía por turbina:** año independiente, selección de 10/80 kW, gráfico por equipo o por kW, matriz de precios, fabricación, margen bruto, OPEX específico y contribución antes de OPEX común. Los adicionales de terceros se asignan por producto únicamente si concilian con fabricación consolidada; una discrepancia material deja el margen sin cálculo. El laboratorio de mix usa ambos productos a costos/precios unitarios constantes, volumen editable y OPEX común fijo: muestra EBITDA aproximado, punto de equilibrio en equipos equivalentes, margen de seguridad y apalancamiento operativo. No recalcula economías de escala, impuestos, capital de trabajo ni capacidad de proveedores.
- **Proyección y caja:** intervalo de años seleccionable, ventas y EBITDA, flujo libre/caja y entregas/capacidad. Los ratios incluyen margen EBITDA ponderado, CAGR de ventas y conversión FCFF/EBITDA. Los flujos se suman; la caja es el saldo del último año seleccionado. La tabla transpuesta muestra demanda, capacidad, entregas, externalización, sobrecostos, resultados y caja.
- **Laboratorio DCF:** tasa de descuento y crecimiento perpetuo editables, inclusión/exclusión del terminal y restauración de los supuestos publicados. Conserva los FCFF de años 0–10 y el FCFF normalizado publicado del año 11. La tasa modifica el descuento y el crecimiento solo el denominador de Gordon: no recalcula el flujo normalizado ni los resultados operativos. Exige r > g para usar terminal. Incluye mapa de sensibilidad y detalle de descuento anual.

Las variaciones del laboratorio se comparan con una base reconstruida usando los mismos importes CSV, que pueden estar redondeados. Los datos faltantes se conservan sin cálculo. `valuation_finance.py` contiene las fórmulas puras; `valuation_interactive.py`, los controles y gráficos. La conversión de moneda afecta la presentación, no los cálculos en USD de la fuente. Los controles conservan sus selecciones al actualizar.

## Presentación como reporte ejecutivo

La vista utiliza una paleta de azul pizarra, blanco y acentos verde azulado. Los KPI se agrupan en bandas compactas; los indicadores derivados tienen menor jerarquía que los resultados publicados. La fuente, moneda y año de detalle están en un panel plegable. Los importes exactos y notas se mantienen visibles.

La economía unitaria usa barras horizontales apiladas con precio de referencia; ventas y EBITDA se presentan en paneles alineados con escalas monetarias identificadas. Los mapas de sensibilidad muestran celdas separadas y valores rotulados. El diseño adapta los KPI a dos columnas en pantallas estrechas y conserva filtros, fórmulas y criterios de conciliación.

## Inversión y socios: condiciones completas de la operación

La vista incorpora las cuatro secciones de **02 Inversión y socios**: condiciones de la operación, precio y participación accionaria, aplicación de fondos y comparación entre negociación y DCF. Actualmente son 26 campos y cinco criterios de lectura, incluyendo mes/año del desembolso, estado, emisión primaria, compra secundaria, accionistas actuales, fracción vendida de acciones antiguas, aporte adicional para caja objetivo y patrimonio contable inicial.

Las tablas conservan las observaciones publicadas, unidades y referencias de celda. Los importes USD se convierten con el selector de visualización; porcentajes, estado y coordenadas del calendario mantienen sus unidades originales. Los ceros contables se muestran como cero, incluido un desembolso en año 0. La diferencia negociación–DCF y el cociente precio/DCF se muestran tal como se publican, respetando sus redondeos. Los gráficos complementan las tablas con destino del pago, estructura accionaria, puente de caja y contraste precio/DCF.

El estado Propuesta no acredita fondos. La compra secundaria se mantiene fuera de la caja de FW. No se infiere el reparto individual entre accionistas ni se convierte mes/año del modelo en una fecha de cierre confirmada. La trazabilidad incluye los valores originales en USD y los criterios completos de la fuente.

## PDF ejecutivo para comité financiero

A la derecha de **Valor indicativo y fundamentos del caso** se descarga un PDF vectorial en A4 horizontal, sin navegador ni captura de pantalla. Incluye dos láminas ejecutivas: alcance documentado de la turbina de 80 kW y síntesis financiera del negocio consolidado 10 + 80 kW. Los anexos conservan la proyección a diez años, inversión y CAPEX, valores financieros exactos, supuestos, condiciones pendientes y el texto íntegro de las actividades de Plan con Hito objetivo 80 kW, en orden natural de ID.

El informe sigue la moneda CLP/USD y el tipo de cambio de presentación. Utiliza el primer año operativo como referencia de economía unitaria y el caso publicado para TIR, VAN y DCF; no exporta los ajustes del laboratorio como si fueran resultados de la fuente. Distingue fabricación y contribución por equipo de EBITDA, VAN económico de VAN de caja, activos fijos en especie de CAPEX pagado por FW e inventario/preoperacionales. Las conclusiones se generan con los datos del caso, incluidos márgenes negativos cuando existen.

La información técnica se consulta de forma independiente en Plan del documento de control del proyecto, sin cruce obligatorio de IDs con Costos. Las descripciones son alcances publicados: no se extrapola una ficha o curva de 10 kW a 80 kW, ni se presenta una norma citada en una partida como certificación obtenida. Las especificaciones resumidas remiten al anexo completo por ID. El estado de la operación, fecha de consulta y fuentes acompañan al informe.

`valuation_report.py` construye las láminas, gráficos y anexos con ReportLab. La caché dura 60 segundos; la descarga usa `on_click='ignore'` para conservar la vista y filtros. Si la fuente técnica no permite preparar el informe, solo el botón queda deshabilitado con una explicación y el análisis financiero sigue disponible.
