"""Executive commercial-cost analysis of the historical amounts published in Costos."""
import html
import hashlib
import re
import unicodedata

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from capital_charts import amount
from display_currency import currency_label, currency_code, currency_export

COMMERCIAL = 'Comercial anterior'
COLORS = ['#244A6C', '#0F766E', '#2E90A5', '#B7791F', '#718096', '#735D96', '#CBD5E1']
VARIATION_HELP = '(Presupuesto vigente − Monto comercial) / Monto comercial × 100. Positivo: presupuesto superior al comercial. Sin cálculo si falta un monto o el comercial es cero.'


def commercial_budget_variation(frame):
    commercial = pd.to_numeric(frame[COMMERCIAL], errors='coerce')
    budget = pd.to_numeric(frame['Presupuesto vigente'], errors='coerce')
    return (budget - commercial).div(commercial.where(commercial.ne(0))) * 100


def commercial_unit_cost(frame):
    return pd.to_numeric(frame['Presupuesto referencia'], errors='coerce')


def commercial_quantities(frame):
    # Costos owns the quantities behind the displayed financial amounts.
    # Keep Plan units only for workbooks predating the Cantidad column.
    if 'Cantidad' in frame:
        return frame['Cantidad']
    return frame.get('Unidades', pd.Series(float('nan'), index=frame.index))


def commercial_product_scope(tasks):
    classification = tasks['Costo para producto'].fillna('').astype(str).str.strip().str.casefold()
    return tasks[classification.eq('aplica')].copy()


def commercial_project_rows(tasks, project):
    capacity = re.search(r'(10|80)\s*kw', str(project), re.I)
    if capacity and '_cost_hito_objetivo' in tasks:
        hitos = tasks['_cost_hito_objetivo'].fillna('').astype(str)
        selected = tasks[hitos.str.contains(rf'(?<!\d){capacity.group(1)}\s*kw\b', case=False, regex=True)].copy()
        selected['Hito objetivo'] = selected['_cost_hito_objetivo']
        return selected
    return tasks[tasks['Proyecto'].eq(project)].copy()


def commercial_composition_scope(tasks, mode):
    if mode == 'Total':
        return tasks.copy()
    def normalize(value):
        text = unicodedata.normalize('NFKD', str(value))
        return ' '.join(''.join(char for char in text if not unicodedata.combining(char)).casefold().split())
    excluded = {'fundaciones y anclajes', 'montaje', 'montaje y logistica', 'logistica y montaje'}
    systems = tasks['Sistema'].fillna('').map(normalize)
    return tasks[~systems.isin(excluded)].copy()


def commercial_hour_values(frame):
    criteria = frame.get('Criterio', pd.Series('', index=frame.index)).fillna('').astype(str)
    is_hh = criteria.str.replace(r'[\s.]', '', regex=True).str.casefold().eq('hh')
    quantities = commercial_quantities(frame).map(lambda value:
        value.strip().replace('\u00a0', '').replace(' ', '').replace('.', '').replace(',', '.')
        if isinstance(value, str) else value)
    quantities = pd.to_numeric(quantities, errors='coerce')
    return quantities.where(is_hh & quantities.ge(0)), is_hh


def commercial_selection_totals(frame):
    hours, is_hh = commercial_hour_values(frame)
    return {
        'HH': hours.sum(min_count=1) if is_hh.any() else 0,
        'HH pendientes': int((is_hh & hours.isna()).sum()),
        COMMERCIAL: frame[COMMERCIAL].sum(min_count=1),
        'Presupuesto vigente': pd.to_numeric(frame.get('Presupuesto vigente', pd.Series(float('nan'), index=frame.index)), errors='coerce').sum(min_count=1),
    }


