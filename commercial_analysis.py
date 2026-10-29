"""Executive commercial-cost analysis of the historical amounts published in Costos."""
import html
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from capital_charts import amount

COMMERCIAL = 'Comercial anterior'
COLORS = ['#244A6C', '#0F766E', '#2E90A5', '#B7791F', '#718096', '#735D96', '#CBD5E1']


def commercial_breakdown(tasks, dimension):
    """Keep missing amounts missing and reconcile every group to its activity IDs."""
    data = tasks.copy()
    data[dimension] = data[dimension].fillna('').replace('', 'Sin clasificar')
    result = data.groupby(dimension, sort=False, dropna=False).agg(
        **{'Monto comercial · CLP': (COMMERCIAL, lambda values: values.sum(min_count=1)),
           'Partidas informadas': (COMMERCIAL, 'count'), 'Actividades': ('ID', 'size')}
    ).reset_index()
    total = result['Monto comercial · CLP'].sum(min_count=1)
    result['Participación %'] = result['Monto comercial · CLP'] / total * 100 if pd.notna(total) and total > 0 else float('nan')
    result['Cobertura %'] = result['Partidas informadas'] / result['Actividades'] * 100
    return result.sort_values('Monto comercial · CLP', ascending=False, na_position='last', kind='stable')


def commercial_donut(summary, project, total):
    positive = summary[summary['Monto comercial · CLP'].gt(0)].copy()
    if len(positive) > 7:
        other = positive.iloc[6:]['Monto comercial · CLP'].sum()
        positive = pd.concat([positive.iloc[:6], pd.DataFrame({'Sistema': ['Otros sistemas'], 'Monto comercial · CLP': [other]})], ignore_index=True)
    fig = go.Figure(go.Pie(labels=positive['Sistema'], values=positive['Monto comercial · CLP'],
        hole=.76, sort=False, direction='clockwise', textinfo='none',
        marker=dict(colors=COLORS, line=dict(color='#FFFFFF', width=3)),
        customdata=[amount(value) for value in positive['Monto comercial · CLP']],
        hovertemplate='<b>%{label}</b><br>%{customdata} CLP<br>%{percent:.1%} del subtotal<extra></extra>'))
    fig.update_layout(height=300, margin=dict(l=25, r=25, t=15, b=15), showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)', font=dict(family='Arial, sans-serif', color='#0F2435'),
        hoverlabel=dict(bgcolor='#FFFFFF', bordercolor='#D8E3EB', font=dict(size=12, color='#0F2435')),
        annotations=[dict(x=.5, y=.54, text='<b>'+amount(total, True)+'</b>', showarrow=False, font=dict(size=25, color='#0F2435')),
                     dict(x=.5, y=.41, text='Subtotal informado · CLP', showarrow=False, font=dict(size=11, color='#64748B'))])
    return fig, positive


def _summary_table(summary, dimension):
    st.dataframe(summary.style.format({'Monto comercial · CLP': amount, 'Participación %': '{:.1f}%', 'Cobertura %': '{:.1f}%'}, na_rep='Sin informar'),
        hide_index=True, use_container_width=True,
        column_config={dimension: st.column_config.TextColumn(dimension, width='medium'),
            'Monto comercial · CLP': st.column_config.NumberColumn('Monto comercial · CLP', width='medium'),
            'Cobertura %': st.column_config.ProgressColumn('Cobertura de datos', min_value=0, max_value=100, format='%.1f%%')})


