"""Interactive executive financial views, isolated from the published source model."""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from display_currency import currency_code
from valuation_lcoe import lcoe_panel
from valuation_finance import financial_diagnostics,unit_economics,mix_analysis,reprice_dcf,projection_diagnostics,divide,complete_sum

NAVY,TEAL,GOLD,ORANGE='#315E7D','#3B8F96','#9DAFC0','#B36A52'


def multiple(value):return 'Sin cálculo' if pd.isna(value) else f'{value:.2f}x'.replace('.',',')
def years(value):return 'No recuperado / sin cálculo' if pd.isna(value) else f'{value:.2f} años'.replace('.',',')


def diagnostics_panel(model):
    from valuation_view import kpis,pct,context,section
    d=financial_diagnostics(model)
    kpis([('DCF / ventas · año 1',multiple(d['DCF/Ventas año 1']),'Múltiplo del modelo, no un comparable de mercado'),
        ('DCF / EBITDA · año 1',multiple(d['DCF/EBITDA año 1']),'Se calcula solo con EBITDA positivo'),
        ('Índice de rentabilidad económico',multiple(d['Índice de rentabilidad económico']),'VP de entradas / VP de salidas económicas · sin terminal'),
        ('Payback económico descontado',years(d['Payback económico descontado']),'Interpolación anual; incluye activos en especie')],secondary=True)
    context('Cómo leer los indicadores',f'Precio previo negociado / DCF: {pct(d["Precio previo / DCF"])}. Spread entre tasa y crecimiento terminal: {d["Spread tasa − crecimiento"]*100:.1f} puntos porcentuales. Payback económico simple: {years(d["Payback económico simple"])}. El índice de rentabilidad compara entradas y salidas descontadas; no es el retorno del inversionista ni incorpora la venta secundaria.')


def diagnostics_definitions():
    with st.expander('Definiciones de rentabilidad y alcance'):
        st.markdown('**DCF/ventas y DCF/EBITDA:** cocientes del valor publicado entre ventas y EBITDA del primer año operativo. No se denominan EV/múltiplos de mercado porque aquí se utiliza el DCF de caja del modelo. '
            '**Índice económico:** valor presente de flujos económicos positivos dividido por el valor presente absoluto de los negativos, usando la tasa publicada y sin terminal. '
            '**Payback económico:** momento de recuperación del flujo económico acumulado, incluyendo el valor de los activos aportados. La interpolación supone reparto uniforme dentro del año y no equivale al calendario mensual. '
            'Los cuatro KPI superiores siguen siendo los resultados publicados; estos indicadores son cálculos analíticos derivados.')