def commercial_participations(frame, project_scope):
    result = frame.copy()
    amounts = pd.to_numeric(result[COMMERCIAL], errors='coerce')
    packages = result['Paquete / línea'].fillna('').astype(str).str.strip()
    systems = result.get('Sistema', pd.Series('', index=result.index)).fillna('').astype(str).str.strip()
    package_totals = amounts.groupby([systems, packages], dropna=False).transform(lambda values: values.sum(min_count=1))
    project_total = pd.to_numeric(project_scope[COMMERCIAL], errors='coerce').sum(min_count=1)
    result['% del paquete'] = amounts.div(package_totals.where(package_totals.gt(0))) * 100
    result['% del proyecto'] = amounts / project_total * 100 if pd.notna(project_total) and project_total > 0 else float('nan')
    return result


def commercial_breakdown(tasks, dimension):
    """Keep missing amounts missing and reconcile every group to its activity IDs."""
    data = tasks.copy()
    data[dimension] = data[dimension].fillna('').replace('', 'Sin clasificar')
    data['_hh'], data['_is_hh'] = commercial_hour_values(data)
    data['_non_commercial'] = pd.to_numeric(data.get('Presupuesto vigente', pd.Series(float('nan'), index=data.index)), errors='coerce')
    result = data.groupby(dimension, sort=False, dropna=False).agg(
        **{'Monto comercial · CLP': (COMMERCIAL, lambda values: values.sum(min_count=1)),
           'Monto no comercial · CLP': ('_non_commercial', lambda values: values.sum(min_count=1)),
           'Partidas informadas': (COMMERCIAL, 'count'), 'Actividades': ('ID', 'size'),
           'HH': ('_hh', lambda values: values.sum(min_count=1)),
           '_hh_activities': ('_is_hh', 'sum')}
    ).reset_index()
    # No HH activities means zero hours; HH activities without quantities remain unknown.
    result['HH'] = result['HH'].mask(result['_hh_activities'].eq(0), 0)
    result = result.drop(columns='_hh_activities')
    total = result['Monto comercial · CLP'].sum(min_count=1)
    result['Participación %'] = result['Monto comercial · CLP'] / total * 100 if pd.notna(total) and total > 0 else float('nan')
    result['Cobertura %'] = result['Partidas informadas'] / result['Actividades'] * 100
    return result.sort_values('Monto comercial · CLP', ascending=False, na_position='last', kind='stable')


def commercial_summary_with_total(summary, dimension, scope):
    totals = commercial_selection_totals(scope)
    count = len(scope)
    known = int(scope[COMMERCIAL].notna().sum())
    total_row = {
        dimension: 'TOTAL',
        'Monto comercial · CLP': totals[COMMERCIAL],
        'Monto no comercial · CLP': totals['Presupuesto vigente'],
        'Partidas informadas': known,
        'Actividades': count,
        'HH': totals['HH'],
        'Participación %': 100.0 if pd.notna(totals[COMMERCIAL]) and totals[COMMERCIAL] > 0 else float('nan'),
        'Cobertura %': known / count * 100 if count else float('nan'),
    }
    return pd.concat([summary, pd.DataFrame([total_row])], ignore_index=True)


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
        hovertemplate='<b>%{label}</b><br>%{customdata} '+currency_code()+'<br>%{percent:.1%} del subtotal<extra></extra>'))
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
    return '<div class="option-commercial-ranking"><div class="option-commercial-ranking-head"><b>Composición del costo por sistema</b><span>MONTO '+currency_code()+' / PARTICIPACIÓN</span></div>'+''.join(rows)+'</div>'


def commercial_group_details(scope, dimension, group, include_missing=False):
    labels = scope[dimension].fillna('').replace('', 'Sin clasificar')
    details = scope[labels.eq(group)].copy()
    if not include_missing:
        details = details[details[COMMERCIAL].notna()]
    return details.sort_values('ID', kind='stable', key=lambda ids:
        ids.astype(str).str.casefold().str.replace(r'\d+', lambda match: match.group().zfill(20), regex=True))


