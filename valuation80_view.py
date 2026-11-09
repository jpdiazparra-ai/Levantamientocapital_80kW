"""Executive report for the standalone 80 kW case, sharing the established palette."""
import html
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from display_currency import currency_code, exchange_rate
from valuation_data import column_name
from valuation80_data import SOURCE, SHEETS, load_valuation80
from valuation_finance import complete_sum, divide, projection_diagnostics
from valuation_interactive import diagnostics_panel, diagnostics_definitions, dcf_lab
from valuation_lcoe import lcoe_panel
from valuation_view import (NAVY, TEAL, GOLD, ORANGE, kpis, context, section, plot, money, pct, count,
    displayed, financial_table, annual_bars, investment_details, operating, cash_view)

PREFIX = 'option4_valuation80'
MAIN_TABS = ['Evaluación 80 kW','Datos y supuestos','Inversión y socios','Resultados y caja',
    'Ventas y fabricación','Gastos operativos','Activos y desarrollo','Controles y fuentes']


def unit_products(model, year):
    row = model['annual'].loc[lambda f:f['Año'].eq(year)].iloc[0]
    units, sales, cost = row['units_80'], row['sales_80'], row['cost_80']
    gross = sales-cost if pd.notna(cost) and pd.notna(row['cogs']) and abs(cost-row['cogs'])<=5 else float('nan')
    variable = row['opex_80']
    return pd.DataFrame([{'Turbina': '80 kW', 'Potencia kW': 80, 'Entregas': units,
        'Precio / equipo': divide(sales, units), 'Fabricación / equipo': divide(cost, units),
        'Margen bruto / equipo': divide(gross, units), 'OPEX específico / equipo': divide(variable, units),
        'Contribución / equipo': divide(gross-variable, units), 'Margen bruto %': divide(gross, sales)}])


def unit_panel80(model):
    section('02 / ECONOMÍA UNITARIA', 'Turbina de 80 kW · margen y escala')
    options = model['annual'].loc[lambda f:f['Año modelo'].gt(0), 'Año'].tolist()
    key = PREFIX+'_unit_year'
    if key in st.session_state and st.session_state[key] not in options:st.session_state[key]=options[0]
    left, right = st.columns(2)
    with left:year = st.selectbox('Año de economía unitaria', options, key=key)
    with right:basis = st.radio('Base de comparación', ['Por equipo', 'Por kW'], horizontal=True, key=PREFIX+'_basis')
    row = model['annual'].loc[lambda f:f['Año'].eq(year)].iloc[0]
    products = unit_products(model, year)
    unit = products.iloc[0]
    kpis([('Precio por equipo', money(unit['Precio / equipo']), year),
        ('Fabricación por equipo', money(unit['Fabricación / equipo']), 'Costo total / entregas, incluidos terceros'),
        ('Margen bruto', pct(unit['Margen bruto %']), money(unit['Margen bruto / equipo'])+' por equipo'),
        ('Contribución por equipo', money(unit['Contribución / equipo']), 'Después de entrega/flota; antes de estructura')])
    divisor = 80 if basis=='Por kW' else 1
    fig = go.Figure()
    for field, label, color in [('Fabricación / equipo','Fabricación',NAVY), ('OPEX específico / equipo','Entrega y flota',GOLD), ('Contribución / equipo','Contribución',TEAL)]:
        fig.add_trace(go.Bar(y=['80 kW'], x=[displayed(unit[field])/divisor], name=label, orientation='h', marker_color=color,
            customdata=[money(unit[field]/divisor)], hovertemplate='%{customdata}<extra>%{fullData.name}</extra>'))
    if pd.notna(unit['Precio / equipo']):fig.add_vline(x=displayed(unit['Precio / equipo'])/divisor,line_dash='dash',line_color=ORANGE,annotation_text='Precio de venta')
    fig.update_layout(barmode='relative', title='Composición del precio · '+basis.lower())
    fig.update_xaxes(title_text=currency_code()+(' / kW' if divisor==80 else ' / equipo'))
    plot(fig,'80_unit_composition',280)
    financial_table(products.drop(columns='Potencia kW'), ['Precio / equipo','Fabricación / equipo','Margen bruto / equipo','OPEX específico / equipo','Contribución / equipo'], ['Margen bruto %'])
    context('Costos y contribución', 'Entrega y flota procede de 08 Gastos operativos. La estructura operativa permanece separada; la contribución por equipo no equivale al EBITDA por equipo. El costo de fabricación conserva el alcance y los presupuestos pendientes de la fuente.')
    with st.expander('Costo base por componente · referencia de fabricación'):
        if model['components'].empty:
            st.info('La hoja 07 no publica un detalle de componentes con la estructura esperada. Los resultados financieros y el PDF conservan sus fuentes propias.')
        else:
            financial_table(model['components'], ['USD base / equipo'])
            st.caption('Detalle publicado en USD/equipo de 07, con los nombres actuales de componentes o sistemas. Los saldos por desglosar se conservan como referencia y no se suman automáticamente. No equivale al costo con margen del proveedor ni al precio de venta.')
    lcoe_panel(model, year, products, key_prefix=PREFIX+'_lcoe')
    section('04 / ESCALA OPERATIVA','Equilibrio y sensibilidad del volumen · 80 kW')
    key = PREFIX+'_volume'
    if st.session_state.get(PREFIX+'_volume_year')!=year:
        st.session_state[key]=float(row['units_80'])
        st.session_state[PREFIX+'_volume_year']=year
    volume = st.number_input('Entregas de 80 kW del laboratorio', min_value=0., value=None, step=1., key=key)
    if volume is None:return
    contribution = unit['Contribución / equipo']
    simulated = contribution*volume-row['opex_common']
    equilibrium = divide(row['opex_common'], contribution)
    kpis([('EBITDA aproximado', money(simulated),'Contribución unitaria × volumen − estructura'),
        ('Equilibrio operativo', count(equilibrium)+' equipos eq.', 'Antes de depreciación, impuestos y CAPEX'),
        ('Margen de seguridad', pct(divide(volume-equilibrium,volume)), 'Respecto del volumen simulado'),
        ('Exceso de capacidad propia', count(max(volume-row['capacity'],0)), 'Equipos que requieren revisar terceros')])
    volumes = sorted(set([0., float(volume), float(row['capacity']), *([float(equilibrium)] if pd.notna(equilibrium) else [])]))
    fig=go.Figure(go.Scatter(x=volumes,y=[displayed(contribution*v-row['opex_common'])/1e6 for v in volumes], mode='lines+markers', line=dict(color=TEAL,width=3)))
    fig.add_hline(y=0,line_color=GOLD);fig.update_layout(title='Sensibilidad del EBITDA al volumen');fig.update_xaxes(title_text='Equipos de 80 kW');fig.update_yaxes(title_text='MM '+currency_code());plot(fig,'80_volume',300)
    context('Alcance del laboratorio','Mantiene precio, fabricación y costo de entrega/flota por equipo del año elegido, con estructura fija. No recalcula inflación, economías de escala, capital de trabajo, anticipos, impuestos, CAPEX ni disponibilidad de terceros. La flota se aproxima como costo proporcional al volumen.')


