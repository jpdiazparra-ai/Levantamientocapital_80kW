"""Executive valuation views for Block 4, Sub block 4."""
from contextvars import ContextVar

import html
import textwrap
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from display_currency import amount, currency_code, exchange_rate
from valuation_data import load_valuation, SOURCE, SHEETS, number
from valuation_interactive import diagnostics_panel, diagnostics_definitions, unit_panel, projection_panel, dcf_lab
from valuation_report import report_payload

chart_palette = ContextVar('valuation_chart_palette', default={})

NAVY,TEAL,GOLD,ORANGE,MUTED='#315E7D','#3B8F96','#9DAFC0','#B36A52','#627588'


def money(value,compact=False):
    return amount(value*exchange_rate() if currency_code()=='CLP' else value,compact)


def displayed(values):
    return values*exchange_rate() if currency_code()=='CLP' else values


def pct(value):return 'Sin dato' if pd.isna(value) else f'{value:.1%}'.replace('.',',')
def count(value):return 'Sin dato' if pd.isna(value) else f'{value:,.0f}'.replace(',','.')


def kpis(items,secondary=False):
    cards=''.join(f'<article><span>{html.escape(label)}</span><strong>{html.escape(str(value))}</strong><small>{html.escape(note)}</small></article>' for label,value,note in items)
    st.html('<div class="valuation-kpis'+(' secondary' if secondary else '')+'">'+cards+'</div>')


def context(title,text):
    st.html('<div class="valuation-reading"><b>'+html.escape(title)+'</b><p>'+html.escape(text)+'</p></div>')


def section(number,title):
    st.html('<div class="valuation-section"><em>'+html.escape(number)+'</em><h3>'+html.escape(title)+'</h3></div>')


def plot(fig,key,height=330):
    pie=bool(fig.data) and fig.data[0].type=='pie'
    has_title=bool(fig.layout.title.text)
    multiple=len(fig.data)>1
    top=80 if has_title and multiple else 52 if has_title else 42
    legend=dict(orientation='h',y=1.03,yanchor='bottom',x=0,font=dict(size=11))
    bottom=40
    if pie:
        height=max(height,360);bottom=80;legend.update(y=-.12,yanchor='top')
    fig.update_layout(height=height,font=dict(family='Arial, sans-serif',color=MUTED,size=11),
        paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='#FFFFFF',margin=dict(l=16,r=30,t=top,b=bottom),
        legend=legend,hoverlabel=dict(bgcolor='#203E58',font=dict(color='white',size=12),bordercolor='#203E58'),
        bargap=.38,separators=',.',modebar=dict(bgcolor='rgba(255,255,255,0)',color='#8296A7'))
    if has_title:fig.update_layout(title=dict(x=.015,y=.98,yanchor='top',font=dict(size=14,color='#203E58')))
    fig.update_xaxes(automargin=True,gridcolor='#EEF2F6',zeroline=False,tickfont=dict(size=11))
    fig.update_yaxes(automargin=True,gridcolor='#EEF2F6',zeroline=False,tickfont=dict(size=11))
    palette=chart_palette.get()
    if palette:
        def recolor(value):
            if isinstance(value, str):return palette.get(value, value)
            if isinstance(value, dict):return {k:recolor(v) for k,v in value.items()}
            if isinstance(value, (list, tuple)):return [recolor(v) for v in value]
            return value
        fig=go.Figure(recolor(fig.to_plotly_json()))
        key='10_'+key
    st.plotly_chart(fig,use_container_width=True,key='option4_valuation_'+key,config={'displaylogo':False,'scrollZoom':False,'modeBarButtonsToRemove':['select2d','lasso2d']})


def financial_table(data,money_cols=(),percent_cols=(),key=None):
    result=data.copy()
    for field in money_cols:
        if field in result:result[field]=displayed(result[field])
    fmt={field:amount for field in money_cols if field in result}
    fmt.update({field:pct for field in percent_cols if field in result})
    config={field:st.column_config.NumberColumn(field.replace('USD',currency_code()) if 'USD' in field else field+' · '+currency_code(),width=175) for field in money_cols if field in result}
    config.update({field:st.column_config.NumberColumn(width=145) for field in percent_cols if field in result})
    for field in ['Concepto','Activo / alcance','Fuente','Sistema','Condición','Control']:
        if field in result:config[field]=st.column_config.TextColumn(width='large')
    st.dataframe(result.style.format(fmt,na_rep='Sin dato'),hide_index=True,use_container_width=True,row_height=52,height=min(600,45+len(result)*52),column_config=config,key=key)


def source_note(*sheets):
    st.caption('Fuente: '+' · '.join(sheets)+'. Los resultados pertenecen al caso activo publicado; no se recalcula la planilla desde el panel.')


