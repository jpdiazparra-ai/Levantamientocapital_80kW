"""Published deal terms retain their original units, comments and references."""
import unittest
from valuation_data import Sheet, parse_deal


class DealDetailsTests(unittest.TestCase):
    def test_terms_survive_row_changes_and_preserve_zero(self):
        rows = [
            ['', '', 'Condiciones de la operación'],
            [],
            ['', '', 'Aporte de capital a FW', '', '3.000.000', 'USD', '', 'Propuesta.'],
            ['', '', 'Año del modelo para desembolso', '', '0', 'año'],
            ['', '', 'Estado de la operación', '', 'Propuesta'],
            ['', '', 'Precio y participación accionaria'],
            ['', '', 'Participación final accionistas actuales', '', '15,0%', '', '', 'Reparto pendiente.'],
            ['', '', 'Aplicación de los fondos en FW'],
            ['', '', 'Pago a fundadores fuera de FW', '', '–', 'USD'],
            ['', '', 'Valorización del modelo y precio negociado'],
            ['', '', 'Diferencia negociación menos DCF', '', '(3.930.268)', 'USD'],
            ['', '', 'Criterios de lectura'],
            ['', '', 'Los fondos no están acreditados.'],
        ]
        terms, criteria = parse_deal(Sheet('02 Inversión y socios', rows))
        self.assertEqual(len(terms), 6)
        self.assertEqual(terms.iloc[0]['Valor'], 3000000)
        self.assertEqual(terms.iloc[0]['Referencia'], '02 Inversión y socios!E3')
        self.assertEqual(terms.iloc[0]['Observación'], 'Propuesta.')
        self.assertEqual(terms.iloc[1]['Valor'], 0)
        self.assertEqual(terms.iloc[2]['Valor fuente'], 'Propuesta')
        self.assertAlmostEqual(terms.iloc[3]['Valor'], .15)
        self.assertEqual(terms.iloc[3]['Unidad'], '%')
        self.assertEqual(terms.iloc[4]['Valor'], 0)
        self.assertEqual(terms.iloc[5]['Valor'], -3930268)
        self.assertEqual(criteria, ['Los fondos no están acreditados.'])


if __name__ == '__main__':
    unittest.main()
