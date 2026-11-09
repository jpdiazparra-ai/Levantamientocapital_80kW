"""Interactive owner-side LCOE assumptions, independent of the corporate DCF."""
import math
import hashlib
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from display_currency import currency_code,exchange_rate
from lcoe_finance import levelized_cost,lcoe_profiles

SOURCE='https://www.nlr.gov/pv/lcoe-calculator/documentation'
FIELDS=['CAPEX equipo','Otros CAPEX instalados','O&M fijo anual','O&M variable / kWh']


def lcoe_text(value,per_mwh=False):
    if pd.isna(value):return 'Sin cálculo'
    shown=value*(exchange_rate() if currency_code()=='CLP' else 1)*(1000 if per_mwh else 1)
    digits=2 if per_mwh or currency_code()=='CLP' else 4
    return ('US$ ' if currency_code()=='USD' else '$')+f'{shown:,.{digits}f}'.replace(',','X').replace('.',',').replace('X','.')


def _reset_inputs(context,key_prefix='option4_lcoe'):
    overrides=dict(st.session_state.get(key_prefix+'_overrides',{}));overrides.pop(context,None)
    st.session_state[key_prefix+'_overrides']=overrides
    # Editor keys change by selection/currency; clear only the current source context.
    prefix=key_prefix+'_editor_'+hashlib.sha1(context.encode()).hexdigest()[:10]
    for key in list(st.session_state):
        if key.startswith(prefix):del st.session_state[key]


def _float(value):
    try:return float(value)
    except (TypeError,ValueError):return float('nan')


