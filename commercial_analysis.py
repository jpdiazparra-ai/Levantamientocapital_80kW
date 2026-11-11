"""Executive commercial-cost analysis of the historical amounts published in Costos."""
import html
import hashlib
import re
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from capital_charts import amount
from display_currency import currency_label, currency_code, currency_export, exchange_rate
from commercial_report import build_commercial_pdf
from commercial_comparison import render_commercial_comparison

cached_commercial_pdf = st.cache_data(show_spinner=False, max_entries=24)(build_commercial_pdf)

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



def commercial_project_label(project):
    capacity = re.search(r'(?<!\d)(10|80)\s*kw\b', str(project), re.I)
    return f'Turbina de {capacity.group(1)} kW' if capacity else str(project)


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
    project_amounts = pd.to_numeric(project_scope[COMMERCIAL], errors='coerce')
    project_packages = project_scope['Paquete / línea'].fillna('').astype(str).str.strip()
    project_systems = project_scope.get('Sistema', pd.Series('', index=project_scope.index)).fillna('').astype(str).str.strip()
    totals_by_package = project_amounts.groupby([project_systems, project_packages], dropna=False).sum(min_count=1)
    # Use the complete pilot as denominator, even when the visible group is a hito.
    package_totals = pd.Series([totals_by_package.get(pair, float('nan')) for pair in zip(systems, packages)], index=result.index)
    project_total = project_amounts.sum(min_count=1)
    result['% del paquete'] = amounts.div(package_totals.where(package_totals.gt(0))) * 100
    result['% del proyecto'] = amounts / project_total * 100 if pd.notna(project_total) and project_total > 0 else float('nan')
    return result


DETAIL_FIELDS = ['ID', 'Actividad / entregable', 'Criterio', 'Unidades',
    'Costo por unidad · CLP', 'Paquete / línea', COMMERCIAL, 'Presupuesto vigente',
    'Variación %', '% del paquete', '% del proyecto', 'Registros conciliados']


def commercial_detail_columns():
    # Explicit widths keep monetary values and percentage headers readable.
    # Streamlit provides horizontal scrolling when the viewport is narrower.
    return {
        'ID': st.column_config.TextColumn(width=64),
        'Actividad / entregable': st.column_config.TextColumn(width=400),
        'Criterio': st.column_config.TextColumn(width=80, help='Criterio de Plan (columna G), vinculado por ID de actividad.'),
        'Cantidad': st.column_config.TextColumn(width=85, help='Cantidad de Costos, vinculada por ID de actividad.'),
        'Costo por unidad · CLP': st.column_config.NumberColumn(currency_label('Costo por unidad · CLP'), width=180, help='Presupuesto referencia de Costos, vinculado por ID. Se muestra directamente como costo por unidad.'),
        'Paquete / línea': st.column_config.TextColumn(width=190),
        COMMERCIAL: st.column_config.NumberColumn(currency_label('Monto comercial · CLP'), width=180),
        'Presupuesto vigente': st.column_config.NumberColumn(currency_label('Presupuesto vigente · CLP'), width=200, help='Presupuesto vigente de Costos, vinculado por ID de actividad.'),
        'Variación %': st.column_config.NumberColumn(width=115, help=VARIATION_HELP),
        '% del paquete': st.column_config.NumberColumn(width=125, help='Monto comercial del ID ÷ total comercial del mismo sistema y paquete en la turbina completa × 100. Solo partidas Aplica de Costos; no cambia al filtrar por hito.'),
        '% del proyecto': st.column_config.NumberColumn(width=130, help='Monto comercial del ID ÷ total comercial de la turbina completa × 100. Solo partidas Aplica según Hito objetivo de Costos; no cambia al filtrar sistema o paquete.'),
        'Registros conciliados': st.column_config.TextColumn(width=185, help='Estado de Registros conciliados de la pestaña Costos, vinculado por ID de actividad.'),
    }


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
        hole=.64, sort=False, direction='clockwise', rotation=90,
        text=[f'{value/total:.1%}'.replace('.', ',') if value/total >= .10 else '' for value in positive['Monto comercial · CLP']],
        textinfo='text', textposition='inside', textfont=dict(size=13, color='#FFFFFF'),
        marker=dict(colors=COLORS, line=dict(color='#FFFFFF', width=3)),
        customdata=[amount(value) for value in positive['Monto comercial · CLP']],
        hovertemplate='<b>%{label}</b><br>%{customdata}<br>%{percent:.1%} del subtotal informado<extra></extra>'))
    fig.update_layout(height=320, margin=dict(l=8, r=8, t=12, b=12), showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)', font=dict(family='Arial, sans-serif', color='#0F2435'),
        hoverlabel=dict(bgcolor='#FFFFFF', bordercolor='#D8E3EB', font=dict(size=12, color='#0F2435')),
        annotations=[dict(x=.5, y=.53, text='<b>'+amount(total, True)+'</b>', showarrow=False, font=dict(size=23, color='#0F2435')),
                     dict(x=.5, y=.42, text='SUBTOTAL INFORMADO', showarrow=False, font=dict(size=10, color='#64748B'))])
    return fig, positive


