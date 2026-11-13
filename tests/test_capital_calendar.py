"""The calendar's turbine selector scopes cash, monthly totals and milestone dates."""
import json
import unittest
import pandas as pd
from streamlit.testing.v1 import AppTest


class CalendarTurbineTests(unittest.TestCase):
    def test_calendar_selection_scopes_months_totals_and_markers(self):
        app=AppTest.from_string('''
import pandas as pd
from analysis_option import render_disbursement_calendar
tasks=pd.DataFrame({'ID':['a','b'],'Proyecto':['Piloto 10kW','Piloto 80kW'],
    'Presupuesto referencia':[100.,900.],'Paquete / línea':['Hito Piloto 10 kW','Hito Producto 80 kW'],
    'Fin previsto actual':pd.to_datetime(['2027-02-28','2027-05-31'])})
if __import__('streamlit').session_state.get('only80',False):tasks=tasks.iloc[1:]
cash=pd.DataFrame({'ID actividad':['a','b'],'Referencia por validar CLP':[10.,90.],
    'Pendiente validado CLP':[2.,3.],'_date':pd.to_datetime(['2026-09-01','2027-03-01']),
    'Validación del saldo':['Por validar','Por validar']})
for field in ['Concepto / cuota','Fecha FC / desembolso','Estado de pago','Saldo pendiente CLP',
    'Caja programada CLP','Alerta caja','Respaldo / observaciones']:cash[field]=''
render_disbursement_calendar(tasks,cash,pd.Timestamp('2026-11-13'))
''',default_timeout=20).run()
        self.assertFalse(app.exception)
        selector='option4_capital_calendar_turbine'
        self.assertEqual(app.selectbox(key=selector).value,'Ambas turbinas')
        self.assertEqual(app.dataframe[1].value['Referencia por validar CLP'].sum(),100)
        app.selectbox(key=selector).select('10 kW').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.dataframe[0].value['ID actividad'].tolist(),['a'])
        monthly=app.dataframe[1].value
        self.assertEqual(monthly['Referencia por validar CLP'].sum(),10)
        self.assertEqual(monthly['Pendiente validado CLP'].sum(),2)
        self.assertEqual(monthly.iloc[0]['Mes'],pd.Timestamp('2026-11-01'))
        spec=json.loads(app.get('plotly_chart')[0].proto.spec)
        self.assertTrue(any('10 kW' in item['text'] for item in spec['layout']['annotations']))
        self.assertFalse(any('80 kW' in item['text'] for item in spec['layout']['annotations']))
        app.selectbox(key=selector).select('80 kW').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.dataframe[0].value['ID actividad'].tolist(),['b'])
        self.assertEqual(app.dataframe[1].value['Referencia por validar CLP'].sum(),90)
        app.session_state['only80']=True
        app.selectbox(key=selector).select('10 kW').run()
        self.assertFalse(app.exception)
        self.assertTrue(app.info)
        self.assertEqual(len(app.get('plotly_chart')),0)
        app.selectbox(key=selector).select('Ambas turbinas').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.dataframe[0].value['ID actividad'].tolist(),['b'])


if __name__=='__main__':unittest.main()