def lcoe_panel(model,year,products,key_prefix='option4_lcoe'):
    from valuation_view import section,kpis,money,pct,plot,displayed,financial_table,context
    section('03 / COSTO DE ENERGÍA','LCOE · costo nivelado de generación')
    st.caption('Escenario del propietario de una turbina instalada. Usa los productos y el año del comparativo superior; no modifica el DCF del negocio ni el equilibrio del mix.')
    if products.empty:st.info('Selecciona una turbina para construir su escenario LCOE.');return
    a,b,c,d=st.columns([1.4,1,1,1],vertical_alignment='bottom')
    with a:factor=st.slider('Factor de planta neto (%)',0.,100.,value=30.,step=.5,key=key_prefix+'_factor',help='Energía neta / (potencia nominal × 8760). Incluye disponibilidad, pérdidas y restricciones; no se descuentan otra vez.')/100
    with b:life=st.number_input('Vida útil LCOE (años)',min_value=1,max_value=60,value=20,step=1,key=key_prefix+'_life')
    with c:rate=st.number_input('Tasa real LCOE (%)',min_value=0.,max_value=100.,value=8.,step=.5,key=key_prefix+'_rate',help='Supuesto independiente de la tasa del DCF corporativo. Costos en moneda constante del año de referencia.')
    with d:om_percent=st.number_input('Supuesto O&M (% equipo/año)',min_value=0.,max_value=100.,value=2.,step=.25,key=key_prefix+'_om_percent',help='Hipótesis ilustrativa para iniciar la tabla. La celda O&M anual se puede sustituir por una cotización propia; una edición manual tiene prioridad. El porcentaje usa la referencia de la fuente, no los CAPEX modificados en la tabla.')
    if any(value is None for value in [life,rate,om_percent]):
        st.info('Completa vida útil, tasa real y supuesto O&M para calcular el escenario.');return
    basis=st.radio('Referencia inicial del CAPEX del equipo',['Precio de venta','Costo de fabricación'],horizontal=True,key=key_prefix+'_basis')
    st.caption('Inicio ilustrativo: factor neto 30 %, vida 20 años, tasa real 8 % y O&M fijo 2 % del precio de referencia del equipo. No son especificaciones certificadas ni cotizaciones de mantenimiento. El precio de venta es una referencia de compra; fabricación es una aproximación interna y no una oferta al cliente.')
    source_field='Precio / equipo' if basis=='Precio de venta' else 'Fabricación / equipo'
    context_key=str(year)+'|'+basis
    all_overrides=dict(st.session_state.get(key_prefix+'_overrides',{}));overrides=all_overrides.get(context_key,{})
    factor_money=exchange_rate() if currency_code()=='CLP' else 1.
    records=[]
    for _,product in products.iterrows():
        cap=int(product['Potencia kW']);custom=overrides.get(str(cap),{})
        equipment=_float(custom.get('CAPEX equipo',product[source_field]));extra=_float(custom.get('Otros CAPEX instalados',0.))
        fixed=_float(custom.get('O&M fijo anual',_float(product[source_field])*om_percent/100))
        records.append({'Turbina':str(cap)+' kW','CAPEX equipo':equipment*factor_money,'Otros CAPEX instalados':extra*factor_money,'O&M fijo anual':fixed*factor_money,'O&M variable / kWh':_float(custom.get('O&M variable / kWh',0.))*factor_money})
    frame=pd.DataFrame(records)
    st.markdown('##### Tabla de supuestos editables · '+currency_code())
    st.caption('Otros CAPEX: fundación, montaje, transporte, conexión y permisos que no estén incluidos en el equipo. O&M fijo: costo anual del sitio; variable: costo por kWh neto. Los valores iniciales de cero son supuestos pendientes de completar.')
    prefix=key_prefix+'_editor_'+hashlib.sha1(context_key.encode()).hexdigest()[:10]
    editor_key=prefix+'_'+currency_code()+'_'+str(exchange_rate())+'_'+'_'.join(frame['Turbina'])
    config={'Turbina':st.column_config.TextColumn('Turbina',width=110,pinned=True)}
    labels={'CAPEX equipo':'Equipo · '+currency_code(),'Otros CAPEX instalados':'Instalación / otros CAPEX · '+currency_code(),'O&M fijo anual':'O&M fijo anual · '+currency_code(),'O&M variable / kWh':'O&M variable · '+currency_code()+'/kWh'}
    help_text={'CAPEX equipo':'Inversión en el equipo. Referencia de compra o fabricación; editable sin cambiar la fuente.','Otros CAPEX instalados':'Fundación, montaje, transporte y conexión que no estén incluidos en el equipo.','O&M fijo anual':'Operación y mantenimiento anual del propietario, independiente del OPEX corporativo.','O&M variable / kWh':'Costo de operación por kWh neto generado, con cuatro decimales de precisión.'}
    for field in FIELDS:
        variable=field=='O&M variable / kWh'
        config[field]=st.column_config.NumberColumn(labels[field],min_value=0.,step=.0001 if variable else .01,format='localized',width=260 if field=='Otros CAPEX instalados' else 220,help=help_text[field])
    edited=st.data_editor(frame,hide_index=True,use_container_width=True,num_rows='fixed',disabled=['Turbina'],column_config=config,key=editor_key,row_height=52)
    # Store only actual user edits, in native USD. A refreshed source still updates unedited defaults.
    for i,row in edited.iterrows():
        cap=str(int(products.iloc[i]['Potencia kW']))
        for field in FIELDS:
            value,original=_float(row[field]),_float(frame.loc[i,field])
            if not ((math.isnan(value) and math.isnan(original)) or math.isclose(value,original,rel_tol=1e-10,abs_tol=1e-10)):
                overrides.setdefault(cap,{})[field]=value/factor_money
    all_overrides[context_key]=overrides;st.session_state[key_prefix+'_overrides']=all_overrides
    st.button('Restaurar costos de referencia LCOE',key=key_prefix+'_restore',on_click=_reset_inputs,args=(context_key,key_prefix))
    with st.expander('Supuestos avanzados · degradación, O&M y reposición'):
        a,b,c,d=st.columns(4,vertical_alignment='bottom')
        with a:degradation=st.number_input('Degradación energética anual (%)',min_value=0.,max_value=20.,value=0.,step=.1,key=key_prefix+'_degradation')
        with b:om_growth=st.number_input('Crecimiento real O&M fijo (%)',min_value=-10.,max_value=30.,value=0.,step=.25,key=key_prefix+'_growth')
        with c:replacement_percent=st.number_input('Reposición (% CAPEX instalado)',min_value=0.,max_value=1000.,value=0.,step=1.,key=key_prefix+'_replacement')
        with d:
            key=key_prefix+'_replacement_year'
            previous=st.session_state.get(key)
            if key not in st.session_state or st.session_state.get(key_prefix+'_year_limit')!=life or (previous is not None and previous>life):
                st.session_state[key]=min(previous if previous is not None else 10,life)
            st.session_state[key_prefix+'_year_limit']=life
            replacement_year=st.number_input('Año de reposición LCOE',min_value=1,max_value=int(life),value=None,step=1,key=key,disabled=not replacement_percent)
        retirement_percent=st.number_input('Retiro final (% CAPEX instalado)',min_value=0.,max_value=1000.,value=0.,step=1.,key=key_prefix+'_retirement')
        st.caption('Reposición única en el año elegido y retiro al final de la vida útil. Los porcentajes se aplican al CAPEX instalado del escenario; son supuestos, no provisiones publicadas.')
    missing=any(value is None for value in [life,rate,om_percent,replacement_percent,retirement_percent,degradation,om_growth])
    if missing or (replacement_percent and replacement_year is None):st.info('Completa los supuestos LCOE para calcular el costo de energía.');return
    if replacement_year is None:replacement_year=1
    degradation/=100;om_growth/=100;replacement_percent/=100;retirement_percent/=100
    results=[];errors=[]
    for _,row in edited.iterrows():
        cap=int(str(row['Turbina']).split()[0]);costs={field:_float(row[field])/factor_money for field in FIELDS};installed=costs['CAPEX equipo']+costs['Otros CAPEX instalados']
        args=dict(capacity_kw=cap,capacity_factor=factor,capex=installed,fixed_om=costs['O&M fijo anual'],variable_om=costs['O&M variable / kWh'],years=life,rate=rate/100,degradation=degradation,om_growth=om_growth,replacement_cost=installed*replacement_percent,replacement_year=replacement_year,decommission_cost=installed*retirement_percent)
        try:result=levelized_cost(**args)
        except ValueError as exc:errors.append(str(row['Turbina'])+': '+str(exc));continue
        results.append({'name':str(row['Turbina']),'args':args,'costs':costs,'result':result})
    for error in errors:st.warning(error)
    if not results:return
    cards=[]
    for entry in results:
        result=entry['result'];cards.extend([('LCOE · '+entry['name'],lcoe_text(result['lcoe'])+' / kWh',lcoe_text(result['lcoe'],True)+' / MWh'),('Energía neta año 1 · '+entry['name'],f'{result["energy_y1"]/1000:,.1f}'.replace(',','X').replace('.',',').replace('X','.')+' MWh','Factor de planta neto '+pct(factor))])
    if len(results)==1:
        entry=results[0];cards.extend([('CAPEX instalado del escenario',money(entry['args']['capex']),'Equipo + otros CAPEX declarados'),('O&M del primer año',money(entry['result']['annual_om_y1']),'Fijo + variable por energía neta')])
    kpis(cards)
    matrix=[]
    metrics=[('CAPEX equipo',lambda e:e['costs']['CAPEX equipo'],'money',currency_code()),('Otros CAPEX instalados',lambda e:e['costs']['Otros CAPEX instalados'],'money',currency_code()),('CAPEX instalado total',lambda e:e['args']['capex'],'money',currency_code()),('O&M fijo anual · año 1',lambda e:e['args']['fixed_om'],'money',currency_code()+'/año'),('O&M variable · año 1',lambda e:e['args']['variable_om']*e['result']['energy_y1'],'money',currency_code()+'/año'),('Energía neta · año 1',lambda e:e['result']['energy_y1']/1000,'number','MWh/año'),('VP energía de toda la vida útil',lambda e:e['result']['pv_energy']/1000,'number','MWh descontados'),('VP costos de toda la vida útil',lambda e:e['result']['pv_costs'],'money',currency_code()),('LCOE · CAPEX inicial',lambda e:e['result']['lcoe_components']['CAPEX inicial'],'lcoe',currency_code()+'/kWh'),('LCOE · O&M fijo',lambda e:e['result']['lcoe_components']['O&M fijo'],'lcoe',currency_code()+'/kWh'),('LCOE · O&M variable',lambda e:e['result']['lcoe_components']['O&M variable'],'lcoe',currency_code()+'/kWh'),('LCOE · reposición y retiro',lambda e:e['result']['lcoe_components']['Reposición']+e['result']['lcoe_components']['Retiro'],'lcoe',currency_code()+'/kWh'),('LCOE TOTAL',lambda e:e['result']['lcoe'],'lcoe',currency_code()+'/kWh')]
    for label,get,kind,unit in metrics:
        record={'Indicador':label,'Unidad':unit}
        for entry in results:
            value=get(entry);record[entry['name']]=money(value) if kind=='money' else lcoe_text(value) if kind=='lcoe' else f'{value:,.2f}'.replace(',','X').replace('.',',').replace('X','.')
        matrix.append(record)
    table=pd.DataFrame(matrix);st.dataframe(table[['Indicador',*[entry['name'] for entry in results],'Unidad']],hide_index=True,use_container_width=True,row_height=34,height=490,column_config={'Indicador':st.column_config.TextColumn(width=320),'Unidad':st.column_config.TextColumn(width=150)},key=key_prefix+'_results')
    fig=go.Figure();factors=sorted(set([v/100 for v in range(5,81,5)]+[factor]))
    for entry,color in zip(results,['#315E7D','#3B8F96']):
        values=[levelized_cost(**{**entry['args'],'capacity_factor':v})['lcoe'] for v in factors]
        fig.add_trace(go.Scatter(x=[v*100 for v in factors],y=[displayed(v) for v in values],mode='lines+markers',name=entry['name'],line=dict(color=color,width=2.5),customdata=[lcoe_text(v) for v in values],hovertemplate='Factor neto %{x:.1f}%<br>%{customdata} / kWh<extra>%{fullData.name}</extra>'))
    fig.add_vline(x=factor*100,line_dash='dot',line_color='#8296A7');fig.update_layout(title='Sensibilidad del LCOE al factor de planta neto');fig.update_xaxes(title_text='Factor de planta neto (%)');fig.update_yaxes(title_text=currency_code()+'/kWh',rangemode='tozero',tickformat='.3f' if currency_code()=='USD' else '.1f');plot(fig,'lcoe_sensitivity',290)
    technical_profiles(results,key_prefix=key_prefix)
    context('Alcance del resultado','LCOE indicativo, antes de impuestos y en moneda constante de '+str(year)+'. Usa energía neta: no se restan pérdidas ni disponibilidad nuevamente. Instalación y costos de sitio no cotizados, O&M supuesto y reposiciones de cero hacen que el escenario sea preliminar. El OPEX específico del fabricante no se utiliza como mantenimiento del activo. Los resultados pertenecen únicamente a este escenario de generación.')
    with st.expander('Fórmula, referencias y flujos anuales LCOE'):
        st.latex(r'\mathrm{LCOE}=\frac{CAPEX_0+\sum_{t=1}^{N}\frac{O\&M_t+Reposicion_t+Retiro_t}{(1+r)^t}}{\sum_{t=1}^{N}\frac{P\,8760\,FP_{neto}\,(1-d)^{t-1}}{(1+r)^t}}')
        st.markdown('[Metodología de costos y energía descontados · NLR/NREL]('+SOURCE+'). Se utiliza degradación geométrica anual desde el segundo año, con combustible cero para eólica. No se incluyen impuestos, subsidios, ingresos por venta de energía, intereses de deuda ni valor residual. La tasa real descuenta costos y energía al cierre de cada año; CAPEX inicial en año 0.')
        reference=products[['Turbina','Precio / equipo','Fabricación / equipo','OPEX específico / equipo']].copy()
        financial_table(reference,['Precio / equipo','Fabricación / equipo','OPEX específico / equipo'])
        st.caption('Referencias por equipo del modelo comercial. El OPEX específico es del fabricante; se presenta para trazabilidad y no como O&M del propietario.')
        names=[entry['name'] for entry in results];key=key_prefix+'_flow_product'
        if key in st.session_state and st.session_state[key] not in names:del st.session_state[key]
        name=st.selectbox('Turbina del flujo anual LCOE',names,index=names.index('80 kW') if '80 kW' in names else 0,key=key)
        chosen=next(entry for entry in results if entry['name']==name)
        financial_table(chosen['result']['flows'],['CAPEX inicial','O&M fijo','O&M variable','Reposición','Retiro','Costo total','VP costos'])


