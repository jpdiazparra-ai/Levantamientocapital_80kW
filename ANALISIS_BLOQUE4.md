# Bloque 4 · Opción de análisis

Fuente: [documento publicado](https://docs.google.com/spreadsheets/d/e/2PACX-1vQOSK1DE0sEuK5Cl-bIahOjtdP6qsBobzqSlekorQCY9gRpwhRDzHYxh9c-Q-mKoQ/pubhtml).
Fecha de corte del documento revisado: 28-10-2026.

## Lectura del documento

- Plan y Costos contienen los mismos 465 IDs: 435 actividades del piloto 10 kW y 30 del piloto 80 kW.
- Hay cinco hitos y doce sistemas. El avance físico ponderado por presupuesto de referencia es 44,6%.
- 264 actividades llegan al 100% de avance; 313 tienen estado informado Completado. Revision identifica 71 inconsistencias entre estado y avance.
- Las 465 bases están sin aprobar y las 465 conciliaciones están pendientes. AC, EAC, EV, PV, CPI y SPI económicos no están disponibles como control validado.
- La caja se edita en Costos: fecha FC, saldo pendiente, estado de pago, inclusión y validación. Se consideran los saldos No pagado o Parcial con inclusión activa; los Pagado o excluidos no entran. Desembolsos presenta el resumen mensual y no contiene una tabla de cuotas. La parte por validar ya está incluida en el programa: no se suma nuevamente.
- El CSV redondea los importes por fila: la suma de referencias es $1.135.322.705 y la caja por validar $642.300.697. El resumen publicado muestra $1.135.322.702 y $642.300.695. Se conserva la suma de partidas, sin ajustes artificiales de conciliación.

## Propuesta implementada

1. **Levantamiento de Capital y Brecha TRL 9**: tarjetas de primer nivel por hito con referencia, caja, avance y fin previsto. Análisis por proyecto, hito y sistema con distribución presupuestaria, validación de caja y lecturas de concentración. Referencia del alcance seleccionado, caja por validar y desembolsos validados. Barras mensuales separan cada condición, con vencidos en el mes de corte. Distribución del capital por hito y detalle de saldos y validación de Costos. La brecha de financiación queda pendiente hasta contar con caja, ingresos y saldos validados.
2. **Hitos Técnicos e Industrialización**: avance físico ponderado por hito, cronograma jerárquico Sistema → Paquete / línea → Actividad, con selectores en cascada, fechas base o previsión actual, nombres de tareas y desplazamiento continuo con fechas y actividades fijas; Top 10 de desvíos previstos y detalle de responsables, dependencias, evidencia y liberación técnica. La previsión no se interpreta como fin real.
3. **Control PMO de Costos**: aprobación y conciliación, inconsistencias, responsables y evidencia faltante. Matriz por ID y prioridades de revisión. Los indicadores económicos permanecen sin validar hasta completar sus condiciones; no se sustituyen vacíos por cero.

Los tres subbloques usan filtros propios por proyecto, hito, sistema y estado derivado del avance. No comparten los filtros ni las fuentes del Bloque 2. La actualización del panel invalida también la caché del nuevo bloque y conserva sus selectores. La clave de caché incluye la URL y los IDs de pestañas para impedir reutilizar datos de una fuente anterior.

## Siguiente evolución

Cuando existan saldos y registros conciliados, incorporar caja inicial, ingresos confirmados y reserva mínima para calcular fondos adicionales. Después añadir curvas de EV/PV/AC sobre datos validados. La aceptación técnica y la liberación TRL requieren evidencia: el porcentaje de avance no las certifica. No se infiere ruta crítica mientras las dependencias no estén validadas. Comercial necesita cantidades, precios y cotizaciones antes de visualizar un costo industrial confirmado.