def projection80(model):
    section('02 / PROYECCIÓN','Operación y caja del negocio de 80 kW')
    operating = model['annual'].loc[lambda f:f['Año modelo'].gt(0)]
    options = operating['Año'].tolist()
    key = PREFIX+'_range'
    if key in st.session_state and any(v not in options for v in st.session_state[key]):del st.session_state[key]
    first,last = st.select_slider('Período del resumen', options, value=(options[0],options[4]), key=key)
    frame = operating.loc[lambda f:f['Año'].between(first,last)]
    d = projection_diagnostics(frame)
    kpis([('Ventas acumuladas',money(d['sales']),first+'–'+last),('Margen EBITDA ponderado',pct(d['margin']),'Σ EBITDA / Σ ventas'),
        ('Flujo libre acumulado',money(d['fcff']),'Σ flujo operativo del período'),('Caja libre al cierre',money(d['cash_close']),'Saldo del último año seleccionado')])
    metric=st.radio('Vista de la proyección',['Ventas y EBITDA','Flujo libre y caja','Entregas y capacidad'],horizontal=True,key=PREFIX+'_projection_metric')
    if metric=='Ventas y EBITDA':annual_bars(frame,[('sales','Ventas',NAVY),('ebitda','EBITDA',TEAL)],'80_projection_income',metric)
    else:
        fig=go.Figure()
        if metric=='Flujo libre y caja':
            fig.add_trace(go.Bar(x=frame['Año'],y=displayed(frame['fcff'])/1e6,name='Flujo libre anual',marker_color=TEAL))
            fig.add_trace(go.Scatter(x=frame['Año'],y=displayed(frame['cash_free'])/1e6,name='Caja libre al cierre',line=dict(color=NAVY,width=3)))
            fig.update_yaxes(title_text='MM '+currency_code())
        else:
            fig.add_trace(go.Bar(x=frame['Año'],y=frame['units_80'],name='Entregas 80 kW',marker_color=NAVY))
            fig.add_trace(go.Scatter(x=frame['Año'],y=frame['capacity'],name='Capacidad propia',line=dict(color=TEAL,dash='dash')))
            fig.update_yaxes(title_text='Equipos por año')
        fig.update_xaxes(type='category');fig.update_layout(title=metric);plot(fig,'80_projection_other')
    context('Ratios del período',f'CAGR de ventas: {pct(d["cagr"])} · Conversión flujo libre/EBITDA: {pct(d["cash_conversion"])} · Entregas externas: {pct(d["external_share"])}. El flujo incluye anticipos, IVA, inventario y CAPEX; los saldos de caja no se suman.')
    fields=[('Demanda 80 kW','demand_80','n'),('Entregas 80 kW','units_80','n'),('Capacidad propia','capacity','n'),('Fabricación externa','external','n'),('Demanda sin atender','unserved','n'),('Ventas','sales','m'),('Fabricación','cogs','m'),('OPEX','opex','m'),('EBITDA','ebitda','m'),('Margen EBITDA','ebitda_margin','p'),('Flujo libre','fcff','m'),('CAPEX','capex','m'),('Anticipos al cierre','advances','m'),('Caja libre al cierre','cash_free','m')]
    matrix=[{'Indicador':label,'Unidad':'equipos' if kind=='n' else '%' if kind=='p' else currency_code(),
        **{r['Año']:count(r[field]) if kind=='n' else pct(r[field]) if kind=='p' else money(r[field]) for _,r in frame.iterrows()}} for label,field,kind in fields]
    st.dataframe(pd.DataFrame(matrix),hide_index=True,use_container_width=True,height=540)


