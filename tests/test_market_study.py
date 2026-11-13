import json
from copy import deepcopy
import unittest
from unittest.mock import patch

import requests
from streamlit.testing.v1 import AppTest

from market_pdf import dashboard_drawings
from market_analytics import analytics_data, price_figure, maturity_figure, geography_figure, cost_figure
from market_study import SNAPSHOT, SOURCE, build_market_pdf, load_market_study, parse_document, table_html


class MarketStudyTests(unittest.TestCase):
    def test_parse_published_body_keeps_tables_and_source_links(self):
        source = '''<div id="banners">Ignore banner</div><div id="contents">
          <p>Fecha de corte: 12 de noviembre de 2026</p><h1>4. Fabricantes y competidores</h1>
          <table><tr><td>Modelo</td><td>Precio</td></tr><tr><td>R&amp;X</td><td>USD 53.793</td></tr></table>
          <h1>Fuentes consultadas</h1><p>[1] <a href="https://example.org/report">Informe</a></p></div>'''
        result = parse_document(source)
        self.assertEqual(result['sections'][0]['blocks'][0]['rows'][1], ['R&X', 'USD 53.793'])
        self.assertEqual(result['sections'][1]['blocks'][0]['links'][0]['url'], 'https://example.org/report')
        self.assertNotIn('Ignore banner', json.dumps(result))
        with self.assertRaises(ValueError):
            parse_document('<html>Login required</html>')
        self.assertIn('&lt;script&gt;', table_html([['Column'], ['<script>']]))

    def test_network_failure_uses_identified_source_snapshot(self):
        load_market_study.clear()
        with patch('market_study.requests.Session.get', side_effect=requests.ConnectionError('offline')):
            document = load_market_study('offline-test')
        self.assertFalse(document['live'])
        self.assertEqual(document['source'], SOURCE)
        self.assertEqual(len(document['sections']), 10)
        self.assertEqual(document['captured_at'], '12-11-2026')
        load_market_study.clear()

    def test_comparisons_preserve_scope_ranges_and_denominators(self):
        document=json.loads(SNAPSHOT.read_text())
        data=analytics_data(document)
        self.assertEqual(data['context']['global_gw'],117)
        self.assertEqual(data['context']['latam_gw'],56)
        self.assertEqual(data['context']['brazil_share'],60)
        self.assertAlmostEqual(data['price_kw'],95295/80)
        self.assertAlmostEqual(data['spread'],95295-72326.02)
        self.assertAlmostEqual(data['spread_ratio'],(95295-72326.02)/95295)
        self.assertEqual(sum(data['countries'].values()),10)
        self.assertEqual(data['countries']['China'],3)
        self.assertEqual(data['countries']['Origen por verificar'],1)
        self.assertEqual(data['priced_competitors'],3)
        refs={row['label']:row for row in data['price_refs']}
        self.assertEqual(refs['GH-H100K · 100 kW']['low'],1080)
        self.assertEqual(refs['GH-H100K · 100 kW']['high'],1320)
        self.assertEqual(refs['Greef · 10 kW']['low'],2555.5)
        self.assertIn('vencida',refs['Greef · 10 kW']['note'])
        self.assertEqual([(r['low'],r['high']) for r in data['maturity']],[(5,6),(3,4),(8,8)])
        changed=deepcopy(document)
        section=next(s for s in changed['sections'] if s['title'].startswith('5.'))
        row=next(r for b in section['blocks'] if b['kind']=='table' for r in b['rows'] if 'costos y precio 80 kW' in r[0])
        row[1]=row[1].replace('95.295','100.000')
        self.assertEqual(analytics_data(changed)['price_kw'],1250)
        self.assertEqual(len(price_figure(data).data),4)
        self.assertEqual(len(maturity_figure(data).data),3)
        self.assertEqual(sum(geography_figure(data).data[0].values),10)
        bridge=cost_figure(data).data[0]
        self.assertAlmostEqual(sum(bridge.y[:3]),data['price'])

    def test_complete_pdf_and_native_sections(self):
        document = json.loads(SNAPSHOT.read_text())
        pdf = build_market_pdf(document)
        charts=dashboard_drawings(analytics_data(document),370)
        self.assertEqual([title for title,_,_ in charts], [
            'Precio por potencia nominal', 'Madurez y distancia a la validación',
            'Composición geográfica de la muestra', 'Del costo informado al precio FW'])
        # All four export charts carry actual data, not only section headings.
        texts=[[item.text for item in drawing.contents if hasattr(item,'text')] for _,drawing,_ in charts]
        self.assertIn('US$ 1.191,19',texts[0])
        self.assertIn('TRL 3–4',texts[1])
        self.assertIn('30,0%',texts[2])
        self.assertIn('US$ 95.295',texts[3])
        self.assertTrue(pdf.startswith(b'%PDF-'))
        self.assertGreater(len(pdf), 20000)
        script = '''
import json
import market_study
model=json.loads(market_study.SNAPSHOT.read_text())
model['live']=False
market_study.load_market_study=lambda revision:model
market_study.render_market_study(0)
'''
        app = AppTest.from_string(script, default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('iframe')), 0)
        self.assertEqual(len(app.get('plotly_chart')),4)
        initial=' '.join(element.proto.body for element in app.get('html'))
        self.assertIn('1.191,19',initial)
        self.assertIn('24,1%',initial)
        self.assertTrue(any(button.label == 'Descargar estudio de mercado · PDF' for button in app.get('download_button')))
        selector = app.selectbox(key='market_study_section')
        self.assertEqual(len(selector.options), 10)
        for section in ['4. Fabricantes y competidores', '5. Precios y comparabilidad', 'Fuentes consultadas']:
            app.selectbox(key='market_study_section').set_value(section).run()
            self.assertFalse(app.exception)
            body = ' '.join(element.proto.body for element in app.get('html'))
            self.assertIn({'4. Fabricantes y competidores':'Wind Harvest', '5. Precios y comparabilidad':'53.793', 'Fuentes consultadas':'GWEC'}[section], body)


if __name__ == '__main__':
    unittest.main()
