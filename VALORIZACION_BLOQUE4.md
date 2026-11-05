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

El año operativo actualiza resultados unitarios, balance y presupuesto OPEX. El DCF y las curvas completas mantienen los diez años de la fuente. Las sensibilidades son los nueve resultados publicados: no se presentan multiplicadores Conservador/Optimista como si fueran resultados recalculados.

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