def evaluation_table(frame):
    """Format the published executive indicators without rebuilding rounded values."""
    result=frame.copy()
    result['Valor publicado']=[money(r['Valor']) if r['Unidad'].startswith('USD') else pct(r['Valor']) if r['Unidad']=='%' else count(r['Valor']) for _,r in frame.iterrows()]
    result['Unidad']=result['Unidad'].str.replace('USD',currency_code(),regex=False)
    st.dataframe(result[['Concepto','Valor publicado','Unidad','Fuente']],hide_index=True,use_container_width=True,
        column_config={'Concepto':st.column_config.TextColumn(width='large'),'Fuente':st.column_config.TextColumn(width='large')})


def overview80(model):
    s,a,e=model['scalars'],model['annual'],model['evaluation']
    section('00 / EVALUACIÓN','El caso de 80 kW en una mirada')
    st.caption('Resultados y valorización · arranque e inversión · economía unitaria y respaldos · primeros cinco años. Cifras publicadas en 00 Evaluación.')
    from valuation80_report import report80_payload
    try:
        pdf=report80_payload(model,currency_code(),exchange_rate(),layout_version=4)
        st.download_button('Descargar PDF ejecutivo · 80 kW',pdf,
            file_name='Turbina_80kW_Caso_exclusivo_'+currency_code()+'.pdf',mime='application/pdf',key=PREFIX+'_pdf',on_click='ignore',
            help='Seis páginas: evaluación, inversión, proyección, economía unitaria con costos del subbloque 1, calendario de desembolsos y detalle de gastos operativos.')
    except Exception as exc:
        st.button('PDF ejecutivo no disponible',disabled=True,key=PREFIX+'_pdf_unavailable')
        st.caption('No se pudo preparar el PDF completo con costos y desembolsos del subbloque 1: '+str(exc))
    with st.container(border=True):
        section('01 / RESULTADOS Y VALORIZACIÓN','Desempeño del primer año y valor del proyecto')
        first_year=e['projection'].iloc[0]['Año']
        kpis([('Ventas netas · año 1',money(s['sales_y1']),first_year+' · ingresos por entregas'),
            ('EBITDA · año 1',money(s['ebitda_y1']),'Margen publicado '+pct(s['ebitda_margin_y1'])),
            ('Flujo libre operativo · año 1',money(s['fcff_y1']),'Incluye capital de trabajo, anticipos, IVA y CAPEX'),
            ('Anticipos pendientes · año 1',money(s['advances_y1']),'Obligación por equipos pendientes de entrega')])
        left,right=st.columns(2,gap='large')
        with left:
            r=a.loc[lambda f:f['Año modelo'].eq(1)].iloc[0]
            vals=[s['sales_y1'],-r['cogs'],-r['opex'],s['ebitda_y1']]
            fig=go.Figure(go.Waterfall(x=['Ventas netas','Fabricación','OPEX','EBITDA'],y=[displayed(v)/1e6 for v in vals],
                measure=['relative','relative','relative','total'],text=[money(v,True) for v in vals],textposition='outside',
                increasing=dict(marker_color=TEAL),decreasing=dict(marker_color=GOLD),totals=dict(marker_color=NAVY)))
            fig.update_layout(title='De las ventas al EBITDA · '+first_year,showlegend=False)
            fig.update_yaxes(title_text='MM '+currency_code(),range=[0,displayed(s['sales_y1'])/1e6*1.2]);plot(fig,'80_evaluation_ebitda',350)
            st.caption('Componentes de fabricación y OPEX: 04 Resultados y flujo. Ventas y EBITDA: 00 Evaluación; pueden existir diferencias de redondeo.')
        with right:
            values=[s['npv_cash'],s['npv_economic'],s['dcf']]
            fig=go.Figure(go.Bar(y=['VAN operativo sin terminal','VAN económico sin terminal','DCF previo al aporte'],
                x=[displayed(v)/1e6 for v in values],orientation='h',marker_color=[GOLD,TEAL,NAVY],
                text=[money(v,True) for v in values],textposition='outside',cliponaxis=False))
            fig.update_layout(title='Tres lecturas del valor del proyecto',showlegend=False)
            fig.update_xaxes(title_text='MM '+currency_code(),range=[min(0,min(displayed(v)/1e6 for v in values)*1.2),max(displayed(v)/1e6 for v in values)*1.35])
            fig.update_yaxes(autorange='reversed');plot(fig,'80_evaluation_values',350)
        kpis([('DCF patrimonial previo al aporte',money(s['dcf']),'Fecha base '+str(s['valuation_date'])),
            ('TIR económica sin terminal',pct(s['irr_economic']),'Incorpora el valor de los activos aportados'),
            ('Recuperación de caja descontada',count(e['recovery_years'])+(' año' if e['recovery_years']==1 else ' años'),'Año completo publicado · flujo de caja de FW'),
            ('Peso del terminal',pct(s['terminal_weight']),'Tasa '+pct(s['rate'])+' · crecimiento '+pct(s['growth']))],secondary=True)
        context('Calidad del flujo y alcance del valor',f'El aumento de anticipos representa {pct(e["contribution_ratio"])} del flujo libre del primer año. Los anticipos financian pedidos pendientes y no equivalen a utilidad. El VAN económico resta el valor de activos aportados; el DCF incluye el terminal mediante {e["terminal_method"]}. La TIR económica corresponde al proyecto; el payback publicado es recuperación de caja, no recuperación económica interpolada ni retorno del socio.')
        with st.expander('Cifras exactas y referencias · resultados y valorización'):evaluation_table(e['results'])
    with st.container(border=True):
        section('02 / ARRANQUE E INVERSIÓN','Del aporte propuesto a la caja disponible')
        f=e['funding'].set_index('Concepto')['Valor']
        kpis([('Capital primario propuesto',money(f['Capital primario']),'Estado '+model['status']+' · aporte '+e['funding_date']),
            ('Pago secundario',money(f['Pago secundario']),'Pago a accionistas fuera de FW'),
            ('Participación final inversionista',pct(f['Participación final del inversionista']),'Precio previo '+money(f['Valor previo implícito negociado'])),
            ('Caja libre al cierre · año 0',money(f['Caja libre al cierre · año 0']),'Después del financiamiento del caso')])
        left,right=st.columns(2,gap='large')
        with left:
            values=[f['Capital primario'],-f['Consumo neto de caja · año 0'],f['Puente teórico máximo requerido'],f['Caja libre al cierre · año 0']]
            fig=go.Figure(go.Waterfall(x=['Aporte primario','Consumo de arranque','Puente teórico','Caja libre'],
                y=[displayed(v)/1e6 for v in values],measure=['relative','relative','relative','total'],
                text=[money(v,True) for v in values],textposition='outside',increasing=dict(marker_color=TEAL),
                decreasing=dict(marker_color=GOLD),totals=dict(marker_color=NAVY)))
            fig.update_layout(title='Aplicación de fondos en el año 0',showlegend=False)
            span=max(abs(displayed(v)/1e6) for v in values) or 1
            fig.update_yaxes(title_text='MM '+currency_code(),range=[min(0,displayed(values[-1])/1e6)-span*.14,span*1.18]);plot(fig,'80_evaluation_funding',350)
        with right:
            values=[f['Caja libre al cierre · año 0'],f['Brecha para caja objetivo · año 0']]
            fig=go.Figure()
            for value,label,color in zip(values,['Caja libre disponible','Brecha para caja objetivo'],[TEAL,ORANGE]):
                fig.add_trace(go.Bar(y=['Caja objetivo al cierre'],x=[displayed(value)/1e6],name=label,orientation='h',marker_color=color,
                    customdata=[money(value)],hovertemplate='%{customdata}<extra>%{fullData.name}</extra>'))
            target=displayed(f['Caja objetivo al cierre · año 0'])/1e6
            fig.add_vline(x=target,line_color=NAVY,line_dash='dash',annotation_text='Objetivo '+money(f['Caja objetivo al cierre · año 0'],True))
            fig.update_layout(title='Cobertura de la reserva objetivo',barmode='relative');fig.update_xaxes(title_text='MM '+currency_code(),range=[0,max(target,sum(displayed(v)/1e6 for v in values),.001)*1.25]);plot(fig,'80_evaluation_reserve',350)
        kpis([('Consumo neto de arranque',money(f['Consumo neto de caja · año 0']),'Uso de caja · año 0'),
            ('Caja objetivo',money(f['Caja objetivo al cierre · año 0']),'Referencia de liquidez al cierre'),
            ('Brecha para caja objetivo',money(f['Brecha para caja objetivo · año 0']),'Necesidad residual para conservar la reserva'),
            ('Puente teórico requerido',money(f['Puente teórico máximo requerido']),'Financiamiento por conseguir, según calendario')],secondary=True)
        context('Precio y disponibilidad del capital',f'Valor previo implícito: {money(f["Valor previo implícito negociado"])} · valor posterior: {money(f["Valor posterior implícito negociado"])}. El precio usa el mismo valor por acción en los tramos primario y secundario. El aporte está en estado {model["status"]}; la caja publicada lo proyecta. El DCF supone que los activos aportados estarán disponibles para operar.')
        with st.expander('Cifras exactas y referencias · inversión y financiamiento'):evaluation_table(e['funding'])
    with st.container(border=True):
        section('03 / ECONOMÍA UNITARIA Y RESPALDOS','Lo que deja cada turbina entregada')
        u=e['unit'].set_index('Concepto')['Valor']
        kpis([('Equipos entregados · año 1',count(u['Equipos entregados']),'Turbinas de 80 kW'),
            ('Precio de venta por equipo',money(u['Precio de venta']),'Referencia publicada del primer año'),
            ('Margen bruto por equipo',money(u['Margen bruto por equipo']),pct(u['Margen bruto'])+' sobre ventas'),
            ('Contribución por equipo',money(u['Contribución antes de estructura operativa']),'Antes de estructura operativa')])
        left,right=st.columns([1.4,1],gap='large')
        with left:
            labels=['Fabricación','Margen bruto','Entrega y flota','Contribución']
            values=[u['Fabricación media por equipo entregado'],u['Margen bruto por equipo'],u['Costo de entrega y flota por equipo'],u['Contribución antes de estructura operativa']]
            fig=go.Figure()
            for i,(label,value,color) in enumerate(zip(labels,values,[NAVY,TEAL,GOLD,TEAL])):
                fig.add_trace(go.Bar(y=['Fabricación y margen' if i<2 else 'Desglose del margen bruto'],x=[displayed(value)],orientation='h',name=label,marker_color=color,
                    customdata=[money(value)],hovertemplate='%{customdata}<extra>%{fullData.name}</extra>'))
            fig.update_layout(title='Del precio al margen y a la contribución',barmode='relative');fig.update_xaxes(title_text=currency_code()+' / equipo');fig.update_yaxes(autorange='reversed');plot(fig,'80_evaluation_unit',330)
        with right:
            st.markdown('##### Condiciones de respaldo publicadas')
            for _,row in e['conditions'].iterrows():
                context(row['Condición'],row['Estado publicado'])
        st.caption('El margen bruto se desglosa en entrega/flota y contribución; ambas barras muestran etapas del mismo precio y no se suman entre sí. Las cifras de 00 están redondeadas por equipo y pueden diferir en una unidad. La capacidad comercial del 80 kW depende de su liberación técnica.')
        with st.expander('Cifras exactas y referencias · economía unitaria'):evaluation_table(e['unit'])
    with st.container(border=True):
        section('04 / PRIMEROS CINCO AÑOS','Trayectoria comercial, rentabilidad y caja')
        p=e['projection'];sales=complete_sum(p['sales']);ebitda=complete_sum(p['ebitda'])
        kpis([('Ventas acumuladas',money(sales),p.iloc[0]['Año']+'–'+p.iloc[-1]['Año']),
            ('Margen EBITDA ponderado',pct(divide(ebitda,sales)),'Σ EBITDA / Σ ventas · derivado'),
            ('Flujo libre acumulado',money(complete_sum(p['fcff'])),'Suma de los cinco flujos anuales'),
            ('Caja libre al último cierre',money(p.iloc[-1]['cash_free']),'Saldo final · no suma de saldos')])
        left,right=st.columns(2,gap='large')
        with left:annual_bars(p,[('sales','Ventas netas',NAVY),('ebitda','EBITDA',TEAL)],'80_evaluation_five_income','Ventas y EBITDA · cinco años')
        with right:
            fig=go.Figure(go.Bar(x=p['Año'],y=displayed(p['fcff'])/1e6,name='Flujo libre anual',marker_color=TEAL))
            fig.add_trace(go.Scatter(x=p['Año'],y=displayed(p['cash_free'])/1e6,name='Caja libre al cierre',mode='lines+markers',line=dict(color=NAVY,width=3)))
            fig.update_layout(title='Generación de flujo y saldo disponible');fig.update_yaxes(title_text='MM '+currency_code());fig.update_xaxes(type='category');plot(fig,'80_evaluation_five_cash')
        left,right=st.columns(2,gap='large')
        with left:
            fig=go.Figure()
            for field,label,color in [('demand_80','Demanda',GOLD),('units_80','Entregas',NAVY),('external','Fabricación externa',ORANGE),('unserved','Demanda sin atender',TEAL)]:
                fig.add_trace(go.Bar(x=p['Año'],y=p[field],name=label,marker_color=color))
            fig.add_trace(go.Scatter(x=p['Año'],y=p['capacity'],name='Capacidad propia',line=dict(color=TEAL,dash='dash'),mode='lines+markers'))
            fig.update_layout(title='Demanda, entregas y capacidad',barmode='group');fig.update_yaxes(title_text='Equipos / año');fig.update_xaxes(type='category');plot(fig,'80_evaluation_five_capacity')
        with right:annual_bars(p,[('advances','Anticipos al cierre',GOLD),('capex','CAPEX pagado por FW',NAVY)],'80_evaluation_five_commitments','Anticipos pendientes y reinversión')
        metrics=[('Demanda proyectada','demand_80','n'),('Capacidad propia','capacity','n'),('Entregas','units_80','n'),('Fabricación externa','external','n'),('Demanda sin atender','unserved','n'),('Ventas netas','sales','m'),('EBITDA','ebitda','m'),('Margen EBITDA','ebitda_margin','p'),('Flujo libre operativo','fcff','m'),('CAPEX pagado por FW','capex','m'),('Anticipos pendientes','advances','m'),('Caja libre al cierre','cash_free','m')]
        matrix=[{'Indicador':label,'Unidad':'equipos' if kind=='n' else '%' if kind=='p' else currency_code(),**{r['Año']:count(r[field]) if kind=='n' else pct(r[field]) if kind=='p' else money(r[field]) for _,r in p.iterrows()}} for label,field,kind in metrics]
        st.dataframe(pd.DataFrame(matrix),hide_index=True,use_container_width=True,height=470,column_config={'Indicador':st.column_config.TextColumn(width='large')})
        st.caption('Los cinco años y los valores proceden directamente de 00 Evaluación. Los acumulados y el margen ponderado son derivados; caja y anticipos son saldos de cierre. El detalle anual completo y el calendario mensual se consultan en Resultados y caja.')


