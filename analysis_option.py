"""Alternative project analysis, using the published workbook's validation rules."""
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
import html
import re
import time
import textwrap

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components
from timeline_scroll import timeline_document

SOURCE = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vQOSK1DE0sEuK5Cl-bIahOjtdP6qsBobzqSlekorQCY9gRpwhRDzHYxh9c-Q-mKoQ/pub'
SHEETS = {'Resumen': '295125200', 'Plan': '1622224524', 'Costos': '1070657893', 'Revision': '735160527', 'Desembolsos': '614082465'}
MONTHS = {'ene':'01','feb':'02','mar':'03','abr':'04','may':'05','jun':'06','jul':'07','ago':'08','sept':'09','sep':'09','oct':'10','nov':'11','dic':'12'}
VIEWS = [
    ('capital', 'SUB BLOQUE 1', 'Levantamiento de Capital y Brecha TRL 9', 'Presupuesto de referencia, desembolsos mensuales y fondos pendientes de validación.'),
    ('technical', 'SUB BLOQUE 2', 'Hitos Técnicos e Industrialización', 'Avance físico, fechas base y previstas, dependencias y evidencia de cierre.'),
    ('pmo', 'SUB BLOQUE 3', 'Control PMO de Costos', 'Aprobación de bases, conciliación económica e inconsistencias por resolver.'),
]


def number(value):
    if pd.isna(value):
        return np.nan
    if isinstance(value, (float, int, np.number)):
        return float(value)
    text = str(value).strip().replace('\u00a0', '').replace(' ', '').replace('$', '').replace('%', '')
    if text in ('', '—', '–', '-'):
        return np.nan
    negative = text.startswith('(') and text.endswith(')')
    text = text.strip('()').replace('.', '').replace(',', '.')
    try:
        result = float(text)
    except ValueError:
        return np.nan
    return -result if negative else result


def money(value):
    return 'Por validar' if pd.isna(value) else '$' + f'{value:,.0f}'.replace(',', '.')


def dates(series):
    def translate(value):
        text = str(value).strip().lower()
        for month, replacement in MONTHS.items():
            text = re.sub(rf'(?<=-){month}(?=-)', replacement, text)
        return text
    return pd.to_datetime(series.map(translate), errors='coerce', format='mixed', dayfirst=True)


def table_from(raw, header, id_column):
    frame = raw.iloc[header + 1:].copy()
    frame.columns = raw.iloc[header].astype(str).str.strip()
    frame = frame.loc[:, frame.columns != ''].copy()
    if id_column not in frame:
        raise ValueError(f'Falta la columna {id_column} en la fuente publicada.')
    return frame[frame[id_column].astype(str).str.strip().ne('')].reset_index(drop=True)


def cash_from_costs(costs, plan):
    """The current workbook keeps one cash balance and FC date per Costos ID."""
    fields = ['Fecha FC / desembolso', 'Saldo pendiente caja CLP', 'Estado de pago caja',
        'Incluir en caja', 'Validación caja', 'Caja programada CLP', 'Caja por validar CLP']
    missing = [field for field in fields if field not in costs]
    if missing:
        raise ValueError('Faltan columnas de caja en Costos: ' + ', '.join(missing))
    include = costs['Incluir en caja'].str.strip().str.casefold().isin(['sí', 'si'])
    unpaid = costs['Estado de pago caja'].str.strip().str.casefold().isin(['no pagado', 'parcial'])
    selected = costs[include & unpaid].merge(plan[['ID', 'Proyecto', 'Actividad / entregable']], on='ID', validate='one_to_one')
    cash = pd.DataFrame(index=selected.index)
    cash['ID actividad'] = selected['ID']
    cash['Proyecto'] = selected['Proyecto']
    cash['Concepto / cuota'] = selected['Actividad / entregable']
    cash['Fecha FC / desembolso'] = selected['Fecha FC / desembolso']
    cash['Saldo pendiente CLP'] = selected['Saldo pendiente caja CLP'].map(number)
    cash['Validación del saldo'] = selected['Validación caja']
    cash['Estado de pago'] = selected['Estado de pago caja']
    cash['Caja programada CLP'] = selected['Caja programada CLP'].map(number)
    cash['Referencia por validar CLP'] = selected['Caja por validar CLP'].map(number)
    validated = selected['Validación caja'].str.strip().str.casefold().eq('validado')
    cash['Pendiente validado CLP'] = cash['Caja programada CLP'].where(validated)
    cash['Respaldo / observaciones'] = selected['Sustento / observaciones']
    cash['Alerta caja'] = selected['Alerta caja']
    cash['Caja sin fecha CLP'] = selected['Caja sin fecha CLP'].map(number)
    cash['_date'] = dates(cash['Fecha FC / desembolso'])
    return cash.reset_index(drop=True)


