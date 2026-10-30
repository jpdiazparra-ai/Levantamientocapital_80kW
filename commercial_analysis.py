"""Executive commercial-cost analysis of the historical amounts published in Costos."""
import html
import hashlib
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from capital_charts import amount

COMMERCIAL = 'Comercial anterior'
COLORS = ['#244A6C', '#0F766E', '#2E90A5', '#B7791F', '#718096', '#735D96', '#CBD5E1']
VARIATION_HELP = '(Presupuesto vigente − Monto comercial) / Monto comercial × 100. Positivo: presupuesto superior al comercial. Sin cálculo si falta un monto o el comercial es cero.'


def commercial_budget_variation(frame):
    commercial = pd.to_numeric(frame[COMMERCIAL], errors='coerce')
    budget = pd.to_numeric(frame['Presupuesto vigente'], errors='coerce')
    return (budget - commercial).div(commercial.where(commercial.ne(0))) * 100


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
        hole=.69, sort=False, direction='clockwise', rotation=90,
        text=[f'{value/total:.1%}'.replace('.', ',') if value/total >= .04 else '' for value in positive['Monto comercial · CLP']],
        textinfo='text', textposition='inside', textfont=dict(size=14, color='#FFFFFF'),
        marker=dict(colors=COLORS, line=dict(color='#FFFFFF', width=3)),
        customdata=[amount(value) for value in positive['Monto comercial · CLP']],
        hovertemplate='<b>%{label}</b><br>%{customdata} CLP<br>%{percent:.1%} del subtotal<extra></extra>'))
    fig.update_layout(height=340, margin=dict(l=14, r=14, t=20, b=20), showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)', font=dict(family='Arial, sans-serif', color='#0F2435'),
        hoverlabel=dict(bgcolor='#FFFFFF', bordercolor='#D8E3EB', font=dict(size=12, color='#0F2435')),
        annotations=[dict(x=.5, y=.53, text='<b>'+amount(total, True)+'</b>', showarrow=False, font=dict(size=27, color='#0F2435')),
                     dict(x=.5, y=.42, text='COMERCIAL INFORMADO', showarrow=False, font=dict(size=10, color='#64748B'))])
    return fig, positive


def commercial_system_ranking(summary, total, wedges):
    """Use the donut's colors while keeping every system's exact amount visible."""
    colors = dict(zip(wedges['Sistema'], COLORS))
    rows = []
    known = summary[summary['Monto comercial · CLP'].notna()]
    for _, row in known.iterrows():
        value = row['Monto comercial · CLP']
        share = value / total * 100 if total > 0 else float('nan')
        label = f'{share:.1f}%'.replace('.', ',') if pd.notna(share) else '—'
        width = min(100, max(0, share)) if pd.notna(share) else 0
        color = colors.get(row['Sistema'], COLORS[-1])
        rows.append('<div class="option-commercial-system">'
            f'<div class="option-commercial-system-label"><i style="background:{color}"></i><b>{html.escape(str(row["Sistema"]))}</b>'
            f'<small>{int(row["Partidas informadas"])} partidas con monto</small></div>'
            f'<div class="option-commercial-system-value"><b>{amount(value)}</b><span>{label}</span></div>'
            f'<div class="option-commercial-system-track"><i style="width:{width:.3f}%;background:{color}"></i></div></div>')
    return '<div class="option-commercial-ranking"><div class="option-commercial-ranking-head"><b>Composición del costo por sistema</b><span>MONTO CLP / PARTICIPACIÓN</span></div>'+''.join(rows)+'</div>'


def commercial_group_details(scope, dimension, group, include_missing=False):
    labels = scope[dimension].fillna('').replace('', 'Sin clasificar')
    details = scope[labels.eq(group)].copy()
    if not include_missing:
        details = details[details[COMMERCIAL].notna()]
    return details.sort_values('ID', kind='stable', key=lambda ids:
        ids.astype(str).str.casefold().str.replace(r'\d+', lambda match: match.group().zfill(20), regex=True))


