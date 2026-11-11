"""Snapshot audit and interaction tests for the independent 80 kW financial case."""
import csv
import json
from io import StringIO
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from valuation80_data import SOURCE, SHEETS, parse_model80, load_valuation80, parse_components80
from valuation_data import Sheet
from valuation80_report import build_report80, report80_data, ExecutiveReport80
from valuation80_view import MAIN_TABS, unit_products, summary_lcoe80
from valuation_finance import reprice_dcf
from valuation80_project import project_calendar80, calendar_plot_data80
from valuation80_unit import unit_cost_inputs80, commercial_unit80, sale_prices80

FIXTURE = Path(__file__).parent/'fixtures'/'valuation80'


def snapshot():
    return {f.stem:list(csv.reader(StringIO(f.read_text(encoding='utf-8-sig')))) for f in FIXTURE.glob('*.csv')}


def model():
    result=parse_model80(snapshot())
    result['fetched_at']='09-11-2026 10:00:00'
    return result


def project_data():
    result=json.loads((FIXTURE.parent/'project80.json').read_text())
    result['monthly']=pd.DataFrame(result['monthly'])
    result['monthly']['_month']=pd.to_datetime(result['monthly']['_month'])
    result['cutoff']=pd.Timestamp(result['cutoff'])
    for field in ['systems','lines','scope']:result['costs'][field]=pd.DataFrame(result['costs'][field])
    return result


