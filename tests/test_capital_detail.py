"""Activity drill-down reconciles to its selected system without repeating budgets."""
import unittest
import pandas as pd
from streamlit.testing.v1 import AppTest
from capital_detail import system_details, package_details
from analysis_option import capital_turbine_labels, table_from
from tests.test_capital_comparison import sample


class CapitalDetailTests(unittest.TestCase):
    def test_budget_counted_once_and_cash_keeps_all_installments(self):
        tasks,cash=sample()
        tasks['_source_plan_row']=[6,7,11,12]
        tasks['_source_costs_row']=[9,10,14,15]
        categories=tasks.Sistema+' · '+capital_turbine_labels(tasks)
        detail,payments=system_details(tasks,cash,categories,'Eléctrico · 10 kW')
        self.assertEqual(detail.ID.tolist(),['a'])
        self.assertEqual(detail['Presupuesto referencia'].sum(),100)
        self.assertEqual(detail['Caja por validar'].sum(),30)
        self.assertEqual(detail['Caja validada'].sum(),3)
        self.assertEqual(len(payments),2)
        self.assertEqual(detail.iloc[0]['Referencia Plan'],'Plan · fila 6 · ID a')
        self.assertEqual(detail.iloc[0]['Referencia Costos'],'Costos · fila 9 · ID a')
        detail,payments=system_details(tasks,cash,categories,'Mecánico · 10 kW')
        self.assertTrue(pd.isna(detail.iloc[0]['Caja por validar']))

    def test_packages_group_multiple_ids_without_repeating_cash_or_budget(self):
        tasks,cash=sample()
        tasks['Paquete / línea']=['Gestión','Otro','Gestión','Otro']
        tasks.loc[tasks.ID.eq('c'),'Sistema']='Eléctrico'
        detail,payments=system_details(tasks,cash,tasks.Sistema+' · '+capital_turbine_labels(tasks),'Eléctrico · 10 kW')
        result=package_details(detail)
        self.assertEqual(len(result),1)
        self.assertEqual(result.iloc[0]['Paquete / línea'],'Gestión')
        self.assertEqual(result.iloc[0]['Presupuesto referencia'],300)
        self.assertEqual(result.iloc[0]['Caja por validar'],30)
        self.assertEqual(result.iloc[0]['Caja validada'],3)
        self.assertEqual(set(result.iloc[0]['IDs de origen'].split(' · ')),{'a','c'})
        self.assertEqual(result.iloc[0]['Registros de origen'],2)
        detail.loc[:,'Presupuesto referencia']=float('nan')
        self.assertTrue(pd.isna(package_details(detail).iloc[0]['Presupuesto referencia']))

    def test_pending_totals_match_chart_system_and_packages_excluding_paid_records(self):
        from analysis_option import capital_comparison_summary
        from capital_charts import comparison_figures
        from display_currency import chart_scale
        tasks,cash=sample()
        tasks['Paquete / línea']=['Cableado','Cableado','Estructura','Otro']
        # A paid activity remains in Plan's budget but has no pending cash record.
        tasks.loc[tasks.ID.eq('c'),'Sistema']='Eléctrico'
        cash=cash.loc[cash['ID actividad'].ne('c')]
        categories=tasks.Sistema+' · '+capital_turbine_labels(tasks)
        summary=capital_comparison_summary(tasks,cash,'Sistema','Ambas turbinas')
        system=summary.loc[summary.Sistema.eq('Eléctrico · 10 kW')].iloc[0]
        self.assertEqual(system['Presupuesto referencia'],300)
        self.assertEqual(system['Caja pendiente de cubrir'],33)
        detail,payments=system_details(tasks,cash,categories,'Eléctrico · 10 kW')
        self.assertEqual(detail.ID.tolist(),['a'])
        packages=package_details(detail)
        self.assertEqual(packages['Caja pendiente de cubrir'].sum(),system['Caja pendiente de cubrir'])
        self.assertEqual(packages['Caja pendiente de cubrir'].sum(),payments[['Referencia por validar CLP','Pendiente validado CLP']].sum().sum())
        fig,_=comparison_figures(summary,'Sistema')
        plotted=dict(zip(fig.data[0].y,fig.data[0].x))
        self.assertAlmostEqual(plotted['Eléctrico · 10 kW']*chart_scale(),33)

    def test_source_rows_preserve_blank_rows_and_original_sheet_order(self):
        raw=pd.DataFrame([['Title',''],['ID','Actividad'],['A1','Primera'],['',''],['A2','Segunda']])
        frame=table_from(raw,1,'ID')
        self.assertEqual(frame.attrs['source_rows'],{'A1':3,'A2':5})
        self.assertEqual(frame.ID.tolist(),['A1','A2'])

    def test_selected_system_renders_trace_and_clears_incompatible_scope(self):
        script='''
import streamlit as st
from tests.test_capital_comparison import sample
from analysis_option import render_capital_dimensions
tasks,cash=sample()
tasks['Actividad / entregable']=['Cableado 10','Cableado 80','Estructura 10','Otro proyecto']
tasks['_source_plan_row']=[6,7,8,9]
tasks['_source_costs_row']=[10,11,12,13]
st.session_state.setdefault('option4_capital_system_selected_group','Eléctrico · 10 kW')
render_capital_dimensions(tasks,cash)
'''
        app=AppTest.from_string(script,default_timeout=20).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe),5)
        details=app.dataframe[3].value
        self.assertEqual(details['IDs de origen'].tolist(),['a'])
        self.assertNotIn('Actividad / entregable',details.columns)
        self.assertEqual(details.iloc[0]['Referencia Plan'],'Plan · fila 6 · ID a')
        self.assertEqual(len(app.dataframe[4].value),2)
        self.assertTrue(any(button.proto.label=='Descargar líneas y paquetes' for button in app.get('download_button')))
        app.session_state['option4_currency']='CLP';app.run()
        self.assertFalse(app.exception)
        app.selectbox(key='option4_capital_comparison_turbine').select('80 kW').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe),3)
        app.session_state['option4_capital_system_selected_group']='Eléctrico'
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.dataframe[3].value['IDs de origen'].tolist(),['b'])
        app.session_state['option4_capital_system_selected_group']=None
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe),3)


if __name__=='__main__':unittest.main()