def annual_bars(a,fields,key,title):
    fig=go.Figure()
    for field,label,color in fields:
        fig.add_trace(go.Bar(name=label,x=a['Año'],y=displayed(a[field])/1e6,marker_color=color,customdata=[money(value) for value in a[field]],hovertemplate='%{x}<br>%{customdata}<extra>%{fullData.name}</extra>'))
    fig.update_layout(title=dict(text=title,font=dict(size=17)),barmode='group')
    fig.update_xaxes(type='category',categoryorder='array',categoryarray=a['Año'].tolist(),tickmode='array',tickvals=a['Año'].tolist())
    fig.update_yaxes(title_text='Millones de '+currency_code())
    plot(fig,key)


def overview(model):
    s,a=model['scalars'],model['annual']
    title,download=st.columns([4.8,1.2],vertical_alignment='center')
    with title:section('01 / RESUMEN EJECUTIVO','Valor indicativo y fundamentos del caso')
    with download:
        try:
            pdf=report_payload(model,currency_code(),exchange_rate())
            st.download_button('Descargar PDF ejecutivo',data=pdf,file_name='Turbina_80kW_Informe_tecnico_financiero_'+currency_code()+'.pdf',mime='application/pdf',key='option4_valuation_executive_pdf',on_click='ignore',use_container_width=True,help='Informe de cinco páginas: alcance técnico, valoración a diez años, operación a cinco años, fuentes y costos de 80 kW por sistema y línea desde el subbloque 1.')
        except Exception as exc:
            st.button('PDF no disponible',disabled=True,key='option4_valuation_executive_pdf_unavailable',help='No se pudo preparar el informe: '+str(exc))
    st.caption('Resumen del caso publicado · '+currency_code()+'. Valor operativo, retorno económico y precio negociado; explora sus fundamentos en las vistas de análisis.')
    kpis([('DCF antes de capital nuevo',money(s['dcf']),f'Tasa {pct(s["rate"])} · crecimiento terminal {pct(s["growth"])}'),
        ('VAN económico sin terminal',money(s['npv_economic']),'Incluye el costo económico de los activos en especie'),
        ('TIR económica sin terminal',pct(s['irr_economic']),'Tasa publicada en 00 Evaluación · sin perpetuidad'),
        ('Precio previo negociado',money(s['pre_money']),'Precio implícito de la operación propuesta; separado del DCF')])
    sections=st.tabs(['Valorización y retorno','Economía por turbina','Proyección financiera','Escenarios de valorización'])
    with sections[0]:
        section('02 / VALORIZACIÓN','Del flujo de caja al valor del proyecto')
        st.caption('Parte de los flujos y su valor presente; compara el DCF con la negociación y revisa después los indicadores de rentabilidad y sensibilidad.')
        with st.container(key='option4_valuation_value_charts'):
            left,right=st.columns([1.2,1],gap='large')
            with left:
                st.markdown('##### Cómo se construye el valor DCF')
                st.caption('El arranque consume caja en Año 0; el terminal se descuenta desde el final del año 10. El aporte de capital nuevo no integra este valor.')
                pv_future=a.loc[a['Año modelo'].gt(0),'pv_fcff'].sum(min_count=1)
                terminal_pv=s['terminal_value']/(1+s['rate'])**10 if s['rate']>s['growth'] else float('nan')
                values=[pv_future,a.iloc[0]['fcff'],terminal_pv,s['dcf']]
                fig=go.Figure(go.Waterfall(x=['VP flujos años 1–10','Caja de arranque','VP del terminal','DCF publicado'],y=[displayed(v)/1e6 for v in values],measure=['relative','relative','relative','total'],text=[money(v,True) for v in values],textposition='outside',connector=dict(line=dict(color='#C8D3DB')),increasing=dict(marker_color=TEAL),decreasing=dict(marker_color=ORANGE),totals=dict(marker_color=NAVY)))
                fig.update_yaxes(title_text='Millones de '+currency_code());plot(fig,'dcf_bridge',300)
            with right:
                st.markdown('##### DCF y precio negociado')
                st.caption('El precio previo más el aporte primario determina el precio posterior implícito. La compra secundaria remunera a fundadores y no ingresa a FW.')
                names=['Precio previo negociado','Precio posterior negociado','DCF antes de fondos nuevos']
                vals=[s['pre_money'],s['post_money'],s['dcf']]
                fig=go.Figure(go.Bar(y=names,x=[displayed(v)/1e6 for v in vals],orientation='h',marker_color=[GOLD,GOLD,NAVY],text=[money(v,True) for v in vals],textposition='outside',cliponaxis=False))
                fig.update_xaxes(title_text='Millones de '+currency_code());fig.update_yaxes(autorange='reversed');plot(fig,'deal_values',300)
        context('Lectura del valor',f'El terminal representa {pct(s["terminal_weight"])} del DCF publicado. El VAN económico de {money(s["npv_economic"])} resta el aporte de activos de {money(s["assets_in_kind"])} al VAN de caja sin terminal. Los fondos primarios de {money(s["primary"])} se presentan aparte y su estado es {model["status"]}.')
        st.markdown('##### Indicadores complementarios de rentabilidad')
        diagnostics_panel(model)
        st.markdown('##### Sensibilidad publicada · precio y tasa de descuento')
        st.caption('Nueve resultados de la matriz nativa de 03 Supuestos. Explora la sensibilidad del DCF manteniendo el resto del caso; no son escenarios completos recalculados aquí.')
        sens=model['sensitivity'].pivot(index='Tasa',columns='Precio x',values='DCF USD').sort_index()
        z=displayed(sens.to_numpy())/1e6
        labels=[[money(v,True) for v in row] for row in sens.to_numpy()]
        fig=go.Figure(go.Heatmap(z=z,x=[f'{v:.2f}x'.replace('.',',') for v in sens.columns],y=sens.index.tolist(),text=labels,texttemplate='%{text}',colorscale=[[0,'#EDF3F6'],[.5,'#7DBBB3'],[1,NAVY]],colorbar=dict(title='MM '+currency_code()),hovertemplate='Precio %{x}<br>Tasa %{y:.0%}<br>%{text}<extra></extra>'))
        fig.update_xaxes(title_text='Multiplicador de precio');fig.update_yaxes(title_text='Tasa de descuento',tickmode='array',tickvals=sens.index.tolist(),ticktext=[pct(v) for v in sens.index],autorange='reversed');plot(fig,'sensitivity',320)
        if not model['pending'].empty:
            with st.expander('Condiciones del caso pendientes de respaldo',expanded=False):
                st.caption('Estados tomados de 00 Evaluación. La conciliación matemática del modelo no acredita presupuestos ni contratos.')
                st.dataframe(model['pending'],hide_index=True,use_container_width=True)
        diagnostics_definitions()
        source_note('00 Evaluación','00 Datos de entrada','01 Resumen','03 Supuestos','04 Resultados y flujo')
    with sections[1]:unit_panel(model)
    with sections[2]:projection_panel(model)
    with sections[3]:dcf_lab(model)

