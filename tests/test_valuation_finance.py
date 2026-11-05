"""Financial invariants independent of published spreadsheet revisions."""
import math
import unittest

import pandas as pd

from valuation_finance import complete_sum, mix_analysis, payback, projection_diagnostics, reprice_dcf, unit_economics


class FinancialAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.model = {
            'scalars': {'terminal_cf': 30},
            'annual': pd.DataFrame({
                'Año': ['Año 0', '2029', '2030'], 'Año modelo': [0, 1, 2],
                'fcff': [-100, 80, 90], 'economic_cf': [-150, 80, 90],
            }),
        }

    def test_discounting_terminal_and_rate_domain(self):
        explicit = -100 + 80 / 1.2 + 90 / 1.2**2
        value = reprice_dcf(self.model, .2, .03)
        self.assertAlmostEqual(value['dcf'], explicit + 30 / (.2-.03) / 1.2**2)
        self.assertAlmostEqual(value['npv_economic'], explicit - 50)
        self.assertEqual(reprice_dcf(self.model, .2, .9, False)['pv_terminal'], 0)
        self.assertLess(reprice_dcf(self.model, .25, .03)['dcf'], value['dcf'])
        with self.assertRaises(ValueError):
            reprice_dcf(self.model, .03, .03)

    def test_payback_and_missing_information(self):
        self.assertAlmostEqual(payback([-100, 60, 60]), 1 + 40/60)
        self.assertTrue(math.isnan(payback([-100, 20, 20])))
        self.assertTrue(math.isnan(complete_sum([1, float('nan')])))
        self.model['annual'].loc[1, 'fcff'] = float('nan')
        with self.assertRaises(ValueError):
            reprice_dcf(self.model, .2, .03)

    def test_product_cost_allocation_prevents_double_counting(self):
        row = {'Año': '2029', 'cogs': 100, 'cost_10': 30, 'cost_80': 50,
               'external_cost_10': 5, 'external_cost_80': 15,
               'units_10': 10, 'units_80': 20, 'sales_10': 100, 'sales_80': 300,
               'opex_10': 10, 'opex_80': 20}
        model = {'annual': pd.DataFrame([row])}
        products, gap = unit_economics(model, '2029')
        self.assertEqual(gap, 0)
        self.assertEqual(products['Fabricación total'].sum(), 100)
        simulation = mix_analysis(products, 2/3, 30, 70, 20)
        self.assertAlmostEqual(simulation['ebitda'], 200)
        self.assertEqual(simulation['external'], 10)
        model['annual'].loc[0, 'cogs'] = 80
        products, gap = unit_economics(model, '2029')
        self.assertEqual(products['Fabricación total'].sum(), 80)
        model['annual'].loc[0, 'cogs'] = 200
        products, gap = unit_economics(model, '2029')
        self.assertTrue(products['Contribución total'].isna().all())

    def test_projection_uses_closing_cash_and_weighted_margin(self):
        frame = pd.DataFrame({'sales': [100, 200], 'ebitda': [10, 40],
                              'fcff': [5, 25], 'cash_free': [50, 80],
                              'external': [2, 4], 'units_total': [10, 20]})
        value = projection_diagnostics(frame)
        self.assertEqual(value['cash_close'], 80)
        self.assertAlmostEqual(value['margin'], 50/300)
        self.assertEqual(value['fcff'], 30)
        self.assertEqual(value['cagr'], 1)


if __name__ == '__main__':
    unittest.main()
