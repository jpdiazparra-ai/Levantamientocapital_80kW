"""10 kW source, capacity, project scope and complete dashboard regression."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest
from valuation10_data import parse_model10, SOURCE
from valuation10_lcoe import summary_lcoe10
from valuation10_unit import sale_prices10
from valuation10_project import project_calendar10
from valuation10_report import build_report10
from valuation10_view import unit_products
from valuation_view import chart_palette

FIXTURE = Path(__file__).parent/'fixtures'


def model():
    result=parse_model10(json.loads((FIXTURE/'valuation10.json').read_text()))
    result['fetched_at']='13-11-2026 10:30:00'
    return result


def project():
    p=json.loads((FIXTURE/'project10.json').read_text())
    for key in ['monthly','cash','milestones']:p[key]=pd.DataFrame(p[key])
    p['monthly']['_month']=pd.to_datetime(p['monthly']['_month'])
    p['milestones']['Fin previsto actual']=pd.to_datetime(p['milestones']['Fin previsto actual'])
    p['cutoff']=pd.Timestamp(p['cutoff'])
    for key in ['scope','systems','lines']:p['costs'][key]=pd.DataFrame(p['costs'][key])
    return p


class Valuation10Tests(unittest.TestCase):
    def test_source_values_capacity_and_unresolved_reconciliations(self):
        m=model()
        self.assertEqual(m['products'],(10,))
        self.assertEqual(m['source_url'],SOURCE)
        self.assertEqual(m['scalars']['dcf'],7317794)
        self.assertEqual(m['scalars']['sales_y1'],2947000)
        self.assertAlmostEqual(summary_lcoe10(m,.35,980)['energy_y1'],30660)
        prices=sale_prices10(m,980)
        self.assertAlmostEqual(prices['net_kw'],prices['net']/10)
        self.assertEqual(unit_products(m,'2029').iloc[0]['Potencia kW'],10)
        self.assertEqual(m['checks'].query('Estado == "Revisar"')['Control'].tolist(),
            ['Inversión económica de arranque','Activos en especie conciliados'])

    def test_calendar_excludes_other_product(self):
        tasks=pd.DataFrame({'ID':['a','b'],'Proyecto':['Turbina de 10 kW','Turbina de 80 kW'],
            'Paquete / línea':['Hito Producto 10 kW','Hito Producto 80 kW'],
            'Fin previsto actual':pd.to_datetime(['2027-01-31','2028-01-31'])})
        cash=pd.DataFrame({'ID actividad':['a','b'],'_date':pd.to_datetime(['2027-01-01','2028-01-01']),
            'Pendiente validado CLP':[100,900],'Referencia por validar CLP':[20,80]})
        result=project_calendar10(tasks,cash,pd.Timestamp('2026-11-13'))
        self.assertEqual(result['total'],120)
        self.assertEqual(result['milestones']['Paquete / línea'].tolist(),['Hito Producto 10 kW'])

    def test_executive_pdf(self):
        pdf=build_report10(model(),'USD',980,project_data=project())
        self.assertTrue(pdf.startswith(b'%PDF'))
        self.assertEqual(pdf.count(b'/Type /Page\n'),7)

    def test_full_view_theme_and_interactions(self):
        script='''
import json
from pathlib import Path
import streamlit as st
from tests.test_valuation10 import model, project
import valuation10_view as view
import valuation10_report as report
import market_study
import analysis_option
st.session_state.setdefault('option4_currency','USD')
st.session_state.setdefault('option4_exchange_rate',980.)
p=project()
view.load_valuation10=lambda revision:model()
view.load_cost_report=lambda revision:p['costs']
report.load_project10=lambda revision:p
market= json.loads(Path('data/market_study.json').read_text())
market['live']=False
market_study.load_market_study=lambda revision:market
analysis_option.load_workbook=lambda revision:(p['costs']['scope'],p['cash'],p['cutoff'],'snapshot')
st.segmented_control=st.radio
view.render_valuation10(1)
'''
        app=AppTest.from_string(script,default_timeout=60).run()
        self.assertFalse(app.exception)
        from valuation10_view import MAIN_TABS
        labels=[tab.label for tab in app.tabs]
        self.assertTrue(all(label in labels for label in MAIN_TABS))
        self.assertEqual(app.tabs[0].label,'Evaluación 10 kW')
        self.assertFalse(app.error)
        html=' '.join(item.proto.body for item in app.get('html'))
        self.assertIn('SUB BLOQUE 4 · TURBINA DE 10 kW',html)
        self.assertIn('#6941A5',html)
        self.assertEqual(chart_palette.get(),{})
        app.slider(key='option4_valuation10_summary_lcoe_factor').set_value(40).run()
        self.assertFalse(app.exception)
        app.session_state['option4_currency']='CLP'
        app.run()
        self.assertFalse(app.exception)


if __name__=='__main__':unittest.main()