def deal_table(model,block):
    """Report table with complete wrapped terms; monetary values follow display currency."""
    data=model['deal_details'];data=data[data['Bloque'].eq(block)]
    rows=[]
    for _,row in data.iterrows():
        value=money(row['Valor']) if row['Unidad']=='USD' else pct(row['Valor']) if row['Unidad']=='%' else row['Valor fuente']+(' '+row['Unidad'] if row['Unidad'] else '')
        rows.append('<tr><th scope="row" title="'+html.escape(row['Referencia'])+'">'+html.escape(row['Concepto'])+'</th><td class="deal-value">'+html.escape(value)+'</td><td class="deal-note">'+html.escape(row['Observación'])+'</td></tr>')
    st.html('<div class="deal-report"><table><caption>'+html.escape(block)+'</caption><thead><tr><th>Concepto</th><th>Valor · '+currency_code()+' / unidad</th><th>Contexto de la fuente</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>')


def investment(model):
    with st.container(key='option4_valuation_investment'):
        investment_details(model)


def investment_details(model):
    s=model['scalars'];details=model['deal_details']
    def value(label):
        rows=details.loc[details['Concepto'].eq(label),'Valor']
        return rows.iloc[0] if len(rows) else float('nan')
    section('01 / OPERACIÓN','Inversión, condiciones y estructura accionaria')
    st.caption('Condiciones publicadas en 02 Inversión y socios. Distingue el aporte que ingresa a FW, la compra secundaria y el precio implícito de las acciones. Los importes mantienen el estado de la operación: '+model['status']+'.')
    kpis([('Pago total del inversionista',money(s['investment_total']),model['status']),
        ('Capital primario para FW',money(s['primary']),'Entrada de caja y capital de la empresa'),
        ('Participación final inversionista',pct(s['investor_share']),'Emisión primaria + compra secundaria'),
        ('Caja objetivo después del arranque',money(s['cash_target']),'Reserva de liquidez publicada')])
    left,right=st.columns([1.1,1],gap='medium')
    with left:deal_table(model,'Condiciones de la operación')
    with right:deal_table(model,'Precio y participación accionaria')
    left,right=st.columns(2,gap='medium')
    with left:
        destinations=['Aporte a FW','Compra a fundadores'];amounts=[s['primary'],s['secondary']]
        fig=go.Figure(go.Bar(y=destinations,x=[displayed(v)/1e6 for v in amounts],orientation='h',width=.4,
            marker_color=[NAVY,GOLD],text=[money(v,True) for v in amounts],textposition='outside',cliponaxis=False,
            customdata=[money(v) for v in amounts],hovertemplate='%{y}<br>%{customdata}<extra></extra>'))
        fig.update_layout(title='Destino del pago de inversión');fig.update_xaxes(title_text='MM '+currency_code(),range=[0,max(max(displayed(v)/1e6 for v in amounts)*1.3,1)]);fig.update_yaxes(autorange='reversed',showgrid=False);plot(fig,'funds',270)
    with right:
        fig=go.Figure(go.Pie(labels=['Inversionista · emisión primaria','Inversionista · compra secundaria','Accionistas actuales'],values=[s['primary_share'],s['secondary_share'],s['founder_share']],hole=.68,sort=False,
            marker=dict(colors=[NAVY,GOLD,TEAL],line=dict(color='white',width=2)),textinfo='percent',textposition='inside',hovertemplate='%{label}<br>%{percent}<extra></extra>'))
        fig.update_layout(title='Participación accionaria después de la operación',annotations=[dict(x=.5,y=.5,text='<b>'+pct(s['investor_share'])+'</b><br>inversionista',showarrow=False,font=dict(size=16,color=NAVY))]);plot(fig,'ownership',360)
    section('02 / LIQUIDEZ','Aplicación de los fondos y caja de arranque')
    st.caption('El uso de caja está neto de anticipos. La reserva objetivo, el financiamiento puente y el aporte adicional se muestran por separado; el patrimonio contable es distinto del precio negociado y del DCF.')
    extra=value('Aporte adicional para caja objetivo');equity=value('Patrimonio contable al cierre del año 0')
    kpis([('Caja libre al cierre del año 0',money(value('Caja libre al cierre del año 0')),'Saldo publicado después del arranque'),
        ('Aporte total para conservar caja',money(s['target_funding']),'Uso de caja + reserva objetivo'),
        ('Aporte adicional para caja objetivo',money(extra),'Necesidad adicional publicada'),
        ('Patrimonio contable inicial',money(equity),'Balance al cierre del año 0')],secondary=True)
    left,right=st.columns([1.2,1],gap='medium')
    with left:deal_table(model,'Aplicación de los fondos en FW')
    with right:
        bridge=value('Financiamiento puente / adicional requerido');closing=value('Caja libre al cierre del año 0')
        vals=[value('Capital de caja aportado a FW'),-s['cash_required'],closing]
        fig=go.Figure(go.Waterfall(x=['Capital a FW','Uso neto de caja','Caja libre Año 0'],y=[displayed(v)/1e6 for v in vals],measure=['relative','relative','total'],text=[money(v,True) for v in vals],textposition='outside',connector=dict(line=dict(color='#CCD8E2')),increasing=dict(marker_color=TEAL),decreasing=dict(marker_color=GOLD),totals=dict(marker_color=NAVY)))
        fig.update_layout(title='Del aporte al saldo disponible');fig.update_yaxes(title_text='MM '+currency_code(),range=[min(0,displayed(closing)/1e6),max(max(displayed(v)/1e6 for v in vals)*1.2,1)]);plot(fig,'start_cash',300)
        context('Caja objetivo y financiamiento',f'El saldo publicado supera o queda bajo la caja objetivo en {money(closing-s["cash_target"])}. El puente / adicional requerido es {money(bridge)} y la necesidad adicional para conservar la reserva es {money(extra)}. El puente es un déficit proyectado, no un aporte firmado.')
    section('03 / PRECIO Y VALOR','Negociación frente a la valorización del modelo')
    st.caption('Compara el valor previo implícito de la operación con el DCF antes de fondos nuevos. La diferencia publicada no acredita un descuento de mercado ni representa el retorno del inversionista.')
    left,right=st.columns([1.2,1],gap='medium')
    with left:deal_table(model,'Valorización del modelo y precio negociado')
    with right:
        labels=['DCF antes de fondos nuevos','Precio previo negociado'];amounts=[value('Valor DCF antes de fondos nuevos'),value('Valor previo implícito en negociación')]
        fig=go.Figure(go.Bar(y=labels,x=[displayed(v)/1e6 for v in amounts],orientation='h',width=.4,marker_color=[NAVY,TEAL],text=[money(v,True) for v in amounts],textposition='outside',cliponaxis=False,customdata=[money(v) for v in amounts],hovertemplate='%{y}<br>%{customdata}<extra></extra>'))
        fig.update_layout(title='Valor operativo y precio de entrada');fig.update_xaxes(title_text='MM '+currency_code(),range=[0,max(max(displayed(v)/1e6 for v in amounts)*1.3,1)]);fig.update_yaxes(autorange='reversed',showgrid=False);plot(fig,'deal_price_comparison',250)
    context('Lectura de la negociación',f'Precio negociado / DCF publicado: {pct(value("Precio negociado / DCF"))}. Diferencia negociación menos DCF: {money(value("Diferencia negociación menos DCF"))}. Se conserva el importe publicado, que puede diferir de una resta entre valores visibles por redondeo. El aporte primario aumenta caja y capital; no aumenta EBITDA ni VAN operativo.')
    with st.expander('Criterios de la operación y trazabilidad de los importes'):
        for criterion in model['deal_criteria']:st.write('• '+criterion)
        st.caption('La participación de los accionistas actuales se presenta agregada; no se infiere un reparto individual ni quién recibe las acciones por activos aportados. Mes y año del desembolso son coordenadas del modelo, no una fecha de cierre confirmada.')
        st.dataframe(details[['Concepto','Valor fuente','Unidad','Referencia']],hide_index=True,use_container_width=True,height=320)
    source_note('02 Inversión y socios','05 Balance y cobros','09 Activos y arranque')