def _summary_table(summary, dimension, scope, key, project_scope=None):
    project_scope = scope if project_scope is None else project_scope
    # Remember the group by name rather than its row number: amounts and IDs
    # can change during refresh, resetting the dataframe's native selection.
    selection_key = key + '_selected_group'
    group_base_key = key
    identity = repr((scope['ID'].tolist(), summary[dimension].tolist())).encode('utf-8')
    key += '_' + hashlib.sha1(identity).hexdigest()[:10]
    groups = summary[dimension].tolist()
    def remember_group():
        rows = st.session_state[key]['selection']['rows']
        st.session_state[selection_key] = groups[rows[0]] if rows and rows[0] < len(groups) else None
    st.caption('Selecciona una fila para ver las partidas que componen su monto comercial.')
    display_summary = commercial_summary_with_total(summary, dimension, scope)
    styled_summary = display_summary.style.format({'Monto comercial · CLP': amount, 'Monto no comercial · CLP': amount, 'HH': lambda value: f'{value:,.1f}'.replace(',', 'X').replace('.', ',').replace('X', '.'), 'Participación %': '{:.1f}%', 'Cobertura %': '{:.1f}%'}, na_rep='Sin informar')
    styled_summary = styled_summary.set_properties(subset=pd.IndexSlice[[display_summary.index[-1]], :], **{'background-color': '#E8F3F0', 'color': '#0F4D46'})
    event = st.dataframe(styled_summary,
        hide_index=True, use_container_width=True,
        key=key, on_select=remember_group, selection_mode='single-row',
        column_config={dimension: st.column_config.TextColumn(dimension, width='medium'),
            'Monto comercial · CLP': st.column_config.NumberColumn(currency_label('Monto comercial · CLP'), width='medium'),
            'Monto no comercial · CLP': st.column_config.NumberColumn(currency_label('Monto no comercial · CLP'), width='medium', help='Suma de Presupuesto vigente de Costos para las partidas incluidas en este sistema o hito, en la moneda seleccionada.'),
            'HH': st.column_config.NumberColumn('HH', width='small', help='Horas-hombre informadas: suma de Cantidad de Costos solo para partidas con criterio HH, tengan o no monto comercial. Las cantidades faltantes no se estiman; no incluye insumos.'),
            'Cobertura %': st.column_config.ProgressColumn('Cobertura de datos', min_value=0, max_value=100, format='%.1f%%')})
    selected = event['selection']['rows']
    if selection_key not in st.session_state and selected and selected[0] < len(summary):
        st.session_state[selection_key] = groups[selected[0]]
    group = st.session_state.get(selection_key)
    if group not in groups:
        return
    group_key = group_base_key + '_' + str(group)
    include_missing = st.checkbox('Incluir partidas sin monto comercial', key=group_key+'_missing')
    details = commercial_group_details(scope, dimension, group, include_missing)
    if details.empty:
        st.info('Este grupo no tiene partidas con monto comercial informado. Activa la opción anterior para revisar sus actividades pendientes de monto.')
        return
    packages = details['Paquete / línea'].fillna('').astype(str).str.strip().replace('', 'Sin paquete')
    package_counts = packages.value_counts()
    package_total = len(details)
    all_packages = 'Todos los paquetes'
    options = [all_packages, *sorted(package_counts.index, key=str.casefold)]
    package_key = group_key + '_package'
    remembered_package = st.session_state.get(package_key, all_packages)
    # Counts are part of the button labels and can change the widget identity.
    # Explicitly carry the current choice into that newly rendered widget.
    st.session_state[package_key] = remembered_package if remembered_package in options else all_packages
    with st.container(key=group_key+'_package_controls'):
        package = st.segmented_control('Paquete / línea de las partidas', options,
            key=package_key, selection_mode='single', width='stretch',
            format_func=lambda value: f'{value} ({package_total if value == all_packages else package_counts[value]})',
            help='Selecciona un paquete para reducir las partidas. Todos los paquetes muestra el sistema o hito completo.')
    if package and package != all_packages:
        details = details[packages.eq(package)].copy()
    selection_label = str(group) + (' · ' + package if package and package != all_packages else ' · Todos los paquetes')
    st.html('<div class="option-commercial-reading"><b>'+html.escape(selection_label)+'</b>'
        f'<p>{len(details)} partidas en la selección</p></div>')
    totals = commercial_selection_totals(details)
    hours_label = 'Sin informar' if pd.isna(totals['HH']) else f'{totals["HH"]:,.2f}'.rstrip('0').rstrip('.').replace(',', 'X').replace('.', ',').replace('X', '.') + ' HH'
    hours_note = f'{totals["HH pendientes"]} partidas HH sin cantidad informada' if totals['HH pendientes'] else 'Solo partidas con criterio HH'
    st.html('<div class="option-commercial-package-totals">'
        f'<article class="hours"><span>Total HH informadas</span><strong>{hours_label}</strong><small>{hours_note}</small></article>'
        f'<article class="commercial"><span>Total monto comercial · {currency_code()}</span><strong>{amount(totals[COMMERCIAL])}</strong><small>Suma de las partidas visibles</small></article>'
        f'<article class="budget"><span>Total presupuesto vigente · {currency_code()}</span><strong>{amount(totals["Presupuesto vigente"])}</strong><small>Suma de las partidas visibles</small></article></div>')
    details['Unidades'] = commercial_quantities(details)
    details['Unidades'] = details['Unidades'].replace('', pd.NA)
    details['Costo por unidad · CLP'] = commercial_unit_cost(details)
    details = commercial_participations(details, project_scope)
    details['Variación %'] = commercial_budget_variation(details)
    fields = ['ID', 'Actividad / entregable', 'Criterio', 'Unidades', 'Costo por unidad · CLP', 'Paquete / línea', COMMERCIAL, 'Presupuesto vigente', '% del paquete', '% del proyecto', 'Variación %']
    details = details.reindex(columns=fields).rename(columns={'Unidades': 'Cantidad'})
    st.dataframe(details.style.format({**{field: amount for field in [COMMERCIAL, 'Presupuesto vigente', 'Costo por unidad · CLP'] if field in details},
            '% del paquete': lambda value: f'{value:.2f}%'.replace('.', ','),
            '% del proyecto': lambda value: f'{value:.2f}%'.replace('.', ','),
            'Variación %': lambda value: f'{value:+.1f}%'.replace('.', ',')}, na_rep='Sin informar')
            .set_properties(subset=[COMMERCIAL], **{'background-color': '#FFF1ED', 'color': '#9F3A28'}),
        hide_index=True, use_container_width=True, row_height=72, height=min(460, 40+len(details)*72),
        column_config={'ID': st.column_config.TextColumn(width='small'),
            'Actividad / entregable': st.column_config.TextColumn(width='large'),
            'Criterio': st.column_config.TextColumn(width='small', help='Criterio de Plan (columna G), vinculado por ID de actividad.'),
            'Cantidad': st.column_config.TextColumn(width='small', help='Cantidad de Costos, vinculada por ID de actividad.'),
            'Costo por unidad · CLP': st.column_config.NumberColumn(currency_label('Costo por unidad · CLP'), width='medium', help='Valor de Presupuesto referencia de Costos, vinculado por ID de actividad. Se muestra directamente como costo por unidad.'),
            COMMERCIAL: st.column_config.NumberColumn(currency_label('Monto comercial · CLP'), width='medium'),
            'Presupuesto vigente': st.column_config.NumberColumn(currency_label('Presupuesto vigente · CLP'), width='medium', help='Presupuesto vigente de Costos, vinculado por ID de actividad.'),
            '% del paquete': st.column_config.NumberColumn(width='small', help='Monto comercial del ID ÷ total comercial de su paquete, dentro del sistema o hito de esta selección × 100.'),
            '% del proyecto': st.column_config.NumberColumn(width='small', help='Monto comercial del ID ÷ total comercial del piloto completo seleccionado × 100. Considera las partidas Aplica de Costos y no cambia al filtrar sistema o paquete.'),
            'Variación %': st.column_config.NumberColumn('Variación %', width='small', help=VARIATION_HELP)})
    st.caption('Participación del ID sobre el monto comercial de su paquete y del piloto completo seleccionado. Los porcentajes se calculan con importes informados; no se calculan si el total es cero o falta información.')
    st.caption('Variación respecto del monto comercial: positivo = presupuesto mayor; negativo = presupuesto menor. Sin cálculo cuando el comercial es cero o falta un monto.')
    st.download_button('Descargar partidas seleccionadas · CSV', currency_export(details).to_csv(index=False).encode('utf-8-sig'),
        file_name='partidas_comerciales_seleccionadas.csv', mime='text/csv', key=group_key+'_download')


