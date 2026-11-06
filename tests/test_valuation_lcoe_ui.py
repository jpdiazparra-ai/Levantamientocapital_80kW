import unittest
import json
from streamlit.testing.v1 import AppTest

SCRIPT='''
import pandas as pd
import streamlit as st
from valuation_lcoe import lcoe_panel
st.session_state.setdefault('option4_currency','USD')
st.session_state.setdefault('option4_fx_rate',925.)
products=pd.DataFrame([
 {'Turbina':'10 kW','Potencia kW':10,'Precio / equipo':50000.,'Fabricación / equipo':40000.,'OPEX específico / equipo':1000.},
 {'Turbina':'80 kW','Potencia kW':80,'Precio / equipo':150000.,'Fabricación / equipo':120000.,'OPEX específico / equipo':2000.}])
lcoe_panel({},'2029',products)
'''


def results(app):
    return next(df.value for df in app.dataframe if 'Indicador' in df.value and df.value.Indicador.eq('LCOE TOTAL').any())


class InteractiveLcoeTests(unittest.TestCase):
    def test_inputs_recalculate_and_currency_preserves_native_user_costs(self):
        app=AppTest.from_string(SCRIPT,default_timeout=30).run()
        self.assertFalse(app.exception)
        first=results(app).set_index('Indicador').at['LCOE TOTAL','80 kW']
        app.slider(key='option4_lcoe_factor').set_value(60.).run()
        self.assertFalse(app.exception)
        changed=results(app).set_index('Indicador').at['LCOE TOTAL','80 kW']
        self.assertNotEqual(first,changed)
        editor=next(k for k in app.session_state.filtered_state if k.startswith('option4_lcoe_editor_'))
        app.session_state[editor]={'edited_rows':{0:{'CAPEX equipo':100000.}},'added_rows':[],'deleted_rows':[]}
        app.run()
        self.assertEqual(app.session_state['option4_lcoe_overrides']['2029|Precio de venta']['10']['CAPEX equipo'],100000.)
        app.session_state['option4_currency']='CLP';app.run()
        self.assertFalse(app.exception)
        self.assertEqual(results(app).set_index('Indicador').at['CAPEX equipo','10 kW'],'$92.500.000')
        app.button(key='option4_lcoe_restore').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(results(app).set_index('Indicador').at['CAPEX equipo','10 kW'],'$46.250.000')
        app.number_input(key='option4_lcoe_life').set_value(25).run()
        self.assertFalse(app.exception)
        self.assertTrue(results(app).Indicador.eq('LCOE TOTAL').any())
        app.number_input(key='option4_lcoe_life').set_value(5).run()
        self.assertTrue(results(app).Indicador.eq('LCOE TOTAL').any())
        self.assertLessEqual(app.number_input(key='option4_lcoe_replacement_year').value,5)
        app.slider(key='option4_lcoe_factor').set_value(0.).run()
        self.assertFalse(app.exception)
        self.assertTrue(app.warning)
        self.assertFalse(any('default value' in w.value for w in app.warning))

    def test_grouped_editable_format_and_80kw_charts_follow_the_selection(self):
        app=AppTest.from_string(SCRIPT,default_timeout=30).run()
        self.assertFalse(app.exception)
        editor=next(df for df in app.dataframe if 'Otros CAPEX instalados' in df.value)
        config=json.loads(editor.proto.columns)
        self.assertEqual(config['CAPEX equipo']['type_config']['format'],'localized')
        self.assertEqual(config['O&M variable / kWh']['type_config']['format'],'localized')
        self.assertGreaterEqual(config['CAPEX equipo']['width'],220)
        self.assertEqual(app.selectbox(key='option4_lcoe_technical_product').value,'80 kW')
        titles=lambda:[json.loads(fig.proto.spec).get('layout',{}).get('title',{}).get('text','') for fig in app.get('plotly_chart')]
        self.assertIn('Generación del escenario · 80 kW',titles())
        self.assertIn('Costos anuales del escenario · 80 kW',titles())
        self.assertIn('Costo nivelado acumulado · 80 kW',titles())
        app.selectbox(key='option4_lcoe_technical_product').set_value('10 kW').run()
        self.assertFalse(app.exception)
        self.assertIn('Generación del escenario · 10 kW',titles())
        app.slider(key='option4_lcoe_factor').set_value(45.).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key='option4_lcoe_technical_product').value,'10 kW')


if __name__=='__main__':unittest.main()