def unit_panel(model):
    from valuation_view import kpis,money,pct,count,plot,displayed,financial_table,context,section
    section('02 / ECONOMÍA UNITARIA','Margen, contribución y escala')
    st.caption('Compara el precio con fabricación, OPEX específico y contribución. La tabla conserva el detalle por equipo; el gráfico permite normalizar por kW.')
    options=model['annual'].loc[model['annual']['Año modelo'].gt(0),'Año'].tolist()
    key='option4_valuation_unit_year'
    if key not in st.session_state or st.session_state[key] not in options:
        st.session_state[key]=st.session_state.get('option4_valuation_year',options[0]) if st.session_state.get('option4_valuation_year',options[0]) in options else options[0]
    c1,c2,c3=st.columns([1,1.5,1])
    with c1:year=st.selectbox('Año de economía unitaria',options,key=key)
    with c2:
        if 'option4_valuation_unit_products' not in st.session_state:st.session_state['option4_valuation_unit_products']=['10 kW','80 kW']
        products=st.multiselect('Productos del comparativo',['10 kW','80 kW'],key='option4_valuation_unit_products',format_func=lambda v:'Turbina de '+v)
    with c3:basis=st.radio('Base de comparación',['Por equipo','Por kW'],horizontal=True,key='option4_valuation_unit_basis')
    data,gap=unit_economics(model,year)
    row=model['annual'].loc[model['annual']['Año'].eq(year)].iloc[0]
    if pd.isna(gap) or abs(gap)>5:
        st.warning('Los costos por producto no concilian con fabricación consolidada. Revisa el alcance y los adicionales de terceros en la fuente antes de interpretar la contribución.')
    selected=data[data['Turbina'].isin(products)].copy()
    if selected.empty:st.info('Selecciona al menos una turbina para ver su economía unitaria.')
    else:
        sales=complete_sum(selected['Ventas']);contribution=complete_sum(selected['Contribución total'])
        kpis([('Ventas de productos seleccionados',money(sales),year),('Contribución antes de OPEX común',money(contribution),'No equivale al EBITDA de la empresa'),('Margen de contribución',pct(divide(contribution,sales)),'Contribución / ventas de la selección'),('Potencia entregada',count(complete_sum(selected['kW entregados']))+' kW',count(complete_sum(selected['Entregas']))+' equipos publicados')])
        divisor=selected['Potencia kW'] if basis=='Por kW' else 1
        fig=go.Figure()
        for field,label,color in [('Fabricación / equipo','Fabricación',NAVY),('OPEX específico / equipo','OPEX específico',GOLD),('Contribución / equipo','Contribución',TEAL)]:
            values=selected[field]/divisor
            fig.add_trace(go.Bar(y=selected['Turbina'],x=displayed(values),orientation='h',width=.42,name=label,marker_color=[ORANGE if v<0 else color for v in values],customdata=[money(v) for v in values],hovertemplate='%{y}<br>%{customdata}<extra>%{fullData.name}</extra>'))
        prices=selected['Precio / equipo']/divisor
        fig.add_trace(go.Scatter(y=selected['Turbina'],x=displayed(prices),name='Precio promedio',mode='markers+text',text=[money(v,True) for v in prices],textposition='top center',textfont=dict(size=12,color=NAVY),marker=dict(symbol='diamond',size=9,color=NAVY,line=dict(color='white',width=1)),customdata=[money(v) for v in prices],hovertemplate='%{y}<br>%{customdata}<extra>Precio</extra>'))
        fig.update_layout(title='Del precio a la contribución · '+year,barmode='relative');fig.update_xaxes(title_text=currency_code()+('/kW' if basis=='Por kW' else '/equipo'),rangemode='tozero');fig.update_yaxes(autorange='reversed',showgrid=False);plot(fig,'summary_unit_chart',280)
        matrix=[]
        metrics=[('Equipos entregados','Entregas','equipos','count'),('Precio de venta promedio','Precio / equipo',currency_code()+'/equipo','money'),('Fabricación media','Fabricación / equipo',currency_code()+'/equipo','money'),('Margen bruto por equipo','Margen bruto / equipo',currency_code()+'/equipo','money'),('Margen bruto','Margen bruto %','%','percent'),('OPEX específico por equipo','OPEX específico / equipo',currency_code()+'/equipo','money'),('Contribución antes de OPEX común','Contribución / equipo',currency_code()+'/equipo','money'),('Margen de contribución','Margen contribución %','%','percent')]
        for label,field,unit,kind in metrics:
            record={'Indicador':label,'Unidad':unit}
            for _,product in selected.iterrows():
                value=product[field];record['Turbina de '+product['Turbina']]=money(value) if kind=='money' else pct(value) if kind=='percent' else count(value)
            matrix.append(record)
        table=pd.DataFrame(matrix);display_columns=['Indicador',*[c for c in table if c.startswith('Turbina')],'Unidad']
        st.dataframe(table[display_columns],hide_index=True,use_container_width=True,row_height=36,height=330,column_config={'Indicador':st.column_config.TextColumn(width=310),'Unidad':st.column_config.TextColumn(width=130)})
        with st.expander('Detalle numérico y conciliación de productos'):
            financial_table(selected.drop(columns='Potencia kW'),['Ventas','Fabricación total','OPEX específico total','Contribución total','Precio / equipo','Fabricación / equipo','Margen bruto / equipo','OPEX específico / equipo','Contribución / equipo'],['Margen bruto %','Margen contribución %'])
            st.caption(('Contribución de ambos productos menos OPEX común frente al EBITDA publicado: '+money(complete_sum(data['Contribución total'])-row['opex_common'])+' frente a '+money(row['ebitda'])+'. Una diferencia material requiere revisar partidas no asignadas o adicionales de terceros.').replace('$', r'\$'))
    lcoe_panel(model,year,selected)
    section('04 / ESCALA OPERATIVA','Equilibrio y sensibilidad del mix')
    st.caption('Aproximación de EBITDA a precios, fabricación y OPEX específico unitarios constantes del año elegido. El OPEX común permanece fijo. Este laboratorio usa ambos productos y es independiente del filtro del comparativo anterior.')
    total_units=complete_sum(data['Entregas']);share=divide(float(data.loc[data['Potencia kW'].eq(80),'Entregas'].iloc[0]),total_units)
    if st.session_state.get('option4_valuation_mix_year') != year:
        st.session_state['option4_valuation_mix_volume']=float(total_units) if pd.notna(total_units) else 0.
        st.session_state['option4_valuation_mix_share']=float(round(100*share,1)) if pd.notna(share) else 50.
        st.session_state['option4_valuation_mix_year']=year
    mix_mode=st.radio('Composición del mix',['Mix del año publicado','Mix personalizado'],horizontal=True,key='option4_valuation_mix_mode')
    custom_share=st.slider('Participación de 80 kW en las entregas (%)',0.,100.,step=.1,key='option4_valuation_mix_share',disabled=mix_mode!='Mix personalizado')/100
    if mix_mode=='Mix personalizado':share=custom_share
    volume=st.number_input('Entregas totales del laboratorio',min_value=0.,value=None,step=1.,key='option4_valuation_mix_volume')
    if volume is None:st.info('Ingresa el volumen del laboratorio para calcular el equilibrio.');return
    if pd.isna(share):st.info('El año no tiene entregas suficientes para construir el mix publicado.');return
    sim=mix_analysis(data,share,volume,row['opex_common'],row['capacity'])
    kpis([('EBITDA aproximado del mix',money(sim['ebitda']),'Contribución simulada − OPEX común publicado'),('Equilibrio operativo',('Sin cálculo' if pd.isna(sim['break_even_units']) else f'{sim["break_even_units"]:,.1f}'.replace(',','X').replace('.',',').replace('X','.')+' equipos eq.'),'OPEX común / contribución media positiva'),('Margen de seguridad',pct(sim['safety_margin']),'Volumen por encima o debajo del equilibrio'),('Apalancamiento operativo',multiple(sim['operating_leverage']),'Contribución / EBITDA positivo del laboratorio')])
    context('Alcance de la aproximación',f'Mix 80 kW: {pct(share)} · ventas de equilibrio: {money(sim["break_even_sales"])}. Con {count(volume)} equipos equivalentes, el excedente respecto de la capacidad propia es {count(sim["external"])}. No se recalculan economías de escala, impuestos, capital de trabajo ni disponibilidad de terceros; el equilibrio es operativo, antes de depreciación, financiamiento y CAPEX.')