@st.cache_data(ttl=60, show_spinner=False)
def load_workbook(refresh_nonce=0, source_url=SOURCE, sheets=tuple(SHEETS.items())):
    token = f'{refresh_nonce}_{time.time_ns()}'
    def download(item):
        name, gid = item
        response = requests.get(source_url, params={'output':'csv', 'gid':gid, '_cb':token},
            headers={'Cache-Control':'no-cache', 'Pragma':'no-cache'}, timeout=(10, 40))
        response.raise_for_status()
        return name, pd.read_csv(BytesIO(response.content), header=None, dtype=str, keep_default_na=False)
    with ThreadPoolExecutor(max_workers=5) as pool:
        raw = dict(pool.map(download, sheets))
    plan = table_from(raw['Plan'], 4, 'ID')
    costs = table_from(raw['Costos'], 4, 'ID')
    revision = table_from(raw['Revision'], 4, 'ID')
    for name, frame in [('Plan', plan), ('Costos', costs), ('Revision', revision)]:
        if frame['ID'].duplicated().any():
            raise ValueError(f'{name} contiene IDs duplicados; revisa la planilla antes de agregar montos.')
    if set(plan['ID']) != set(costs['ID']):
        raise ValueError('Plan y Costos deben contener los mismos IDs de actividad.')
    cash = cash_from_costs(costs, plan)
    shared = [c for c in costs if c in plan and c != 'ID']
    tasks = plan.merge(costs.drop(columns=shared), on='ID', how='left', validate='one_to_one')
    tasks = tasks.merge(revision[['ID', 'Estado / avance actual', 'Control de dependencia']], on='ID', how='left', validate='one_to_one')
    for col in ['Presupuesto referencia', 'Presupuesto vigente', 'AC económico', 'EAC económico', 'VAC al cierre', 'EV', 'PV', 'CPI', 'SPI', 'ETC actualizado']:
        tasks[col] = tasks[col].map(number)
    tasks['_progress'] = tasks['Avance físico'].map(number)
    for col in ['Inicio base', 'Fin base', 'Fin previsto actual', 'Fin real']:
        tasks[col] = dates(tasks[col])
    tasks['_delay'] = (tasks['Fin previsto actual'] - tasks['Fin base']).dt.days
    cutoff = dates(pd.Series([raw['Resumen'].iloc[3,1]])).iloc[0]
    if pd.isna(cutoff):
        raise ValueError('La fecha de corte del documento no es válida.')
    return tasks, cash, cutoff, pd.Timestamp.now(tz='America/Santiago').strftime('%d-%m-%Y %H:%M:%S')


def weighted_progress(frame):
    known = frame['_progress'].notna() & frame['Presupuesto referencia'].notna() & frame['Presupuesto referencia'].gt(0)
    scope = frame[known]
    total = scope['Presupuesto referencia'].sum()
    return float((scope['_progress'] * scope['Presupuesto referencia']).sum() / total) if total > 0 else np.nan


def metrics(items):
    body = ''.join(f'<article class="option-kpi"><span>{html.escape(label)}</span><strong>{html.escape(str(value))}</strong><small>{html.escape(note)}</small></article>' for label, value, note in items)
    st.html(f'<div class="option-kpis">{body}</div>')


def chart(fig, key):
    fig.update_layout(font=dict(family='Arial, sans-serif', size=12, color='#475569'), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='#FFFFFF', margin=dict(l=16,r=25,t=40,b=40), legend_title_text=None)
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True, gridcolor='#EDF2F6')
    st.plotly_chart(fig, use_container_width=True, config={'displaylogo':False}, key=f'option4_{key}')


def filters(tasks, view):
    with st.container(border=True):
        st.markdown('**Filtros de análisis**')
        scope = tasks.copy()
        cols = st.columns(4)
        for area, field in zip(cols, ['Proyecto','Hito objetivo','Sistema','Estado por avance']):
            key=f'option4_{view}_{field}'
            options=sorted(scope[field].dropna().astype(str).loc[lambda x:x.ne('')].unique())
            if key in st.session_state:
                st.session_state[key]=[v for v in st.session_state[key] if v in options]
            with area:
                selected=st.multiselect(field, options, key=key, placeholder='Todos')
            if selected:
                scope=scope[scope[field].isin(selected)].copy()
        st.caption(f'{len(scope)} de {len(tasks)} actividades · Todos los indicadores de esta vista respetan la selección.')
    return scope


def capital_dimension_summary(tasks, cash, dimension):
    """Aggregate budgets once per activity and cash once per disbursement."""
    rows = []
    for name, group in tasks.groupby(dimension, dropna=False):
        quotas = cash[cash['ID actividad'].isin(group['ID'])]
        rows.append({
            dimension: name if pd.notna(name) and str(name).strip() else 'Sin clasificar',
            'Actividades': len(group),
            'Presupuesto referencia': group['Presupuesto referencia'].sum(min_count=1),
            'Caja por validar': quotas['Referencia por validar CLP'].sum(min_count=1),
            'Caja validada': quotas['Pendiente validado CLP'].sum(min_count=1),
            'Actividades de caja': len(quotas),
            'Avance físico %': weighted_progress(group),
        })
    summary = pd.DataFrame(rows).sort_values('Presupuesto referencia', ascending=False, na_position='last')
    total = summary['Presupuesto referencia'].sum(min_count=1)
    summary['Participación %'] = summary['Presupuesto referencia'] / total * 100 if pd.notna(total) and total > 0 else np.nan
    return summary


