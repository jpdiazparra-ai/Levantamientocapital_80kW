"""The equipment selector filters installed costs in both unit overviews."""
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest


class CommercialScopeUITests(unittest.TestCase):
    def test_selector_keeps_selection_on_rerun(self):
        app = AppTest.from_string('''
import streamlit as st
from commercial_analysis import render_commercial_scope, commercial_scope_label
mode = render_commercial_scope('Turbina de 80 kW')
st.write(commercial_scope_label(mode))
''').run()
        self.assertFalse(app.exception)
        self.assertIn('Turbina + instalación', app.markdown[0].value)
        app.button_group[0].set_value(['Comercial']).run()
        self.assertFalse(app.exception)
        self.assertIn('Solo equipo turbina', app.markdown[0].value)
        # AppTest exposes single-selection button groups as lists when setting state.
        app.button_group[0].set_value(['Comercial']).run()
        self.assertIn('Solo equipo turbina', app.markdown[0].value)

    def test_unit_overviews_filter_installation_and_coverage(self):
        import valuation10_view
        import valuation80_view
        scope = pd.DataFrame({
            'Sistema': ['Aspas', 'Fundaciones y anclajes', 'Montaje y Logística', 'Eléctrico'],
            'Comercial anterior': [100., 200., 300., float('nan')],
            'Presupuesto vigente': [120., 220., 320., 50.],
        })
        data = dict(base=10., before_margin=20., with_margin=30., final_is_price=False,
                    margin=.1, references={}, labels={})
        for capacity, module in [(10, valuation10_view), (80, valuation80_view)]:
            for mode, subtotal, coverage in [('Total', 600., '3/4'), ('Comercial', 100., '1/2')]:
                with self.subTest(capacity=capacity, mode=mode):
                    with patch.object(module, 'load_cost_report', return_value={'scope': scope, 'totals': {'Comercial anterior': 600., 'Informadas': 3, 'Partidas': 4}}), \
                         patch.object(module, f'unit_cost_inputs{capacity}', return_value=data), \
                         patch.object(module, f'sale_prices{capacity}', return_value=dict(net=40., gross=48., vat_rate=.2)), \
                         patch.object(module, 'exchange_rate', return_value=1.), \
                         patch.object(module.st, 'html') as rendered, \
                         patch.object(module, 'plot'), \
                         patch.object(module, 'money', side_effect=lambda value: str(value)):
                        getattr(module, f'unit_cost_overview{capacity}')({'fetched_at': 'test'}, mode)
                        card = rendered.call_args_list[0].args[0]
                        self.assertIn(f'<td>{subtotal}</td>', card)
                        self.assertIn(coverage+' partidas', card)


if __name__ == '__main__':
    unittest.main()
