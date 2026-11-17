"""Scenario submission, display currency and source changes remain consistent."""
import json
import unittest

from streamlit.testing.v1 import AppTest


SCRIPT = '''
import streamlit as st
from lcoe_finance import levelized_cost
from monte_carlo_view import render_lcoe_monte_carlo
st.session_state.setdefault('option4_currency','USD')
st.session_state['option4_fx_rate']=980.
capex=st.session_state.get('test_base',100000.)
base=levelized_cost(capacity_kw=80,capacity_factor=.35,capex=capex,
    fixed_om=capex*.02,variable_om=0.,years=20,rate=.08)
base.update(capex=capex, years=20)
render_lcoe_monte_carlo(base,capacity_factor=.35,
    scope=st.session_state.get('test_scope','Solo equipo turbina'),
    source_revision=st.session_state.get('test_consulted_at','test'))
'''


class MonteCarloUITests(unittest.TestCase):
    def test_submit_reproduce_and_convert_currency_without_resampling(self):
        app=AppTest.from_string(SCRIPT, default_timeout=20).run()
        self.assertFalse(app.exception)
        self.assertFalse(app.get('plotly_chart'))
        app.button[0].click().run()
        self.assertFalse(app.exception)
        result=app.session_state['option4_valuation80_mc_result']['result']
        self.assertEqual(result['samples'], 10000)
        self.assertEqual(len(app.get('download_button')), 1)
        spec=json.loads(app.get('plotly_chart')[0].proto.spec)
        self.assertIn('USD/kWh', spec['layout']['xaxis']['title']['text'])
        p50=result['p50']
        cards=' '.join(item.proto.body for item in app.get('html'))
        self.assertEqual(cards.count('/ MWh'), 3)
        for key in ('p10', 'p50', 'p90'):
            value=f"{result[key]*1000:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            self.assertIn('US$ '+value+' / MWh', cards)
        app.session_state['option4_currency']='CLP'
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['option4_valuation80_mc_result']['result']['p50'], p50)
        spec=json.loads(app.get('plotly_chart')[0].proto.spec)
        self.assertIn('CLP/kWh', spec['layout']['xaxis']['title']['text'])
        cards=' '.join(item.proto.body for item in app.get('html'))
        for key in ('p10', 'p50', 'p90'):
            value=f"{result[key]*1000*980:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            self.assertIn('$'+value+' / MWh', cards)
        self.assertAlmostEqual(spec['layout']['shapes'][1]['x0'], p50*980.)
        app.button[0].click().run()
        self.assertEqual(app.session_state['option4_valuation80_mc_result']['result']['p50'], p50)

    def test_consultation_time_alone_preserves_results_and_ranges(self):
        app=AppTest.from_string(SCRIPT, default_timeout=20).run()
        app.button[0].click().run()
        before=app.session_state['option4_valuation80_mc_result']
        app.session_state['test_consulted_at']='later consultation, same values'
        app.run()
        self.assertFalse(app.exception)
        after=app.session_state['option4_valuation80_mc_result']
        self.assertEqual(before['signature'], after['signature'])
        self.assertTrue(before['assumptions'].equals(after['assumptions']))
        self.assertTrue(before['result']['frame'].equals(after['result']['frame']))
        self.assertEqual(len(app.get('plotly_chart')), 1)

    def test_changed_basis_hides_stale_results_until_resubmitted(self):
        app=AppTest.from_string(SCRIPT, default_timeout=20).run()
        app.button[0].click().run()
        p50=app.session_state['option4_valuation80_mc_result']['result']['p50']
        app.session_state['test_base']=200000.
        app.run()
        self.assertFalse(app.exception)
        self.assertFalse(app.get('plotly_chart'))
        self.assertFalse(app.get('download_button'))
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertAlmostEqual(app.session_state['option4_valuation80_mc_result']['result']['p50'], p50*2)
        app.session_state['test_scope']='Turbina + instalación'
        app.run()
        self.assertFalse(app.get('plotly_chart'))


if __name__ == '__main__':
    unittest.main()