def technical_profiles(results,key_prefix='option4_lcoe'):
    from valuation_view import money,pct,plot,displayed
    st.markdown('##### Seguimiento técnico · generación, costos y horizonte')
    names=[entry['name'] for entry in results];key=key_prefix+'_technical_product'
    if key in st.session_state and st.session_state[key] not in names:del st.session_state[key]
    preferred=names.index('80 kW') if '80 kW' in names else 0
    name=st.selectbox('Turbina de los gráficos técnicos LCOE',names,index=preferred,key=key)
    entry=next(item for item in results if item['name']==name);args=entry['args'];result=entry['result']
    profile=lcoe_profiles(result);annual=profile[profile['Año'].gt(0)]
    st.caption('Turbina de '+name+' · factor neto '+pct(args['capacity_factor'])+' · vida '+str(args['years'])+' años · tasa real '+pct(args['rate'])+'. Las curvas se actualizan con la tabla editable y los supuestos avanzados.')
    views=st.tabs(['Generación neta','O&M y reposiciones','LCOE por horizonte'])
    with views[0]:
        fig=make_subplots(rows=2,cols=1,shared_xaxes=True,vertical_spacing=.18,
            subplot_titles=('Producción neta por año','Producción neta acumulada'))
        for row,field,label,color in [(1,'Energía anual MWh','Energía anual','#315E7D'),(2,'Energía acumulada MWh','Energía acumulada','#3B8F96')]:
            fig.add_trace(go.Scatter(x=annual['Año'],y=annual[field],name=label,mode='lines+markers',line=dict(color=color,width=2.5),marker=dict(size=5),hovertemplate='Año %{x}<br>%{y:,.2f} MWh<extra>%{fullData.name}</extra>'),row=row,col=1)
        fig.update_annotations(font=dict(size=12,color='#203E58'))
        fig.update_yaxes(title_text='MWh/año',rangemode='tozero',tickformat=',.1f',row=1,col=1);fig.update_yaxes(title_text='MWh acumulados',rangemode='tozero',tickformat=',.0f',row=2,col=1)
        fig.update_xaxes(title_text='Año operativo',row=2,col=1);fig.update_xaxes(dtick=max(1,int(args['years']//6)),tickformat='d')
        fig.update_layout(title='Generación del escenario · '+name,showlegend=False);plot(fig,'lcoe_energy_profile',360)
        st.caption('Energía neta = potencia × 8760 × factor neto, con la degradación anual ingresada. La curva acumulada suma energía física, sin descuento financiero.')
    with views[1]:
        fig=go.Figure()
        for field,label,color,dash in [('O&M anual','O&M fijo + variable','#315E7D','solid'),('Reposición y retiro','Reposición + retiro','#AD6551','dot'),('Costo operativo anual','Costo anual total','#3B8F96','dash')]:
            fig.add_trace(go.Scatter(x=annual['Año'],y=displayed(annual[field]),name=label,mode='lines+markers',line=dict(color=color,width=2.5,dash=dash),marker=dict(size=5),customdata=[money(v) for v in annual[field]],hovertemplate='Año %{x}<br>%{customdata}<extra>%{fullData.name}</extra>'))
        if args['replacement_cost']>0:fig.add_vline(x=args['replacement_year'],line_dash='dot',line_color='#AD6551')
        fig.update_layout(title='Costos anuales del escenario · '+name)
        fig.update_xaxes(title_text='Año operativo',dtick=max(1,int(args['years']//6)),tickformat='d');fig.update_yaxes(title_text=currency_code()+'/año',rangemode='tozero',tickformat=',.0f')
        plot(fig,'lcoe_cost_profile',310)
        st.caption('Importes reales de cada año antes de descuento. El CAPEX inicial de '+money(args['capex']).replace('$',r'\$')+' se desembolsa en año 0 y se incluye en el LCOE, separado de estas curvas operativas.')
    with views[2]:
        fig=go.Figure(go.Scatter(x=annual['Año'],y=displayed(annual['LCOE acumulado']),name='Costo nivelado hasta cada año',mode='lines+markers',line=dict(color='#315E7D',width=2.5),marker=dict(size=5),customdata=[lcoe_text(v) for v in annual['LCOE acumulado']],hovertemplate='Hasta año %{x}<br>%{customdata} / kWh<extra></extra>'))
        fig.add_hline(y=displayed(result['lcoe']),line_dash='dot',line_color='#3B8F96')
        fig.update_layout(title='Costo nivelado acumulado · '+name)
        fig.update_xaxes(title_text='Horizonte acumulado · años',dtick=max(1,int(args['years']//6)),tickformat='d');fig.update_yaxes(title_text=currency_code()+'/kWh',rangemode='tozero',tickformat='.3f' if currency_code()=='USD' else '.1f')
        plot(fig,'lcoe_horizon_profile',310)
        st.caption('Cada punto divide los costos descontados desde año 0 hasta ese año entre la energía descontada del mismo período. El punto final coincide con el LCOE total de la tabla; la línea punteada marca ese valor de vida completa.')