def _summary_table(summary, dimension, scope, key):
    # Keep a selected row tied to the same scope and displayed group order.
    identity = repr((scope['ID'].tolist(), summary[dimension].tolist())).encode('utf-8')
    key += '_' + hashlib.sha1(identity).hexdigest()[:10]
    st.caption('Selecciona una fila para ver las partidas que componen su monto comercial.')
    event = st.dataframe(summary.style.format({'Monto comercial · CLP': amount, 'Participación %': '{:.1f}%', 'Cobertura %': '{:.1f}%'}, na_rep='Sin informar'),
        hide_index=True, use_container_width=True,
        key=key, on_select='rerun', selection_mode='single-row',
        column_config={dimension: st.column_config.TextColumn(dimension, width='medium'),
            'Monto comercial · CLP': st.column_config.NumberColumn('Monto comercial · CLP', width='medium'),
            'Cobertura %': st.column_config.ProgressColumn('Cobertura de datos', min_value=0, max_value=100, format='%.1f%%')})
    selected = event['selection']['rows']
    if not selected or selected[0] >= len(summary):
        return
    group = summary.iloc[selected[0]][dimension]
    group_key = key + '_' + str(group)
    include_missing = st.checkbox('Incluir partidas sin monto comercial', key=group_key+'_missing')
    details = commercial_group_details(scope, dimension, group, include_missing)
    st.html('<div class="option-commercial-reading"><b>'+html.escape(str(group))+'</b>'
        f'<p>{len(details)} partidas · Subtotal comercial: {amount(details[COMMERCIAL].sum(min_count=1))}</p></div>')
    if details.empty:
        st.info('Este grupo no tiene partidas con monto comercial informado. Activa la opción anterior para revisar sus actividades pendientes de monto.')
        return
    if 'Unidades' not in details:
        details['Unidades'] = pd.NA
    details['Unidades'] = details['Unidades'].replace('', pd.NA)
    details['Variación %'] = commercial_budget_variation(details)
    fields = ['ID', 'Actividad / entregable', 'Unidades', 'Sistema', 'Hito objetivo', 'Paquete / línea', COMMERCIAL, 'Presupuesto vigente', 'Variación %']
    details = details[[field for field in fields if field in details]].rename(columns={'Unidades': 'Cantidad'})
    st.dataframe(details.style.format({**{field: amount for field in [COMMERCIAL, 'Presupuesto vigente'] if field in details},
            'Variación %': lambda value: f'{value:+.1f}%'.replace('.', ',')}, na_rep='Sin informar'),
        hide_index=True, use_container_width=True, height=min(460, 38+len(details)*35),
        column_config={'ID': st.column_config.TextColumn(width='small'),
            'Actividad / entregable': st.column_config.TextColumn(width='large'),
            'Cantidad': st.column_config.TextColumn(width='small', help='Unidades de Plan (columna G), vinculadas por ID de actividad.'),
            COMMERCIAL: st.column_config.NumberColumn('Monto comercial · CLP', width='medium'),
            'Presupuesto vigente': st.column_config.NumberColumn('Presupuesto vigente · CLP', width='medium', help='Presupuesto vigente de Costos, vinculado por ID de actividad.'),
            'Variación %': st.column_config.NumberColumn('Variación %', width='small', help=VARIATION_HELP)})
    st.caption('Variación respecto del monto comercial: positivo = presupuesto mayor; negativo = presupuesto menor. Sin cálculo cuando el comercial es cero o falta un monto.')
    st.download_button('Descargar partidas seleccionadas · CSV', details.to_csv(index=False).encode('utf-8-sig'),
        file_name='partidas_comerciales_seleccionadas.csv', mime='text/csv', key=group_key+'_download')