def commercial_system_ranking(summary, total, wedges):
    """Exact amounts, shares and coverage aligned with the distribution colors."""
    colors=dict(zip(wedges['Sistema'],COLORS))
    rows=[]
    for rank,(_,row) in enumerate(summary.iterrows(),1):
        value=row['Monto comercial · CLP']
        share=value/total*100 if pd.notna(value) and pd.notna(total) and total>0 else float('nan')
        label=f'{share:.1f}%'.replace('.',',') if pd.notna(share) else '—'
        width=min(100,max(0,share)) if pd.notna(share) else 0
        color=colors.get(row['Sistema'],COLORS[-1])
        known=int(row['Partidas informadas']);count=int(row['Actividades'])
        rows.append('<div class="option-commercial-system">'
            f'<div class="option-commercial-system-label"><i style="background:{color}" aria-hidden="true"></i>'
            f'<b>{html.escape(str(row["Sistema"]))}</b><small>{known} / {count} partidas informadas</small></div>'
            f'<b class="option-commercial-system-amount">{html.escape(amount(value))}</b>'
            f'<span class="option-commercial-system-share">{label}</span>'
            f'<div class="option-commercial-system-track"><i style="width:{width:.3f}%;background:{color}"></i></div></div>')
    return ('<div class="option-commercial-ranking"><div class="option-commercial-ranking-head">'
        '<b>Composición del costo por sistema</b><span>Importe · '+currency_code()+'</span><span>Participación</span></div>'
        +''.join(rows)+'</div>')


def commercial_group_details(scope, dimension, group, include_missing=False):
    labels = scope[dimension].fillna('').replace('', 'Sin clasificar')
    details = scope[labels.eq(group)].copy()
    if not include_missing:
        details = details[details[COMMERCIAL].notna()]
    return details.sort_values('ID', kind='stable', key=lambda ids:
        ids.astype(str).str.casefold().str.replace(r'\d+', lambda match: match.group().zfill(20), regex=True))