def render_commercial_analysis(tasks):
    with st.container(border=True, key='option4_analysis_commercial'):
        st.subheader('Costo comercial de los pilotos')
        st.caption('Analiza el monto comercial informado para cada piloto y su composición por sistema y paquete. Se incluyen solo las partidas marcadas Aplica en Costos; el detalle permite contrastar cantidades, costos de referencia y presupuesto vigente.')
        if COMMERCIAL not in tasks:
            st.info('La fuente publicada no contiene la columna Comercial anterior en Costos.')
            return
        if 'Costo para producto' not in tasks:
            st.info('Falta Costo para producto en Costos para identificar las partidas aplicables al análisis comercial.')
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
        def select_project():
            selected = re.sub(r'\W+', '_', str(st.session_state[project_key]))
            st.session_state[f'option4_commercial_composition_{selected}'] = 'Total'
        project = st.selectbox('Piloto del análisis comercial', projects, key=project_key,
            on_change=select_project,
            help='Alterna los pilotos de 10 kW y 80 kW para revisar sus montos comerciales y partidas.')
        index = re.sub(r'\W+', '_', str(project))
        project_tasks = commercial_project_rows(tasks, project)
        project_scope = commercial_product_scope(project_tasks)
        composition_key = f'option4_commercial_composition_{index}'
        remembered_mode = st.session_state.get(composition_key, 'Total')
        mode = remembered_mode if remembered_mode in ('Total', 'Comercial') else 'Total'
        st.session_state[composition_key] = mode
        mode = st.segmented_control('Alcance del análisis', ['Total', 'Comercial'], key=composition_key,
            help='Controla el gráfico y las tablas: Comercial excluye Fundaciones y anclajes y Montaje y Logística. Los KPI superiores conservan el total del piloto completo.') or 'Total'
        scope = commercial_composition_scope(project_scope, mode)
        excluded = len(project_tasks) - len(project_scope)
        mode_note = f' · Vista Comercial: {len(scope)} partidas, con {len(project_scope) - len(scope)} excluidas del gráfico y detalle' if mode == 'Comercial' else ''
        st.caption(f'Piloto completo: {len(project_scope)} partidas Aplica · {excluded} excluidas por su clasificación en Costos.{mode_note}')
        values = scope[COMMERCIAL]
        total = values.sum(min_count=1)
        project_values = project_scope[COMMERCIAL]
        project_total = project_values.sum(min_count=1)
        project_known, project_count = int(project_values.notna().sum()), len(project_scope)
        project_coverage = 100 * project_known / project_count if project_count else 0
        project_summary = commercial_breakdown(project_scope, 'Sistema')
        project_systems = int(project_summary['Monto comercial · CLP'].notna().sum())
        project_top_count = min(3, project_systems)
        project_concentration = project_summary['Monto comercial · CLP'].head(project_top_count).sum(min_count=1) / project_total * 100 if pd.notna(project_total) and project_total > 0 else float('nan')
        project_concentration_label = f'{project_concentration:.1f}%'.replace('.', ',') if pd.notna(project_concentration) else 'Sin informar'
        if mode == 'Comercial':
            excluded_scope = project_scope[~project_scope['ID'].isin(scope['ID'])]
            excluded_amount = excluded_scope[COMMERCIAL].sum(min_count=1) if len(excluded_scope) else 0
            st.html('<div class="option-commercial-note"><b>El gráfico Comercial excluye fundaciones y montaje</b>'
                f'<span>Total comercial del piloto: <b>{amount(project_scope[COMMERCIAL].sum(min_count=1))}</b>'
                f' · Fuera del gráfico Comercial: <b>{amount(excluded_amount)}</b>'
                f' · Subtotal del gráfico: <b>{amount(total)}</b>.</span></div>')
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
        unit = amount(project_total / capacity) if capacity and pd.notna(project_total) else 'Sin informar'
        unit_label = 'Subtotal del piloto por kW' if project_known < project_count else 'Monto del piloto por kW'
        with st.container(border=False, key=f'option4_commercial_project_{index}'):
            st.html(f'<div class="option-commercial-executive-head"><div><span>ANÁLISIS COMERCIAL</span><h4>{safe_project}</h4></div>'
                f'<span class="option-commercial-source">Gráfico: {mode} · Costos · Comercial anterior</span></div>'
                '<div class="option-commercial-executive-kpis">'
                f'<article class="primary"><span>Total comercial del piloto · {currency_code()}</span><strong>{amount(project_total)}</strong><small>Costos · Hito objetivo {capacity if capacity else ""} kW · Aplica</small></article>'
                f'<article><span>{unit_label} · {currency_code()}/kW</span><strong>{unit}</strong><small>Potencia nominal: {capacity if capacity else "sin informar"} kW · base histórica</small></article>'
                f'<article><span>Cobertura del piloto completo</span><strong>{project_coverage:.1f}%</strong><small>{project_known} de {project_count} partidas · {project_count-project_known} sin monto</small>'
                f'<div class="option-commercial-coverage-track"><i style="width:{project_coverage:.3f}%"></i></div></article>'
                f'<article><span>Concentración del piloto en {project_top_count or 3} sistemas</span><strong>{project_concentration_label}</strong><small>{project_systems} sistemas con monto informado</small></article></div>')
            st.caption(f'Gráfico y desglose · Vista {mode} · Subtotal del gráfico: {amount(total)}. El total comercial del piloto conserva todas las partidas Aplica del Hito objetivo correspondiente en Costos.')
            donut_col, detail_col = st.columns([.85, 1.3], gap='large')
            with donut_col:
                if can_draw:
                    fig, wedges = commercial_donut(summary, project, total)
                    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False}, key=f'option4_commercial_donut_{index}')
                    st.html('<div class="option-commercial-chart-note">Participación sobre el subtotal informado · Detalle completo a la derecha</div>')
                else:
                    reason = 'Sin partidas aplicables al producto' if not count else 'Sin montos comerciales informados' if not known else 'Sin distribución positiva' if nonnegative else 'Hay ajustes negativos en la fuente'
                    st.html('<div class="option-commercial-empty"><div>—</div><b>'+reason+'</b><span>Consulta el detalle de partidas. El donut requiere montos no negativos y un subtotal positivo.</span></div>')
            with detail_col:
                if known:
                    if not can_draw:
                        wedges = pd.DataFrame(columns=['Sistema'])
                    st.html(commercial_system_ranking(summary, total, wedges))
                elif count:
                    st.html('<div class="option-commercial-pending"><span>DATOS PENDIENTES</span><b>Completar la base comercial del piloto</b>'
                        f'<p>Hay {count} actividades sin monto comercial informado. Al completar Comercial anterior en Costos y actualizar el panel, aparecerán aquí los montos y su distribución.</p></div>')
                else:
                    st.info('El proyecto no tiene partidas clasificadas como Aplica en Costo para producto de Costos.')
            if can_draw:
                st.html('<div class="option-commercial-insight"><span>LECTURA EJECUTIVA</span>'
                    f'<p>Los {concentration_count} sistemas de mayor monto concentran <b>{concentration_label}</b> del subtotal. '
                    f'La cobertura es de <b>{coverage:.1f}% de los registros</b>; '
                    + ('el costo completo del piloto sigue pendiente de completar.' if known < count else 'todas las actividades seleccionadas tienen monto informado.') + '</p></div>')
            with st.expander('Composición por sistema e hito', expanded=False):
                st.caption(f'Alcance seleccionado: {mode}. ' + ('Excluye fundaciones y anclajes, montaje y logística.' if mode == 'Comercial' else 'Incluye todos los sistemas de las partidas marcadas Aplica en Costos.'))
                system_tab, milestone_tab = st.tabs(['Por sistema', 'Por hito'])
                with system_tab:
                    _summary_table(summary, 'Sistema', scope, f'option4_commercial_system_{index}', project_scope=project_scope)
                with milestone_tab:
                    _summary_table(commercial_breakdown(scope, 'Hito objetivo'), 'Hito objetivo', scope, f'option4_commercial_milestone_{index}', project_scope=project_scope)
            with st.expander('Trazabilidad de partidas · Costos'):
                fields = ['ID', 'Actividad / entregable', 'Criterio', 'Unidades', 'Costo por unidad · CLP', 'Paquete / línea', COMMERCIAL, 'Presupuesto vigente', '% del paquete', '% del proyecto']
                detail = commercial_participations(scope, project_scope).assign(**{'Unidades': commercial_quantities(scope), 'Costo por unidad · CLP': commercial_unit_cost(scope)})
                detail = detail.reindex(columns=fields).sort_values(COMMERCIAL, ascending=False, na_position='last', kind='stable')
                detail = detail.rename(columns={'Unidades': 'Cantidad'})
                detail['Variación %'] = commercial_budget_variation(detail)
                st.dataframe(detail.style.format({**{field: amount for field in [COMMERCIAL, 'Presupuesto vigente', 'Costo por unidad · CLP'] if field in detail},
                        '% del paquete': lambda value: f'{value:.2f}%'.replace('.', ','),
                        '% del proyecto': lambda value: f'{value:.2f}%'.replace('.', ','),
                        'Variación %': lambda value: f'{value:+.1f}%'.replace('.', ',')}, na_rep='Sin informar')
                        .set_properties(subset=[COMMERCIAL], **{'background-color': '#FFF1ED', 'color': '#9F3A28'}),
                    hide_index=True, use_container_width=True, row_height=72, height=350,
                    column_config={'Actividad / entregable': st.column_config.TextColumn(width='large'),
                        'Criterio': st.column_config.TextColumn(width='small', help='Criterio de Plan (columna G), vinculado por ID de actividad.'),
                        'Cantidad': st.column_config.TextColumn(width='small', help='Cantidad de Costos, vinculada por ID de actividad.'),
                        'Costo por unidad · CLP': st.column_config.NumberColumn(currency_label('Costo por unidad · CLP'), width='medium', help='Valor de Presupuesto referencia de Costos, vinculado por ID de actividad. Se muestra directamente como costo por unidad.'),
                        'Presupuesto vigente': st.column_config.NumberColumn(currency_label('Presupuesto vigente · CLP'), width='medium', help='Presupuesto vigente de Costos, vinculado por ID de actividad.'),
                        '% del paquete': st.column_config.NumberColumn(width='small', help='Monto comercial del ID ÷ total comercial de su paquete dentro del mismo sistema × 100.'),
                        '% del proyecto': st.column_config.NumberColumn(width='small', help='Monto comercial del ID ÷ total comercial del piloto completo seleccionado, con partidas Aplica de Costos × 100.'),
                        'Variación %': st.column_config.NumberColumn('Variación %', width='small', help=VARIATION_HELP)})
                st.download_button('Descargar análisis comercial · CSV', currency_export(detail).to_csv(index=False).encode('utf-8-sig'),
                    file_name=f'costo_comercial_{index}.csv', mime='text/csv', key=f'option4_commercial_download_{index}')
        with st.expander('Cómo interpretar el costo comercial'):
            st.markdown('El subtotal suma **Comercial anterior** una sola vez por ID de actividad, vinculado desde **Costos** a **Plan**. '
                'Se incluyen únicamente las partidas con **Costo para producto = Aplica** en Costos. Las filas Aprobado, No aplica o sin clasificación se excluyen de los importes, conteos, gráficos y descargas comerciales. '
                'La cobertura mide registros con monto respecto de las actividades seleccionadas; no mide cuánto presupuesto está cubierto. '
                'Los ceros explícitos cuentan como informados y los vacíos se conservan como faltantes. '
                'El donut distribuye el subtotal informado por sistema. El indicador por kW divide ese mismo subtotal por la potencia nominal del proyecto; '
                'con información parcial también es parcial. Estos montos se presentan separados de la caja pendiente y no se suman al calendario de desembolsos.')