def projection_panel(model):
    from valuation_view import kpis,money,pct,count,plot,displayed,context,section
    section('02 / PROYECCIÓN','Operación, resultados y caja')
    a=model['annual'];operating=a[a['Año modelo'].gt(0)];options=operating['Año'].tolist()
    key='option4_valuation_summary_range'
    if key in st.session_state and any(v not in options for v in st.session_state[key]):del st.session_state[key]
    first,last=st.select_slider('Período del resumen',options,value=(options[0],options[min(4,len(options)-1)]),key=key)
    frame=operating[operating['Año'].between(first,last)].copy();d=projection_diagnostics(frame)
    kpis([('Ventas acumuladas',money(d['sales']),first+'–'+last),('Margen EBITDA ponderado',pct(d['margin']),'Σ EBITDA / Σ ventas del período'),('Flujo libre acumulado',money(d['fcff']),'Σ FCFF; no suma saldos de caja'),('Caja libre al cierre',money(d['cash_close']),'Saldo del último año seleccionado')])
    metric=st.radio('Vista de la proyección',['Ventas y EBITDA','Flujo libre y caja','Entregas y capacidad'],horizontal=True,key='option4_valuation_summary_metric')
    fig=go.Figure()
    if metric=='Ventas y EBITDA':
        fig=make_subplots(rows=1,cols=2,subplot_titles=('Ingresos por ventas','EBITDA operativo'),horizontal_spacing=.13)
        for col,field,label,color in [(1,'sales','Ventas',NAVY),(2,'ebitda','EBITDA',TEAL)]:
            fig.add_trace(go.Bar(x=frame['Año'],y=displayed(frame[field])/1e6,name=label,marker_color=color,text=[money(v,True) for v in frame[field]],textposition='outside',cliponaxis=False,textfont=dict(size=11),customdata=[money(v) for v in frame[field]],hovertemplate='%{x}<br>%{customdata}<extra>%{fullData.name}</extra>'),row=1,col=col)
        fig.update_yaxes(title_text='MM '+currency_code(),rangemode='tozero');fig.update_layout(showlegend=False)
        fig.update_annotations(font=dict(size=13,color=NAVY))
    elif metric=='Flujo libre y caja':
        fig.add_trace(go.Bar(x=frame['Año'],y=displayed(frame['fcff'])/1e6,name='Flujo libre anual',marker_color=TEAL))
        fig.add_trace(go.Scatter(x=frame['Año'],y=displayed(frame['cash_free'])/1e6,name='Caja libre al cierre',mode='lines+markers',line=dict(color=NAVY,width=3)))
        fig.update_yaxes(title_text='Millones de '+currency_code())
    else:
        for field,label,color in [('units_80','Entregas 80 kW',GOLD),('units_10','Entregas 10 kW',NAVY)]:fig.add_trace(go.Bar(x=frame['Año'],y=frame[field],name=label,marker_color=color))
        fig.add_trace(go.Scatter(x=frame['Año'],y=frame['capacity'],name='Capacidad propia',mode='lines+markers',line=dict(color=TEAL,dash='dash')))
        fig.update_layout(barmode='stack');fig.update_yaxes(title_text='Equipos por año')
    fig.update_layout(title=metric+' · '+first+'–'+last);fig.update_xaxes(type='category',tickmode='array',tickvals=frame['Año']);plot(fig,'summary_projection',330)
    context('Ratios del período',f'Crecimiento compuesto de ventas (CAGR): {pct(d["cagr"])}. Conversión FCFF/EBITDA acumulado: {pct(d["cash_conversion"])}. Entregas que requieren ampliar o externalizar: {pct(d["external_share"])}. La conversión de caja incorpora capital de trabajo, anticipos, IVA y CAPEX; no representa margen de utilidad.')
    metrics=[('Demanda 80 kW','demand_80','count'),('Demanda 10 kW','demand_10','count'),('Capacidad propia','capacity','count'),('Entregas 80 kW','units_80','count'),('Entregas 10 kW','units_10','count'),('Equipos a ampliar / externalizar','external','count'),('Demanda sin atender','_unserved','count'),('Sobrecosto de terceros','_external_cost','money'),('Ventas','sales','money'),('EBITDA','ebitda','money'),('Margen EBITDA','ebitda_margin','pct'),('Flujo libre','fcff','money'),('CAPEX pagado por FW','capex','money'),('Caja libre al cierre','cash_free','money')]
    frame['_unserved']=(frame['demand_80']+frame['demand_10']-frame['units_total']).clip(lower=0)
    frame['_external_cost']=frame['external_cost_80']+frame['external_cost_10']
    matrix=[]
    for label,field,kind in metrics:
        record={'Indicador':label,'Unidad':'equipos' if kind=='count' else '%' if kind=='pct' else currency_code()}
        for _,row in frame.iterrows():record[row['Año']]=count(row[field]) if kind=='count' else pct(row[field]) if kind=='pct' else money(row[field])
        matrix.append(record)
    st.dataframe(pd.DataFrame(matrix),hide_index=True,use_container_width=True,row_height=34,height=535,column_config={'Indicador':st.column_config.TextColumn(width=270),'Unidad':st.column_config.TextColumn(width=85)})
    st.caption('La demanda no atendida se deriva de demanda total menos entregas, sin valores negativos. Los sobrecostos externos corresponden a las filas específicas de 07. Los saldos de caja son cierres, no flujos acumulables.')