def operating(model,year):
    a=model['annual'];periods=a[a['Año modelo'].gt(0)];row=periods[periods['Año'].eq(year)].iloc[0]
    st.subheader('Resultados y escala productiva · '+year)
    st.caption('Ventas y entregas proyectadas, con costos de fabricación y gastos específicos de cada turbina. El modo Comercial de esta planilla permite terceros; es distinto del filtro Comercial de costos de los otros sub bloques.')
    kpis([('Ventas proyectadas',money(row['sales']),year),('EBITDA proyectado',money(row['ebitda']),'Margen '+pct(row['ebitda_margin'])),('Flujo libre del proyecto',money(row['fcff']),'Después de CT, CAPEX, anticipos e IVA'),('Entregas / capacidad propia',count(row['units_total'])+' / '+count(row['capacity']),count(row['external'])+' equipos requieren ampliar o externalizar')])
    annual_bars(periods,[('sales','Ventas',NAVY),('ebitda','EBITDA',GOLD),('fcff','Flujo libre',TEAL)],'profit_trend','Proyección operativa · horizonte completo')
    left,right=st.columns(2,gap='large')
    with left:
        st.markdown('##### De las ventas al EBITDA · '+year)
        fig=go.Figure(go.Waterfall(x=['Ventas','Fabricación','OPEX','EBITDA'],y=[displayed(v)/1e6 for v in [row['sales'],-row['cogs'],-row['opex'],row['ebitda']]],measure=['relative','relative','relative','total'],text=[money(v,True) for v in [row['sales'],row['cogs'],row['opex'],row['ebitda']]],textposition='outside',decreasing=dict(marker_color=GOLD),increasing=dict(marker_color=TEAL),totals=dict(marker_color=NAVY)))
        fig.update_yaxes(title_text='Millones de '+currency_code());plot(fig,'ebitda_bridge')
    with right:
        st.markdown('##### Entregas y capacidad propia')
        fig=go.Figure()
        for cap,color in [(cap, NAVY if cap==10 else GOLD) for cap in model.get('products',(10,80))]:fig.add_trace(go.Bar(name=f'Turbina de {cap} kW',x=periods['Año'],y=periods[f'units_{cap}'],marker_color=color))
        fig.add_trace(go.Scatter(name='Capacidad propia',x=periods['Año'],y=periods['capacity'],mode='lines+markers',line=dict(color=TEAL,width=3,dash='dash')))
        fig.update_layout(barmode='stack');fig.update_xaxes(type='category',tickmode='array',tickvals=periods['Año'].tolist());fig.update_yaxes(title_text='Equipos por año');plot(fig,'capacity')
    products=[]
    for cap in model.get('products',(10,80)):
        units=row[f'units_{cap}'];rev=row[f'sales_{cap}'];cost=row[f'cost_{cap}'];specific=row[f'opex_{cap}']
        products.append({'Turbina':f'{cap} kW','Entregas':units,'Ventas':rev,'Precio promedio':rev/units if units>0 else float('nan'),'Fabricación / equipo':cost/units if units>0 else float('nan'),'Margen bruto / equipo':(rev-cost)/units if units>0 else float('nan'),'Margen bruto %':(rev-cost)/rev if rev>0 else float('nan'),'OPEX específico / equipo':specific/units if units>0 else float('nan'),'Contribución / equipo':(rev-cost-specific)/units if units>0 else float('nan')})
    st.markdown('##### Economía técnica por turbina · '+year)
    financial_table(pd.DataFrame(products),['Ventas','Precio promedio','Fabricación / equipo','Margen bruto / equipo','OPEX específico / equipo','Contribución / equipo'],['Margen bruto %'])
    st.caption('Contribución antes del OPEX común. Los promedios se derivan de ingresos, costo de ventas y entregas publicados para conservar la conciliación. No se suman a los resultados consolidados.')
    with st.expander('Detalle anual de resultados y flujo'):
        columns={'Año':'Año','sales':'Ventas','cogs':'Fabricación','opex':'OPEX','ebitda':'EBITDA','da':'Depreciación','tax':'Impuesto estimado','net_income':'Utilidad neta','ct_change':'Variación CT','advance_change':'Variación anticipos','vat_change':'Variación IVA','capex':'CAPEX','fcff':'Flujo libre'}
        table=a[list(columns)].rename(columns=columns);financial_table(table,[name for name in table if name!='Año'])
    source_note('04 Resultados y flujo','07 Ventas y producción','08 Gastos operativos')


