"""Grouped projection presentation keeps the selected source values intact."""
import unittest

import pandas as pd

from projection_matrix import matrix_html


class ProjectionMatrixTests(unittest.TestCase):
    def test_selected_years_amounts_percentages_and_balances(self):
        frame=pd.DataFrame({'Año':['2029','2030'], 'units_80':[100,110],
            'sales':[1000.75,2000.25], 'ebitda_margin':[.063,.083],
            'cash_free':[100.,150.]})
        original=frame.copy(deep=True)
        fields=[('Entregas','units_80','n'),('Ventas','sales','m'),
            ('Margen EBITDA','ebitda_margin','p'),('Caja libre al cierre','cash_free','m')]
        usd=matrix_html(frame,fields,currency='USD',fx=980,title='Proyección anual')
        clp=matrix_html(frame,fields,currency='CLP',fx=980,title='Proyección anual')
        self.assertIn('Producción y capacidad',usd)
        self.assertIn('Resultados del negocio',usd)
        self.assertIn('Flujo y posición de caja',usd)
        self.assertIn('1.001',usd)
        self.assertIn('2.000',usd)
        self.assertIn('980.735',clp)
        self.assertIn('1.960.245',clp)
        self.assertIn('6,3%',usd)
        self.assertIn('6,3%',clp)
        self.assertIn('saldo al cierre',usd)
        self.assertIn('>150</td>',usd)
        self.assertNotIn('>250</td>',usd)
        self.assertIn('2029 — 2030',usd)
        self.assertIn('last-year',usd)
        pd.testing.assert_frame_equal(frame,original)

    def test_missing_and_negative_values_and_safe_labels(self):
        frame=pd.DataFrame({'Año':['2029','2030'], 'fcff':[float('nan'),-1000.75]})
        markup=matrix_html(frame,[('Flujo <libre>','fcff','m')],
            currency='USD',fx=980,title='Caja <anual>',theme='violet')
        self.assertIn('Sin informar',markup)
        self.assertIn('negative',markup)
        self.assertIn('-1.001',markup)
        self.assertIn('Flujo &lt;libre&gt;',markup)
        self.assertIn('Caja &lt;anual&gt;',markup)
        self.assertNotIn('<libre>',markup)
        self.assertIn('projection-matrix violet',markup)


if __name__ == '__main__':
    unittest.main()