def _summary_table(summary, dimension, scope, key, project_scope=None, report_context=None):
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
    all_packages = 'Todos los paquetes'
    options = [all_packages, *sorted(package_counts.index, key=str.casefold)]
    package_key = group_key + '_package'
    remembered_package = st.session_state.get(package_key, all_packages)
    package = remembered_package if remembered_package in options else all_packages
    st.session_state[package_key] = package
    group_details = commercial_group_details(scope, dimension, group, include_missing=True)
    package_hours, _ = commercial_hour_values(details)
    def select_package(value):
        st.session_state[package_key] = value
    with st.container(key=group_key+'_package_controls'):
        st.html('<div class="option-package-heading"><div><span>DESGLOSE TÉCNICO</span>'
            '<strong>Líneas del '+('sistema' if dimension == 'Sistema' else 'hito')+'</strong>'
            f'<p>{html.escape(str(group))}</p></div></div>')
        st.caption(f'Selecciona una línea · {package_counts.size} líneas con partidas visibles · {len(details)} de {len(group_details)} partidas. HH considera solo cantidades con criterio HH.')
        cards_per_row = 7  # About 30% narrower than the previous five-column layout.
        for row_start in range(0, len(options), cards_per_row):
            columns = st.columns(cards_per_row, gap='small')
            for column, value in zip(columns, options[row_start:row_start + cards_per_row]):
                mask = pd.Series(True, index=details.index) if value == all_packages else packages.eq(value)
                count = int(mask.sum())
                hours = package_hours[mask].sum(min_count=1)
                hh_note = f" · {hours:,.1f} HH".replace(',', 'X').replace('.', ',').replace('X', '.') if pd.notna(hours) else ''
                line_name = 'Todas las líneas' if value == all_packages else ('Sin línea asignada' if value == 'Sin paquete' else value)
                label = ('✓ ' if value == package else '') + f'{line_name}\n\n{count} '+('partida' if count == 1 else 'partidas')+hh_note
                with column:
                    st.button(label, key=group_key+'_package_card_'+hashlib.sha1(value.encode()).hexdigest()[:12],
                        type='primary' if value == package else 'secondary', use_container_width=True,
                        on_click=select_package, args=(value,),
                        help=f'Ver {count} partidas de {line_name}. Las cantidades de insumos no se suman como HH.')
    if package and package != all_packages:
        details = details[packages.eq(package)].copy()
    selection_label = str(group) + (' · ' + package if package and package != all_packages else ' · Todas las líneas')
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
    fields = DETAIL_FIELDS
    details = details.reindex(columns=fields).rename(columns={'Unidades': 'Cantidad'})
    st.dataframe(details.style.format({**{field: amount for field in [COMMERCIAL, 'Presupuesto vigente', 'Costo por unidad · CLP'] if field in details},
            '% del paquete': lambda value: f'{value:.2f}%'.replace('.', ','),
            '% del proyecto': lambda value: f'{value:.2f}%'.replace('.', ','),
            'Variación %': lambda value: f'{value:+.1f}%'.replace('.', ',')}, na_rep='Sin informar')
            .set_properties(subset=[COMMERCIAL], **{'background-color': '#FFF1ED', 'color': '#9F3A28'}),
        hide_index=True, use_container_width=True, row_height=72, height=min(460, 40+len(details)*72),
        column_config=commercial_detail_columns())
    st.caption('Participación del ID sobre el monto comercial de su mismo sistema y paquete, y de la turbina completa seleccionada. Ambas bases incluyen todas las partidas Aplica de la turbina y se mantienen al filtrar. Los porcentajes se calculan con importes informados; no se calculan si el total es cero o falta información.')
    st.caption('Variación respecto del monto comercial: positivo = presupuesto mayor; negativo = presupuesto menor. Sin cálculo cuando el comercial es cero o falta un monto.')
    context = dict(report_context or {})
    context.update(currency=currency_code(), fx_rate=exchange_rate(), selection=selection_label,
        project=context.get('project', 'Análisis comercial'), mode=context.get('mode', 'Total'),
        hours=totals['HH'], missing_hours=totals['HH pendientes'],
        generated_at=datetime.now(ZoneInfo('America/Santiago')).strftime('%d-%m-%Y %H:%M'),
        cutoff=scope.attrs.get('document_cutoff'), consulted_at=scope.attrs.get('consulted_at'),
        source_url=scope.attrs.get('source_url'))
    filename = re.sub(r'[^a-zA-Z0-9_-]+', '_', context['project']+'_'+selection_label).strip('_')
    st.download_button('Descargar informe de la selección · PDF', cached_commercial_pdf(details, context),
        file_name=filename+'.pdf', mime='application/pdf', key=group_key+'_download', on_click='ignore')


