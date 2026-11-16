"""Zero supplier margin ties displayed prices and owner LCOE to sheet 07."""
import importlib
import unittest
from unittest.mock import patch
import pandas as pd


class ZeroSupplierMarginTests(unittest.TestCase):
    def model(self, margin='0%', price='50.000'):
        return {'raw': {
            '07 Ventas y producción': [
                ['', '', 'Costo equivalente con margen proveedor', margin, ''],
                ['', '', 'Precio Venta', 'USD', price]],
            '03 Supuestos': [['', '', 'IVA referencial', '', '19%']]}}

    def test_zero_margin_uses_sheet07_for_net_vat_and_lcoe(self):
        for cap in (10, 80):
            unit=importlib.import_module(f'valuation{cap}_unit')
            lcoe=importlib.import_module(f'valuation{cap}_lcoe')
            for fx in (925., 1000.):
                with self.subTest(capacity=cap, fx=fx):
                    m=self.model()
                    prices=getattr(unit, f'sale_prices{cap}')(m, fx)
                    self.assertEqual(prices['net'], 50000.)
                    self.assertEqual(prices['gross'], 59500.)
                    self.assertEqual(prices['net_kw'], 50000./cap)
                    self.assertEqual(prices['gross_kw'], 59500./cap)
                    a=getattr(lcoe, f'summary_lcoe{cap}')(m, .35, fx)
                    self.assertEqual(a['capex'], prices['net'])
                    self.assertEqual(a['price_source'], 'Precio calculado · hoja 07')
                    b=getattr(lcoe, f'summary_lcoe{cap}')(self.model(price='25.000'), .35, fx)
                    self.assertAlmostEqual(a['lcoe'], b['lcoe']*2)
                    self.assertEqual(a['energy_y1'], b['energy_y1'])

    def test_overview_shows_sheet07_price_and_vat_row(self):
        from streamlit.testing.v1 import AppTest
        for cap in (10, 80):
            script = """
import streamlit as st
import valuationCAP_view as view
st.session_state['option4_currency']='USD'
view.load_cost_report=lambda revision: {'totals': {'Comercial anterior': 1000., 'Informadas': 1, 'Partidas': 1}}
view.unit_cost_overviewCAP(MODEL)
view.summary_lcoe_panelCAP(MODEL)
""".replace('CAP', str(cap)).replace('MODEL', repr(dict(self.model(), fetched_at='test')))
            with self.subTest(capacity=cap):
                app=AppTest.from_string(script, default_timeout=20).run()
                self.assertFalse(app.exception)
                card=' '.join(item.proto.body for item in app.get('html'))
                self.assertIn('Precio de venta · sin IVA', card)
                self.assertIn('Precio de venta · con IVA', card)
                self.assertIn('US$ 50.000,00', card)
                self.assertIn('US$ 59.500,00', card)
                self.assertIn('precio calculado · hoja 07', card)
                self.assertEqual(len(app.get('plotly_chart')), 2)

    def test_positive_margin_keeps_existing_sale_price(self):
        for cap in (10, 80):
            unit=importlib.import_module(f'valuation{cap}_unit')
            with patch.object(unit, f'commercial_unit{cap}', return_value={'Precio de venta': 75000.}):
                prices=getattr(unit, f'sale_prices{cap}')(self.model(margin='20%'), 980.)
                self.assertEqual(prices['net'], 75000.)

    def test_missing_sheet07_price_does_not_fall_back_to_initial_price(self):
        for cap in (10, 80):
            unit=importlib.import_module(f'valuation{cap}_unit')
            lcoe=importlib.import_module(f'valuation{cap}_lcoe')
            m=self.model(price='')
            self.assertTrue(pd.isna(getattr(unit, f'sale_prices{cap}')(m, 980.)['net']))
            with self.assertRaises(ValueError):
                getattr(lcoe, f'summary_lcoe{cap}')(m, .35, 980.)


if __name__ == '__main__':
    unittest.main()
