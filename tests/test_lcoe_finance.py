import unittest
import numpy as np
from lcoe_finance import levelized_cost,lcoe_profiles


class LevelizedCostTests(unittest.TestCase):
    def args(self):return dict(capacity_kw=80,capacity_factor=.3,capex=100000,fixed_om=2000,variable_om=.01,years=20,rate=.08)

    def test_equals_capital_recovery_formula_for_constant_costs_and_energy(self):
        args=self.args();result=levelized_cost(**args)
        crf=.08*(1.08**20)/(1.08**20-1)
        expected=(100000*crf+2000)/(80*8760*.3)+.01
        self.assertAlmostEqual(result['lcoe'],expected)
        self.assertEqual(result['energy_y1'],80*8760*.3)
        self.assertAlmostEqual(sum(result['lcoe_components'].values()),result['lcoe'])
        self.assertEqual(len(result['flows']),21)
        self.assertEqual(result['flows'].iloc[0]['CAPEX inicial'],100000)
        self.assertEqual(result['flows'].iloc[0]['Energía neta kWh'],0)

    def test_zero_discount_and_one_year(self):
        r=levelized_cost(**{**self.args(),'years':1,'rate':0})
        self.assertAlmostEqual(r['lcoe'],102000/(80*8760*.3)+.01)

    def test_factor_sensitivity_does_not_double_count_variable_om(self):
        a=levelized_cost(**self.args());b=levelized_cost(**{**self.args(),'capacity_factor':.6})
        self.assertAlmostEqual(a['lcoe_components']['O&M variable'],.01)
        self.assertAlmostEqual(b['lcoe_components']['O&M variable'],.01)
        self.assertAlmostEqual((a['lcoe']-.01)/2,b['lcoe']-.01)

    def test_replacement_retirement_degradation_and_real_om_growth(self):
        args={**self.args(),'degradation':.01,'om_growth':.02,'replacement_cost':20000,'replacement_year':10,'decommission_cost':10000}
        r=levelized_cost(**args);f=r['flows']
        self.assertAlmostEqual(f.iloc[2]['Energía neta kWh'],f.iloc[1]['Energía neta kWh']*.99)
        self.assertAlmostEqual(f.iloc[2]['O&M fijo'],2040)
        self.assertAlmostEqual(r['components']['Reposición'],20000/1.08**10)
        self.assertAlmostEqual(r['components']['Retiro'],10000/1.08**20)
        self.assertGreater(r['lcoe'],levelized_cost(**self.args())['lcoe'])

    def test_invalid_or_missing_inputs_do_not_produce_an_lcoe(self):
        for overrides in [{'capacity_factor':0},{'capacity_factor':1.01},{'capex':-1},{'fixed_om':float('nan')},{'years':1.5},{'rate':-.01},{'degradation':1},{'replacement_cost':100,'replacement_year':21}]:
            with self.subTest(overrides=overrides),self.assertRaises(ValueError):levelized_cost(**{**self.args(),**overrides})

    def test_currency_scaling_is_linear(self):
        args=self.args();usd=levelized_cost(**args)
        clp=levelized_cost(**{**args,'capex':args['capex']*925,'fixed_om':args['fixed_om']*925,'variable_om':args['variable_om']*925})
        self.assertAlmostEqual(clp['lcoe'],usd['lcoe']*925)
        self.assertAlmostEqual(clp['pv_energy'],usd['pv_energy'])

    def test_technical_profiles_reconcile_to_energy_costs_and_final_lcoe(self):
        r=levelized_cost(**{**self.args(),'degradation':.01,'replacement_cost':20000,'replacement_year':10,'decommission_cost':10000})
        original=r['flows'].copy(deep=True);p=lcoe_profiles(r)
        self.assertTrue(original.equals(r['flows']))
        self.assertTrue(np.isnan(p.iloc[0]['LCOE acumulado']))
        self.assertAlmostEqual(p.iloc[-1]['LCOE acumulado'],r['lcoe'])
        self.assertAlmostEqual(p.iloc[-1]['Energía acumulada MWh'],original['Energía neta kWh'].sum()/1000)
        self.assertEqual(p.iloc[0]['Costo operativo anual'],0)
        self.assertEqual(p.loc[p['Año'].eq(10),'Reposición y retiro'].iloc[0],20000)
        self.assertEqual(p.iloc[-1]['Reposición y retiro'],10000)
        self.assertLess(p.iloc[-1]['Energía anual MWh'],p.iloc[1]['Energía anual MWh'])
        expected=(original.iloc[0]['VP costos']+original.iloc[1]['VP costos'])/original.iloc[1]['VP energía kWh']
        self.assertAlmostEqual(p.iloc[1]['LCOE acumulado'],expected)


if __name__=='__main__':unittest.main()