def cash_view(model,year,key_prefix='option4_valuation'):
    s,a=model['scalars'],model['annual'];row=a[a['Año'].eq(year)].iloc[0]
    st.subheader('Caja, cobros y obligaciones de entrega')
    st.caption('La caja después del aporte depende de que la operación propuesta se concrete. Los anticipos financian la operación y representan equipos pendientes de entrega; no son utilidad ni capital aportado.')
    kpis([('Caja libre al cierre · '+year,money(row['cash_free']),'Excluye reserva de caja operativa'),('Anticipos pendientes · '+year,money(row['advances']),'Obligación de entregar equipos'),('Necesidad de caja inicial sin aporte',money(s['cash_required']),'Incluye el efecto de IVA del arranque'),('Puente adicional del caso',money(s['bridge']),'Según aporte y calendario publicados')])
    m=model['monthly'].copy();m['Caja antes de aportes (derivada)']=m['Flujo neto USD'].cumsum()
    choices=['Arranque y primer año','Horizonte DCF completo',*[str(v) for v in sorted(m['Fecha'].dt.year.unique())]]
    key=key_prefix+'_cash_window'
    if key in st.session_state and st.session_state[key] not in choices:
        st.session_state[key]=choices[0]
    window=st.selectbox('Ventana de caja mensual',choices,key=key)
    if window==choices[0]:selection=m[m['Año modelo'].le(1)]
    elif window==choices[1]:selection=m[~m['Apoyo terminal']]
    else:selection=m[m['Fecha'].dt.year.eq(int(window))]
    fig=go.Figure()
    for field,label,color,dash in [('Caja antes de aportes (derivada)','Caja antes de aportes · derivada',NAVY,'dash'),('Caja tras aporte y puente','Caja con aporte y puente · proyectada',TEAL,'solid')]:
        fig.add_trace(go.Scatter(x=selection['Fecha'],y=displayed(selection[field])/1e6,name=label,mode='lines',line=dict(color=color,width=3,dash=dash),customdata=[money(v) for v in selection[field]],hovertemplate='%{x|%m-%Y}<br>%{customdata}<extra>%{fullData.name}</extra>'))
    fig.add_hline(y=0,line_color='#AEBCC7',line_width=1);fig.update_yaxes(title_text='Millones de '+currency_code());plot(fig,'monthly_cash',420)
    st.caption('Caja antes de aportes = acumulado del flujo neto mensual publicado. La columna fuente “Caja sin puente” ya incorpora el aporte primario; por eso no se presenta como caja sin aporte. El año de apoyo terminal está fuera del horizonte DCF y solo se muestra si se elige su año.')
    fig=go.Figure()
    for field,label,color in [('Flujo neto USD','Flujo neto antes de capital',NAVY),('Capital inversionista','Aporte propuesto',GOLD)]:fig.add_trace(go.Bar(x=selection['Fecha'],y=displayed(selection[field])/1e6,name=label,marker_color=color))
    fig.update_yaxes(title_text='Millones de '+currency_code());plot(fig,'monthly_flows',320)
    annual_bars(a,[('collections','Cobros recibidos',TEAL),('sales','Ingresos por entregas',NAVY),('advances','Anticipos pendientes al cierre',GOLD)],'advances','Cobros, ventas y pedidos pendientes · no se suman entre sí')
    with st.expander('Balance proyectado y detalle mensual'):
        table=a[['Año','assets','liabilities','equity','cash_total','cash_free','advances']].rename(columns={'assets':'Activos','liabilities':'Pasivos','equity':'Patrimonio','cash_total':'Caja total','cash_free':'Caja libre','advances':'Anticipos pendientes'})
        financial_table(table,table.columns[1:])
        fields=['Mes','Año modelo','Ventas USD','Fabricación USD','OPEX USD','Flujo neto USD','Capital inversionista','Caja sin puente','Puente requerido mes','Caja tras aporte y puente','Anticipos cierre']
        financial_table(selection[fields],fields[2:])
    source_note('05 Balance y cobros','06 Caja mensual','04 Resultados y flujo')