def inputs80(model):
    section('00 + 03 / DATOS Y SUPUESTOS','Las variables que construyen el caso')
    st.caption('Datos publicados de escenario, capacidad, cobros, precios e inversión. Los cambios del caso se realizan en la hoja de origen.')
    s=model['scalars']
    kpis([('Escenario',model['scenario'],'Producción '+model['production']),('Anticipo de clientes',pct(s['advance_rate']),count(s['advance_days'])+' días antes de entregar'),
        ('Tasa de descuento',pct(s['rate']),'Crecimiento terminal '+pct(s['growth'])),('Primer año de operación',str(int(s['first_year'])),'Fecha base DCF '+str(s['valuation_date']))])
    from valuation_data import Sheet
    inputs=Sheet('00 Datos de entrada',model['raw']['00 Datos de entrada'])
    groups={};group=None
    for i,row in enumerate(inputs.rows,1):
        label=inputs.cell(f'B{i}')
        if label[:2] in ['01','02','03'] and '   ' in label:
            group=label[5:].strip();groups[group]=[];continue
        if label.startswith('04   '):break
        value=inputs.cell(f'C{i}')
        if group and label and value and label!='Variable':
            unit=inputs.cell(f'D{i}') or inputs.cell(f'E{i}')
            note=inputs.cell(f'F{i}') if not inputs.cell(f'D{i}') and unit else inputs.cell(f'E{i}')
            groups[group].append({'Variable':label,'Valor publicado':value,'Unidad':unit if len(unit)<25 else '',
                'Criterio':note,'Fuente':f'00 Datos de entrada!C{i}'})
    for title,rows in groups.items():
        st.markdown('##### '+title.capitalize())
        st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True,column_config={'Variable':st.column_config.TextColumn(width='large'),'Criterio':st.column_config.TextColumn(width='large')})
    st.caption('Esta tabla conserva monedas y unidades originales, incluido el precio inicial en CLP; no representa valores convertidos por el selector de visualización.')
    with st.expander('Calendario manual de demanda, capacidad e inversión'):
        header=next(i for i in range(1,len(inputs.rows)+1) if inputs.cell(f'C{i}')==str(int(s['first_year'])))
        years=inputs.rows[header-1][2:12]
        rows=[{'Variable':inputs.cell(f'B{i}'),**{year:inputs.cell(f'{column_name(j+3)}{i}') or 'Sin ajuste manual' for j,year in enumerate(years)}} for i in range(header+1,header+5) if inputs.cell(f'B{i}')]
        st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
        st.caption('Una celda vacía usa la proyección o conserva capacidad; un cero explícito conserva su efecto en el caso publicado.')
    st.markdown('##### Sensibilidad publicada · precio y tasa')
    sens=model['sensitivity'].pivot(index='Tasa',columns='Precio x',values='DCF USD').sort_index()
    fig=go.Figure(go.Heatmap(z=displayed(sens.to_numpy())/1e6,x=sens.columns,y=sens.index,
        text=[[money(v,True) for v in r] for r in sens.to_numpy()],texttemplate='%{text}',
        colorscale=[[0,'#EDF3F6'],[.5,'#7DBBB3'],[1,NAVY]],xgap=5,ygap=5,colorbar=dict(title='MM '+currency_code())))
    fig.update_xaxes(title_text='Multiplicador de precio',tickvals=sens.columns);fig.update_yaxes(title_text='Tasa de descuento',tickformat='.0%',tickvals=sens.index,autorange='reversed');plot(fig,'80_sensitivity')
    with st.expander('Escenario analítico · tasa de descuento y terminal'):
        dcf_lab(model,key_prefix=PREFIX)
    with st.expander('Indicadores derivados y definiciones de rentabilidad'):
        diagnostics_panel(model)
        diagnostics_definitions()
    with st.expander('Supuestos técnicos y financieros de 03 · detalle publicado'):
        raw=model['raw']['03 Supuestos'];rows=[]
        for i,r in enumerate(raw,1):
            if len(r)>7 and r[2] and r[4] and r[7] and r[2] not in ['Supuesto','Variable']:
                rows.append({'Supuesto':r[2],'Valor publicado':r[4],'Unidad':r[5],'Criterio':r[7],'Fuente':f'03 Supuestos!E{i}'})
        st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True,height=400)