def render_commercial_analysis(tasks):
    with st.container(border=True, key='option4_analysis_commercial'):
        st.subheader('Costo comercial de los pilotos')
        st.caption('Visión ejecutiva · Costos → Comercial anterior · Comparación por piloto y composición por sistema.')
        if COMMERCIAL not in tasks:
            st.info('La fuente publicada no contiene la columna Comercial anterior en Costos.')
            return
        st.html('<div class="option-commercial-note"><b>Base comercial histórica</b><span>Los valores representan las partidas informadas en “Comercial anterior”. '
            'Un subtotal con cobertura parcial no determina el costo completo del piloto ni un precio de venta actualizado.</span></div>')
        projects = list(tasks['Proyecto'].dropna().unique())
        projects.sort(key=lambda name: (0 if re.search(r'10\s*k[wW]', name) else 1, name))
        if not projects:
            st.info('No hay proyectos para la selección de capital.')
            return
        project_key = 'option4_commercial_project_select'
        if project_key in st.session_state and st.session_state[project_key] not in projects:
            st.session_state[project_key] = projects[0]
        project = st.selectbox('Piloto del análisis comercial', projects, key=project_key,
            help='Alterna los pilotos de 10 kW y 80 kW para revisar sus montos comerciales y partidas.')
        index = re.sub(r'\W+', '_', str(project))
        scope = tasks[tasks['Proyecto'].eq(project)].copy()
        values = scope[COMMERCIAL]
        total = values.sum(min_count=1)
        known, count = int(values.notna().sum()), len(scope)
        coverage = 100 * known / count if count else 0
        summary = commercial_breakdown(scope, 'Sistema')
        capacity = re.search(r'(10|80)\s*kw', str(project), re.I)
        capacity = int(capacity.group(1)) if capacity else None
        safe_project = html.escape(str(project))
        nonnegative = values.dropna().ge(0).all()
        can_draw = known > 0 and nonnegative and total > 0
        funded_systems = int(summary['Monto comercial · CLP'].notna().sum())
        concentration_count = min(3, funded_systems)
        concentration = summary['Monto comercial · CLP'].head(concentration_count).sum(min_count=1) / total * 100 if can_draw else float('nan')
        concentration_label = f'{concentration:.1f}%'.replace('.', ',') if pd.notna(concentration) else 'Sin informar'
        unit = amount(total / capacity) if capacity and pd.notna(total) else 'Sin informar'
        unit_label = 'Subtotal por kW' if known < count else 'Monto por kW'
        with st.container(border=False, key=f'option4_commercial_project_{index}'):
            st.html(f'<div class="option-commercial-executive-head"><div><span>ANÁLISIS COMERCIAL</span><h4>{safe_project}</h4></div>'
                '<span class="option-commercial-source">Costos · Comercial anterior</span></div>'
                '<div class="option-commercial-executive-kpis">'
                f'<article class="primary"><span>Subtotal comercial · CLP</span><strong>{amount(total)}</strong><small>{known} partidas con monto informado</small></article>'
                f'<article><span>{unit_label} · CLP/kW</span><strong>{unit}</strong><small>Potencia nominal: {capacity if capacity else "sin informar"} kW · base histórica</small></article>'
                f'<article><span>Cobertura de registros</span><strong>{coverage:.1f}%</strong><small>{known} de {count} partidas · {count-known} sin monto</small>'
                f'<div class="option-commercial-coverage-track"><i style="width:{coverage:.3f}%"></i></div></article>'
                f'<article><span>Concentración en {concentration_count or 3} sistemas</span><strong>{concentration_label}</strong><small>{funded_systems} sistemas con monto informado</small></article></div>')
            donut_col, detail_col = st.columns([.85, 1.3], gap='large')
            with donut_col:
                if can_draw:
                    fig, wedges = commercial_donut(summary, project, total)
                    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False}, key=f'option4_commercial_donut_{index}')
                    st.html('<div class="option-commercial-chart-note">Participación sobre el subtotal informado · Detalle completo a la derecha</div>')
                else:
                    reason = 'Sin montos comerciales informados' if not known else 'Sin distribución positiva' if nonnegative else 'Hay ajustes negativos en la fuente'
                    st.html('<div class="option-commercial-empty"><div>—</div><b>'+reason+'</b><span>Consulta el detalle de partidas. El donut requiere montos no negativos y un subtotal positivo.</span></div>')
            with detail_col:
                if known:
                    if not can_draw:
                        wedges = pd.DataFrame(columns=['Sistema'])
                    st.html(commercial_system_ranking(summary, total, wedges))
                else:
                    st.html('<div class="option-commercial-pending"><span>DATOS PENDIENTES</span><b>Completar la base comercial del piloto</b>'
                        f'<p>Hay {count} actividades sin monto comercial informado. Al completar Comercial anterior en Costos y actualizar el panel, aparecerán aquí los montos y su distribución.</p></div>')
            if can_draw:
                st.html('<div class="option-commercial-insight"><span>LECTURA EJECUTIVA</span>'
                    f'<p>Los {concentration_count} sistemas de mayor monto concentran <b>{concentration_label}</b> del subtotal. '
                    f'La cobertura es de <b>{coverage:.1f}% de los registros</b>; '
                    + ('el costo completo del piloto sigue pendiente de completar.' if known < count else 'todas las actividades seleccionadas tienen monto informado.') + '</p></div>')
            with st.expander('Composición por sistema e hito', expanded=False):
                system_tab, milestone_tab = st.tabs(['Por sistema', 'Por hito'])
                with system_tab:
                    _summary_table(summary, 'Sistema', scope, f'option4_commercial_system_{index}')
                with milestone_tab:
                    _summary_table(commercial_breakdown(scope, 'Hito objetivo'), 'Hito objetivo', scope, f'option4_commercial_milestone_{index}')
            with st.expander('Trazabilidad de partidas · Costos'):
                fields = ['ID', 'Actividad / entregable', 'Hito objetivo', 'Unidades', 'Sistema', 'Paquete / línea', COMMERCIAL, 'Presupuesto vigente']
                detail = scope.reindex(columns=fields).sort_values(COMMERCIAL, ascending=False, na_position='last', kind='stable')
                detail = detail.rename(columns={'Unidades': 'Cantidad'})
                detail['Variación %'] = commercial_budget_variation(detail)
                st.dataframe(detail.style.format({**{field: amount for field in [COMMERCIAL, 'Presupuesto vigente'] if field in detail},
                        'Variación %': lambda value: f'{value:+.1f}%'.replace('.', ',')}, na_rep='Sin informar'),
                    hide_index=True, use_container_width=True, height=350,
                    column_config={'Actividad / entregable': st.column_config.TextColumn(width='large'),
                        'Cantidad': st.column_config.TextColumn(width='small', help='Unidades de Plan (columna G), vinculadas por ID de actividad.'),
                        'Presupuesto vigente': st.column_config.NumberColumn('Presupuesto vigente · CLP', width='medium', help='Presupuesto vigente de Costos, vinculado por ID de actividad.'),
                        'Variación %': st.column_config.NumberColumn('Variación %', width='small', help=VARIATION_HELP)})
                st.download_button('Descargar análisis comercial · CSV', detail.to_csv(index=False).encode('utf-8-sig'),
                    file_name=f'costo_comercial_{index}.csv', mime='text/csv', key=f'option4_commercial_download_{index}')
        with st.expander('Cómo interpretar el costo comercial'):
            st.markdown('El subtotal suma **Comercial anterior** una sola vez por ID de actividad, vinculado desde **Costos** a **Plan**. '
                'La cobertura mide registros con monto respecto de las actividades seleccionadas; no mide cuánto presupuesto está cubierto. '
                'Los ceros explícitos cuentan como informados y los vacíos se conservan como faltantes. '
                'El donut distribuye el subtotal informado por sistema. El indicador por kW divide ese mismo subtotal por la potencia nominal del proyecto; '
                'con información parcial también es parcial. Estos montos se presentan separados de la caja pendiente y no se suman al calendario de desembolsos.')