def cost_assets(model,year,key_prefix='option4_valuation'):
    s=model['scalars'];opex=model['opex'][model['opex']['Año'].eq(year)].copy();assets=model['assets'].copy()
    st.subheader('OPEX, activos aportados y arranque')
    st.caption('El OPEX incorpora cada partida y ajuste una sola vez. Los activos en especie no consumen caja de FW. El capital de trabajo histórico es una referencia separada del cálculo operativo.')
    inventory_label='Preoperacionales e inventario' if model.get('products')==(80,) else 'Preoperacionales y repuestos'
    kpis([('OPEX del año '+year,money(opex['USD'].sum(min_count=1)),'Detalle más ajustes de regalía, repuestos y empleador'),('Activos aportados en especie',money(s['assets_in_kind']),'Asignación provisional publicada · no efectivo'),(inventory_label,money(s['preop']+s['spares']),'Salida inicial de FW antes del IVA'),('CT histórico · solo referencia',money(s['historical_wc']),'No se suma nuevamente al flujo')])
    left,right=st.columns(2,gap='large')
    with left:
        agg=opex.groupby('Área')['USD'].sum(min_count=1).sort_values()
        fig=go.Figure(go.Bar(y=['<br>'.join(textwrap.wrap(v,23)) for v in agg.index],x=displayed(agg)/1e6,orientation='h',marker_color=NAVY,customdata=[money(v) for v in agg],hovertemplate='%{y}<br>%{customdata}<extra></extra>'))
        fig.update_layout(title='OPEX por área · '+year);fig.update_xaxes(title_text='Millones de '+currency_code());plot(fig,'opex_area',450)
    with right:
        amounts=[s['assets_in_kind'],s['preop'],s['spares']]
        fig=go.Figure(go.Pie(labels=['Activos en especie','Preoperacionales','Inventario inicial' if model.get('products')==(80,) else 'Repuestos iniciales'],values=amounts,hole=.65,marker=dict(colors=[NAVY,GOLD,TEAL]),textinfo='percent',customdata=[money(v) for v in amounts],hovertemplate='%{label}<br>%{customdata}<extra></extra>'))
        fig.update_layout(title='Inversión económica inicial · sin IVA ni CT histórico',annotations=[dict(x=.5,y=.5,text='<b>'+money(s['economic_investment'],True)+'</b>',showarrow=False,font=dict(size=17,color=NAVY))]);plot(fig,'initial_investment',450)
    opex_tab,assets_tab=st.tabs(['Presupuesto operativo','Inventario de activos y arranque'])
    with opex_tab:
        st.caption('Las tarifas y presupuestos CLP de 08 se convierten con el tipo de cambio del modelo para conciliar con el OPEX en USD; los ajustes de filas 65–67 ya están en USD. La visualización usa la moneda elegida en el panel.')
        statuses=sorted(opex['Estado'].dropna().unique())
        key=key_prefix+'_opex_status'
        if key in st.session_state:
            st.session_state[key]=[value for value in st.session_state[key] if value in statuses]
        selected=st.multiselect('Estado del presupuesto OPEX',statuses,key=key,placeholder='Todos los estados publicados')
        if selected:opex=opex[opex['Estado'].isin(selected)]
        financial_table(opex[['ID','Área','Concepto','Destino','USD','Estado','Fuente']].rename(columns={'USD':'Presupuesto'}),['Presupuesto'])
    with assets_tab:
        include_reference=st.checkbox('Incluir referencias históricas de capital de trabajo',key=key_prefix+'_include_wc')
        if not include_reference:assets=assets[~assets['Naturaleza'].eq('Capital de trabajo')]
        st.caption('Se utiliza Costo aplicado USD (columna P), que concilia el aporte de activos de la planilla. Los costos unitarios y el presupuesto previo son referencias distintas. La asignación por activo requiere respaldo según el modelo.')
        financial_table(assets[['ID','Área','Activo / alcance','Naturaleza','Asignación','Cantidad','Costo aplicado USD','Vida útil','Origen / estado','Fuente']],['Costo aplicado USD'])
        annual_bars(model['annual'],[('assets_book','Valor contable de activos',NAVY),('asset_da','Depreciación anual',GOLD)],'asset_book','Activos netos y depreciación · horizonte publicado')
    source_note('08 Gastos operativos','09 Activos y arranque','03 Supuestos')


