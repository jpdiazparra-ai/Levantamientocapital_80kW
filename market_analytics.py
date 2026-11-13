"""Traceable comparisons derived from the market-study tables, not market-share estimates."""
from collections import Counter
from html import escape
import re

import plotly.graph_objects as go
import streamlit as st

NAVY = '#244A6C'
TEAL = '#7FA8A4'
GOLD = '#D9A766'
CORAL = '#D7605E'
INK = '#203E58'


def number(text):
    return float(text.replace('.', '').replace(',', '.'))


def usd(value, decimals=0):
    formatted = f'{value:,.{decimals}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return 'US$ '+formatted


def percent(value):
    return f'{value*100:.1f}%'.replace('.', ',')


def analytics_data(document):
    def tables(prefix):
        section = next(s for s in document['sections'] if s['title'].startswith(prefix))
        return [b['rows'] for b in section['blocks'] if b['kind']=='table']
    prices = tables('5.')[0][1:]
    competitors = tables('4.')[0][1:]
    fw = next(row for row in prices if 'costos y precio 80 kW' in row[0])
    def labelled(label):
        match = re.search(re.escape(label)+r'\s+USD\s+([\d.,]+)',fw[1],re.I)
        if not match:
            raise ValueError('Falta '+label+' en la tabla de precios del estudio.')
        return number(match.group(1))
    cost, opex_cost, price = (labelled(label) for label in ['Costo informado','costo unitario + OPEX','precio de venta neto'])
    if not 0 < cost <= opex_cost < price:
        raise ValueError('Revisar costo, costo + OPEX y precio del snapshot antes de compararlos.')
    price_refs = []
    for prefix,label,capacity,note in [
        ('R&X','R&X · 100 kW',100,'Distribuidor · alcance por confirmar'),
        ('Greef','Greef · 10 kW',10,'Kit híbrido EXW · oferta vencida el 02-08-2026'),
        ('GH-H100K','GH-H100K · 100 kW',100,'Ex-works · identidad OEM por verificar')]:
        row = next(row for row in prices if row[0].startswith(prefix))
        match = re.search(r'USD\s+([\d.,]+)(?:[–−-]([\d.,]+))?',row[1])
        if not match:
            raise ValueError('Precio USD no reconocido para '+label)
        low = number(match.group(1))/capacity
        high = number(match.group(2))/capacity if match.group(2) else low
        price_refs.append(dict(label=label,low=low,high=high,note=note,fw=False))
    price_refs.append(dict(label='FW Axial · 80 kW',low=price/80,high=price/80,
        note='Precio neto del concepto · snapshot del estudio',fw=True))
    price_refs.sort(key=lambda row:row['low'])
    maturity = []
    for row in tables('3.')[1][1:]:
        match = re.search(r'TRL\s+(\d+)(?:[–−-](\d+))?',row[2])
        if match:
            low,high = int(match.group(1)),int(match.group(2) or match.group(1))
            maturity.append(dict(label='FW Axial · 10 kW' if 'Piloto' in row[0] else 'FW Axial · 80 kW',
                low=low,high=high,note=row[3],basis='Evaluación provisional del estudio'))
    wind = next(row for row in competitors if row[0].startswith('Wind Harvest'))
    match = re.search(r'TRL\s+(\d+)',wind[2])
    if match:
        maturity.append(dict(label='Wind Harvest · 50–75 kW',low=int(match.group(1)),high=int(match.group(1)),
            note='TRL declarado por el fabricante; certificación y disponibilidad comercial por confirmar.',basis='Declaración del fabricante'))
    countries = Counter()
    for row in competitors:
        country = row[1].split('/')[0].strip()
        if 'no verificado' in row[1]:
            country = 'Origen por verificar'
        countries[country] += 1
    market_section=next(s for s in document['sections'] if s['title'].startswith('2.'))
    market_text=' '.join(b.get('text','') for b in market_section['blocks'])
    global_match=re.search(r'reportó (\d+) GW de nueva capacidad.*?en (20\d{2})',market_text)
    latam_match=re.search(r'Latinoamérica en (\d+) GW al cierre de (20\d{2}), alrededor de (\d+)% en Brasil',market_text)
    regional_context=dict(global_gw=int(global_match.group(1)),global_year=global_match.group(2),
        latam_gw=int(latam_match.group(1)),latam_year=latam_match.group(2),brazil_share=int(latam_match.group(3))) if global_match and latam_match else None
    return dict(context=regional_context,cost=cost,opex_cost=opex_cost,price=price,spread=price-opex_cost,
        spread_ratio=(price-opex_cost)/price,price_kw=price/80,price_refs=price_refs,
        maturity=maturity,countries=dict(countries),competitor_count=len(competitors),
        priced_competitors=len(price_refs)-1)


