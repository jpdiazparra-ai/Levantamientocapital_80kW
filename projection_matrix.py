"""Readable annual matrices with grouped indicators and frozen labels/years."""
import html
from pathlib import Path

import pandas as pd
import streamlit as st

from display_currency import amount, currency_code, exchange_rate


GROUPS = [
    ('Producción y capacidad', 'Demanda, entregas y fabricación',
     {'demand_10', 'demand_80', 'units_10', 'units_80', 'capacity', 'external', 'unserved'}),
    ('Resultados del negocio', 'Ingresos, costos y rentabilidad',
     {'sales', 'cogs', 'opex', 'ebitda', 'ebitda_margin'}),
    ('Flujo y posición de caja', 'Flujos anuales y saldos al cierre',
     {'fcff', 'capex', 'advances', 'cash_free'}),
]
HIGHLIGHTS = {'sales', 'ebitda', 'fcff', 'cash_free'}


def matrix_html(frame, fields, *, currency, fx, title, theme='blue'):
    """Render source values without aggregating annual flows or closing balances."""
    palette = 'violet' if theme == 'violet' else 'blue'
    years = frame['Año'].astype(str).tolist()
    escape = lambda value: html.escape(str(value), quote=True)
    columns = ''.join('<th scope="col"'+(' class="last-year"' if i == len(years)-1 else '')+
        '>'+escape(year)+'</th>' for i, year in enumerate(years))
    body = []
    grouped = set()
    for group, description, members in GROUPS:
        selected = [item for item in fields if item[1] in members]
        if not selected:
            continue
        body.append('<tr class="matrix-group"><th scope="row">'+escape(group)+
            '</th><td colspan="'+str(len(years))+'">'+escape(description)+'</td></tr>')
        for index, (label, field, kind) in enumerate(selected):
            grouped.add(field)
            unit = 'equipos' if kind == 'n' else '%' if kind == 'p' else currency
            if field in ('advances', 'cash_free'):
                unit += ' · saldo al cierre'
            elif kind == 'm':
                unit += ' · importe anual'
            classes = ['matrix-row', 'alternate' if index % 2 else '']
            if field in HIGHLIGHTS:
                classes.append('key-indicator')
            cells = []
            for col, value in enumerate(frame[field]):
                missing = pd.isna(value)
                if missing:
                    shown = 'Sin informar'
                elif kind == 'p':
                    shown = f'{value*100:.1f}%'.replace('.', ',')
                else:
                    number = value * fx if kind == 'm' and currency == 'CLP' else value
                    shown = f'{number:,.0f}'.replace(',', '.')
                css = 'last-year ' if col == len(years)-1 else ''
                css += 'missing' if missing else 'negative' if value < 0 else ''
                cells.append('<td class="'+css.strip()+'">'+escape(shown)+'</td>')
            body.append('<tr class="'+' '.join(classes).strip()+'"><th scope="row">'+
                '<span>'+escape(label)+'</span><small>'+escape(unit)+'</small></th>'+''.join(cells)+'</tr>')
    unknown = {field for _, field, _ in fields} - grouped
    if unknown:
        raise ValueError('Indicadores sin grupo de presentación: '+', '.join(sorted(unknown)))
    period = years[0]+' — '+years[-1] if len(years) > 1 else (years[0] if years else 'Sin período')
    return ('<section class="projection-matrix '+palette+'"><header><div><h4>'+escape(title)+
        '</h4><p>'+escape(period)+' · '+str(len(fields))+' indicadores</p></div>'+
        '<span class="matrix-currency">'+escape(currency)+' · montos sin decimales</span></header>'+
        '<div class="matrix-scroll" role="region" aria-label="'+escape(title)+'" tabindex="0">'+
        '<table><caption>'+escape(title)+' · '+escape(period)+'</caption><thead><tr>'+
        '<th scope="col" class="indicator-column">Indicador / unidad</th>'+columns+
        '</tr></thead><tbody>'+''.join(body)+'</tbody></table></div>'+
        '<footer>El indicador y los años permanecen visibles al desplazar la tabla. '+
        'La columna final destaca el último año del período. Los saldos de cierre no son acumulados.</footer></section>')


def render_projection_matrix(frame, fields, *, key, title='Proyección anual', theme='blue'):
    if frame.empty:
        st.info('No hay años para el período seleccionado.')
        return
    css = Path(__file__).with_name('assets').joinpath('projection_matrix.css').read_text()
    st.html('<style>'+css+'</style>')
    st.html(matrix_html(frame, fields, currency=currency_code(), fx=exchange_rate(),
        title=title, theme=theme))
    # Keep the previous native table's selection, copying and export tools accessible.
    matrix = []
    for label, field, kind in fields:
        def format_value(value):
            if pd.isna(value):return 'Sin informar'
            if kind == 'p':return f'{value*100:.1f}%'.replace('.', ',')
            if kind == 'n':return f'{value:,.0f}'.replace(',', '.')
            return amount(value * exchange_rate() if currency_code() == 'CLP' else value)
        matrix.append({'Indicador':label, 'Unidad':'equipos' if kind=='n' else '%' if kind=='p' else currency_code(),
            **{str(row['Año']):format_value(row[field]) for _, row in frame.iterrows()}})
    with st.expander('Tabla completa · copiar y descargar'):
        st.dataframe(pd.DataFrame(matrix), hide_index=True, use_container_width=True,
            height=min(540, 38+len(matrix)*35), key=key+'_source_table')
