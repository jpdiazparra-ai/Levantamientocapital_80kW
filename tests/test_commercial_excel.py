"""Excel preserves the report's scope, currency, missing amounts and detail IDs."""
from io import BytesIO
import unittest

import openpyxl
import pandas as pd
from streamlit.testing.v1 import AppTest

from commercial_analysis import commercial_breakdown, commercial_composition_scope
from commercial_excel import build_commercial_excel


def tasks():
    return pd.DataFrame({
        'ID': ['A1', 'A2', 'A3'], 'Proyecto': ['Turbina de 80 kW'] * 3,
        'Hito objetivo': ['Producto 80 kW'] * 3,
        'Sistema': ['Aspas', 'Aspas', 'Fundaciones y anclajes'],
        'Paquete / línea': ['Fabricación', 'Fabricación', 'Obra'],
        'Actividad / entregable': ['Fabricar aspas', '=1+1', 'Fundación'],
        'Criterio': ['HH', 'HH', 'Insumo'], 'Cantidad': [12., float('nan'), 1.],
        'Comercial anterior': [100., float('nan'), 200.],
        'Presupuesto vigente': [120., 50., 220.],
        'Presupuesto referencia': [10., float('nan'), 200.],
        'Costo para producto': ['Aplica'] * 3,
        'Registros conciliados': ['Validado', 'Pendiente', 'Validado'],
    })


class CommercialExcelTests(unittest.TestCase):
    def test_numeric_amounts_missing_values_sources_and_totals(self):
        for currency in ('USD', 'CLP'):
            for mode in ('Total', 'Comercial'):
                scope = commercial_composition_scope(tasks(), mode)
                details = scope.drop(columns=['Presupuesto referencia', 'Costo para producto'])
                context = dict(project='Turbina de 80 kW', mode=mode,
                    selection='Todos los sistemas · Todas las líneas', currency=currency,
                    fx_rate=980., generated_at='16-11-2026 15:00', cutoff=None,
                    consulted_at='16-11-2026', source_url='https://example.com/costos',
                    system_summary=commercial_breakdown(scope, 'Sistema').to_dict('records'))
                payload = build_commercial_excel(details, context)
                book = openpyxl.load_workbook(BytesIO(payload), data_only=True)
                formulas = openpyxl.load_workbook(BytesIO(payload), data_only=False)
                with self.subTest(currency=currency, mode=mode):
                    self.assertEqual(book.sheetnames, ['Resumen', 'Detalle'])
                    sheet = book['Detalle']
                    columns = {cell.value: cell.column for cell in sheet[6]}
                    amount_col = columns['Monto comercial · ' + currency]
                    self.assertEqual(sheet.cell(7, amount_col).value, 100.)
                    self.assertIsNone(sheet.cell(8, amount_col).value)
                    self.assertEqual(sheet.cell(8, columns['Actividad / entregable']).value, '=1+1')
                    self.assertEqual(formulas['Detalle'].cell(8, columns['Actividad / entregable']).data_type, 's')
                    self.assertEqual(sheet.max_row, 6 + len(scope))
                    self.assertEqual(sheet.freeze_panes, 'C7')
                    self.assertEqual(len(sheet.tables), 1)
                    total = next(row for row in book['Resumen'] if row[0].value == 'TOTAL INFORMADO')
                    self.assertEqual(total[1].value, scope['Comercial anterior'].sum())
                    self.assertEqual(total[2].value, scope['Presupuesto vigente'].sum())
                    self.assertTrue(formulas['Resumen'].cell(total[1].row, 2).value.startswith('=SUM(Detalle!'))
                    self.assertEqual(book['Resumen']['B11'].value, context['source_url'])
                    self.assertEqual(len(book['Resumen']._charts), 1)

    def test_full_report_has_pdf_and_excel_buttons_with_filtered_scope(self):
        import streamlit as st
        self.addCleanup(setattr, st, 'segmented_control', st.segmented_control)
        app = AppTest.from_string('''
import streamlit as st
import commercial_analysis as commercial
from tests.test_commercial_excel import tasks
st.segmented_control=st.radio
st.session_state.setdefault('option4_commercial_composition_Turbina_de_80_kW','Comercial')
commercial.cached_commercial_pdf=lambda details, context: b'%PDF-test'
commercial.render_commercial_analysis(tasks(), fixed_project='Turbina de 80 kW', embedded=True)
''', default_timeout=20).run()
        self.assertFalse(app.exception)
        downloads = app.get('download_button')
        self.assertTrue(any('informe completo' in item.label and 'PDF' in item.label for item in downloads))
        self.assertTrue(any('informe completo' in item.label and 'Excel' in item.label for item in downloads))
        app.radio[0].set_value('Total').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('download_button')), 2)


if __name__ == '__main__':
    unittest.main()