def chart_style(fig, height=340):
    fig.update_layout(height=height,font=dict(family='Arial, sans-serif',size=12,color=INK),
        paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='#FFFFFF',margin=dict(l=16,r=35,t=20,b=45),
        hoverlabel=dict(bgcolor='white',font=dict(color=INK)),showlegend=False)
    fig.update_xaxes(gridcolor='#E8EEF2',zeroline=False,automargin=True)
    fig.update_yaxes(gridcolor='#E8EEF2',zeroline=False,automargin=True)
    return fig


def price_figure(data):
    fig = go.Figure()
    for row in data['price_refs']:
        midpoint = (row['low']+row['high'])/2
        value = usd(row['low'],2) if row['low']==row['high'] else usd(row['low'])+'–'+usd(row['high'])
        fig.add_trace(go.Scatter(x=[midpoint],y=[row['label']],mode='markers',
            marker=dict(size=15 if row['fw'] else 11,color=NAVY if row['fw'] else GOLD),
            error_x=dict(type='data',array=[(row['high']-row['low'])/2],color=GOLD,thickness=5,width=10),
            customdata=[[value,row['note']]],hovertemplate='<b>%{y}</b><br>%{customdata[0]} / kW<br>%{customdata[1]}<extra></extra>'))
    fig.add_vline(x=data['price_kw'],line_dash='dot',line_color=NAVY,line_width=1)
    chart_style(fig)
    fig.update_xaxes(title='USD por kW nominal · precios netos / EXW',rangemode='tozero',range=[0,max(r['high'] for r in data['price_refs'])*1.15])
    fig.update_yaxes(autorange='reversed')
    return fig


def maturity_figure(data):
    fig = go.Figure()
    for row in data['maturity']:
        fig.add_trace(go.Scatter(x=[(row['low']+row['high'])/2],y=[row['label']],mode='markers',
            marker=dict(size=13,color=NAVY if row['label'].startswith('FW') else GOLD),
            error_x=dict(type='data',array=[(row['high']-row['low'])/2],color=NAVY if row['label'].startswith('FW') else GOLD,thickness=4,width=9),
            customdata=[[str(row['low']) if row['low']==row['high'] else f'{row["low"]}–{row["high"]}',row['basis'],row['note']]],
            hovertemplate='<b>%{y}</b><br>TRL %{customdata[0]}<br>%{customdata[1]}<br>%{customdata[2]}<extra></extra>'))
    chart_style(fig)
    fig.update_xaxes(title='Escala TRL · rangos y valores reportados',tickmode='linear',dtick=1,range=[.5,9.5])
    fig.update_yaxes(autorange='reversed')
    return fig


def geography_figure(data):
    countries=data['countries']
    fig=go.Figure(go.Pie(labels=list(countries),values=list(countries.values()),hole=.68,sort=False,
        marker=dict(colors=[NAVY,TEAL,GOLD,CORAL,'#718096','#CBD5E1'],line=dict(color='white',width=3)),
        textinfo='label+percent',textposition='outside',
        hovertemplate='%{label}<br>%{value} de '+str(data['competitor_count'])+' referencias · %{percent}<extra></extra>'))
    chart_style(fig,360)
    fig.update_layout(annotations=[dict(x=.5,y=.54,text='<b>'+str(data['competitor_count'])+'</b>',font=dict(size=31,color=NAVY),showarrow=False),
        dict(x=.5,y=.41,text='REFERENCIAS',font=dict(size=10,color=INK),showarrow=False)])
    return fig


def cost_figure(data):
    fig=go.Figure(go.Waterfall(x=['Costo informado','OPEX añadido','Diferencia al precio','Precio neto'],
        y=[data['cost'],data['opex_cost']-data['cost'],data['spread'],data['price']],
        measure=['absolute','relative','relative','total'],text=[usd(v) for v in [data['cost'],data['opex_cost']-data['cost'],data['spread'],data['price']]],
        textposition='outside',cliponaxis=False,increasing=dict(marker_color=TEAL),totals=dict(marker_color=NAVY),
        connector=dict(line=dict(color='#CAD7E0')),hovertemplate='%{x}<br>USD %{y:,.2f}<extra></extra>'))
    chart_style(fig,360)
    fig.update_yaxes(title='USD por equipo · snapshot del estudio',range=[0,data['price']*1.25])
    return fig


