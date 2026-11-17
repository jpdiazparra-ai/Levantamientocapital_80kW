"""Editable exploratory Monte Carlo scenarios beneath the 80 kW owner LCOE."""
import hashlib
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from display_currency import currency_code, exchange_rate
from monte_carlo_lcoe import PARAMETERS, simulate_lcoe
from valuation_lcoe import lcoe_text
from valuation_view import BLUE_UNIT_PALETTE, NAVY, TEAL, GOLD, displayed, kpis, money, plot


PREFIX = 'option4_valuation80_mc'
LABELS = ['CAPEX por kW · % de la base', 'O&M anual · % del CAPEX',
          'Factor de planta neto · %', 'Tasa de descuento real · %']


def render_lcoe_monte_carlo(base, *, capacity_factor, scope, source_revision):
    # Consultation timestamps may change while the actual scenario stays identical.
    signature = hashlib.sha256(repr((base['capex'], base['years'], capacity_factor,
        scope)).encode()).hexdigest()[:16]
    with st.container(border=True, key=PREFIX):
        st.markdown('##### Monte Carlo · incertidumbre del LCOE de 80 kW')
        st.caption('Rangos exploratorios editables; no son intervalos validados del proyecto. '
            'La simulación usa el precio sin IVA del alcance activo como inversión inicial del propietario.')
        st.caption(('Base: '+money(base['capex']/80)+' / kW · '+scope+
            ' · Vida: '+str(base['years'])+' años · LCOE de referencia: '+lcoe_text(base['lcoe'])+
            ' '+currency_code()+'/kWh.').replace('$', r'\$'))
        defaults = pd.DataFrame({'Variable': LABELS,
            'Mínimo': [80., 1., max(1., capacity_factor*100-5), 6.],
            'Más probable': [100., 2., capacity_factor*100, 8.],
            'Máximo': [120., 3., min(100., capacity_factor*100+5), 10.]})
        with st.form(PREFIX+'_form'):
            edited = st.data_editor(defaults, hide_index=True, use_container_width=True,
                num_rows='fixed', disabled=['Variable'], key=PREFIX+'_ranges_'+signature,
                column_config={'Variable': st.column_config.TextColumn(width='large'),
                    **{name: st.column_config.NumberColumn(format='%.2f', required=True)
                       for name in ['Mínimo', 'Más probable', 'Máximo']}})
            count = st.selectbox('Número de simulaciones', [1000, 5000, 10000, 25000],
                index=2, key=PREFIX+'_count')
            st.caption('100 % de CAPEX representa el costo por kW de la base. '
                'Cada variable usa una distribución triangular (mínimo, más probable, máximo). '
                'O&M es mantenimiento anual del propietario; el OPEX comercial ya está incluido en el precio inicial.')
            submitted = st.form_submit_button('Simular LCOE · Monte Carlo', type='primary')
        if submitted:
            try:
                ranges = {name: tuple(float(v)/100 for v in edited.iloc[i][
                    ['Mínimo', 'Más probable', 'Máximo']]) for i, name in enumerate(PARAMETERS)}
                result = simulate_lcoe(capacity_kw=80, base_capex=base['capex'], years=base['years'],
                    ranges=ranges, samples=count, seed=2026)
                st.session_state[PREFIX+'_result'] = dict(signature=signature, result=result,
                    assumptions=edited.copy(), scope=scope, source=str(source_revision))
            except (ValueError, TypeError) as exc:
                st.session_state.pop(PREFIX+'_result', None)
                st.error('Revisa los rangos: '+str(exc))
        saved = st.session_state.get(PREFIX+'_result')
        if saved and saved['signature'] != signature:
            st.session_state.pop(PREFIX+'_result', None)
            saved = None
        if not saved:
            st.info('Revisa los rangos y pulsa Simular LCOE para obtener la distribución.')
            return
        result = saved['result']
        st.caption(f"Última simulación: {result['samples']:,} escenarios · semilla fija {result['seed']}. "
            'Los resultados corresponden a los rangos enviados al pulsar Simular.')
        kpis([('P10 · '+currency_code()+'/kWh', lcoe_text(result['p10']), lcoe_text(result['p10'], True)+' / MWh · 10 % de escenarios por debajo'),
            ('P50 · '+currency_code()+'/kWh', lcoe_text(result['p50']), lcoe_text(result['p50'], True)+' / MWh · Mediana de los escenarios'),
            ('P90 · '+currency_code()+'/kWh', lcoe_text(result['p90']), lcoe_text(result['p90'], True)+' / MWh · 90 % de escenarios por debajo')])
        values = displayed(result['frame']['LCOE · USD/kWh'])
        fig = go.Figure(go.Histogram(x=values, nbinsx=50, histnorm='probability',
            marker_color=TEAL, marker_line_color='#FFFFFF', marker_line_width=.5,
            hovertemplate='LCOE: %{x:.5f}<br>Proporción: %{y:.1%}<extra></extra>'))
        for percentile, color, position in [('p10', GOLD, 'top left'),
                ('p50', TEAL, 'top'), ('p90', NAVY, 'top right')]:
            fig.add_vline(x=displayed(result[percentile]), line_color=color, line_dash='dash',
                annotation_text=percentile.upper(), annotation_position=position)
        fig.update_layout(title='Distribución simulada del costo de energía', showlegend=False)
        fig.update_xaxes(title_text='LCOE · '+currency_code()+'/kWh', rangemode='tozero')
        fig.update_yaxes(title_text='Proporción de simulaciones', tickformat='.0%', rangemode='tozero')
        plot(fig, PREFIX+'_histogram', 330,palette=BLUE_UNIT_PALETTE)
        st.caption('P90 de LCOE significa que el 90 % de los escenarios tiene un costo igual o inferior a ese valor. '
            'P10–P90 contiene el 80 % central de los resultados; depende de los rangos y distribuciones elegidos.')
        with st.expander('Rangos utilizados y método de cálculo'):
            st.dataframe(saved['assumptions'], hide_index=True, use_container_width=True)
            st.caption('Cada escenario mantiene constantes energía y mantenimiento durante la vida útil. '
                'Se descuentan costos y generación al cierre de cada año. Las cuatro variables se muestrean '
                'independientemente; el mantenimiento monetario depende del CAPEX de cada escenario. '
                'Moneda constante, sin degradación, impuestos, reposiciones ni valor residual. '
                'La simulación representa únicamente los costos incluidos en el alcance seleccionado.')
            st.caption('Referencia de aplicación de Monte Carlo con distribuciones triangulares: '
                '[NREL · Energy Storage Analysis](https://www.nrel.gov/docs/fy21osti/77833.pdf). '
                'Los rangos de este panel son supuestos propios editables, no cifras extraídas de esa publicación.')
        exported = result['frame'].copy()
        if currency_code() == 'CLP':
            for field in list(exported):
                if 'USD' in field:
                    exported[field] *= exchange_rate()
            exported = exported.rename(columns=lambda name: name.replace('USD', 'CLP'))
        exported['Potencia · kW'] = result['capacity_kw']
        exported['Vida útil · años'] = result['years']
        exported['Semilla'] = result['seed']
        exported['Alcance'] = saved['scope']
        exported['Revisión de fuente'] = saved['source']
        # Keep the exact sampling assumptions with the downloaded rows.
        exported['Rangos utilizados'] = json.dumps(result['ranges'], ensure_ascii=False)
        st.download_button('Descargar simulaciones · CSV', exported.to_csv(index=False).encode('utf-8-sig'),
            file_name='monte_carlo_lcoe_80kW_'+currency_code()+'.csv', mime='text/csv',
            key=PREFIX+'_download', on_click='ignore')