class Model80Tests(unittest.TestCase):
    def test_renamed_price_row_is_read_without_relabeling_it_as_a_cost(self):
        m=model()
        rows=list(csv.reader(StringIO((FIXTURE.parent/'valuation80_unit_price_renamed.csv').read_text())))
        m['raw']['07 Ventas y producción']=rows
        data=unit_cost_inputs80(m)
        self.assertEqual(data['with_margin'],90239)
        self.assertTrue(data['final_is_price'])
        self.assertEqual(data['references']['with_margin'],'07!E83')
        self.assertEqual(data['before_margin'],72191.32)
        self.assertEqual(data['margin'],.2)
        # Moving rows must not break readings or their provenance.
        m['raw']['07 Ventas y producción']=[[]]+rows
        self.assertEqual(unit_cost_inputs80(m)['with_margin'],90239)
        self.assertEqual(unit_cost_inputs80(m)['references']['with_margin'],'07!E84')
        rows[82][2]='Concepto desconocido'
        self.assertTrue(pd.isna(unit_cost_inputs80(m)['with_margin']))

    def test_calendar_includes_both_80kw_milestones_outside_cash_months(self):
        data=project_data()
        original=data['monthly'].copy(deep=True)
        data['milestones']=pd.DataFrame({'Paquete / línea':['Hito Piloto 80 kW','Hito Producto 80 kW','Hito Producto 10 kW'],
            'Fin previsto actual':pd.to_datetime(['2027-06-30','2027-12-31','2028-02-01'])})
        chart,markers=calendar_plot_data80(data)
        self.assertEqual(len(markers),2)
        self.assertEqual(chart['_month'].max(),pd.Timestamp('2027-12-01'))
        self.assertEqual(chart['Total CLP'].sum(),original['Total CLP'].sum())
        pd.testing.assert_frame_equal(data['monthly'],original)
        self.assertTrue(chart.loc[chart['_month'].eq('2027-12-01'),'Total CLP'].isna().all())

    def test_usd_price_is_not_divided_by_sidebar_fx(self):
        m=model()
        m['raw']['00 Datos de entrada']=list(csv.reader(StringIO((FIXTURE.parent/'valuation80_inputs_usd.csv').read_text())))
        for fx in [925.,980.,1000.]:
            prices=sale_prices80(m,fx)
            self.assertEqual(prices['net'],89690)
            self.assertEqual(prices['net_kw'],1121.125)
            self.assertAlmostEqual(prices['gross'],106731.1)
            self.assertEqual(summary_lcoe80(m,.35,fx)['capex'],89690)
        sheet=Sheet('00 Datos de entrada',m['raw']['00 Datos de entrada'])
        row=sheet.find('Precio de venta inicial','B')
        m['raw']['00 Datos de entrada'][row-1][4]=''
        with self.assertRaisesRegex(ValueError,'USD o CLP'):sale_prices80(m,980.)

    def test_sale_prices_use_source_vat_power_and_sidebar_fx(self):
        m=model()
        sheet=Sheet('00 Datos de entrada',m['raw']['00 Datos de entrada'])
        m['raw']['00 Datos de entrada'][sheet.find('Precio de venta inicial','B')-1][2]='83.850.325'
        result=sale_prices80(m,925)
        self.assertEqual(result['net'],90649)
        self.assertEqual(result['net_kw'],1133.1125)
        self.assertEqual(result['vat_rate'],.19)
        self.assertAlmostEqual(result['gross'],107872.31)
        self.assertAlmostEqual(result['gross_kw'],1348.403875)
        self.assertAlmostEqual(sale_prices80(m,1000)['gross']*1000,result['gross']*925)
        assumptions=Sheet('03 Supuestos',m['raw']['03 Supuestos'])
        m['raw']['03 Supuestos'][assumptions.find('IVA referencial')-1][4]='0%'
        self.assertEqual(sale_prices80(m,925)['gross'],90649)

    def test_sidebar_fx_reconciles_unit_price_margin_and_lcoe(self):
        m=model()
        sheet=Sheet('00 Datos de entrada',m['raw']['00 Datos de entrada'])
        row=sheet.find('Precio de venta inicial','B')
        m['raw']['00 Datos de entrada'][row-1][2]='83.850.325'
        before=m['evaluation']['unit'].copy(deep=True)
        unit=commercial_unit80(m,925)
        self.assertEqual(unit['Precio de venta'],90649)
        self.assertEqual(unit['Margen bruto por equipo'],90649-unit['Fabricación media por equipo entregado'])
        self.assertEqual(unit['Contribución antes de estructura operativa'],unit['Margen bruto por equipo']-unit['Costo de entrega y flota por equipo'])
        self.assertEqual(summary_lcoe80(m,.35,925)['capex'],90649)
        self.assertEqual(commercial_unit80(m,1000)['Precio de venta'],83850.325)
        self.assertAlmostEqual(commercial_unit80(m,915)['Precio de venta'],91639.69945355)
        pd.testing.assert_frame_equal(before,m['evaluation']['unit'])

    def test_unit_cost_cells_preserve_margin_opex_and_published_total(self):
        m=model()
        m['raw']['07 Ventas y producción']=list(csv.reader(StringIO((FIXTURE.parent/'valuation80_unit_costs.csv').read_text())))
        result=unit_cost_inputs80(m)
        self.assertEqual(result['base'],72095)
        self.assertEqual(result['opex'],4956.8)
        self.assertEqual(result['margin'],.15)
        self.assertEqual(result['before_margin'],77051.8)
        self.assertEqual(result['with_margin'],90649)
        self.assertAlmostEqual(result['margin_amount'],13597.2)
        # The displayed final price is the published rounded value, never rebuilt.
        self.assertNotEqual(result['with_margin'],result['before_margin']/(1-result['margin']))

    def test_absent_unit_cost_inputs_remain_missing(self):
        result=unit_cost_inputs80(model())
        self.assertTrue(pd.isna(result['opex']))
        self.assertTrue(pd.isna(result['before_margin']))
        self.assertTrue(pd.isna(result['with_margin']))

    def test_pdf_preserves_selected_lcoe_and_rejects_impossible_factor(self):
        import valuation80_report
        original=valuation80_report.lcoe_page80
        captured=[]
        def page(c,r,m,factor,result):
            captured.append((r.currency,r.fx,factor,result))
            return original(c,r,m,factor,result)
        with patch.object(valuation80_report,'lcoe_page80',page):
            for currency in ['USD','CLP']:
                for factor in [.33,.35]:
                    build_report80(model(),currency,925.,project_data=project_data(),capacity_factor=factor)
        for currency,fx,factor,result in captured:
            self.assertEqual(fx,925 if currency=='CLP' else 1)
            expected=summary_lcoe80(model(),factor,925)
            self.assertEqual(result['lcoe'],expected['lcoe'])
            self.assertEqual(result['energy_y1'],80*8760*factor)
        with self.assertRaises(ValueError):
            build_report80(model(),project_data=project_data(),capacity_factor=3.35)

    def test_summary_lcoe_changes_only_energy_when_factor_changes(self):
        a=summary_lcoe80(model(),.3);b=summary_lcoe80(model(),.6)
        self.assertEqual(a['capex'],158470)
        self.assertAlmostEqual(a['fixed_om'],3169.4)
        self.assertEqual(a['energy_y1'],210240)
        self.assertEqual(b['energy_y1'],420480)
        self.assertAlmostEqual(a['lcoe']/2,b['lcoe'])
        self.assertEqual(a['pv_costs'],b['pv_costs'])
        with self.assertRaises(ValueError):summary_lcoe80(model(),0)

    def test_current_system_names_in_07_do_not_require_aspas_or_contingency(self):
        raw=snapshot()
        rows=list(csv.reader(StringIO((FIXTURE.parent/'valuation80_operations_systems.csv').read_text())))
        raw['07 Ventas y producción']=rows
        result=parse_model80(raw)
        components=result['components'].set_index('Componente')
        self.assertEqual(components.at['Eléctrico y control','USD base / equipo'],36382)
        self.assertEqual(components.at['Aspas FRP','USD base / equipo'],16768)
        self.assertEqual(len(components),7)
        self.assertNotIn('Aspas',components.index)
        self.assertFalse(any('Costo base presupuestado'==name for name in components.index))
        self.assertEqual(result['annual'].iloc[1]['unit_cost_80'],133566)

    def test_missing_component_detail_does_not_block_financial_model(self):
        raw=snapshot()
        raw['07 Ventas y producción']=raw['07 Ventas y producción'][:64]
        result=parse_model80(raw)
        self.assertTrue(result['components'].empty)
        self.assertEqual(result['scalars']['dcf'],10565289)
        self.assertTrue(result['checks']['Estado'].eq('Conciliado').all())
        pd.testing.assert_frame_equal(result['annual'],model()['annual'])

    def test_components_follow_header_columns_and_optional_balance(self):
        sheet=Sheet('07 Ventas y producción',[
            ['', '', 'Componente / criterio','','Origen','USD por equipo'],
            ['', '', 'Nuevo sistema','','Cotización fuente','3.500'],
            ['', '', 'Costo base presupuestado','','','3.500'],
            ['', '', 'Costo equivalente con margen proveedor','','','5.000']])
        frame=parse_components80(sheet)
        self.assertEqual(frame.Componente.tolist(),['Nuevo sistema'])
        self.assertEqual(frame.iloc[0]['USD base / equipo'],3500)
        self.assertEqual(frame.iloc[0]['Origen'],'Cotización fuente')
        self.assertEqual(frame.iloc[0]['Fuente'],'07 Ventas y producción!F2')

    def test_source_snapshot_conciles_and_contains_only_80kw_series(self):
        m=model();s=m['scalars']
        self.assertEqual(s['dcf'],10565289)
        self.assertEqual(s['npv_economic'],7017267)
        self.assertAlmostEqual(s['irr_economic'],.757)
        self.assertEqual(m['annual']['Año'].tolist(),['Año 0',*[str(i) for i in range(2029,2039)]])
        self.assertFalse(any('_10' in col for col in m['annual']))
        self.assertTrue(m['checks']['Estado'].eq('Conciliado').all(),m['checks'].to_string())
        self.assertEqual(len(m['monthly']),142)
        self.assertEqual(len(m['monthly'].loc[lambda f:~f['Apoyo terminal']]),132)
        self.assertEqual(len(m['native_checks']),46)
        self.assertIn('INV-001',m['assets']['ID'].tolist())
        self.assertEqual(m['development']['USD base'].sum(),2000000)
        self.assertEqual(s['production_stock']+s['plant_spares'],s['spares'])
        self.assertEqual(s['cash_gap'],888925)

    def test_blank_monthly_column_keeps_sales_and_opex_aligned(self):
        m=model();months=m['monthly']
        first=months[months['Año modelo'].eq(1)]
        annual=m['annual'].iloc[1]
        self.assertAlmostEqual(first['Ventas USD'].sum(),annual['sales'],delta=12)
        self.assertAlmostEqual(first['OPEX USD'].sum(),annual['opex'],delta=12)
        self.assertEqual(months['Capital inversionista'].sum(),m['scalars']['primary'])
        self.assertEqual(months.iloc[0]['Fecha'],pd.Timestamp('2028-01-01'))

    def test_executive_page_retains_published_values_and_five_year_horizon(self):
        m=model();e=m['evaluation'];unit=e['unit'].set_index('Concepto')
        self.assertEqual(unit.at['Fabricación media por equipo entregado','Valor'],125161)
        self.assertEqual(unit.at['Contribución antes de estructura operativa','Valor'],31247)
        self.assertEqual(e['recovery_years'],1)
        self.assertAlmostEqual(e['contribution_ratio'],.591)
        self.assertEqual(e['funding_date'],'jul 2028')
        self.assertEqual(e['projection']['Año'].tolist(),['2029','2030','2031','2032','2033'])
        self.assertEqual(e['projection']['capex'].tolist(),[0,0,0,0,445898])
        self.assertEqual(len(e['conditions']),3)
        # A distinct summary edition must be read from 00, rather than reconstructed from 04/07.
        raw=snapshot()
        r=next(row for row in raw['00 Evaluación'] if len(row)>1 and row[1]=='Precio de venta')
        r[2]='200.000'
        changed=parse_model80(raw)
        self.assertEqual(changed['evaluation']['unit'].set_index('Concepto').at['Precio de venta','Valor'],200000)
        self.assertEqual(changed['annual'].iloc[1]['sales'],m['annual'].iloc[1]['sales'])

    def test_unit_contribution_and_dcf_reconstruct_the_exclusive_case(self):
        m=model();row=unit_products(m,'2029').iloc[0]
        self.assertEqual(row['Turbina'],'80 kW')
        self.assertAlmostEqual(row['Precio / equipo'],158469.95)
        self.assertAlmostEqual(row['Fabricación / equipo'],125161.43)
        self.assertAlmostEqual(row['Contribución / equipo'],31247.32)
        a=m['annual'].iloc[1]
        self.assertAlmostEqual(row['Contribución / equipo']*a['units_80']-a['opex_common'],a['ebitda'],delta=5)
        base=reprice_dcf(m,.22,.03)
        self.assertAlmostEqual(base['dcf'],m['scalars']['dcf'],delta=10)
        self.assertLess(reprice_dcf(m,.3,.03)['dcf'],base['dcf'])

    def test_missing_source_or_changed_years_fail_without_other_workbook(self):
        raw=snapshot();raw.pop('10 Controles')
        with self.assertRaisesRegex(ValueError,'Faltan pestañas'):parse_model80(raw)
        raw=snapshot();raw['04 Resultados y flujo'][4][5]='2040'
        with self.assertRaisesRegex(ValueError,'calendario'):parse_model80(raw)

    def test_loader_uses_new_source_and_each_gid_and_honors_refresh(self):
        calls=[]
        def get(url,params,**kwargs):
            calls.append((url,params))
            name=next(name for name,gid in SHEETS.items() if gid==params['gid'])
            class Response:
                text='csv'
                content=(FIXTURE/(name+'.csv')).read_bytes()
                def raise_for_status(self):pass
            return Response()
        load_valuation80.clear()
        with patch('valuation80_data.requests.get',side_effect=get):
            load_valuation80(801);load_valuation80(801)
            self.assertEqual(len(calls),11)
            load_valuation80(802)
            self.assertEqual(len(calls),22)
        self.assertTrue(all(url==SOURCE for url,_ in calls))
        self.assertEqual({params['gid'] for _,params in calls},set(SHEETS.values()))
        load_valuation80.clear()

    def test_pdf_has_seven_pages_and_builder_does_not_read_network(self):
        with patch('requests.get',side_effect=AssertionError('Unexpected external source')):
            for currency in ['USD','CLP']:
                pdf=build_report80(model(),currency,925.,project_data=project_data())
                self.assertTrue(pdf.startswith(b'%PDF'))
                self.assertEqual(len(re.findall(rb'/Type\s*/Page\b',pdf)),7)
                self.assertNotIn(b'/Subtype /Image',pdf)
                self.assertIn(b'/Subtype /Link',pdf)
        with self.assertRaises(ValueError):build_report80(model(),'USD',0)
        with self.assertRaisesRegex(ValueError,'Faltan costos'):build_report80(model(),'USD',925.)

    def test_pdf_uses_00_rounding_and_has_charts_on_each_page(self):
        m=model();data=report80_data(m)
        self.assertEqual(data['unit']['Fabricación media por equipo entregado'],125161)
        self.assertEqual(data['projection']['Año'].tolist(),['2029','2030','2031','2032','2033'])
        self.assertEqual(data['funding']['Capital primario'],3000000)
        original=ExecutiveReport80.hbars
        calls=[]
        def capture(self,*args,**kwargs):
            calls.append(args[5]);return original(self,*args,**kwargs)
        with patch.object(ExecutiveReport80,'hbars',capture):build_report80(m,project_data=project_data())
        self.assertEqual(len(calls),7)
        self.assertIn('Presupuesto por comportamiento',calls)
        self.assertIn('Costos informados de 80 kW por sistema',calls)

    def test_report_ends_with_calendar_without_validated_column_and_full_opex(self):
        headers=[];calendar_kpis=[];calendar_columns=[];opex_ids=[]
        header=ExecutiveReport80.header;kpis=ExecutiveReport80.kpis;table=ExecutiveReport80.table
        def capture_header(self,c,number,title,subtitle):
            headers.append(title);return header(self,c,number,title,subtitle)
        def capture_kpis(self,c,y,items):
            if len(headers)==5:calendar_kpis.extend(item[0] for item in items)
            return kpis(self,c,y,items)
        def capture_table(self,rows,widths,size=7.5,header=True):
            if len(headers)==5:calendar_columns.extend(rows[0])
            if len(headers)==6:opex_ids.extend(row[0] for row in rows[1:])
            return table(self,rows,widths,size,header)
        with patch.object(ExecutiveReport80,'header',capture_header),patch.object(ExecutiveReport80,'kpis',capture_kpis),patch.object(ExecutiveReport80,'table',capture_table):
            build_report80(model(),project_data=project_data())
        self.assertEqual(len(headers),7)
        self.assertIn('trayectoria operativa',headers[2])
        self.assertIn('economía unitaria',headers[3])
        self.assertIn('calendario de desembolsos',headers[4])
        self.assertIn('detalle de gastos operativos',headers[5])
        self.assertIn('costo nivelado de la energía',headers[6])
        self.assertNotIn('Caja validada',calendar_kpis)
        self.assertEqual(calendar_columns,['Mes de necesidad','Caja por validar','Total mensual'])
        expected=model()['opex'].loc[lambda d:d['Año'].eq('2029'),'ID'].tolist()
        self.assertCountEqual(opex_ids,expected)
        self.assertEqual(len(opex_ids),33)

    def test_calendar_matches_subblock1_rules_without_commercial_filter(self):
        tasks=pd.DataFrame({'ID':['A','B','C','D'],'Proyecto':['Piloto 80kW','Piloto 80 kW','Piloto 10kW','Piloto 80kW']})
        cash=pd.DataFrame({'ID actividad':['A','B','C','D'],'_date':pd.to_datetime(['2026-09-01','2026-11-12','2026-11-12',None]),
            'Pendiente validado CLP':[100.,float('nan'),999.,50.],'Referencia por validar CLP':[float('nan'),200.,0.,float('nan')]})
        tasks['Paquete / línea']='Actividad';tasks['Fin previsto actual']=pd.NaT
        result=project_calendar80(tasks,cash,pd.Timestamp('2026-10-28'))
        self.assertEqual(result['total'],300)
        self.assertEqual(result['validated'],100)
        self.assertEqual(result['pending'],200)
        self.assertEqual(result['missing_dates'],1)
        self.assertEqual(result['undated_total'],50)
        self.assertEqual(result['overdue_count'],1)
        self.assertEqual(result['monthly']['_month'].tolist(),[pd.Timestamp('2026-10-01'),pd.Timestamp('2026-11-01')])
        self.assertTrue(pd.isna(result['monthly'].iloc[0]['Referencia por validar CLP']))
        self.assertEqual(set(result['cash']['ID actividad']),{'A','B','D'})

    def test_project_snapshot_costs_and_schedule_concile_in_native_clp(self):
        project=project_data();costs=project['costs']
        self.assertEqual(project['total'],385707150)
        self.assertEqual(project['monthly']['Total CLP'].sum(),project['total'])
        self.assertEqual(costs['systems']['Monto comercial · CLP'].sum(),costs['totals']['Comercial anterior'])
        self.assertEqual(costs['lines']['Comercial'].sum(),costs['totals']['Comercial anterior'])
        self.assertEqual(costs['totals']['Comercial anterior'],86483822)
        self.assertEqual(costs['totals']['Informadas'],81)
        self.assertEqual(costs['totals']['Partidas'],102)