def render_analytics(document):
    try:
        data=analytics_data(document)
    except (ValueError,StopIteration,IndexError,KeyError):
        st.info('La estructura del documento cambió. Revisa sus tablas originales antes de actualizar las comparaciones.')
        return
    context=data['context']
    if context:
        st.html('<div class="market-context"><article><strong>'+str(context['global_gw'])+' GW</strong><span>Nueva capacidad eólica mundial · '+context['global_year']+'</span></article><article><strong>'+str(context['latam_gw'])+' GW</strong><span>Capacidad eólica acumulada LATAM · '+context['latam_year']+'</span></article><article><strong>≈ '+str(context['brazil_share'])+'%</strong><span>Peso de Brasil en la capacidad LATAM</span></article></div>')
        st.caption('Contexto de eólica total, dominada por HAWT; no dimensiona ventas ni demanda VAWT. Flujos nuevos y capacidad acumulada son métricas distintas. Fuente: capítulo 2, GWEC citado en el estudio. La cuota de FW y el tamaño específico de VAWT no están cuantificados.')
    st.html('<div class="market-section-title"><span>POSICIÓN FW AXIAL / LECTURA COMPARATIVA</span><h3>Dónde estamos frente a las referencias</h3></div>')
    cards=[('Precio neto · 80 kW',usd(data['price']),'Snapshot del estudio; moneda de origen USD'),
        ('Precio por kW · FW',usd(data['price_kw'],2),'Precio neto / 80 kW nominales'),
        ('Diferencia sobre costo + OPEX',percent(data['spread_ratio']),usd(data['spread'],2)+' por equipo; no es utilidad neta'),
        ('Precios públicos externos',f'{data["priced_competitors"]} / {data["competitor_count"]}','Referencias USD identificadas en el estudio')]
    st.html('<div class="market-analysis-kpis">'+''.join('<article><span>'+escape(label)+'</span><strong>'+escape(value)+'</strong><small>'+escape(note)+'</small></article>' for label,value,note in cards)+'</div>')
    gh=next(row for row in data['price_refs'] if row['label'].startswith('GH-H100K'))
    position='por debajo del' if data['price_kw']<gh['low'] else 'por encima del' if data['price_kw']>gh['high'] else 'dentro del'
    st.html('<div class="market-analysis-reading"><b>Posicionamiento de precio</b><p>FW presenta '+escape(usd(data['price_kw'],2))+'/kW nominal. Su precio se ubica '+position+' rango anunciado de GH-H100K ('+escape(usd(gh['low'])+'–'+usd(gh['high']))+'/kW). Es una comparación de precios publicados con alcances distintos; no demuestra ventaja de costo instalado, energía anual ni rentabilidad.</p></div>')
    left,right=st.columns(2,gap='large')
    with left:
        st.markdown('#### Precio por potencia nominal')
        st.caption('Fuente: capítulo 5 · referencias con precio USD. Azul: FW; ocre: externos. Pasa el cursor para revisar importe y alcance.')
        st.plotly_chart(price_figure(data),use_container_width=True,key='market_price_comparison',config={'displaylogo':False})
        st.caption('R&X: distribuidor; GH: OEM por verificar; Greef: kit híbrido 10 kW y oferta vencida. No incluye una normalización de instalación, garantías o logística. Las ofertas sin precio público quedan fuera del gráfico.')
    with right:
        st.markdown('#### Madurez y distancia a la validación')
        st.caption('Fuente: capítulos 3 y 4 · se muestran únicamente los TRL explícitos en el estudio.')
        st.plotly_chart(maturity_figure(data),use_container_width=True,key='market_maturity_comparison',config={'displaylogo':False})
        st.caption('FW 10/80 kW: evaluación provisional del estudio. Wind Harvest: declaración del fabricante. Las bases no equivalen a auditorías homogéneas; el resto no recibe un TRL inferido. Los intervalos son rangos publicados, no incertidumbre estadística.')
    left,right=st.columns(2,gap='large')
    with left:
        st.markdown('#### Composición geográfica de la muestra')
        st.caption('Fuente: capítulo 4 · cada fila de fabricante/modelo pesa una referencia; FW no se incluye en este universo externo.')
        st.plotly_chart(geography_figure(data),use_container_width=True,key='market_geography',config={'displaylogo':False})
        st.caption('Los porcentajes describen las '+str(data['competitor_count'])+' referencias revisadas. No representan cuota de mercado, ventas, capacidad instalada ni demanda regional. El origen sin verificar permanece visible.')
    with right:
        st.markdown('#### Del costo informado al precio FW')
        st.caption('Fuente: capítulo 5 · concepto de 80 kW; importes históricos del documento, independientes del panel financiero en vivo.')
        st.plotly_chart(cost_figure(data),use_container_width=True,key='market_cost_bridge',config={'displaylogo':False})
        st.caption('Costo informado + OPEX añadido + diferencia aritmética = precio neto. La diferencia no acredita margen final ni gastos cubiertos; depende del alcance y de la validación de la lógica de precio.')
    st.html('<div class="market-actions"><article><span>HOY / PILOTO 10 kW</span><h4>Cerrar la evidencia de operación</h4><p>El estudio sitúa al piloto en TRL 5–6: completar FAT/SAT, curva de potencia medida, disponibilidad y mantenimiento en campo.</p></article><article><span>SIGUIENTE ESCALÓN / 80 kW</span><h4>Convertir el concepto en diseño validado</h4><p>TRL 3–4 provisional: congelar diseño, revisar cargas de forma independiente y ensayar un prototipo integrado antes de prometer desempeño comercial.</p></article><article><span>DECISIÓN COMERCIAL</span><h4>Homologar ofertas y caso de uso</h4><p>Solicitar tres ofertas OEM 80–100 kW y una HAWT, con el mismo alcance. Priorizar telecom y sitios híbridos; comparar AEP y costo total instalado por sitio.</p></article></div>')