def render_capital_dimensions(tasks, cash):
    tabs = st.tabs(['Por proyecto', 'Por hito', 'Por sistema'])
    for tab, dimension, key in zip(tabs, ['Proyecto', 'Hito objetivo', 'Sistema'], ['project', 'milestone', 'system']):
        with tab:
            summary = capital_dimension_summary(tasks, cash, dimension)
            height = max(300, 110 + len(summary) * 36)
            ref_col, cash_col = st.columns([1, 1])
            with ref_col:
                st.markdown('**Distribución del presupuesto de referencia**')
                known = summary[summary['Presupuesto referencia'].notna()]
                fig = go.Figure(go.Bar(
                    x=known['Presupuesto referencia'] / 1e6, y=known[dimension], orientation='h',
                    marker=dict(color='#244A6C', cornerradius=4),
                    customdata=[[money(value), f'{share:.1f}%', int(count)] for value, share, count in zip(known['Presupuesto referencia'], known['Participación %'], known['Actividades'])],
                    hovertemplate='<b>%{y}</b><br>Referencia: %{customdata[0]}<br>Participación: %{customdata[1]}<br>Actividades: %{customdata[2]}<extra></extra>',
                ))
                fig.update_layout(height=height, xaxis_title='Millones de CLP', yaxis=dict(autorange='reversed'))
                chart(fig, f'capital_{key}_reference')
            with cash_col:
                st.markdown('**Caja validada y referencias por validar**')
                fig = go.Figure()
                for field, color in [('Caja por validar', '#B7791F'), ('Caja validada', '#0F766E')]:
                    known = summary[summary[field].notna()]
                    if not known.empty:
                        fig.add_bar(x=known[field] / 1e6, y=known[dimension], orientation='h', name=field,
                            marker=dict(color=color, cornerradius=4), customdata=[[money(value)] for value in known[field]],
                            hovertemplate='<b>%{y}</b><br>%{customdata[0]}<extra>' + field + '</extra>')
                if fig.data:
                    fig.update_layout(height=height, barmode='group', xaxis_title='Millones de CLP',
                        yaxis=dict(autorange='reversed', categoryorder='array', categoryarray=summary[dimension].tolist()),
                        legend=dict(orientation='h', y=1.12, x=0))
                    chart(fig, f'capital_{key}_cash')
                else:
                    st.info('No hay importes de caja informados para esta selección.')
            # Reads come from the same aggregates as the charts, respecting all filters.
            known = summary[summary['Presupuesto referencia'].notna()]
            if not known.empty:
                lead = known.iloc[0]
                share = lead['Participación %']
                share_text = f' ({share:.1f}% de la referencia seleccionada)' if pd.notna(share) else ''
                top = html.escape(str(lead[dimension]))
                pending = summary['Caja por validar'].sum(min_count=1)
                valid = summary['Caja validada'].sum(min_count=1)
                validation_text = 'No hay caja validada informada.' if pd.isna(valid) else f'Caja validada informada: {money(valid)}.'
                st.html('<div class="option-capital-reading"><span>LECTURA DE CAPITAL</span>'
                    f'<p><b>{top}</b> concentra la mayor referencia: <b>{money(lead["Presupuesto referencia"])}</b>{share_text}.</p>'
                    f'<p>Caja por validar de la selección: <b>{money(pending)}</b>. {validation_text}</p></div>')
            with st.expander(f'Detalle de capital por {dimension.lower()}'):
                st.dataframe(summary, hide_index=True, use_container_width=True,
                    column_config={
                        field: st.column_config.NumberColumn(field + ' (CLP)', format='$ %.0f')
                        for field in ['Presupuesto referencia', 'Caja por validar', 'Caja validada']
                    })
                st.download_button('Descargar este análisis', summary.to_csv(index=False).encode('utf-8-sig'),
                    file_name=f'capital_por_{key}.csv', mime='text/csv', key=f'option4_capital_{key}_download')


