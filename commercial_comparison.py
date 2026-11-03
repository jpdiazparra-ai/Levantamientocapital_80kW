"""Comparable commercial indicators for the 10 kW and 80 kW turbines."""
import html
import textwrap

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from display_currency import amount, currency_code

COMMERCIAL = 'Comercial anterior'
NAVY, TEAL, GOLD, MUTED = '#183448', '#0F766E', '#B99847', '#526578'


def _ratio_change(current, base):
    return (current - base).div(base.where(base.gt(0))) * 100


def comparison_data(scopes, by_line=False):
    """Align names by system and line; missing values remain missing."""
    dimensions = ['Sistema', 'Paquete / línea'] if by_line else ['Sistema']
    sides = []
    for capacity in (10, 80):
        data = scopes[capacity].copy()
        for field in dimensions:
            data[field] = data[field].fillna('').astype(str).str.strip().replace('', 'Sin clasificar')
        grouped = data.groupby(dimensions, dropna=False, sort=False).agg(**{
            'Comercial': (COMMERCIAL, lambda values: values.sum(min_count=1)),
            'Presupuesto': ('Presupuesto vigente', lambda values: values.sum(min_count=1)),
            'HH': ('_hh', lambda values: values.sum(min_count=1)),
            '_hh_count': ('_is_hh', 'sum'), '_hh_known': ('_hh', 'count'),
            'Partidas': ('ID', 'size'), 'Informadas': (COMMERCIAL, 'count'),
        })
        grouped['HH'] = grouped['HH'].mask(grouped['_hh_count'].eq(0), 0)
        grouped['HH pendientes'] = grouped['_hh_count'] - grouped['_hh_known']
        grouped = grouped.drop(columns=['_hh_count', '_hh_known'])
        total = data[COMMERCIAL].sum(min_count=1)
        grouped['Participación %'] = grouped['Comercial'] / total * 100 if pd.notna(total) and total > 0 else float('nan')
        grouped['Cobertura %'] = grouped['Informadas'] / grouped['Partidas'] * 100
        grouped['Costo/kW'] = grouped['Comercial'] / capacity
        grouped['HH/kW'] = grouped['HH'] / capacity
        grouped = grouped.rename(columns={col: f'{col} {capacity}' for col in grouped})
        sides.append(grouped)
    result = sides[0].join(sides[1], how='outer')
    for capacity in (10, 80):
        for metric in ['Partidas', 'Informadas', 'HH pendientes']:
            result[f'{metric} {capacity}'] = result[f'{metric} {capacity}'].fillna(0).astype(int)
    result['Diferencia comercial'] = result['Comercial 80'] - result['Comercial 10']
    result['Variación total %'] = _ratio_change(result['Comercial 80'], result['Comercial 10'])
    result['Variación por kW %'] = _ratio_change(result['Costo/kW 80'], result['Costo/kW 10'])
    result['Cambio participación · pp'] = result['Participación % 80'] - result['Participación % 10']
    result['Comparabilidad'] = [
        'Ambas con monto' if pd.notna(a) and pd.notna(b) else 'Solo 10 kW con monto' if pd.notna(a) else 'Solo 80 kW con monto' if pd.notna(b) else 'Sin montos informados'
        for a, b in zip(result['Comercial 10'], result['Comercial 80'])]
    result['_rank'] = result[['Comercial 10', 'Comercial 80']].sum(axis=1, min_count=1)
    return result.sort_values('_rank', ascending=False, na_position='last', kind='stable').drop(columns='_rank').reset_index()


def _pct(value, signed=False):
    if pd.isna(value):
        return 'Sin cálculo'
    return (f'{value:+.1f}' if signed else f'{value:.1f}').replace('.', ',')+'%'


def _total(series):
    return series.sum(min_count=1)