def opex80(model,year):
    section('08 / GASTOS OPERATIVOS','Estructura, entregas y flota · '+year)
    opex=model['opex'].loc[lambda f:f['Año'].eq(year)].copy()
    row=model['annual'].loc[lambda f:f['Año'].eq(year)].iloc[0]
    kpis([('OPEX total',money(row['opex']),year),('Estructura operativa',money(row['opex_common']),'Dotación, administración y operación de planta'),
        ('Entrega y flota',money(row['opex_80']),'Costos asociados a equipos y conectividad'),('Cobertura del detalle',str(opex['USD'].notna().sum())+' / '+str(len(opex)),'Partidas y ajustes con importe publicado')])
    left,right=st.columns(2,gap='large')
    with left:
        agg=opex.groupby('Área')['USD'].agg(complete_sum).sort_values()
        fig=go.Figure(go.Bar(y=agg.index,x=displayed(agg)/1e6,orientation='h',marker_color=NAVY,customdata=[money(v) for v in agg],hovertemplate='%{y}<br>%{customdata}<extra></extra>'))
        fig.update_layout(title='Distribución de gastos por área');fig.update_xaxes(title_text='MM '+currency_code());plot(fig,'80_opex_area',440)
    with right:annual_bars(model['annual'].loc[lambda f:f['Año modelo'].gt(0)],[('opex_common','Estructura',NAVY),('opex_80','Entrega y flota',TEAL)],'80_opex_trend','Evolución del presupuesto operativo')
    statuses=sorted(opex['Estado'].dropna().unique());key=PREFIX+'_opex_status'
    if key in st.session_state:st.session_state[key]=[v for v in st.session_state[key] if v in statuses]
    selected=st.multiselect('Estado del presupuesto OPEX',statuses,key=key,placeholder='Todos los estados publicados')
    if selected:opex=opex[opex['Estado'].isin(selected)]
    financial_table(opex[['ID','Área','Concepto','Destino','USD','Estado','Fuente']].rename(columns={'USD':'Presupuesto'}),['Presupuesto'])
    st.caption('08 Gastos operativos: detalle CLP convertido con el tipo de cambio interno del modelo, más ajustes USD una sola vez. Los filtros afectan el detalle; los KPI y gráficos conservan el presupuesto completo del año.')


