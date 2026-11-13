"""Native market-study presentation and PDF from the published source document."""
from datetime import datetime
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import requests
import streamlit as st

from market_analytics import render_analytics

SOURCE = 'https://docs.google.com/document/d/e/2PACX-1vTxFjPYiU6LQRt29hSiAXafzw-ITwxPSNqkDlGZJWMtlLI827KKRVf7FPK1gMY_IA/pub'
SNAPSHOT = Path(__file__).with_name('data') / 'market_study.json'


class Node:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def raw_text(self):
        return ''.join(c.raw_text() if isinstance(c, Node) else c for c in self.children)

    def text(self):
        return re.sub(r'\s+', ' ', self.raw_text()).strip()

    def find(self, predicate):
        for child in self.children:
            if isinstance(child, Node):
                if predicate(child):
                    yield child
                yield from child.find(predicate)


class DocumentParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
            self.stack.append(node)
        elif tag == 'br':
            node.children.append(' ')

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse_document(content):
    parser = DocumentParser()
    parser.feed(content)
    root = next(parser.root.find(lambda n: n.attrs.get('id') == 'contents'), None)
    if root is None:
        raise ValueError('El documento publicado no contiene un cuerpo reconocible.')
    blocks = []

    def visit(node):
        if node.tag in {'script','style'}:
            return
        if node.tag == 'table':
            rows = [[cell.text() for cell in row.children if isinstance(cell, Node) and cell.tag in {'td','th'}]
                    for row in node.find(lambda n: n.tag == 'tr')]
            if rows:
                blocks.append({'kind':'table', 'rows':rows})
            return
        if node.tag in {'h1','h2','h3','p','li'}:
            text = node.text()
            if text:
                kind = 'heading' if node.tag == 'h1' else 'subheading' if node.tag in {'h2','h3'} else 'bullet' if node.tag == 'li' else 'paragraph'
                links = []
                for link in node.find(lambda n:n.tag == 'a'):
                    url = link.attrs.get('href','')
                    if url.startswith('https://www.google.com/url?'):
                        url = parse_qs(urlparse(url).query).get('q',[url])[0]
                    if url.startswith(('https://','http://')):
                        links.append({'label':link.text(), 'url':url})
                blocks.append({'kind':kind, 'text':text, 'links':links})
            return
        for child in node.children:
            if isinstance(child, Node):
                visit(child)
    visit(root)
    preface, sections = [], []
    for block in blocks:
        if block['kind'] == 'heading':
            sections.append({'title':block['text'], 'blocks':[]})
        elif sections:
            sections[-1]['blocks'].append(block)
        else:
            preface.append(block)
    if not any(s['title'].startswith('4.') for s in sections) or not any(s['title'] == 'Fuentes consultadas' for s in sections):
        raise ValueError('No se reconocieron los capítulos y las fuentes del estudio.')
    return {'source':SOURCE, 'preface':preface, 'sections':sections}


@st.cache_data(ttl=300, max_entries=4, show_spinner=False)
def load_market_study(revision=0):
    try:
        # This is a public document; no account cookies or credentials are used.
        with requests.Session() as session:
            session.trust_env = False
            response = session.get(SOURCE, timeout=(5,15))
            response.raise_for_status()
        document = parse_document(response.text)
        document['live'] = True
        document['consulted_at'] = datetime.now(ZoneInfo('America/Santiago')).strftime('%d-%m-%Y %H:%M')
        return document
    except (requests.RequestException, ValueError):
        document = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
        document['live'] = False
        return document


def table_html(rows):
    header = ''.join('<th scope="col">'+escape(value)+'</th>' for value in rows[0])
    body = ''.join('<tr>'+''.join('<'+('th scope="row"' if i == 0 else 'td')+'>'+escape(value)+'</'+('th' if i == 0 else 'td')+'>'
                                for i,value in enumerate(row))+'</tr>' for row in rows[1:])
    return '<div class="market-table"><table><thead><tr>'+header+'</tr></thead><tbody>'+body+'</tbody></table></div>'