def render_commercial_analysis(tasks):
    st.subheader('Costo comercial de los pilotos')
    st.caption('Visión ejecutiva · Costos → Comercial anterior · Se aplican los filtros del análisis de capital.')
    if COMMERCIAL not in tasks:
        st.info('La fuente publicada no contiene la columna Comercial anterior en Costos.')
        return
    st.html('<div class="option-commercial-note"><b>Base comercial histórica</b><span>Los valores representan las partidas informadas en “Comercial anterior”. '
        'Un subtotal con cobertura parcial no determina el costo completo del piloto ni un precio de venta actualizado.</span></div>')
    projects = list(tasks['Proyecto'].dropna().unique())
    projects.sort(key=lambda name: (0 if re.search(r'10\s*k[wW]', name) else 1, name))
    columns = st.columns(min(2, max(1, len(projects))), gap='large')
    for index, project in enumerate(projects):
        scope = tasks[tasks['Proyecto'].eq(project)].copy()
        values = scope[COMMERCIAL]
        total = values.sum(min_count=1)
        known, count = int(values.notna().sum()), len(scope)
        coverage = 100 * known / count if count else 0
        summary = commercial_breakdown(scope, 'Sistema')
        capacity = re.search(r'(10|80)\s*kw', str(project), re.I)
        capacity = int(capacity.group(1)) if capacity else None
        safe_project = html.escape(str(project))
        with columns[index % len(columns)]:
            with st.container(border=True, key=f'option4_commercial_project_{index}'):
                st.html(f'<div class="option-commercial-head"><span>ANÁLISIS COMERCIAL</span><h4>{safe_project}</h4>'
                    f'<p>{known} de {count} partidas con monto · {coverage:.1f}% de cobertura de registros</p></div>')
                if known and values.dropna().ge(0).all() and total > 0:
                    fig, wedges = commercial_donut(summary, project, total)
                    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False}, key=f'option4_commercial_donut_{index}')
                    legend = ''.join(f'<span><i style="background:{COLORS[n % len(COLORS)]}"></i>{html.escape(str(row["Sistema"]))}</span>' for n, (_, row) in enumerate(wedges.iterrows()))
                    st.html('<div class="option-commercial-legend">'+legend+'</div>')
                else:
                    reason = 'Sin montos comerciales informados' if not known else 'Sin distribución positiva' if not values.lt(0).any() else 'Hay ajustes negativos en la fuente'
                    st.html('<div class="option-commercial-empty"><div>—</div><b>'+reason+'</b><span>Consulta el detalle de partidas. El donut requiere montos no negativos y un subtotal positivo.</span></div>')
                    st.html('<div class="option-commercial-legend">Distribución por sistema pendiente de datos graficables.</div>')
                unit = amount(total / capacity) if capacity and pd.notna(total) else 'Sin informar'
                unit_label = 'Subtotal por kW' if known < count else 'Monto por kW'
                st.html('<div class="option-commercial-metrics">'
                    f'<div><span>Subtotal comercial · CLP</span><b>{amount(total)}</b></div>'
                    f'<div><span>{unit_label} · CLP/kW</span><b>{unit}</b></div>'
                    f'<div><span>Partidas sin monto</span><b>{count-known}</b></div></div>')
                if known:
                    leader = summary.dropna(subset=['Monto comercial · CLP']).iloc[0]
                    share = leader['Participación %']
                    share_text = f' ({share:.1f}% del subtotal)' if pd.notna(share) else ''
                    st.html('<div class="option-commercial-reading"><b>Mayor concentración</b><p>'+html.escape(str(leader['Sistema']))
                        +' · '+amount(leader['Monto comercial · CLP'])+share_text+'.</p></div>')
                else:
                    st.caption('Pendiente de completar Comercial anterior en Costos para calcular este piloto. No se extrapolan los montos del piloto de 10 kW.')
                with st.expander('Composición por sistema e hito', expanded=False):
                    system_tab, milestone_tab = st.tabs(['Por sistema', 'Por hito'])
                    with system_tab:
                        _summary_table(summary, 'Sistema')
                    with milestone_tab:
                        _summary_table(commercial_breakdown(scope, 'Hito objetivo'), 'Hito objetivo')
                with st.expander('Trazabilidad de partidas · Costos'):
                    fields = ['ID', 'Actividad / entregable', 'Hito objetivo', 'Sistema', 'Paquete / línea', COMMERCIAL, 'Presupuesto vigente', 'Sustento / observaciones']
                    detail = scope[[field for field in fields if field in scope]].sort_values(COMMERCIAL, ascending=False, na_position='last', kind='stable')
                    st.dataframe(detail.style.format({field: amount for field in [COMMERCIAL, 'Presupuesto vigente'] if field in detail}, na_rep='Sin informar'),
                        hide_index=True, use_container_width=True, height=350,
                        column_config={'Actividad / entregable': st.column_config.TextColumn(width='large')})
                    st.download_button('Descargar análisis comercial · CSV', detail.to_csv(index=False).encode('utf-8-sig'),
                        file_name=f'costo_comercial_{index+1}.csv', mime='text/csv', key=f'option4_commercial_download_{index}')
    with st.expander('Cómo interpretar el costo comercial'):
        st.markdown('El subtotal suma **Comercial anterior** una sola vez por ID de actividad, vinculado desde **Costos** a **Plan**. '
            'La cobertura mide registros con monto respecto de las actividades seleccionadas; no mide cuánto presupuesto está cubierto. '
            'Los ceros explícitos cuentan como informados y los vacíos se conservan como faltantes. '
            'El donut distribuye el subtotal informado por sistema. El indicador por kW divide ese mismo subtotal por la potencia nominal del proyecto; '
            'con información parcial también es parcial. Estos montos se presentan separados de la caja pendiente y no se suman al calendario de desembolsos.')