def capital_view(tasks, cash, cutoff):
    render_milestone_overview(tasks, cash=cash)
    st.caption('Visión general por hito. Los filtros siguientes se aplican al análisis de capital y al calendario de desembolsos.')
    st.subheader('Análisis de capital')
    tasks = filters(tasks, 'capital')
    if tasks.empty:
        st.info('No hay actividades para la selección.')
        return
    selected = cash[cash['ID actividad'].isin(tasks['ID'])].copy()
    reference = tasks['Presupuesto referencia'].sum(min_count=1)
    pending = selected['Referencia por validar CLP'].sum(min_count=1)
    valid = selected['Pendiente validado CLP'].sum(min_count=1)
    metrics([
        ('Presupuesto de referencia',money(reference),'Suma de referencias informadas'),
        ('Caja por validar',money(pending),'Referencia pendiente de revisión'),
        ('Desembolsos validados',money(valid),'Solo saldos con validación confirmada'),
        ('Actividades de caja por validar',str(selected['Validación del saldo'].eq('Por validar').sum()),'Saldos y fechas FC de Costos'),
    ])
    st.caption('Los totales se suman desde las partidas publicadas; pueden diferir algunos pesos del resumen por redondeo.')
    st.info('La caja se toma de Costos: saldos No pagado o Parcial con inclusión activa. La parte por validar está incluida en el programa, no se suma nuevamente. La brecha exige caja disponible e ingresos confirmados.')
    render_capital_dimensions(tasks, selected)
    st.subheader('Calendario de desembolsos')
    selected['_month']=selected['_date'].dt.to_period('M').dt.to_timestamp()
    first_month=cutoff.to_period('M').to_timestamp()
    selected['_month']=selected['_month'].mask(selected['_month'].lt(first_month),first_month)
    monthly=selected.dropna(subset=['_month']).groupby('_month')[['Pendiente validado CLP','Referencia por validar CLP']].sum(min_count=1).reset_index()
    visible=monthly[monthly[['Pendiente validado CLP','Referencia por validar CLP']].notna().any(axis=1)]
    fig=go.Figure()
    for field,label,color in [('Pendiente validado CLP','Validado','#0F766E'),('Referencia por validar CLP','Por validar','#B7791F')]:
        if visible[field].notna().any():
            fig.add_bar(x=visible['_month'],y=visible[field]/1e6,name=label,marker_color=color,hovertemplate='%{x|%m/%Y}<br>%{y:,.2f} MM CLP<extra>'+label+'</extra>')
    if fig.data:
        fig.update_layout(barmode='group',yaxis_title='Millones de CLP',xaxis_title='Mes de salida de caja')
        chart(fig,'cash')
    else:
        st.info('La selección no tiene desembolsos calendarizados con montos informados.')
    st.caption('Los vencimientos anteriores al corte se agrupan en el mes de corte, como en la planilla. Los aportes en especie no equivalen a caja.')
    with st.expander('Detalle de saldos de caja y validación · Costos'):
        st.dataframe(selected[['ID actividad','Concepto / cuota','Fecha FC / desembolso','Estado de pago','Saldo pendiente CLP','Validación del saldo','Caja programada CLP','Pendiente validado CLP','Referencia por validar CLP','Alerta caja','Respaldo / observaciones']].rename(columns={'Concepto / cuota':'Actividad / entregable'}),hide_index=True,use_container_width=True)
    with st.expander('Calendario mensual · selección activa'):
        st.dataframe(monthly.rename(columns={'_month':'Mes'}),hide_index=True,use_container_width=True)


