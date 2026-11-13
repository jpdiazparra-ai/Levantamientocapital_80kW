"""Turbine selection must preserve budget and cash scope across every dimension."""
import json
import unittest
import pandas as pd
from streamlit.testing.v1 import AppTest
from analysis_option import capital_turbine_scope, capital_comparison_summary


def sample():
    tasks=pd.DataFrame({
        'ID':['a','b','c','d'], 'Proyecto':['Piloto 10kW','Piloto 80kW','Producto 10 kW','Piloto 100kW'],
        'Sistema':['Eléctrico','Eléctrico','Mecánico','Eléctrico'],
        'Hito objetivo':['Producto','Producto','Piloto','Producto'],
        'Presupuesto referencia':[100.,400.,200.,900.], '_progress':[.5,.25,0.,0.]})
    cash=pd.DataFrame({'ID actividad':['a','a','b','c','d'],
        'Referencia por validar CLP':[10.,20.,40.,float('nan'),90.],
        'Pendiente validado CLP':[1.,2.,4.,float('nan'),9.]})
    return tasks,cash


class CapitalComparisonTests(unittest.TestCase):
    def test_individual_scope_and_totals_in_all_tabs(self):
        tasks,cash=sample()
        for selection,expected_ids,budget,pending,valid in [
                ('10 kW',{'a','c'},300,30,3),('80 kW',{'b'},400,40,4)]:
            scoped=capital_turbine_scope(tasks,selection)
            self.assertEqual(set(scoped.ID),expected_ids)
            for dimension in ['Proyecto','Hito objetivo','Sistema']:
                result=capital_comparison_summary(scoped,cash,dimension,selection)
                self.assertEqual(result['Presupuesto referencia'].sum(),budget)
                self.assertEqual(result['Caja por validar'].sum(),pending)
                self.assertEqual(result['Caja validada'].sum(),valid)
                self.assertAlmostEqual(result['Participación %'].sum(),100)
        result=capital_comparison_summary(capital_turbine_scope(tasks,'10 kW'),cash,'Sistema','10 kW')
        self.assertTrue(pd.isna(result.set_index('Sistema').loc['Mecánico','Caja por validar']))

    def test_joint_systems_stay_separate_and_preserve_all_project_totals(self):
        tasks,cash=sample()
        result=capital_comparison_summary(tasks,cash,'Sistema','Ambas turbinas')
        amounts=result.set_index('Sistema')['Presupuesto referencia']
        self.assertEqual(amounts['Eléctrico · 10 kW'],100)
        self.assertEqual(amounts['Eléctrico · 80 kW'],400)
        self.assertEqual(amounts['Eléctrico · Otros proyectos'],900)
        self.assertEqual(amounts.sum(),tasks['Presupuesto referencia'].sum())
        self.assertEqual(result['Caja por validar'].sum(),cash['Referencia por validar CLP'].sum())

    def test_selector_updates_charts_downloads_and_empty_state(self):
        app=AppTest.from_string('''
import streamlit as st
from tests.test_capital_comparison import sample
from analysis_option import render_capital_dimensions
tasks,cash=sample()
if st.session_state.get('empty',False):tasks=tasks.loc[tasks.Proyecto.eq('Piloto 80kW')]
render_capital_dimensions(tasks,cash)
''',default_timeout=20).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('plotly_chart')),6)
        specs=' '.join(json.dumps(json.loads(item.proto.spec),ensure_ascii=False) for item in app.get('plotly_chart'))
        self.assertIn('Eléctrico · 10 kW',specs)
        self.assertIn('Eléctrico · 80 kW',specs)
        select=app.selectbox(key='option4_capital_comparison_turbine')
        select.select('10 kW').run()
        self.assertFalse(app.exception)
        specs=' '.join(json.dumps(json.loads(item.proto.spec),ensure_ascii=False) for item in app.get('plotly_chart'))
        self.assertNotIn('80kW',specs)
        self.assertNotIn('100kW',specs)
        self.assertEqual(app.dataframe[2].value['Caja pendiente de cubrir'].sum(),33)
        app.selectbox(key='option4_capital_comparison_turbine').select('80 kW').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.dataframe[2].value['Caja pendiente de cubrir'].sum(),44)
        app.session_state['empty']=True
        app.selectbox(key='option4_capital_comparison_turbine').select('10 kW').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('plotly_chart')),0)
        self.assertTrue(app.info)
        app.selectbox(key='option4_capital_comparison_turbine').select('Ambas turbinas').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.dataframe[2].value['Caja pendiente de cubrir'].sum(),44)


if __name__=='__main__':unittest.main()