def render_blocks(blocks, competitors=False, summary=False):
    for block in blocks:
        kind = block['kind']
        if kind == 'table' and (competitors or summary):
            rows = block['rows']
            cards = []
            for row in rows[1:]:
                fields = ''.join('<div><span>'+escape(label)+'</span><p>'+escape(value)+'</p></div>' for label,value in zip(rows[0][1:],row[1:]))
                cards.append('<article><h4>'+escape(row[0])+'</h4>'+fields+'</article>')
            st.html('<div class="market-cards">'+''.join(cards)+'</div>')
        elif kind == 'table':
            st.html(table_html(block['rows']))
        elif kind == 'subheading':
            st.markdown('#### '+block['text'])
        elif kind == 'bullet':
            st.html('<div class="market-bullet"><i></i><p>'+escape(block['text'])+'</p></div>')
        else:
            st.html('<p class="market-paragraph">'+escape(block['text'])+'</p>')
        if block.get('links'):
            links = ' · '.join('<a href="'+escape(link['url'],quote=True)+'" target="_blank" rel="noopener noreferrer">'+escape(link['label'])+'</a>' for link in block['links'])
            st.html('<div class="market-links">'+links+'</div>')


@st.cache_data(max_entries=8, show_spinner=False)
def build_market_pdf(document):
    from market_pdf import build_report
    return build_report(document, SOURCE)


def render_market_study(revision=0):
    with st.container(key='market_study'):
        st.html('<style>'+Path(__file__).with_name('assets').joinpath('market_study.css').read_text()+'</style>')
        document = load_market_study(revision)
        preface = [b['text'] for b in document['preface'] if b['kind']=='paragraph']
        subtitle = next((text for text in preface if text.startswith('Panorama ')), 'Panorama competitivo y oportunidad comercial')
        cutoff = next((text for text in preface if text.startswith('Fecha de corte:')), '')
        st.html('<header class="market-hero"><span>FW AXIAL ENERGY / INTELIGENCIA DE MERCADO</span><h2>La oportunidad VAWT</h2><p>'+escape(subtitle)+'</p><small>'+escape(cutoff)+'</small></header>')
        left,right = st.columns([1,1])
        with left:
            try:
                st.download_button('Descargar estudio de mercado · PDF',build_market_pdf(document),file_name='Estudio_de_mercado_VAWT_FW_Axial.pdf',mime='application/pdf',key='market_study_pdf',on_click='ignore',use_container_width=True)
            except ImportError:
                st.info('La descarga PDF requiere ReportLab en el servidor.')
        with right:
            st.link_button('Consultar documento fuente',SOURCE,use_container_width=True)
        if document.get('live'):
            st.caption('Documento publicado · Consulta: '+document['consulted_at']+' · Santiago. Los importes corresponden a la moneda y fecha indicadas en el estudio.')
        else:
            st.caption('Copia local del documento · Capturada el '+document['captured_at']+'. No se pudo actualizar la fuente en esta consulta. Los importes conservan la moneda y fecha del estudio.')
        conclusion = next((text for text in preface if text.startswith('Conclusión ejecutiva.')), '')
        if conclusion:
            st.html('<aside class="market-thesis"><span>TESIS DE INVERSIÓN</span><p>'+escape(conclusion.removeprefix('Conclusión ejecutiva.').strip())+'</p></aside>')
        sections = document['sections']
        competitors = next(s for s in sections if s['title'].startswith('4.'))
        references = next(s for s in sections if s['title']=='Fuentes consultadas')
        competitor_count = sum(len(b['rows'])-1 for b in competitors['blocks'] if b['kind']=='table')
        source_count = sum(bool(re.match(r'^\[\d+\]',b.get('text',''))) for b in references['blocks'])
        st.html('<div class="market-metrics"><article><strong>80–100 kW</strong><span>Foco competitivo del estudio</span></article><article><strong>'+str(competitor_count)+'</strong><span>Fabricantes y modelos revisados</span></article><article><strong>'+str(source_count)+'</strong><span>Referencias documentales</span></article></div>')
        for text in preface:
            if text.startswith('Este documento separa'):
                st.caption(text)
        render_analytics(document)
        selected = st.selectbox('Contenido del estudio',[s['title'] for s in sections],key='market_study_section')
        active = next(s for s in sections if s['title']==selected)
        st.html('<div class="market-section-title"><span>ESTUDIO DE MERCADO</span><h3>'+escape(active['title'])+'</h3></div>')
        render_blocks(active['blocks'],competitors=selected.startswith('4.'),summary=selected=='Síntesis para decisión')