def assets80(model):
    section('09 / ACTIVOS Y DESARROLLO','Recursos de arranque e industrialización')
    s=model['scalars'];assets=model['assets'].copy()
    kpis([('Activos aportados en especie',money(s['assets_in_kind']),'Aporte patrimonial sin entrada de efectivo'),('Desarrollo y preoperacionales',money(s['preop']),'Incluye el presupuesto de hitos'),
        ('Stock inicial de producción',money(s['production_stock']),'Incluido en capital de trabajo'),('Repuestos de planta',money(s['plant_spares']),'Reserva inicial con reposición OPEX')])
    left,right=st.columns(2,gap='large')
    with left:
        values=[s['assets_in_kind'],s['preop'],s['production_stock'],s['plant_spares']]
        fig=go.Figure(go.Pie(labels=['Activos en especie','Preoperacionales','Stock de producción','Repuestos de planta'],values=values,hole=.64,
            marker=dict(colors=[NAVY,GOLD,TEAL,ORANGE]),customdata=[money(v) for v in values],textinfo='percent',hovertemplate='%{label}<br>%{customdata}<extra></extra>'))
        fig.update_layout(title='Composición de la inversión económica inicial');plot(fig,'80_assets_investment',390)
    with right:annual_bars(model['annual'],[('assets_book','Valor contable',NAVY),('asset_da','Depreciación',GOLD)],'80_assets_book','Activos y depreciación · diez años')
    include=st.checkbox('Incluir referencias históricas de capital de trabajo',key=PREFIX+'_include_wc')
    if not include:assets=assets.loc[lambda f:~f['Naturaleza'].eq('Capital de trabajo')]
    financial_table(assets,['Costo aplicado USD'])
    st.caption('Registro CAP e INV de 09, columna P: costo aplicado. CT histórico es referencia y no se suma de nuevo. Los activos en especie no consumen caja de FW.')
    section('09 / DESARROLLO INDUSTRIAL','Presupuesto por hito y responsable')
    agg=model['development'].groupby('Fase',sort=False)['USD base'].agg(complete_sum)
    fig=go.Figure(go.Bar(y=agg.index,x=displayed(agg)/1e6,orientation='h',marker_color=NAVY,text=[money(v,True) for v in agg],textposition='outside',cliponaxis=False))
    fig.update_layout(title='Distribución del desarrollo · presupuesto base');fig.update_xaxes(title_text='MM '+currency_code(),range=[0,displayed(agg).max()/1e6*1.4]);plot(fig,'80_development')
    financial_table(model['development'],['USD base'])
    context('Alcance del desarrollo','Distribución base provisional de 09 Activos y arranque. Los hitos ya están incluidos en CAP-001 y CAP-002; no se suman nuevamente al gasto preoperacional aplicado. Permisos, puesta en marcha y ajustes se conservan en el registro de origen.')


