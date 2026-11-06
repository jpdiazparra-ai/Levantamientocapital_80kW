import unittest
import pandas as pd
from valuation_costs import cost_report_data


class TurbineCostReportTests(unittest.TestCase):
    def setUp(self):
        self.plan=[['ID','Hito objetivo','Sistema','Paquete / línea','criterio','Unidades','Costo para producto'],
            ['A1','Producto 10 kW','Eléctrico','Línea común','HH','999','No aplica'],
            ['A2','Producto 80 kW','Eléctrico','Línea común','HH','999','Aplica'],
            ['A3','Producto 80 kW','Aspas','Fabricación','HH','999','Aplica'],
            ['A4','Producto 80 kW','Aspas','Fabricación','HH','999','Aplica'],
            ['A5','Producto 80 kW','Mecánica','Línea común','Insumo','999','Aplica'],
            ['A6','Producto 800 kW','Mecánica','Otra','HH','999','Aplica']]
        self.costs=[['ID','Hito objetivo','Costo para producto','Comercial anterior','Presupuesto vigente','Cantidad'],
            ['A1','Producto 80 kW','Aplica','1.000','1.200','12'],
            ['A2','Producto 10 kW','Aplica','99.999','99.999','123'],
            ['A3','Producto 80 kW','No aplica','99.999','99.999','123'],
            ['A4','Producto 80 kW','Aplica','—','500',''],
            ['A5','Producto 80 kW','Aplica','100','200','3'],
            ['A6','Producto 800 kW','Aplica','99.999','99.999','123']]

    def test_costos_controls_product_scope_and_hh_use_cost_quantities(self):
        result=cost_report_data(self.plan,self.costs);t=result['totals']
        self.assertEqual(set(result['scope'].ID),{'A1','A4','A5'})
        self.assertEqual(t['Comercial anterior'],1100)
        self.assertEqual(t['Presupuesto vigente'],1900)
        self.assertEqual(t['HH'],12)
        self.assertEqual(t['HH pendientes'],1)
        self.assertEqual(t['Informadas'],2)
        self.assertEqual(t['Partidas'],3)
        self.assertAlmostEqual(t['Variación %'],800/1100*100)
        self.assertEqual(len(result['lines']),3)  # Equal line names in distinct systems stay separate.
        self.assertEqual(result['systems']['Monto comercial · CLP'].sum(min_count=1),1100)
        self.assertEqual(result['lines']['Presupuesto'].sum(min_count=1),1900)
        self.assertTrue(pd.isna(result['scope'].set_index('ID').at['A4','Comercial anterior']))

    def test_unmatched_eligible_costs_are_not_silently_omitted(self):
        self.costs.append(['A99','Producto 80 kW','Aplica','9.999','9.999','1'])
        with self.assertRaisesRegex(ValueError,'A99'):cost_report_data(self.plan,self.costs)

    def test_duplicate_ids_cannot_double_the_report(self):
        self.costs.append(self.costs[1])
        with self.assertRaisesRegex(ValueError,'duplicados'):cost_report_data(self.plan,self.costs)


if __name__=='__main__':unittest.main()
