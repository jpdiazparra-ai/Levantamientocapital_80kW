"""Whole monetary amounts preserve underlying values and small LCOE rates."""
import ast
from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch

import openpyxl

import display_currency
from commercial_report import _money
from valuation_report import Report
from valuation_lcoe import lcoe_text


class WholeMoneyDisplayTests(unittest.TestCase):
    def test_usd_and_clp_amounts_have_no_fractional_part(self):
        for currency, prefix in [('USD', 'US$ '), ('CLP', '$')]:
            with self.subTest(currency=currency), patch.dict(display_currency.st.session_state,
                    {'option4_currency': currency}, clear=False):
                self.assertEqual(display_currency.amount(165200682.001), prefix+'165.200.682')
                self.assertEqual(display_currency.amount(1234.75), prefix+'1.235')
                self.assertEqual(display_currency.amount(-1234.75), prefix+'-1.235')
                self.assertNotIn(',', display_currency.amount(165200682.75, compact=True))
                self.assertIn('%.0f', display_currency.currency_number_format())
                self.assertEqual(display_currency.amount(float('nan')), 'Sin informar')

    def test_pdf_money_matches_whole_amounts(self):
        self.assertEqual(_money(1234.75, 'USD'), 'US$ 1.235')
        self.assertEqual(_money(1234.75, 'CLP'), '$1.235')
        self.assertEqual(Report({}, 'USD', 980).money(1234.75), 'US$ 1.235')
        self.assertEqual(Report({}, 'CLP', 980).money(1234.75), '$1.210.055')

    def test_lcoe_keeps_fractional_rates(self):
        with patch.dict(display_currency.st.session_state, {'option4_currency': 'USD'}, clear=False):
            self.assertEqual(lcoe_text(.0319), 'US$ 0,0319')
            self.assertEqual(lcoe_text(.0319, True), 'US$ 31,90')

    def test_excel_format_hides_decimals_without_rounding_source_data(self):
        from commercial_excel import build_commercial_excel
        from commercial_analysis import commercial_breakdown
        from tests.test_commercial_excel import tasks
        details=tasks()
        details.loc[0, 'Comercial anterior']=1234.75
        payload=build_commercial_excel(details, dict(project='80 kW', mode='Solo equipo turbina',
            selection='Todas las líneas', currency='USD',
            system_summary=commercial_breakdown(details, 'Sistema').to_dict('records')))
        sheet=openpyxl.load_workbook(BytesIO(payload), data_only=True)['Detalle']
        column=next(cell.column for cell in sheet[6] if cell.value=='Monto comercial · USD')
        self.assertEqual(sheet.cell(7, column).value, 1234.75)
        self.assertEqual(sheet.cell(7, column).number_format, '"US$ "#,##0')
        self.assertEqual(details.loc[0, 'Comercial anterior'], 1234.75)

    def test_main_application_money_helpers_do_not_require_running_the_app(self):
        tree=ast.parse(Path('app.py').read_text())
        functions=[node for node in tree.body if isinstance(node, ast.FunctionDef)
            and node.name in ('format_usd', 'format_clp', 'format_compact_usd')]
        namespace={}
        exec(compile(ast.Module(body=functions, type_ignores=[]), '<formatters>', 'exec'), namespace)
        self.assertEqual(namespace['format_usd'](165200682.001), 'US$165.200.682')
        self.assertNotIn(',', namespace['format_compact_usd'](165200682.001))


if __name__ == '__main__':
    unittest.main()