def build_timeline_rows(tasks, end, level):
    """Create one lane per hierarchy node, preserving distinct package parents."""
    scope = tasks.dropna(subset=['Inicio base', end]).copy()
    scope = scope[scope[end].ge(scope['Inicio base'])]
    for field in ['Sistema', 'Paquete / línea']:
        scope[field] = scope[field].fillna('').astype(str).str.strip().replace('', 'Sin clasificar')
    if level == 'Actividades':
        scope = scope.sort_values(['Sistema', 'Paquete / línea', 'Inicio base', end, 'ID'])
        scope['_lane'] = scope['ID']
        scope['_label'] = scope['ID'] + ' · ' + scope['Actividad / entregable']
        scope['_start'] = scope['Inicio base']
        scope['_end'] = scope[end]
        scope['_state'] = scope['Estado por avance']
        scope['_base_end'] = scope['Fin base']
        return scope
    fields = ['Sistema'] if level == 'Sistemas' else ['Sistema', 'Paquete / línea']
    rows = []
    for keys, group in scope.groupby(fields, sort=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        progress = weighted_progress(group)
        row = {field: value for field, value in zip(fields, keys)}
        row.update({
            '_lane': str(len(rows)), '_label': ' › '.join(keys),
            '_start': group['Inicio base'].min(), '_end': group[end].max(),
            '_base_end': group['Fin base'].max(), '_progress': progress,
            'Actividades': len(group), 'Avance físico %': progress,
            'Terminadas': int(group['_progress'].ge(100).sum()),
            '_state': 'Sin avance' if pd.isna(progress) else 'Completado' if progress >= 100 else 'En curso' if progress > 0 else 'Pendiente',
        })
        rows.append(row)
    return pd.DataFrame(rows)


def _timeline_select(label, options, key, **kwargs):
    if st.session_state.get(key) not in options:
        st.session_state[key] = options[0]
    return st.selectbox(label, options, key=key, **kwargs)


def timeline_tooltip(row, level, mode):
    """Keep hover cards bounded even for long task names or unbroken text."""
    def wrapped(value, lines=2):
        chunks = textwrap.wrap(' '.join(str(value).split()), width=42, break_long_words=True, break_on_hyphens=False)
        if len(chunks) > lines:
            chunks = chunks[:lines]
            chunks[-1] = chunks[-1][:41].rstrip() + '…'
        return '<br>'.join(html.escape(chunk) for chunk in chunks)

    def field(label, value):
        return f'{label}: {wrapped(value)}'

    progress = row.get('_progress')
    progress_label = 'Sin informar' if pd.isna(progress) else f'{progress:.1f}%'.replace('.', ',')
    title = wrapped(row['_label'], lines=3)
    items = [f'<b>{title}</b>', '']
    if level == 'Actividades':
        items += [field('Sistema', row['Sistema']), field('Paquete', row['Paquete / línea'])]
    items += [field('Estado', row['_state']), f'Avance físico: <b>{progress_label}</b>']
    if level != 'Actividades':
        items += [f'Actividades: {int(row["Actividades"])} · Terminadas: {int(row["Terminadas"])}']
    finish_label = 'Fin previsto' if mode == 'Previsión actual' else 'Fin base'
    items += [f'Inicio: {row["_start"]:%d-%m-%Y}', f'{finish_label}: {row["_end"]:%d-%m-%Y}']
    return '<br>'.join(items)


def render_technical_timeline(tasks):
    st.caption('Explora el alcance por sistema, luego por paquete / línea y finalmente por actividad.')
    with st.container(border=True, key='option4_timeline_controls'):
        hito_key = 'option4_timeline_hitos'
        hito_options = sorted(tasks['Hito objetivo'].dropna().loc[lambda value: value.ne('')].unique())
        if hito_key in st.session_state:
            st.session_state[hito_key] = [value for value in st.session_state[hito_key] if value in hito_options]
        selected_hitos = st.multiselect('Hito objetivo del cronograma', hito_options, key=hito_key,
            placeholder='Todos los hitos', help='Selecciona uno o varios hitos. Sistemas y paquetes se ajustan a esta selección.')
        hito_scope = tasks[tasks['Hito objetivo'].isin(selected_hitos)].copy() if selected_hitos else tasks.copy()
        system_col, package_col = st.columns(2)
        with system_col:
            systems = sorted(hito_scope['Sistema'].dropna().loc[lambda x: x.ne('')].unique())
            system = _timeline_select('Sistema del cronograma', ['Todos los sistemas', *systems], 'option4_timeline_system')
        scope = hito_scope[hito_scope['Sistema'].eq(system)].copy() if system != 'Todos los sistemas' else hito_scope.copy()
        with package_col:
            packages = sorted(scope['Paquete / línea'].dropna().loc[lambda x: x.ne('')].unique())
            package = _timeline_select('Paquete / línea del cronograma', ['Todos los paquetes', *packages], 'option4_timeline_package')
        if package != 'Todos los paquetes':
            scope = scope[scope['Paquete / línea'].eq(package)].copy()
        states = ['Completado', 'En curso', 'Pendiente']
        state_key = 'option4_timeline_states'
        if state_key not in st.session_state:
            st.session_state[state_key] = states.copy()
        selected_states = st.multiselect('Estado de las actividades del cronograma', states, key=state_key,
            placeholder='Selecciona uno o varios estados', help='Filtra las actividades antes de resumir sistemas o paquetes. Estos controles afectan al cronograma y a su detalle.')
        scope = scope[scope['Estado por avance'].isin(selected_states)].copy()
        level_col, date_col = st.columns(2)
        with level_col:
            level = st.radio('Nivel de detalle', ['Sistemas', 'Paquetes / líneas', 'Actividades'], horizontal=True, key='option4_timeline_level')
        with date_col:
            if not st.session_state.get('option4_forecast_finish_default_v1'):
                st.session_state['option4_dates'] = 'Previsión actual'
                st.session_state['option4_forecast_finish_default_v1'] = True
            mode = st.radio('Fechas del cronograma', ['Previsión actual', 'Base'], horizontal=True, key='option4_dates',
                help='La previsión actual termina cada barra en Fin previsto actual. Base permite comparar con Fin base.')
        if level == 'Actividades':
            ids = scope.sort_values(['Inicio base', 'Fin base', 'ID'])['ID'].tolist()
            if 'option4_timeline_ids' in st.session_state:
                st.session_state['option4_timeline_ids'] = [value for value in st.session_state['option4_timeline_ids'] if value in ids]
            names = scope.set_index('ID')['Actividad / entregable'].to_dict()
            chosen = st.multiselect('Actividades del cronograma', ids, key='option4_timeline_ids', format_func=lambda value: f'{value} · {names.get(value, value)}', placeholder='Todas las actividades de la selección')
            if chosen:
                scope = scope[scope['ID'].isin(chosen)].copy()
        compare_col, order_col = st.columns(2)
        with compare_col:
            compare_base = st.checkbox('Comparar con línea base', value=True, disabled=mode == 'Base', key='option4_timeline_baseline')
        with order_col:
            if not st.session_state.get('option4_timeline_chronological_default_v1'):
                st.session_state['option4_timeline_sort'] = 'Fecha de inicio'
                st.session_state['option4_timeline_chronological_default_v1'] = True
            order = st.selectbox('Orden de lectura', ['Fecha de inicio', 'Fecha de término', 'Sistema y paquete'], key='option4_timeline_sort')
        end = 'Fin base' if mode == 'Base' else 'Fin previsto actual'
        rows = build_timeline_rows(scope, end, level)
        if rows.empty:
            st.info('No hay actividades con los estados y fechas seleccionados. Ajusta los filtros del cronograma.')
            return
        if order != 'Sistema y paquete':
            rows = rows.sort_values(['_start', '_end', '_label'] if order == 'Fecha de inicio' else ['_end', '_start', '_label'], kind='stable')

    scheduled_count = len(rows) if level == 'Actividades' else int(rows['Actividades'].sum())
    shown = rows.copy()
    overview_progress = weighted_progress(scope)
    progress_label = 'Sin referencia' if pd.isna(overview_progress) else f'{overview_progress:.1f}%'.replace('.', ',')
    state_colors = {'Completado':'#15803D', 'En curso':'#D97706', 'Pendiente':'#64748B'}
    badges = ''.join(
        f'<span class="option-state-badge"><i style="background:{color}"></i>{name}<b>{int(scope["Estado por avance"].eq(name).sum())}</b></span>'
        for name, color in state_colors.items()
    )
    hito_label = ' + '.join(selected_hitos) if selected_hitos else 'Todos los hitos'
    st.html(
        '<div class="option-timeline-context"><div><span class="option-timeline-eyebrow">RUTA DE EJECUCIÓN</span><strong>'
        + html.escape(hito_label + ' → ' + system + ' → ' + package) + '</strong>'
        f'<span>{level} · {mode} · {len(rows)} filas · cronograma completo</span></div>'
        f'<div class="option-state-legend">{badges}</div></div>'
        '<div class="option-timeline-summary">'
        f'<div><span>Actividades seleccionadas</span><b>{len(scope)}</b></div>'
        f'<div><span>Avance físico ponderado</span><b>{progress_label}</b></div>'
        f'<div><span>Con atraso previsto</span><b>{int(scope["_delay"].gt(0).sum())}</b></div>'
        f'<div><span>Actividades con fechas</span><b>{scheduled_count} / {len(scope)}</b></div></div>'
    )
    shown['_tooltip'] = shown.apply(lambda row: timeline_tooltip(row, level, mode), axis=1)
    document, panel_height = timeline_document(shown, level, mode, compare_base)
    components.html(document, height=panel_height, scrolling=False)
    st.caption('Color: estado por avance · Porcentaje al final de cada barra: avance físico ponderado del grupo.' if level != 'Actividades' else 'Color: estado por avance · Porcentaje al final de cada barra: avance físico de la actividad.')
    if mode == 'Previsión actual' and compare_base:
        st.caption('Línea punteada debajo de la barra: plazo base. La barra de color termina en Fin previsto actual.')
    if scheduled_count < len(scope):
        st.caption(f'{len(scope) - scheduled_count} actividades no se dibujan por fechas incompletas o un fin anterior al inicio. Puedes revisarlas en el detalle de fechas.')
    if level != 'Actividades':
        st.caption('Cada barra resume el intervalo entre la primera y la última fecha del grupo; puede incluir períodos sin actividad. El estado y el avance del grupo se ponderan por presupuesto de referencia.')
    st.caption('Los rombos identifican actividades de un solo día. Fin real conserva el cierre efectivo; la previsión técnica se mantiene separada de las fechas de desembolso.')
    st.markdown('#### Detalle del cronograma')
    detail = scope.copy()
    columns = ['Hito objetivo', 'Sistema', 'Paquete / línea', 'ID', 'Actividad / entregable', 'Estado por avance', '_progress', 'Inicio base', 'Fin base', 'Fin previsto actual', 'Fin real', '_delay']
    detail_order = ['Inicio base', end, 'ID'] if order == 'Fecha de inicio' else [end, 'Inicio base', 'ID'] if order == 'Fecha de término' else ['Sistema', 'Paquete / línea', 'Inicio base', 'ID']
    detail = detail[columns].sort_values(list(dict.fromkeys(detail_order)), kind='stable')
    st.caption(f'{len(detail)} actividades · Los filtros de hito, estado, sistema y paquete también se aplican al detalle.')
    st.dataframe(detail, hide_index=True, use_container_width=True, height=400,
        column_config={
            'Actividad / entregable': st.column_config.TextColumn('Actividad / entregable', width='large'),
            '_progress': st.column_config.ProgressColumn('Avance físico', min_value=0, max_value=100, format='%.1f%%'),
            '_delay': st.column_config.NumberColumn('Desvío previsto (días)', format='%d'),
            **{name: st.column_config.DatetimeColumn(name, format='DD-MM-YYYY', width='small') for name in ['Inicio base', 'Fin base', 'Fin previsto actual', 'Fin real']},
        })
    st.download_button('Descargar detalle del cronograma', data=detail.rename(columns={'_progress':'Avance físico %','_delay':'Desvío previsto (días)'}).to_csv(index=False).encode('utf-8-sig'),
        file_name='cronograma_tecnico_filtrado.csv', mime='text/csv', key='option4_timeline_download')


def explicit_milestone_rows(tasks):
    # Only the explicit Hito markers in Plan define the overview cards.
    packages = tasks['Paquete / línea'].fillna('').astype(str)
    return tasks[packages.str.contains(r'\bhitos?\b', case=False, regex=True, na=False)].copy()


def render_milestone_overview(tasks, cash=None):
    milestone_rows = explicit_milestone_rows(tasks)
    if milestone_rows.empty:
        st.info('No hay filas con Hito en Paquete / línea para construir las tarjetas.')
        return
    sequence = ['Premontaje 10 kW', 'Montaje 10 kW', 'Producto 10 kW', 'Piloto 80 kW', 'Producto 80 kW']
    available = milestone_rows['Hito objetivo'].dropna().unique().tolist()
    ordered = [name for name in sequence if name in available] + sorted(name for name in available if name not in sequence)
    cards = []
    finish_sources = []
    for index, name in enumerate(ordered, start=1):
        group = tasks[tasks['Hito objetivo'].eq(name)]
        markers = milestone_rows[milestone_rows['Hito objetivo'].eq(name)]
        display_name = ' / '.join(markers['Paquete / línea'].astype(str).str.strip().drop_duplicates())
        progress = weighted_progress(group)
        progress_label = 'Sin avance informado' if pd.isna(progress) else f'{progress:.1f}%'.replace('.', ',')
        percentage = 0 if pd.isna(progress) else float(np.clip(progress, 0, 100))
        completed = int(group['_progress'].ge(100).sum())
        delayed = int(group['_delay'].gt(0).sum())
        finish = markers['Fin previsto actual'].max()
        finish_label = 'Sin fecha' if pd.isna(finish) else finish.strftime('%d-%m-%Y')
        drivers = markers[markers['Fin previsto actual'].eq(finish)] if pd.notna(finish) else markers.iloc[:0]
        driver_ids = drivers['ID'].astype(str).tolist()
        source_label = 'Plan · ' + ', '.join(driver_ids[:2]) if driver_ids else 'Sin fecha informada en Plan'
        if len(driver_ids) > 2:
            source_label += f' + {len(driver_ids) - 2} actividades'
        finish_sources.extend(drivers[['Hito objetivo', 'Paquete / línea', 'ID', 'Actividad / entregable', 'Fin previsto actual']].to_dict('records'))
        tag = '80 kW' if '80' in name else '10 kW' if '10' in name else 'Hito'
        capital_html = ''
        if cash is not None:
            quotas = cash[cash['ID actividad'].isin(group['ID'])]
            reference = group['Presupuesto referencia'].sum(min_count=1)
            pending = quotas['Referencia por validar CLP'].sum(min_count=1)
            valid = quotas['Pendiente validado CLP'].sum(min_count=1)
            capital_html = (
                f'<div class="option-milestone-capital"><span>Presupuesto de referencia</span><strong>{money(reference)}</strong></div>'
                f'<div class="option-milestone-cash"><span>Caja por validar<b>{money(pending)}</b></span>'
                f'<span>Caja validada<b>{money(valid)}</b></span></div>'
            )
        cards.append(
            '<article class="option-milestone-card">'
            f'<div class="option-milestone-top"><span>HITO {index:02d}</span><i>{tag}</i></div>'
            f'<h3>{html.escape(display_name)}</h3>'
            f'{capital_html}'
            f'<div class="option-milestone-progress"><strong>{progress_label}</strong><span>avance físico</span></div>'
            f'<div class="option-milestone-track" role="img" aria-label="Avance: {progress_label}"><i style="width:{percentage:.2f}%"></i></div>'
            f'<div class="option-milestone-stats"><span><b>{completed} / {len(group)}</b> terminadas</span>'
            f'<span class="{"has-delay" if delayed else ""}"><b>{delayed}</b> con atraso previsto</span></div>'
            f'<div class="option-milestone-finish"><span title="Fin previsto actual de las filas con Hito en Paquete / línea">Fin previsto actual</span><b>{finish_label}</b><small>{html.escape(source_label)}</small></div>'
            '</article>'
        )
    grid_class = 'option-milestone-grid option-capital-milestones' if cash is not None else 'option-milestone-grid'
    st.html(f'<div class="{grid_class}">' + ''.join(cards) + '</div>')
    st.caption('Nombre y fin previsto: filas de Plan que contienen Hito en Paquete / línea. El avance ponderado, los importes y los conteos resumen las actividades asignadas a cada hito.')
    with st.expander('Filas Hito que determinan las tarjetas y sus fechas'):
        st.caption('Solo se consideran los marcadores Hito de Paquete / línea. Si hay varios para el mismo Hito objetivo, la fecha corresponde al último de esos marcadores.')
        if finish_sources:
            st.dataframe(pd.DataFrame(finish_sources), hide_index=True, use_container_width=True,
                column_config={'Actividad / entregable':st.column_config.TextColumn(width='large'),
                    'Fin previsto actual':st.column_config.DatetimeColumn(format='DD-MM-YYYY')})
        else:
            st.info('No hay fechas previstas informadas para los hitos.')


def technical_view(tasks):
    render_milestone_overview(tasks)
    st.subheader('Cronograma técnico')
    render_technical_timeline(tasks)
    st.subheader('Top 10 · desvío previsto')
    delayed=tasks[tasks['_delay'].gt(0)].nlargest(10,'_delay')
    st.dataframe(delayed[['ID','Actividad / entregable','Sistema','Estado por avance','Presupuesto referencia','Fin base','Fin previsto actual','Fin real','_delay']].rename(columns={'_delay':'Días de desvío'}),hide_index=True,use_container_width=True,column_config={'Actividad / entregable':st.column_config.TextColumn(width='large'),'Presupuesto referencia':st.column_config.NumberColumn('Referencia CLP',format='$ %.0f')})
    with st.expander('Detalle técnico y evidencia'):
        st.dataframe(tasks[['ID','Actividad / entregable','Entidad responsable','Responsable persona','Estado informado','Avance físico','Predecesoras (ID)','Evidencia / aceptación','Liberación técnica','Acción requerida']],hide_index=True,use_container_width=True)


def pmo_view(tasks):
    approved=tasks['Base aprobada'].str.casefold().isin(['sí','si'])
    reconciled=tasks['Registros conciliados'].eq('Validado')
    inconsistent=tasks['Estado / avance actual'].fillna('').str.casefold().ne('consistente')
    missing_owner=tasks['Responsable persona'].str.strip().eq('')
    metrics([
        ('Bases aprobadas',f'{approved.sum()} / {len(tasks)}','Presupuesto revisado y aprobado'),
        ('Registros conciliados',f'{reconciled.sum()} / {len(tasks)}','Costos y pagos completos al corte'),
        ('Estado / avance por revisar',str(inconsistent.sum()),'Inconsistencias de Revision'),
        ('Sin responsable persona',str(missing_owner.sum()),'Asignación pendiente'),
    ])
    st.subheader('Control económico validado')
    economic_ready=approved & reconciled
    complete=economic_ready.all()
    def aggregate(field):
        return tasks[field].sum(min_count=1) if complete and tasks[field].notna().all() else np.nan
    ac,ev,pv=aggregate('AC económico'),aggregate('EV'),aggregate('PV')
    cpi=ev/ac if pd.notna(ac) and ac>0 and pd.notna(ev) else np.nan
    spi=ev/pv if pd.notna(pv) and pv>0 and pd.notna(ev) else np.nan
    metrics([
        ('AC económico',money(ac),'Costo monetario más aportes valorizados'),
        ('EAC económico',money(aggregate('EAC económico')),'Costo final estimado'),
        ('CPI','Sin validar' if pd.isna(cpi) else f'{cpi:.2f}','EV / AC económico'),
        ('SPI','Sin validar' if pd.isna(spi) else f'{spi:.2f}','EV / PV'),
    ])
    if not complete:st.info('La selección aún requiere aprobación de bases y conciliación. Los indicadores económicos permanecen sin validar; el avance físico se consulta por separado.')
    actions=pd.DataFrame({'Acción':['Aprobar base','Conciliar registros','Asignar persona','Revisar estado / avance','Respaldar cierres'], 'Actividades':[int((~approved).sum()),int((~reconciled).sum()),int(missing_owner.sum()),int(inconsistent.sum()),int((tasks['_progress'].ge(100)&tasks['Evidencia / aceptación'].str.strip().eq('')).sum())]})
    st.subheader('Prioridades de control')
    chart(px.bar(actions,x='Actividades',y='Acción',orientation='h',color_discrete_sequence=['#B7791F']),'actions')
    st.subheader('Matriz de validación y seguimiento')
    st.dataframe(tasks[['ID','Actividad / entregable','Hito objetivo','Sistema','Base aprobada','Registros conciliados','Presupuesto referencia','AC económico','EAC económico','Estado / avance actual','Acción requerida']],hide_index=True,use_container_width=True)
    st.download_button('Descargar análisis PMO',data=tasks.drop(columns=[c for c in tasks if c.startswith('_')]).to_csv(index=False).encode('utf-8-sig'),file_name='opcion_analisis_pmo.csv',mime='text/csv',key='option4_download')


def render_analysis_option(refresh_nonce, render_navigation):
    with st.container(key='analysis_option'):
        st.html('<style>'+Path(__file__).with_name('assets').joinpath('analysis_option.css').read_text()+'</style>')
        st.html('<header class="option-head"><span>BLOQUE 4 · FUENTE ALTERNATIVA</span><h1>Opción de análisis</h1><p>Una lectura integrada del capital, el avance técnico y la validación económica del proyecto.</p></header>')
        def choose(value):st.session_state['option4_view']=value
        render_navigation(VIEWS,st.session_state.get('option4_view'),choose,'option4_subnav',heading='Capital, hitos y control PMO',description='Selecciona la dimensión del proyecto que quieres analizar.',variant='secondary')
        view=st.session_state.get('option4_view')
        if view is None:
            st.info('Comienza por capital y desembolsos, continúa con el avance técnico y revisa la validación económica en Control PMO de Costos.')
            return
        try:
            with st.spinner('Consultando el documento de análisis…'):
                tasks,cash,cutoff,fetched_at=load_workbook(refresh_nonce)
        except Exception as exc:
            st.error(f'No se pudo cargar el documento de análisis: {exc}')
            return
        st.caption(f'Corte del documento: {cutoff:%d-%m-%Y} · Consultado: {fetched_at} · Hora de Santiago')
        st.markdown(f'[Abrir documento fuente]({SOURCE}?output=csv)')
        title=next(item[2] for item in VIEWS if item[0]==view)
        st.subheader(title)
        scoped=tasks.copy() if view in ('technical', 'capital') else filters(tasks,view)
        if scoped.empty:
            st.info('No hay actividades para la selección.')
            return
        if view=='capital':capital_view(scoped,cash,cutoff)
        elif view=='technical':technical_view(scoped)
        else:pmo_view(scoped)