def audit80(model):
    section('01 / TRAZABILIDAD','Conciliaciones y condiciones del caso de 80 kW')
    checks=model['checks'];native=model['native_checks']
    kpis([('Controles propios conciliados',f'{checks["Estado"].eq("Conciliado").sum()} / {len(checks)}','Contraste entre CSV y cálculos independientes'),
        ('Controles de la fuente',str(len(native)),'Incluye lógica, presupuestos y financiamiento'),
        ('Condiciones por resolver',str(len(model['pending'])),'Estados publicados; no se dan por validados'),
        ('Tipo de cambio del modelo',count(model['scalars']['model_fx'])+' CLP/USD','Diferente del tipo de cambio de presentación')])
    st.dataframe(checks,hide_index=True,use_container_width=True)
    st.caption('Las diferencias y tolerancias conservan su unidad de control. El CSV redondea valores; los controles publicados usan precisión interna. Una conciliación no valida un contrato ni un presupuesto.')
    st.markdown('##### Controles publicados · hoja 10')
    st.dataframe(native,hide_index=True,use_container_width=True,height=420)
    st.markdown('##### Localización de indicadores')
    st.dataframe(model['provenance'],hide_index=True,use_container_width=True,height=350)
    st.markdown('##### Revisión íntegra de las once pestañas de origen')
    sheet=st.selectbox('Pestaña de la fuente',list(SHEETS),key=PREFIX+'_source_sheet')
    rows=model['raw'][sheet];width=max(map(len,rows))
    frame=pd.DataFrame([r+['']*(width-len(r)) for r in rows],columns=[column_name(i+1) for i in range(width)])
    frame.insert(0,'Fila',range(1,len(frame)+1))
    st.dataframe(frame,hide_index=True,use_container_width=True,height=430)
    st.link_button('Abrir pestaña en la fuente · 80 kW',SOURCE+'html#gid='+SHEETS[sheet])
    st.download_button('Descargar pestaña original · CSV',frame.to_csv(index=False).encode('utf-8-sig'),file_name=sheet.replace(' ','_')+'_80kW.csv',mime='text/csv',key=PREFIX+'_raw_csv',on_click='ignore')
    if not model['formula_errors'].empty:st.dataframe(model['formula_errors'],hide_index=True,use_container_width=True)