def dcf_lab(model,key_prefix='option4_valuation'):
    from valuation_view import kpis,money,pct,plot,displayed,financial_table,context,section
    section('02 / ESCENARIOS','Escenarios de tasa y valor terminal')
    st.caption('Simulación analítica local. Conserva los FCFF publicados de Año 0 a Año 10 y el flujo normalizado del Año 11. La tasa cambia el descuento; g cambia únicamente el denominador de Gordon. No recalcula ventas, impuestos, capacidad ni el crecimiento de los flujos operativos.')
    s=model['scalars']
    for key,value in [(key_prefix+'_lab_rate',float(s['rate']*100)),(key_prefix+'_lab_growth',float(s['growth']*100)),(key_prefix+'_lab_terminal',True)]:
        if key not in st.session_state:st.session_state[key]=value
    left,middle,right=st.columns(3)
    with left:rate_input=st.number_input('Tasa de descuento del laboratorio (%)',min_value=.1,max_value=1000.,value=None,step=.5,key=key_prefix+'_lab_rate')
    with right:terminal=st.checkbox('Incluir valor terminal',key=key_prefix+'_lab_terminal')
    with middle:growth_input=st.number_input('Crecimiento perpetuo del laboratorio (%)',min_value=-10.,max_value=100.,value=None,step=.1,key=key_prefix+'_lab_growth',disabled=not terminal)
    st.button('Restaurar tasa y crecimiento publicados',key=key_prefix+'_lab_restore',on_click=_restore_lab,args=(s['rate']*100,s['growth']*100,key_prefix))
    if rate_input is None or (terminal and growth_input is None):
        st.info('Completa la tasa y el crecimiento para calcular la sensibilidad.');return
    rate=rate_input/100;growth=(growth_input if growth_input is not None else 0)/100
    try:result=reprice_dcf(model,rate,growth,terminal);base=reprice_dcf(model,s['rate'],s['growth'],True)
    except ValueError as exc:st.warning(str(exc));return
    delta=result['dcf']-base['dcf']
    kpis([('DCF del laboratorio',money(result['dcf']),'Flujos de caja publicados · no es un nuevo caso de negocio'),('Variación vs base reconstruida',pct(divide(delta,base['dcf'])),money(delta)),('VP del valor terminal',money(result['pv_terminal']),pct(result['terminal_weight'])+' del DCF simulado'),('VAN económico sin terminal',money(result['npv_economic']),'Tasa del laboratorio · mismos flujos económicos')])
    st.caption(('Base publicada: '+money(s['dcf'])+' · Base reconstruida con CSV: '+money(base['dcf'])+'. La diferencia puede reflejar redondeos; las variaciones se comparan con la misma base reconstruida.').replace('$', r'\$'))
    rates=sorted(set(max(.001,rate+offset) for offset in [-.04,-.02,0,.02,.04]));growths=[growth-.01,growth,growth+.01]
    if terminal:
        values=[];labels=[]
        for r in rates:
            row=[];text=[]
            for g in growths:
                try:value=reprice_dcf(model,r,g,True)['dcf']
                except ValueError:value=float('nan')
                row.append(displayed(value)/1e6);text.append(money(value,True) if pd.notna(value) else 'r ≤ g')
            values.append(row);labels.append(text)
        fig=go.Figure(go.Heatmap(x=growths,y=rates,z=values,text=labels,texttemplate='%{text}',colorscale=[[0,'#EDF3F6'],[.5,'#7DBBB3'],[1,NAVY]],colorbar=dict(title='MM '+currency_code()),hovertemplate='g %{x:.1%}<br>r %{y:.1%}<br>%{text}<extra></extra>'))
        fig.update_xaxes(title_text='g · FCF normalizado de Año 11 fijo',tickvals=growths,ticktext=[pct(v) for v in growths]);fig.update_yaxes(title_text='Tasa de descuento r',tickvals=rates,ticktext=[pct(v) for v in rates],autorange='reversed');fig.update_traces(xgap=5,ygap=5,textfont=dict(size=13));plot(fig,'summary_lab_heatmap',330)
    else:
        fig=go.Figure(go.Scatter(x=rates,y=[displayed(reprice_dcf(model,r,growth,False)['dcf'])/1e6 for r in rates],mode='lines+markers',line=dict(color=NAVY,width=3)))
        fig.update_xaxes(title_text='Tasa de descuento',tickformat='.0%');fig.update_yaxes(title_text='VAN de caja sin terminal · MM '+currency_code());plot(fig,'summary_lab_no_terminal',300)
    with st.expander('Detalle de descuento y fórmulas del laboratorio'):
        financial_table(result['periods'],['Flujo publicado USD','VP explícito USD'])
        st.markdown('**VAN explícito:** Σ FCFFₜ / (1+r)ᵗ, incluyendo Año 0. **Terminal:** FCFF normalizado publicado de Año 11 / (r−g). **DCF:** VAN explícito + terminal / (1+r)¹⁰. '
            '**VAN económico:** descuenta los flujos económicos publicados, que incorporan los activos en especie al arranque. El aporte nuevo y la compra secundaria se mantienen fuera de la valoración operativa. Las celdas r ≤ g no se valoran con Gordon.')
    context('Estado de los datos',f'La simulación no modifica la planilla ni los KPI publicados. Se mantienen los supuestos y condiciones pendientes del caso {model["scenario"]}; el estado del aporte sigue siendo {model["status"]}.')


def _restore_lab(rate,growth,key_prefix='option4_valuation'):
    st.session_state[key_prefix+'_lab_rate']=rate
    st.session_state[key_prefix+'_lab_growth']=growth
    st.session_state[key_prefix+'_lab_terminal']=True
