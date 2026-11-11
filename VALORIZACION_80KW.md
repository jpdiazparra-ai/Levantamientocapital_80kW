# Bloque 2 · Subbloque 5 · Caso de Inversión · 80 kW

El caso financiero exclusivo de 80 kW se consulta en [Valorización FW V14](https://docs.google.com/spreadsheets/d/e/2PACX-1vRtQHrMkPa0wA7KpcUf_foYsbIpmh4gC4UuppPkWWIpFGPPhs3lxtRmzwB8D21sXw/pubhtml). La aplicación lee la publicación actual y conserva la trazabilidad de las cifras; las capturas de pruebas nunca se usan como fuente del dashboard.

## Navegación y fuentes

Las ocho pestañas siguen la estructura del archivo: Evaluación 80 kW (00), Datos y supuestos (00 Datos de entrada y 03), Inversión y socios (02), Resultados y caja (04–06), Ventas y fabricación (07), Gastos operativos (08), Activos y desarrollo (09) y Controles y fuentes (10). La publicación tiene once hojas y no contiene 01 Resumen. No se extrapola el caso conjunto de 10 y 80 kW.

La evaluación es una vista continua con resultados y valorización, arranque e inversión, economía unitaria y proyección quinquenal. Las cifras financieras publicadas y sus redondeos se conservan en sus tablas originales. Datos y supuestos muestra primero Escenarios de tasa y valor terminal, después Sensibilidad publicada · precio y tasa, ambos visibles antes de las tablas.

La caché de lectura dura 60 segundos e incluye la URL, los identificadores y el nonce de actualización. Los controles usan el prefijo independiente `option4_valuation80`. Moneda y tipo de cambio se comparten con el bloque 2; la moneda inicial es USD y el TC inicial es 980 CLP/USD, editable manualmente. Actualizar todo restablece USD.

## Monedas y economía unitaria

Los resultados del modelo son USD nominales. Para presentarlos en CLP se multiplica una sola vez por el TC del panel. Las tarifas OPEX de origen CLP se convierten primero con el TC interno del archivo para conciliar la salida USD. Vacíos permanecen faltantes; guiones contables explícitos representan cero.

`valuation80_unit.py` interpreta la moneda del precio inicial de 00 Datos de entrada: busca USD o CLP en D/E de la fila. USD se usa directamente; CLP se divide por el TC del panel. Se conservan los multiplicadores de precio del escenario y adicional de 03. Si no hay moneda reconocida, no se infiere por la magnitud del valor. El lector de la tabla distingue un valor auxiliar numérico en D de la unidad publicada en E.

La economía unitaria reúne costos y precios en un recuadro con columnas Por equipo y Por kW, junto al LCOE en columnas de igual ancho. Incluye:

- Costo informado del Producto 80 kW: Comercial anterior de las partidas Aplica del subbloque 1, con fundaciones y montaje, y cobertura de registros. Costo por kW = subtotal / 80.
- Costo base más OPEX unitario de 07; inicialmente E78 + E82.
- Valor con margen de 07: se reconocen las etiquetas anteriores y los alias Precio Venta / Precio de venta. La lectura sigue las etiquetas y conserva la referencia si las filas cambian de posición. Un precio se identifica como Precio calculado · hoja 07, separado del precio inicial de 00. Etiquetas desconocidas, ambiguas y valores ausentes quedan sin informar.
- Margen del proveedor publicado en D de su fila, definido sobre precio; no se confunde con margen bruto sobre ventas.
- Precio de venta por equipo y por kW, sin IVA y con el IVA referencial de 03 Supuestos. Potencia base: 80 kW.

Si el precio neto y el valor con margen coinciden dentro de 0,005 USD, se muestran juntos con una nota; si difieren, permanecen separados. El gráfico compara costo base, costo más OPEX y el valor final publicado; no repite una barra adicional de precio de venta. Los importes completos no se suman entre sí. Las fuentes y criterios quedan en un desplegable.

Esta conciliación unitaria respeta la moneda de origen y no reconstruye los flujos ni el DCF publicados. El primer quinquenio procede de 00; el detalle anual conserva diez años de 04–06. Los acumulados suman flujos, los cierres de caja son saldos y el margen ponderado es suma EBITDA / suma ventas.

## LCOE del propietario

`valuation80_lcoe.py` comparte el cálculo entre pantalla y PDF. El panel compacto permite modificar únicamente el factor de planta neto (1–100 %, inicial 35 %). Una sesión antigua en 30 % migra una vez a 35 %; los cambios manuales posteriores se conservan. El laboratorio avanzado de Ventas y fabricación mantiene controles independientes.

- Potencia: 80 kW. Energía anual = 80 × 8.760 × FP; el FP ya incorpora disponibilidad y pérdidas.
- CAPEX de referencia: precio neto por equipo, leído en la moneda publicada y con los multiplicadores de precio activos.
- O&M anual ilustrativo: 2 % de ese precio; no es el OPEX de la empresa fabricante.
- Vida útil: 20 años. Tasa de descuento real: 8 %. Son hipótesis visibles, independientes del DCF y no confirmadas por el archivo.
- LCOE = valor presente de costos / valor presente de energía. CAPEX al inicio; energía y O&M al cierre de cada año.
- Sin degradación, O&M variable, crecimiento real del O&M, reposiciones, retiro, impuestos ni valor residual. Costos de sitio no incluidos en el precio quedan por completar: es un resultado indicativo.

El panel muestra generación, LCOE por kWh y MWh y sensibilidad al FP. La descarga incorpora el FP activo, que forma parte de la clave de caché.

## Análisis financiero y controles

Se distinguen DCF/VAN, precio negociado, aporte primario y pago secundario. La TIR económica incorpora activos aportados y corresponde al proyecto. La recuperación descontada publicada es de caja en años completos; los anticipos son obligaciones de entrega. El laboratorio DCF conserva flujos y terminal normalizado y requiere tasa mayor que crecimiento para Gordon.

La columna mensual reservada H se conserva para no desplazar los datos. Año 0 y años operativos 1–10 comprenden 132 meses; el apoyo terminal queda fuera de la ventana DCF predeterminada. El laboratorio de volumen no recalcula CT, anticipos, IVA, impuestos, CAPEX ni disponibilidad de fabricación externa.

Inventario inicial separa stock de producción y repuestos de planta. El desarrollo base ya integra CAP-001/CAP-002 y no se suma nuevamente a preoperacionales. CT histórico permanece como referencia. Los detalles de fabricación mantienen saldos por desglosar y no acreditan presupuestos completos.

Se realizan 19 conciliaciones independientes: completitud, VAN/DCF, terminal, activos, operación societaria, inventarios, balance, EBITDA, fabricación, OPEX, flujo mensual/anual, aporte recibido y brecha de reserva. Las tolerancias identifican su unidad y reconocen redondeos. Los 46 controles originales de 10, sus pendientes y n.a., sus referencias y los errores de fórmula permanecen visibles. Una conciliación no acredita disponibilidad de capital, contratos ni validación técnica.

## PDF ejecutivo

El diseño 11 genera siete páginas vectoriales:

1. Resultados y valorización, con dos criterios técnicos de evaluación financiera.
2. Arranque e inversión.
3. Trayectoria operativa y caja.
4. Economía unitaria y costos: precios por equipo/kW, sin/con IVA, gráfico de 07 y evidencia de costos del subbloque 1.
5. Calendario de desembolsos de 80 kW.
6. Gastos operativos: estructura, entrega/flota, gráficos y partidas del primer año.
7. LCOE: escenario activo, curva de sensibilidad, valor presente, aportes al costo nivelado, fórmula, fuentes y supuestos.

El calendario usa `valuation80_project.py`, el mismo lector del subbloque 1 y el proyecto de 80 kW de Plan. Conserva saldos No pagado/Parcial incluidos, agrupa vencidos en el mes de corte y declara los saldos sin fecha. No restringe la caja a las partidas comerciales Aplica ni la suma al flujo operativo financiero. El KPI y la tabla no muestran Caja validada, pero el gráfico conserva esa serie cuando hay importes.

Solo se muestran Hito Piloto 80 kW y Hito Producto 80 kW, con nombre y Fin previsto actual de Plan en recuadros independientes. El eje continuo se extiende hasta el último hito, incluso sin desembolso ese mes; no se crean montos ni se alteran los totales. Los recuadros se separan aunque ambos hitos caigan en un mismo mes.

Los costos comerciales reutilizan `valuation_costs.py`: Hito objetivo de Costos = 80 kW, Costo para producto = Aplica, alcance Total. Se muestran sistemas, principales paquetes/líneas, Comercial anterior, Presupuesto vigente, cobertura y conciliación. Estas bases no reemplazan ni se suman al costo de fabricación del archivo financiero. Plan/Costos son CLP nativos: se dividen una vez por el TC del panel para USD y se conservan para CLP.

Si falla la fuente de costos/caja, solo se deshabilita la descarga completa con una explicación; el caso financiero sigue disponible. El diseño, moneda, TC y FP forman parte de los argumentos del reporte para evitar PDFs de otro escenario.

## Presentación de capital y ejecución técnica

Los hitos técnicos tienen tarjetas compactas, con tonos arena para 10 kW y gris azulado para 80 kW. Referencias y notas se agrupan en fuentes y criterios. Cronograma técnico contiene sus filtros, resumen y gráfico en un recuadro separado del detalle; inicia en Premontaje 10 kW, estados En curso/Pendiente y nivel Actividades, sin impedir cambios manuales.

Los cuatro KPI de capital están dentro de Calendario de desembolsos; se retiró el panel Análisis de capital. El gráfico mensual conserva los cinco hitos con 20 % menos altura y KPI aproximadamente 35 % más compactos. Los criterios quedan agrupados en un desplegable. Moneda/corte aparecen en una línea; consulta, actualización y enlace de origen están en Fuente y actualización.

Fondos por responsable combina barras ordenadas, tabla lateral de validada/por validar/participación y mayor asignación, con agrupación por entidad o persona. Los importes abreviados conservan su detalle completo. Se retiraron los desplegables Criterios de comparación de presupuesto y caja, Trazabilidad de partidas · Costos y Cómo interpretar el costo comercial.

El análisis comercial elimina Base comercial histórica y mejora el donut y el desglose por sistema: colores vinculados, columnas de importe/participación y cobertura de partidas por sistema. Los faltantes se mantienen visibles y no se convierten en cero. Los controles Total/Comercial siguen delimitando KPI, gráficos, tablas e informes.

## Verificación

Las capturas públicas en `tests/fixtures` cubren la estructura original, la transición de CLP a USD y el cambio de etiqueta a Precio Venta. Se prueban cálculos, lectura de columnas, monedas, fechas de hitos, conciliaciones, PDF, FP, invalidación de caché e independencia de controles. Se complementa con AppTest y revisión visual local del PDF y del dashboard. Comando: `.venv/bin/python -m unittest discover -s tests -q`.