def render_commercial_analysis(tasks):
    with st.container(border=True, key='option4_analysis_commercial'):
        st.subheader('Costo comercial de las turbinas')
        st.caption('Analiza el monto comercial informado para cada turbina y su composición por sistema y paquete. Se incluyen solo las partidas marcadas Aplica en Costos; el detalle permite contrastar cantidades, costos de referencia y presupuesto vigente.')
        if COMMERCIAL not in tasks:
            st.info('La fuente publicada no contiene la columna Comercial anterior en Costos.')
            return
        if 'Costo para producto' not in tasks:
            st.info('Falta Costo para producto en Costos para identificar las partidas aplicables al análisis comercial.')
            return
        projects = list(tasks['Proyecto'].dropna().unique())
        projects.sort(key=lambda name: (0 if re.search(r'10\s*k[wW]', name) else 1, name))
        if not projects:
            st.info('No hay proyectos para la selección de capital.')
            return
        projects.append('Comparar ambas turbinas')
        project_key = 'option4_commercial_project_select'
        if project_key in st.session_state and st.session_state[project_key] not in projects:
            st.session_state[project_key] = projects[0]
        def select_project():
            selected = re.sub(r'\W+', '_', str(st.session_state[project_key]))
            st.session_state[f'option4_commercial_composition_{selected}'] = 'Total'
        project = st.selectbox('Turbina del análisis comercial', projects, key=project_key, format_func=commercial_project_label,
            on_change=select_project,
            help='Revisa una turbina o compara ambas por sistema y línea, con costos, HH y variaciones porcentuales.')
        if project == 'Comparar ambas turbinas':
            scopes = {}
            for capacity in (10, 80):
                source_project = next((name for name in projects if re.search(rf'(?<!\d){capacity}\s*kw\b', str(name), re.I)), f'Turbina de {capacity} kW')
                scopes[capacity] = commercial_product_scope(commercial_project_rows(tasks, source_project))
            render_commercial_comparison(scopes)
            return
        index = re.sub(r'\W+', '_', str(project))
        project_tasks = commercial_project_rows(tasks, project)
        project_scope = commercial_product_scope(project_tasks)
        composition_key = f'option4_commercial_composition_{index}'
        remembered_mode = st.session_state.get(composition_key, 'Total')
        mode = remembered_mode if remembered_mode in ('Total', 'Comercial') else 'Total'
        st.session_state[composition_key] = mode
        mode = st.segmented_control('Alcance del análisis', ['Total', 'Comercial'], key=composition_key,
            help='Actualiza KPI, gráficos, tablas e informe general. Comercial excluye Fundaciones y anclajes y Montaje y Logística; Total incluye todas las partidas Aplica de la turbina.') or 'Total'
        scope = commercial_composition_scope(project_scope, mode)
        excluded = len(project_tasks) - len(project_scope)
        mode_note = f' · Vista Comercial: {len(scope)} partidas, con {len(project_scope) - len(scope)} excluidas del alcance' if mode == 'Comercial' else ''
        st.caption(f'Turbina completa: {len(project_scope)} partidas Aplica · {excluded} excluidas por su clasificación en Costos.{mode_note}')
        values = scope[COMMERCIAL]
        total = values.sum(min_count=1)
        if mode == 'Comercial':
            excluded_scope = project_scope[~project_scope['ID'].isin(scope['ID'])]
            excluded_amount = excluded_scope[COMMERCIAL].sum(min_count=1) if len(excluded_scope) else 0
            st.html('<div class="option-commercial-note"><b>El alcance Comercial excluye fundaciones y montaje</b>'
                f'<span>Referencia de la turbina completa (Total): <b>{amount(project_scope[COMMERCIAL].sum(min_count=1))}</b>'
                f' · Excluido del alcance Comercial: <b>{amount(excluded_amount)}</b>'
                f' · Monto del alcance Comercial: <b>{amount(total)}</b>.</span></div>')
        known, count = int(values.notna().sum()), len(scope)
        coverage = 100 * known / count if count else 0
        summary = commercial_breakdown(scope, 'Sistema')
        capacity = re.search(r'(10|80)\s*kw', str(project), re.I)
        capacity = int(capacity.group(1)) if capacity else None
        safe_project = html.escape(commercial_project_label(project))
        nonnegative = values.dropna().ge(0).all()
        can_draw = known > 0 and nonnegative and total > 0
        funded_systems = int(summary['Monto comercial · CLP'].notna().sum())
        concentration_count = min(3, funded_systems)
        concentration = summary['Monto comercial · CLP'].head(concentration_count).sum(min_count=1) / total * 100 if pd.notna(total) and total > 0 else float('nan')
        concentration_label = f'{concentration:.1f}%'.replace('.', ',') if pd.notna(concentration) else 'Sin informar'
        unit = amount(total / capacity) if capacity and pd.notna(total) else 'Sin informar'
        unit_label = 'Subtotal del alcance por kW' if known < count else 'Monto del alcance por kW'
        with st.container(border=False, key=f'option4_commercial_project_{index}'):
            st.html(f'<div class="option-commercial-executive-head"><div><span>ANÁLISIS COMERCIAL</span><h4>{safe_project}</h4></div>'
                f'<span class="option-commercial-source">Alcance: {mode} · Costos · Comercial anterior</span></div>'
                '<div class="option-commercial-executive-kpis">'
                f'<article class="primary"><span>Monto comercial · Alcance {mode} · {currency_code()}</span><strong>{amount(total)}</strong><small>Costos · Hito objetivo {capacity if capacity else ""} kW · Aplica</small></article>'
                f'<article><span>{unit_label} · {currency_code()}/kW</span><strong>{unit}</strong><small>Potencia nominal: {capacity if capacity else "sin informar"} kW</small></article>'
                f'<article><span>Cobertura del alcance {mode}</span><strong>{coverage:.1f}%</strong><small>{known} de {count} partidas · {count-known} sin monto</small>'
                f'<div class="option-commercial-coverage-track"><i style="width:{coverage:.3f}%"></i></div></article>'
                f'<article><span>Concentración en {concentration_count} sistemas</span><strong>{concentration_label}</strong><small>{funded_systems} sistemas con monto informado</small></article></div>')
            donut_col, detail_col = st.columns([.85, 1.3], gap='large')
            with donut_col, st.container(key=f'option4_commercial_distribution_{index}'):
                st.html('<div class="option-commercial-distribution-head"><b>Participación por sistema</b><span>Distribución del subtotal informado</span></div>')
                if can_draw:
                    fig, wedges = commercial_donut(summary, project, total)
                    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False}, key=f'option4_commercial_donut_{index}')
                    st.html('<div class="option-commercial-chart-note">Pasa el cursor sobre cada segmento para ver el sistema y su importe</div>')
                else:
                    reason = 'Sin partidas aplicables al producto' if not count else 'Sin montos comerciales informados' if not known else 'Sin distribución positiva' if nonnegative else 'Hay ajustes negativos en la fuente'
                    st.html('<div class="option-commercial-empty"><div>—</div><b>'+reason+'</b><span>Consulta el detalle de partidas. El donut requiere montos no negativos y un subtotal positivo.</span></div>')
            with detail_col:
                if known:
                    if not can_draw:
                        wedges = pd.DataFrame(columns=['Sistema'])
                    st.html(commercial_system_ranking(summary, total, wedges))
                elif count:
                    st.html('<div class="option-commercial-pending"><span>DATOS PENDIENTES</span><b>Completar la base comercial de la turbina</b>'
                        f'<p>Hay {count} actividades sin monto comercial informado. Al completar Comercial anterior en Costos y actualizar el panel, aparecerán aquí los montos y su distribución.</p></div>')
                else:
                    st.info('El proyecto no tiene partidas clasificadas como Aplica en Costo para producto de Costos.')
            if can_draw:
                st.html('<div class="option-commercial-insight"><span>CONCENTRACIÓN DEL COSTO</span>'
                    f'<p>Los {concentration_count} sistemas de mayor monto concentran <b>{concentration_label}</b> del subtotal. '
                    f'La cobertura es de <b>{coverage:.1f}% de los registros</b>; '
                    + ('el costo completo de la turbina sigue pendiente de completar.' if known < count else 'todas las actividades seleccionadas tienen monto informado.') + '</p></div>')
            if count:
                download_slot = st.empty()
                overview_details = commercial_participations(scope, project_scope)
                overview_details['Unidades'] = commercial_quantities(overview_details)
                overview_details['Costo por unidad · CLP'] = commercial_unit_cost(overview_details)
                overview_details['Variación %'] = commercial_budget_variation(overview_details)
                overview_details = overview_details.reindex(columns=[*DETAIL_FIELDS, 'Sistema']).rename(columns={'Unidades': 'Cantidad'})
                overview_details = overview_details.sort_values('ID', kind='stable', key=lambda ids:
                    ids.astype(str).str.casefold().str.replace(r'\d+', lambda match: match.group().zfill(20), regex=True))
                overview_totals = commercial_selection_totals(scope)
                overview_context = dict(project=commercial_project_label(project), selection='Todos los sistemas · Todas las líneas', mode=mode,
                    currency=currency_code(), fx_rate=exchange_rate(), hours=overview_totals['HH'], missing_hours=overview_totals['HH pendientes'],
                    chart_dimension='Sistema', system_summary=summary.to_dict('records'),
                    generated_at=datetime.now(ZoneInfo('America/Santiago')).strftime('%d-%m-%Y %H:%M'),
                    cutoff=scope.attrs.get('document_cutoff'), consulted_at=scope.attrs.get('consulted_at'), source_url=scope.attrs.get('source_url'))
                download_slot.download_button('Descargar informe completo de la turbina · PDF', cached_commercial_pdf(overview_details, overview_context),
                    file_name=f'informe_completo_turbina_{capacity}_kW.pdf', mime='application/pdf',
                    key=f'option4_commercial_full_download_{index}', on_click='ignore')
                st.caption(f'Informe general · {commercial_project_label(project)} · Todos los sistemas y líneas del alcance actual, incluidas partidas sin monto. Disponible sin seleccionar un sistema; el detalle de una selección conserva su descarga independiente.')
            with st.expander('Composición por sistema e hito', expanded=False):
                st.caption(f'Alcance seleccionado: {mode}. ' + ('Excluye fundaciones y anclajes, montaje y logística.' if mode == 'Comercial' else 'Incluye todos los sistemas de las partidas marcadas Aplica en Costos.'))
                system_tab, milestone_tab = st.tabs(['Por sistema', 'Por hito'])
                with system_tab:
                    _summary_table(summary, 'Sistema', scope, f'option4_commercial_system_{index}', project_scope=project_scope, report_context={'project': commercial_project_label(project), 'mode': mode})
                with milestone_tab:
                    _summary_table(commercial_breakdown(scope, 'Hito objetivo'), 'Hito objetivo', scope, f'option4_commercial_milestone_{index}', project_scope=project_scope, report_context={'project': commercial_project_label(project), 'mode': mode})