def render_valuation80(refresh_nonce=0):
    with st.container(key=PREFIX):
        css=Path(__file__).with_name('assets').joinpath('valuation.css').read_text().replace('.st-key-option4_valuation', '.st-key-'+PREFIX)
        st.html('<style>'+css+'</style>')
        try:
            with st.spinner('Leyendo el modelo exclusivo de 80 kW y sus once pestañas…'):model=load_valuation80(refresh_nonce)
        except Exception as exc:
            st.error(f'No se pudo cargar la fuente de 80 kW: {exc}')
            st.link_button('Abrir modelo de 80 kW',SOURCE+'html')
            return
        s=model['scalars']
        st.html('<header class="valuation-hero"><div><span>SUB BLOQUE 5 · TURBINA DE 80 kW</span><h2>Caso de Inversión · 80 kW</h2><p>Modelo exclusivo: valorización, fabricación, desarrollo industrial, operación y caja.</p></div><div class="valuation-badges"><b>'+html.escape(model['scenario'])+'</b><b>Producción '+html.escape(model['production'])+'</b><b>Aporte: '+html.escape(model['status'])+'</b></div></header>')
        with st.expander('Fuente, moneda y año de detalle'):
            st.caption(f'Fecha base DCF: {s["valuation_date"]} · Consulta: {model["fetched_at"]} · Hora de Santiago · Proyección {int(s["first_year"])}–{int(s["first_year"])+9}')
            st.caption(f'Fuente en USD nominales · Visualización {currency_code()} · TC de presentación {exchange_rate():,.2f} CLP/USD · TC interno del modelo {s["model_fx"]:,.2f} CLP/USD. La conversión se aplica una sola vez.')
            st.caption('Consulta independiente de once pestañas, incluida 10 Controles. Actualización cada 60 segundos y mediante Actualizar todo; las simulaciones no modifican la fuente.')
            st.link_button('Abrir documento exclusivo de 80 kW',SOURCE+'html')
            options=model['annual'].loc[lambda f:f['Año modelo'].gt(0),'Año'].tolist()
            key=PREFIX+'_year'
            if key in st.session_state and st.session_state[key] not in options:st.session_state[key]=options[0]
            year=st.selectbox('Año operativo para los detalles',options,key=key)
        issues=model['checks'].loc[lambda f:~f['Estado'].eq('Conciliado')]
        if not issues.empty:st.warning(f'{len(issues)} conciliaciones requieren revisión; consulta Controles y fuentes.')
        if not model['formula_errors'].empty:st.error('La fuente contiene errores de fórmula; revisa su ubicación en trazabilidad.')
        tabs=st.tabs(MAIN_TABS)
        with tabs[0]:overview80(model)
        with tabs[1]:inputs80(model)
        with tabs[2]:investment_details(model)
        with tabs[3]:
            st.caption('04 Resultados y flujo · 05 Balance y cobros · 06 Caja mensual')
            projection80(model)
            operating(model,year)
            cash_view(model,year,key_prefix=PREFIX)
        with tabs[4]:
            st.caption('07 Ventas y producción · economía por equipo, componentes y escala de fabricación')
            unit_panel80(model)
        with tabs[5]:opex80(model,year)
        with tabs[6]:assets80(model)
        with tabs[7]:audit80(model)