SCRIPT = '''
import csv
from io import StringIO
from pathlib import Path
import streamlit as st
import valuation80_view
import valuation80_report
from valuation80_data import parse_model80
st.session_state.setdefault('option4_currency','USD')
st.session_state.setdefault('option4_fx_rate',925.)
root=Path(__FIXTURE__)
model=parse_model80({f.stem:list(csv.reader(StringIO(f.read_text(encoding='utf-8-sig')))) for f in root.glob('*.csv')})
model['fetched_at']='09-11-2026 10:00:00'
valuation80_view.load_valuation80=lambda nonce:model
import json
import pandas as pd
project=json.loads((root.parent/'project80.json').read_text())
project['monthly']=pd.DataFrame(project['monthly'])
project['monthly']['_month']=pd.to_datetime(project['monthly']['_month'])
project['cutoff']=pd.Timestamp(project['cutoff'])
for field in ['systems','lines','scope']:project['costs'][field]=pd.DataFrame(project['costs'][field])
valuation80_report.load_project80=lambda revision:project
valuation80_view.load_cost_report=lambda revision:project['costs']
valuation80_view.render_valuation80(1)
'''.replace('__FIXTURE__',repr(str(FIXTURE.resolve())))


class UI80Tests(unittest.TestCase):
    def test_renamed_07_price_is_visible_and_distinct_from_input_sale_price(self):
        script=SCRIPT.replace('valuation80_view.render_valuation80(1)',
            "model['raw']['07 Ventas y producción']=list(csv.reader(StringIO((root.parent/'valuation80_unit_price_renamed.csv').read_text())))\nvaluation80_view.unit_cost_overview80(model)")
        app=AppTest.from_string(script,default_timeout=30).run()
        self.assertFalse(app.exception)
        text=' '.join(item.proto.body for item in app.get('html'))
        self.assertIn('Precio calculado · hoja 07',text)
        self.assertIn('US$ 90.239,00',text)
        self.assertIn('US$ 1.127,99',text)
        self.assertNotIn('Sin informar',text)
        self.assertIn('Precio de venta · sin IVA',text)

    def test_unit_cost_cards_convert_project_clp_once_and_preserve_sheet_units(self):
        script=SCRIPT.replace('valuation80_view.render_valuation80(1)','valuation80_view.unit_cost_overview80(model)')
        app=AppTest.from_string(script,default_timeout=30).run()
        self.assertFalse(app.exception)
        text=re.sub(r'<[^>]+>','',' '.join(element.proto.body for element in app.get('html')))
        self.assertIn('US$ 93.496,02',text)
        self.assertIn('US$ 1.168,70 / kW',text)
        self.assertIn('81/102 partidas con monto',text)
        app.session_state['option4_currency']='CLP';app.run()
        text=re.sub(r'<[^>]+>','',' '.join(element.proto.body for element in app.get('html')))
        self.assertIn('$86.483.822',text)
        self.assertIn('$1.081.048 / kW',text)
        self.assertFalse(app.exception)

    def test_pdf_uses_active_slider_factor_and_invalidates_cached_scenario(self):
        import valuation80_report
        original=valuation80_report.build_report80
        factors=[]
        def capture(*args,**kwargs):
            factors.append(kwargs['capacity_factor'])
            return original(*args,**kwargs)
        script=SCRIPT.replace('valuation80_view.render_valuation80(1)','valuation80_view.overview80(model)')
        valuation80_report.report80_payload.clear()
        with patch.object(valuation80_report,'build_report80',capture):
            app=AppTest.from_string(script,default_timeout=30).run()
            self.assertFalse(app.exception)
            app.slider(key='option4_valuation80_summary_lcoe_factor').set_value(33).run()
            self.assertFalse(app.exception)
            app.slider(key='option4_valuation80_summary_lcoe_factor').set_value(35).run()
            self.assertFalse(app.exception)
        self.assertEqual(factors,[.35,.33])
        valuation80_report.report80_payload.clear()

    def test_missing_project_source_only_disables_the_complete_pdf(self):
        script=SCRIPT.replace('valuation80_report.load_project80=lambda revision:project',
            "def unavailable(revision):raise RuntimeError('Costos no disponible')\nvaluation80_report.load_project80=unavailable\nvaluation80_report.report80_payload.clear()")
        app=AppTest.from_string(script,default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertTrue(app.button(key='option4_valuation80_pdf_unavailable').disabled)
        self.assertEqual([tab.label for tab in app.tabs if tab.label in MAIN_TABS],MAIN_TABS)

    def test_evaluation_is_one_executive_view_without_nested_tabs(self):
        script=SCRIPT.replace('valuation80_view.render_valuation80(1)','valuation80_view.overview80(model)')
        app=AppTest.from_string(script,default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.tabs),0)
        self.assertGreaterEqual(len(app.get('plotly_chart')),9)
        text=' '.join(element.proto.body for element in app.get('html'))
        self.assertIn('RESULTADOS Y VALORIZACIÓN',text)
        self.assertIn('ARRANQUE E INVERSIÓN',text)
        self.assertIn('ECONOMÍA UNITARIA Y RESPALDOS',text)
        self.assertIn('PRIMEROS CINCO AÑOS',text)
        self.assertFalse(app.number_input)
        self.assertEqual(len(app.slider),1)
        self.assertEqual(app.slider[0].key,'option4_valuation80_summary_lcoe_factor')
        self.assertEqual(app.slider[0].value,35)
        app.session_state['option4_currency']='CLP';app.run()
        self.assertFalse(app.exception)

    def test_summary_lcoe_factor_recalculates_and_survives_currency_and_refresh(self):
        script=SCRIPT.replace('valuation80_view.render_valuation80(1)','valuation80_view.overview80(model)')
        app=AppTest.from_string(script,default_timeout=30).run()
        import json
        def point():
            spec=next(json.loads(fig.proto.spec) for fig in app.get('plotly_chart') if 'Factor de planta neto (%)' in fig.proto.spec)
            return spec['data'][1]['y'][0]
        first=point()
        app.slider(key='option4_valuation80_summary_lcoe_factor').set_value(60).run()
        self.assertFalse(app.exception)
        self.assertAlmostEqual(point(),first*.35/.6)
        app.session_state['option4_currency']='CLP';app.run()
        self.assertAlmostEqual(point(),first*.35/.6*925)
        self.assertEqual(app.slider[0].value,60)
        app.run()
        self.assertEqual(app.slider[0].value,60)
        self.assertFalse(app.number_input)

    def test_all_tabs_currency_year_and_scenarios_are_independent(self):
        app=AppTest.from_string(SCRIPT,default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertTrue(any(button.proto.label=='Descargar PDF ejecutivo · 80 kW' for button in app.get('download_button')))
        self.assertEqual([tab.label for tab in app.tabs if tab.label in MAIN_TABS],MAIN_TABS)
        self.assertEqual(len(app.get('plotly_chart'))>20,True)
        state=app.session_state.filtered_state
        self.assertFalse(any(key.startswith('option4_lcoe_') for key in state))
        self.assertFalse(any(key.startswith('option4_valuation_') for key in state))
        specs=' '.join(fig.proto.spec for fig in app.get('plotly_chart'))
        self.assertNotIn('10 kW',specs)
        self.assertFalse(any('10 kW' in option for item in app.selectbox for option in item.options))
        app.number_input(key='option4_valuation80_lab_rate').set_value(30.).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.number_input(key='option4_valuation80_lab_rate').value,30.)
        app.selectbox(key='option4_valuation80_year').set_value('2033').run()
        self.assertFalse(app.exception)
        app.session_state['option4_currency']='CLP';app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.number_input(key='option4_valuation80_lab_rate').value,30.)
        app.button(key='option4_valuation80_lab_restore').click().run()
        self.assertEqual(app.number_input(key='option4_valuation80_lab_rate').value,22.)
        app.selectbox(key='option4_valuation80_source_sheet').set_value('10 Controles').run()
        self.assertFalse(app.exception)
        app.run()
        self.assertEqual(app.selectbox(key='option4_valuation80_source_sheet').value,'10 Controles')


if __name__=='__main__':unittest.main()
