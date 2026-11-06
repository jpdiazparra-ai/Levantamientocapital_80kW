"""PDF data scope and conversion remain independent of Streamlit session state."""
import unittest
import pandas as pd
from valuation_report import Report, parse_technical, financial_bullets
from valuation_finance import unit_economics


class ExecutiveReportTests(unittest.TestCase):
    def test_technical_scope_uses_exact_power_and_natural_id_order(self):
        rows=[['ID','Hito objetivo','Actividad / entregable','Sistema'],
              ['A20','Producto 80 kW','Conjunto <80>','Eléctrico'],
              ['A3','Piloto 80KW','Rotor','Mecánica'],
              ['A4','Producto 10 kW','Otra turbina','Mecánica'],
              ['A8','Producto 800 kW','Otra potencia','Mecánica'],
              ['','Producto 80 kW','Nota sin ID','']]
        result=parse_technical(rows)
        self.assertEqual(result.ID.tolist(),['A3','A20'])
        self.assertEqual(result.iloc[1]['Actividad / entregable'],'Conjunto <80>')
        with self.assertRaises(ValueError):parse_technical([['columna desconocida']])

    def test_usd_is_not_converted_twice_and_percentages_are_invariant(self):
        usd=Report({},'USD',925);clp=Report({},'CLP',925)
        self.assertEqual(usd.money(1000),'US$ 1.000,00')
        self.assertEqual(clp.money(1000),'$925.000')
        self.assertEqual(usd.pct(.741),clp.pct(.741))
        self.assertEqual(usd.money(float('nan')),'Sin dato')

    def test_investment_bullets_identify_consolidated_not_sponsor_returns(self):
        scalars=dict(dcf=1000,npv_economic=500,irr_economic=.4,rate=.2,growth=.03,
            pre_money=100,primary=300,secondary=0,investor_share=.75,
            assets_in_kind=100,preop=20,spares=30,cash_y0=200,cash_target=100,
            advance_rate=.5,advance_days=60,terminal_weight=.2)
        initial=dict.fromkeys(['cost_10','cost_80','cogs','external_cost_10','external_cost_80',
            'units_10','units_80','sales_10','sales_80','opex_10','opex_80','sales','ebitda','fcff','economic_cf'],0)
        first=dict(initial,Año='2029',**{'Año modelo':1,'sales':300,'ebitda':190,'fcff':150,
            'economic_cf':150,'cost_10':30,'cost_80':50,'cogs':80,'units_10':2,'units_80':4,
            'sales_10':100,'sales_80':200,'opex_10':10,'opex_80':10})
        initial.update({'Año':'Año 0','Año modelo':0,'economic_cf':-100})
        model=dict(scalars=scalars,annual=pd.DataFrame([initial,first]),status='Propuesta')
        products,_=unit_economics(model,'2029')
        text=' '.join(label+' '+body for label,body in financial_bullets(model,products,Report(model,'USD',925)))
        self.assertIn('consolidados de 10 y 80 kW',text)
        self.assertIn('no la TIR del socio',text)
        self.assertIn('No es EBITDA por turbina',text)
        self.assertIn('Fabricación media US$ 12,50',text)


if __name__=='__main__':unittest.main()