def render_commercial_comparison(project_scopes):
    # Local imports avoid a cycle while sharing the existing eligibility rules.
    from commercial_analysis import commercial_composition_scope, commercial_hour_values
    st.markdown('#### Comparación técnica y comercial · 10 kW vs 80 kW')
    st.caption('Contrasta el costo informado, la intensidad de HH y la composición de ambas turbinas. La potencia de 80 kW es ocho veces la de 10 kW: el indicador por kW permite leer el escalamiento junto con la cobertura de los datos.')
    with st.container(border=True, key='option4_comparison_controls'):
        scope_col, level_col = st.columns(2)
        with scope_col:
            mode = st.segmented_control('Alcance de la comparación', ['Total', 'Comercial'], default='Total', key='option4_compare_mode') or 'Total'
        with level_col:
            level = st.segmented_control('Nivel de comparación', ['Por sistema', 'Por línea'], default='Por sistema', key='option4_compare_level') or 'Por sistema'
        scopes = {}
        for capacity in (10, 80):
            data = commercial_composition_scope(project_scopes[capacity], mode)
            data['_hh'], data['_is_hh'] = commercial_hour_values(data)
            scopes[capacity] = data
        if any(data.empty for data in scopes.values()):
            st.info('No hay partidas Aplica para ambas turbinas en este alcance. Revisa la clasificación y el Hito objetivo en Costos.')
            return
        system_options = ['Todos los sistemas', *sorted(set(scopes[10]['Sistema'].dropna()) | set(scopes[80]['Sistema'].dropna()), key=str.casefold)]
        system_key = 'option4_compare_system'
        if st.session_state.get(system_key) not in system_options:
            st.session_state[system_key] = system_options[0]
        system = st.selectbox('Sistema a comparar', system_options, key=system_key)
        frame = comparison_data(scopes, by_line=level == 'Por línea')
        if system != system_options[0]:
            frame = frame[frame['Sistema'].eq(system)].copy()
        if level == 'Por línea':
            # Keys include both system and line so identically named lines never mix systems.
            choices = [(row['Sistema'], row['Paquete / línea']) for _, row in frame.iterrows()]
            line_labels = {pair: pair[1]+' · '+pair[0] for pair in choices}
            line_key = 'option4_compare_lines'
            if line_key in st.session_state:
                st.session_state[line_key] = [pair for pair in st.session_state[line_key] if pair in choices]
            selected_lines = st.multiselect('Líneas a comparar', choices, key=line_key, format_func=lambda pair: line_labels[pair], placeholder='Todas las líneas del sistema seleccionado')
            if selected_lines:
                frame = frame[[pair in selected_lines for pair in zip(frame['Sistema'], frame['Paquete / línea'])]].copy()
        metric = st.radio('Indicador del gráfico', ['Monto comercial', 'Costo comercial por kW', 'Presupuesto vigente', 'HH informadas', 'HH por kW'], horizontal=True, key='option4_compare_metric')
        st.caption('Total incluye todas las partidas Aplica. Comercial excluye fundaciones y anclajes, montaje y logística. La comparación usa Hito objetivo de Costos para asignar cada turbina.')
    if frame.empty:
        st.info('No hay líneas o sistemas para la selección actual.')
        return
    totals = {cap: _total(frame[f'Comercial {cap}']) for cap in (10, 80)}
    changes = _ratio_change(pd.Series([totals[80]]), pd.Series([totals[10]])).iloc[0]
    unit_changes = _ratio_change(pd.Series([totals[80]/80]), pd.Series([totals[10]/10])).iloc[0]
    cards = []
    for cap in (10, 80):
        count, known = int(frame[f'Partidas {cap}'].sum()), int(frame[f'Informadas {cap}'].sum())
        coverage = 100*known/count if count else float('nan')
        hours = _total(frame[f'HH {cap}'])
        hour_text = 'Sin informar' if pd.isna(hours) else f'{hours:,.1f}'.replace(',', 'X').replace('.', ',').replace('X', '.')+' HH'
        missing_hours = int(frame[f'HH pendientes {cap}'].sum())
        cards.append(f'<article><span>TURBINA DE {cap} kW · {currency_code()}</span><strong>{html.escape(amount(totals[cap]))}</strong><p>{html.escape(amount(totals[cap]/cap))} / kW · {hour_text}</p><small>{known} de {count} partidas con monto · {_pct(coverage)} de cobertura · {missing_hours} partidas HH sin cantidad</small></article>')
    cards += [f'<article><span>VARIACIÓN DEL MONTO TOTAL</span><strong>{_pct(changes, True)}</strong><p>80 kW respecto de 10 kW</p><small>Diferencia: {html.escape(amount(totals[80]-totals[10]))}</small></article>',
        f'<article class="normalized"><span>VARIACIÓN DEL COSTO POR kW</span><strong>{_pct(unit_changes, True)}</strong><p>Costos divididos por 80 y 10 kW</p><small>Negativo: menor costo informado por kW</small></article>']
    st.html('<div class="option-comparison-kpis">'+''.join(cards)+'</div>')
    st.caption('Los indicadores y gráficos siguen la selección actual. Los montos son parciales cuando faltan registros; una reducción por kW no demuestra ahorro validado si la cobertura o el alcance técnico difieren.')
    by_line = level == 'Por línea'
    labels = [row['Paquete / línea']+' · '+row['Sistema'] if by_line else row['Sistema'] for _, row in frame.iterrows()]
    wrapped = ['<br>'.join(textwrap.wrap(label, 34)) for label in labels]
    # Numeric row IDs avoid collisions if different labels wrap identically.
    rows = list(range(len(frame)))
    heights = max(390, 100 + len(frame)*65)
    metric_field = {'Monto comercial':'Comercial', 'Costo comercial por kW':'Costo/kW', 'Presupuesto vigente':'Presupuesto', 'HH informadas':'HH', 'HH por kW':'HH/kW'}[metric]
    fig = go.Figure()
    for cap, color in [(10, NAVY), (80, GOLD)]:
        values = frame[f'{metric_field} {cap}']
        display = [((f'{value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')+' '+metric_field) if metric_field in ('HH', 'HH/kW') else amount(value)) if pd.notna(value) else 'Sin informar' for value in values]
        fig.add_trace(go.Bar(name=f'Turbina de {cap} kW', y=rows, x=values, orientation='h', marker_color=color, text=display, textposition='outside', cliponaxis=False,
            customdata=list(zip(labels, display)), hovertemplate='<b>%{customdata[0]}</b><br>%{customdata[1]}<extra>%{fullData.name}</extra>'))
    fig.update_layout(barmode='group', height=heights, title=dict(text=metric+' · '+('por línea' if by_line else 'por sistema'), font=dict(size=17)),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='#FFFFFF', font=dict(color=MUTED,size=12), margin=dict(l=20,r=135,t=115,b=35), legend=dict(orientation='h',y=1.10,x=0,yanchor='bottom',font=dict(size=12),bgcolor='#FFFFFF'))
    fig.update_yaxes(tickvals=rows,ticktext=wrapped,autorange='reversed',automargin=True,showgrid=False)
    fig.update_xaxes(title_text=metric_field if metric_field in ('HH', 'HH/kW') else currency_code()+'/kW' if metric_field == 'Costo/kW' else currency_code(), gridcolor='#E8EDF1',zerolinecolor='#B8C6D0')
    st.plotly_chart(fig,use_container_width=True,key='option4_compare_grouped',config={'displaylogo':False})
    valid = frame['Variación por kW %'].notna()
    if valid.any():
        change = frame.loc[valid,'Variación por kW %']
        valid_labels = [wrapped[i] for i in range(len(rows)) if valid.iloc[i]]
        delta = go.Figure(go.Bar(x=change,y=list(range(int(valid.sum()))),orientation='h',marker_color=[TEAL if value<0 else GOLD for value in change],
            text=[_pct(value,True) for value in change],textposition='outside',cliponaxis=False,
            customdata=[[labels[i]] for i in range(len(rows)) if valid.iloc[i]],hovertemplate='<b>%{customdata[0]}</b><br>%{x:+.1f}% por kW<extra></extra>'))
        delta.update_layout(height=max(300,70+int(valid.sum())*45),title='Variación del costo por kW · 80 kW frente a 10 kW',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='#FFFFFF',font=dict(color=MUTED,size=12),margin=dict(l=20,r=90,t=60,b=35))
        delta.update_yaxes(tickvals=list(range(int(valid.sum()))),ticktext=valid_labels,autorange='reversed',automargin=True)
        delta.update_xaxes(title_text='Variación % · negativo = menor costo informado por kW',zeroline=True,zerolinewidth=2,zerolinecolor=NAVY,gridcolor='#E8EDF1')
        st.plotly_chart(delta,use_container_width=True,key='option4_compare_delta',config={'displaylogo':False})
    else:
        st.info('No hay una base comercial positiva de 10 kW y monto de 80 kW para calcular variaciones por kW en esta selección.')
    st.markdown('##### Matriz técnica y económica')
    st.caption('Los porcentajes de participación se refieren al total de cada turbina dentro del alcance Total/Comercial, y permanecen estables al filtrar sistemas o líneas. pp = puntos porcentuales. Sin cálculo indica que no existe una base positiva de 10 kW o falta un monto.')
    dims = ['Sistema','Paquete / línea'] if by_line else ['Sistema']
    columns = [*dims,'Comparabilidad','Comercial 10','Comercial 80','Diferencia comercial','Variación total %','Costo/kW 10','Costo/kW 80','Variación por kW %','Presupuesto 10','Presupuesto 80','HH 10','HH 80','HH/kW 10','HH/kW 80','HH pendientes 10','HH pendientes 80','Partidas 10','Partidas 80','Informadas 10','Informadas 80','Cobertura % 10','Cobertura % 80','Participación % 10','Participación % 80','Cambio participación · pp']
    money = ['Comercial 10','Comercial 80','Diferencia comercial','Costo/kW 10','Costo/kW 80','Presupuesto 10','Presupuesto 80']
    percentages = ['Variación total %','Variación por kW %','Cobertura % 10','Cobertura % 80','Participación % 10','Participación % 80']
    style = frame[columns].style.format({**{field:amount for field in money},**{field:lambda value:_pct(value) for field in percentages},'Cambio participación · pp':lambda value:f'{value:+.1f} pp'.replace('.',','),'HH 10':'{:,.1f}','HH 80':'{:,.1f}','HH/kW 10':'{:,.2f}','HH/kW 80':'{:,.2f}'},na_rep='Sin informar')
    configs = {field:st.column_config.NumberColumn(field+' · '+currency_code()+('/kW' if field.startswith('Costo/kW') else ''),width=180) for field in money}
    configs.update({field:st.column_config.NumberColumn(width=155) for field in percentages})
    configs['Paquete / línea'] = st.column_config.TextColumn('Línea del sistema',width=220)
    configs['Sistema'] = st.column_config.TextColumn(width=200)
    configs['Comparabilidad'] = st.column_config.TextColumn(width=190)
    st.dataframe(style,hide_index=True,use_container_width=True,height=min(650,38+len(frame)*36),column_config=configs)
    with st.expander('Criterios de comparación y lectura técnica'):
        st.markdown('**Base:** Comercial anterior y Presupuesto vigente de Costos, solo Costo para producto = Aplica, asignadas por Hito objetivo de 10/80 kW. '
            '**Variación:** (80 − 10) / 10 × 100, tanto en monto total como en costo/kW; una base cero, negativa o faltante queda sin cálculo. '
            '**HH:** Cantidad de Costos solo para criterio HH; los insumos no se suman como horas. '
            '**Alineación:** se comparan nombres de sistema y, en detalle, sistema + línea; no se infiere equivalencia entre líneas con nombres diferentes. '
            '**Cobertura:** partidas con monto / partidas Aplica; incluye ceros explícitos. Un sistema ausente se conserva sin monto, no como cero. '
            'Los gráficos muestran todas las filas filtradas, sin páginas.')
