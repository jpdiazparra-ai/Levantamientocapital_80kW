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

Capital muestra ambos proyectos completos, sin el panel general de filtros. El cronograma técnico y PMO conservan sus selectores propios. No comparten los filtros ni las fuentes del Bloque 2. La actualización del panel invalida también la caché del nuevo bloque y conserva sus selectores. La clave de caché incluye la URL y los IDs de pestañas para impedir reutilizar datos de una fuente anterior.

## Siguiente evolución

Cuando existan saldos y registros conciliados, incorporar caja inicial, ingresos confirmados y reserva mínima para calcular fondos adicionales. Después añadir curvas de EV/PV/AC sobre datos validados. La aceptación técnica y la liberación TRL requieren evidencia: el porcentaje de avance no las certifica. No se infiere ruta crítica mientras las dependencias no estén validadas. Comercial necesita cantidades, precios y cotizaciones antes de visualizar un costo industrial confirmado.

## Regla de los KPI por hito

Los nombres y las fechas de las tarjetas se construyen exclusivamente con las filas cuya columna **Paquete / línea** contiene la palabra **Hito**. El nombre mostrado es el paquete marcador y **Fin previsto actual** se toma de esos marcadores, sin extenderlo por actividades ordinarias. Si existen varios marcadores para un mismo Hito objetivo, se muestra el fin máximo entre ellos. El avance ponderado, los importes y los conteos siguen resumiendo las actividades asignadas a ese hito; los gráficos y el cronograma conservan su alcance según los filtros.

## Lectura visual del capital

Los gráficos comparativos de presupuesto y caja comparten escala y muestran los montos al final de cada barra. Azul identifica referencia, verde caja validada y ámbar caja por validar. El calendario apila los importes disjuntos validados y por validar, muestra el total mensual e identifica el mes con mayor necesidad. También marca los hitos con líneas verticales y recuadros superiores de nombre y Fin previsto actual; usa solo las filas Hito de Paquete / línea y respeta los filtros. Las etiquetas se escalonan para evitar superponerse. Los montos faltantes permanecen sin informar.

Fondos por responsable agrupa las actividades seleccionadas por **Entidad responsable** (opción inicial) o **Responsable persona**; la asignación vacía aparece como Sin responsable asignado. La suma coincide con la caja seleccionada sin duplicar actividades. Esta clasificación describe al responsable de ejecución y no acredita al aportante del financiamiento.

### Costo comercial de los pilotos

Antes de Fondos por responsable se muestra Comercial anterior, de Costos, vinculado por ID a Plan. La suma y los desgloses por sistema e hito corresponden al piloto elegido en el selector comercial. Los donuts representan únicamente importes no negativos informados; las partidas sin monto no se convierten en cero. Si hay ajustes negativos se conserva el subtotal y el detalle, sin graficar proporciones engañosas. Se informa cobertura de registros, subtotal por kW nominal y concentración por sistema. La trazabilidad incluye la actividad, hito, sistema, paquete, presupuesto vigente y sustento, con descarga CSV. La base histórica no determina un precio de venta actualizado; un subtotal parcial no representa el costo total. No se extrapola de 10 kW a 80 kW ni se incorpora el subtotal a la caja.

El selector Piloto del análisis comercial muestra un proyecto a la vez y conserva la selección durante las actualizaciones mientras siga disponible en la fuente. En Composición por sistema e hito, seleccionar una fila despliega las partidas con Comercial anterior informado (incluidos ceros explícitos), con subtotal y CSV del grupo. Una casilla permite incluir también actividades sin monto. La selección de fila se vincula al proyecto, IDs del alcance y orden de grupos para evitar mostrar otro grupo después de cambiar filtros.

El diseño comercial presenta cuatro KPI (subtotal, subtotal por kW, cobertura de registros y concentración en los tres sistemas de mayor monto), un donut con porcentajes visibles en las porciones principales y un desglose lateral con importe exacto, porcentaje y partidas informadas de cada sistema. El panel general de filtros de capital fue eliminado; sus selecciones antiguas no afectan los importes.

Cada análisis de capital tiene un solo marco exterior: resumen ejecutivo, calendario, presupuesto/caja, comercial y responsables. Los títulos, controles, gráficos, notas y descargas quedan dentro del marco correspondiente. El calendario mantiene su posición antes del presupuesto y contiene el detalle mensual y los saldos de Costos. Los comparativos de presupuesto y caja usan dos columnas internas separadas por una línea, sin tarjetas exteriores duplicadas. El selector comercial y el criterio de interpretación también pertenecen al marco comercial.

El análisis comercial toma exclusivamente filas de Costos con Costo para producto igual a Aplica (normalizando espacios y mayúsculas). Aprobado, No aplica y las clasificaciones vacías quedan excluidas del subtotal comercial, cobertura, gráficos, composición, trazabilidad y CSV. La opción de incluir partidas sin monto actúa únicamente sobre ese conjunto aplicable. La clasificación comercial proviene de Costos vinculada por ID, aunque Plan publique una columna del mismo nombre; este criterio no elimina actividades del cronograma, presupuesto general ni caja. El piloto sin filas aplicables muestra su estado explícito, sin sugerir que su costo es cero.

Al seleccionar un sistema o hito, el detalle comercial incluye botones visibles de Paquete / línea, con cantidad de partidas y una opción Todos los paquetes. La selección filtra la tabla, su subtotal y el CSV; conserva el orden numérico por ID y la regla exclusiva Aplica de Costos. Los botones se construyen desde las partidas del grupo y respetan la opción de incluir partidas sin monto. La selección se conserva mientras el paquete siga disponible.