def audit_view(model):
    s=model['scalars']
    st.subheader('Supuestos, calidad y trazabilidad')
    st.caption('Los controles contrastan salidas de las hojas 00–09 y componentes publicados. La tolerancia reconoce el redondeo del CSV: una conciliación no reemplaza las condiciones comerciales pendientes.')
    checks=model['checks'];bad=checks[~checks['Estado'].eq('Conciliado')]
    kpis([('Controles conciliados',f'{checks["Estado"].eq("Conciliado").sum()} / {len(checks)}','DCF, inversión, OPEX, balance y caja'),('Condiciones pendientes',str(len(model['pending'])),'Estados de la hoja 00 Evaluación'),('Tasa / crecimiento terminal',pct(s['rate'])+' / '+pct(s['growth']),'Supuestos publicados; no tasas de mercado verificadas'),('Tipo de cambio del modelo',f'{s["model_fx"]:,.2f}'.replace(',','X').replace('.',',').replace('X','.'),'CLP/USD usado por la planilla')])
    if not bad.empty:st.warning('Hay conciliaciones o datos que requieren revisión. Consulta la diferencia y su fuente antes de interpretar el valor.')
    if not model['formula_errors'].empty:st.error('La publicación contiene errores de fórmula. Se muestran en el detalle de fuente.')
    st.dataframe(checks,hide_index=True,use_container_width=True,column_config={'Control':st.column_config.TextColumn(width='large'),'Fuente':st.column_config.TextColumn(width='large')})
    st.caption('Las diferencias y tolerancias conservan la unidad del control (USD de origen o cantidad de celdas); no se convierten con la moneda de visualización.')
    st.markdown('##### Variables del caso activo')
    raw=model['raw']['03 Supuestos']
    variables=[]
    for i,row in enumerate(raw,1):
        if len(row)>7 and row[2] and row[4] and row[7] and row[2] not in ['Supuesto','Variable']:
            variables.append({'Supuesto':row[2],'Valor publicado':row[4],'Unidad':row[5],'Criterio / fuente':row[7],'Celda':'03 Supuestos!E'+str(i)})
    st.dataframe(pd.DataFrame(variables),hide_index=True,use_container_width=True,height=380,column_config={'Supuesto':st.column_config.TextColumn(width='large'),'Criterio / fuente':st.column_config.TextColumn(width='large')})
    st.markdown('##### Localización de indicadores principales')
    st.dataframe(model['provenance'],hide_index=True,use_container_width=True)
    with st.expander('Caso activo frente a base V6 fija · valores de origen'):
        evaluation=model['raw']['00 Evaluación'];rows=[]
        for i,row in enumerate(evaluation,1):
            if len(row)>4 and row[1] and row[2] and row[3] and row[4] and i>10 and i<25:
                rows.append({'Indicador':row[1],'Caso activo':row[2],'Base V6 fija':row[3],'Variación publicada':row[4],'Fuente':f'00 Evaluación!C{i}:E{i}'})
        st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
        st.caption('La base V6 es la referencia fija de 14-10-2026 de la fuente; tasas en puntos porcentuales. Esta tabla conserva las unidades y los formatos publicados.')
    st.markdown('##### Revisión íntegra de pestañas 00–09')
    sheet=st.selectbox('Pestaña de la fuente',list(SHEETS),key='option4_valuation_source_sheet')
    raw=model['raw'][sheet];width=max(map(len,raw))
    from valuation_data import column_name
    source_table=pd.DataFrame([row+['']*(width-len(row)) for row in raw],columns=[column_name(i+1) for i in range(width)])
    source_table.insert(0,'Fila',list(range(1,len(source_table)+1)))
    st.dataframe(source_table,hide_index=True,use_container_width=True,height=430)
    st.caption('Celdas originales y moneda de origen; esta vista permite comprobar encabezados, notas y resultados sin modificar la planilla.')
    st.link_button('Abrir esta pestaña en el documento fuente',SOURCE+'html#gid='+SHEETS[sheet])
    if not model['formula_errors'].empty:st.dataframe(model['formula_errors'],hide_index=True,use_container_width=True)


