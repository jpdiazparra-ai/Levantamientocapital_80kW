"""Reconcile the user's published unpaid budgets to balances and scheduled cash."""
from pathlib import Path
import unittest
import pandas as pd
from streamlit.testing.v1 import AppTest
from analysis_option import cash_from_costs, cash_reconciliation_data, number
from capital_charts import calendar_cash_rows
from display_currency import convert_workbook


def source():
    costs=pd.read_csv(Path(__file__).parent/'fixtures/cash_reconciliation.csv',dtype=str,keep_default_na=False)
    plan=costs[['ID','Proyecto','Actividad / entregable']].copy()
    return costs,plan


class CashReconciliationTests(unittest.TestCase):
    def test_live_snapshot_reconciles_pending_and_preserves_source_scheduling_blocks(self):
        costs,plan=source();cash=cash_from_costs(costs,plan)
        self.assertFalse(costs.ID.duplicated().any())
        reconciled=cash_reconciliation_data(costs,cash).set_index('Concepto')['Monto']
        self.assertEqual(reconciled.iloc[0],645475132)
        self.assertEqual(reconciled.iloc[1],10000000)
        self.assertEqual(reconciled.iloc[2],635475132)
        self.assertEqual(reconciled.iloc[3],160000)
        self.assertEqual(reconciled.iloc[4],635315132)
        self.assertEqual(reconciled.iloc[5],542409920)
        self.assertEqual(reconciled.iloc[6],92905212)
        self.assertEqual(cash['Referencia por validar CLP'].sum(),633446172)
        self.assertEqual(cash['Pendiente validado CLP'].sum(),1868960)
        self.assertNotIn('A518',cash['ID actividad'].tolist())
        self.assertNotIn('A519',cash['ID actividad'].tolist())
        scheduled=calendar_cash_rows(cash)
        self.assertEqual(scheduled['Referencia por validar CLP'].sum(),540540960)
        self.assertEqual(scheduled['Pendiente validado CLP'].sum(),1868960)
        blocked=cash[cash['Saldo pendiente CLP'].sub(cash['Caja programada CLP'].fillna(0)).gt(0)]
        self.assertEqual(len(blocked),75)
        self.assertEqual(set(blocked['Alerta caja']),{'ID duplicado'})

    def test_currency_conversion_applies_once_to_total_and_scheduled_cash(self):
        costs,plan=source();cash=cash_from_costs(costs,plan)
        _,converted=convert_workbook(plan,cash,number)
        self.assertAlmostEqual(converted['Referencia por validar CLP'].sum()*980,633446172,delta=.001)
        self.assertAlmostEqual(converted['Caja calendarizada por validar CLP'].sum()*980,540540960,delta=.001)
        self.assertAlmostEqual(calendar_cash_rows(converted)['Referencia por validar CLP'].sum()*980,540540960,delta=.001)

    def test_calendar_shows_reconciliation_and_pending_totals(self):
        app=AppTest.from_string('''
import pandas as pd
import streamlit as st
from tests.test_cash_reconciliation import source
from analysis_option import cash_from_costs,render_disbursement_calendar
costs,plan=source()
cash=cash_from_costs(costs,plan)
tasks=costs.copy()
tasks['Paquete / línea']=''
tasks['Fin previsto actual']=pd.NaT
st.session_state['option4_currency']='CLP'
render_disbursement_calendar(tasks,cash,pd.Timestamp('2026-11-13'))
''',default_timeout=30).run()
        self.assertFalse(app.exception)
        text=' '.join(item.proto.body for item in app.get('html'))
        self.assertIn('$635.315.132',text)
        self.assertIn('$633.446.172',text)
        self.assertIn('$1.868.960',text)
        self.assertTrue(any('Conciliación' in item.label for item in app.expander))
        self.assertEqual(len(app.dataframe[1].value),75)


if __name__=='__main__':unittest.main()
