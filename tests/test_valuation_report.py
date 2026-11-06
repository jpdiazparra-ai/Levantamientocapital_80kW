"""PDF data scope and conversion remain independent of Streamlit session state."""
import unittest
import re
import pandas as pd
from valuation_report import Report, parse_technical, financial_bullets, five_year_summary, build_executive_pdf
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
        self.assertEqual(usd.cost_money(925000),'US$ 1.000,00')
        self.assertEqual(clp.cost_money(925000),'$925.000')

    def test_investment_bullets_identify_consolidated_not_sponsor_returns(self):
        scalars=dict(dcf=1000,npv_economic=500,irr_economic=.4,rate=.2,growth=.03,
            pre_money=100,primary=300,secondary=0,investor_share=.75,
            assets_in_kind=100,preop=20,spares=30,cash_y0=200,cash_target=100,
            advance_rate=.5,advance_days=60,terminal_weight=.2)
        initial=dict.fromkeys(['cost_10','cost_80','cogs','external_cost_10','external_cost_80',
            'units_10','units_80','sales_10','sales_80','opex_10','opex_80','sales','ebitda','fcff','economic_cf','cash_free','external','units_total'],0)
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

    def test_five_year_summary_uses_weighted_margin_and_excludes_later_years(self):
        frame=pd.DataFrame({'Año':['Año 0',*[str(2029+i) for i in range(10)]],
            'Año modelo':list(range(11)),'sales':[0,100,200,300,400,500,100000,100000,100000,100000,100000],
            'ebitda':[0,10,40,90,160,250,90000,90000,90000,90000,90000],
            'fcff':[0,1,2,3,4,5,99999,99999,99999,99999,99999],
            'cash_free':[0]+[7]*10,'external':[0]*11,'units_total':[0]+[1]*10})
        summary=five_year_summary({'annual':frame})
        self.assertEqual((summary['start'],summary['end'],summary['years']),('2029','2033',5))
        self.assertEqual(summary['sales'],1500)
        self.assertEqual(summary['ebitda'],550)
        self.assertAlmostEqual(summary['margin'],550/1500)
        self.assertNotAlmostEqual(summary['margin'],.3)
        self.assertEqual(summary['fcff'],15)

    def test_report_has_exactly_five_pages_in_each_currency(self):
        scalars={key:100. for key in ['dcf','npv_cash','npv_economic','pre_money','post_money','primary','secondary',
            'assets_in_kind','preop','spares','cash_y0','cash_target','advance_days','economic_investment',
            'cash_required','target_funding','historical_wc','sales_y1','ebitda_y1','fcff_y1','model_fx']}
        scalars.update(rate=.2,growth=.03,irr_economic=.4,advance_rate=.5,terminal_weight=.2,investor_share=.75,founder_share=.25)
        annual=pd.DataFrame([dict(Año='Año 0' if i==0 else str(2028+i),**{
            'Año modelo':i,'sales':300,'sales_10':100,'sales_80':200,'ebitda':190,'ebitda_margin':190/300,
            'fcff':150,'economic_cf':-100 if i==0 else 150,'cost_10':30,'cost_80':50,'cogs':80,
            'external_cost_10':0,'external_cost_80':0,'units_10':2,'units_80':4,'opex_10':10,'opex_80':10,
            'cash_free':200,'external':0,'units_total':6,'capex':0,'advances':0}) for i in range(11)])
        model=dict(scalars=scalars,annual=annual,status='Propuesta',scenario='Base',production='Comercial',
            fetched_at='06-11-2026 10:00',checks=pd.DataFrame({'Estado':['Conciliado']}),pending=pd.DataFrame())
        technical=parse_technical([['ID','Hito objetivo','Actividad / entregable','Sistema'],['A533','Producto 80 kW','Mástil según plano','Mecánica']])
        for currency in ['USD','CLP']:
            from valuation_costs import cost_report_data
            cost_data=cost_report_data([['ID','Hito objetivo','Sistema','Paquete / línea','Criterio'],['A533','Producto 80 kW','Mecánica','Mástil','HH']],
                [['ID','Hito objetivo','Costo para producto','Comercial anterior','Presupuesto vigente','Cantidad'],['A533','Producto 80 kW','Aplica','100','125','2']])
            data=build_executive_pdf(model,technical,currency,925,cost_data=cost_data)
            self.assertTrue(data.startswith(b'%PDF'))
            self.assertEqual(len(re.findall(rb'/Type /Page\b',data)),5)


if __name__=='__main__':unittest.main()