def render_valuation(refresh_nonce=0):
    with st.container(key='option4_valuation'):
        st.html('<style>'+Path(__file__).with_name('assets').joinpath('valuation.css').read_text()+'</style>')
        try:
            with st.spinner('Leyendo las once pestañas de valorización (00–09)…'):model=load_valuation(refresh_nonce)
        except Exception as exc:
            st.error(f'No se pudo cargar el documento de valorización: {exc}')
            st.markdown('[Abrir documento fuente de valorización]('+SOURCE+'html)')
            return
        s=model['scalars']
        st.html('<header class="valuation-hero"><div><span>SUB BLOQUE 4 · NEGOCIO CONJUNTO</span><h2>Valor del Negocio · 10 y 80 kW</h2><p>Del caso publicado a sus fundamentos: flujos, operación, caja y activos de las turbinas de 10 y 80 kW.</p></div>'
            '<div class="valuation-badges"><b>'+html.escape(model['scenario'])+'</b><b>Producción '+html.escape(model['production'])+'</b><b>Aporte: '+html.escape(model['status'])+'</b></div></header>')
        with st.expander('Fuente, moneda y año de detalle',expanded=False):
            st.caption(f'Revisión referencial de la fuente: {s["valuation_date"]} · Consultado: {model["fetched_at"]} · Hora de Santiago · Proyección {int(s["first_year"])}–{int(s["first_year"])+9}')
            st.caption('Fuente en USD nominales · Visualización '+currency_code()+(f' a {exchange_rate():,.2f} CLP/USD' if currency_code()=='CLP' else '')+f' · Tipo de cambio del modelo: {s["model_fx"]:,.2f} CLP/USD. La conversión visual no modifica precios ni supuestos de la fuente.')
            st.caption('Actualización automática cada 60 segundos y mediante Actualizar todo. Se consulta exclusivamente el documento de valorización; el caso activo se modifica en la planilla original.')
            st.link_button('Abrir modelo de valorización · 00–09',SOURCE+'html')
            year_options=model['annual'].loc[model['annual']['Año modelo'].gt(0),'Año'].tolist()
            year_key='option4_valuation_year'
            if year_key in st.session_state and st.session_state[year_key] not in year_options:st.session_state[year_key]=year_options[0]
            year=st.selectbox('Año operativo para los detalles',year_options,key=year_key,help='Actualiza resultados por turbina, balance y OPEX. La valorización DCF y las curvas completas conservan el horizonte de diez años.')
        issues=model['checks'][~model['checks']['Estado'].eq('Conciliado')]
        if not issues.empty:st.warning(f'La publicación tiene {len(issues)} controles por revisar. Consulta Supuestos y trazabilidad para localizar las diferencias.')
        if not model['formula_errors'].empty:st.error('Hay errores de fórmula en la publicación. Revísalos en Supuestos y trazabilidad.')
        tabs=st.tabs(['Resumen y valorización','Inversión y socios','Resultados y operación','Caja y cobros','OPEX y activos','Supuestos y trazabilidad'])
        with tabs[0]:overview(model)
        with tabs[1]:investment(model)
        with tabs[2]:operating(model,year)
        with tabs[3]:cash_view(model,year)
        with tabs[4]:cost_assets(model,year)
        with tabs[5]:audit_view(model)
