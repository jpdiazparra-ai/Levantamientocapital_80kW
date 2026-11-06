"""Interactive owner-side LCOE assumptions, independent of the corporate DCF."""
import math
import hashlib
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from display_currency import currency_code,exchange_rate
from lcoe_finance import levelized_cost

SOURCE='https://www.nlr.gov/pv/lcoe-calculator/documentation'
FIELDS=['CAPEX equipo','Otros CAPEX instalados','O&M fijo anual','O&M variable / kWh']


def lcoe_text(value,per_mwh=False):
    if pd.isna(value):return 'Sin cálculo'
    shown=value*(exchange_rate() if currency_code()=='CLP' else 1)*(1000 if per_mwh else 1)
    digits=2 if per_mwh or currency_code()=='CLP' else 4
    return ('US$ ' if currency_code()=='USD' else '$')+f'{shown:,.{digits}f}'.replace(',','X').replace('.',',').replace('X','.')


def _reset_inputs(context):
    overrides=dict(st.session_state.get('option4_lcoe_overrides',{}));overrides.pop(context,None)
    st.session_state['option4_lcoe_overrides']=overrides
    # Editor keys change by selection/currency; clear only the current source context.
    prefix='option4_lcoe_editor_'+hashlib.sha1(context.encode()).hexdigest()[:10]
    for key in list(st.session_state):
        if key.startswith(prefix):del st.session_state[key]


def _float(value):
    try:return float(value)
    except (TypeError,ValueError):return float('nan')


def lcoe_panel(model,year,products):
    from valuation_view import section,kpis,money,pct,plot,displayed,financial_table,context
    section('03 / COSTO DE ENERGÍA','LCOE · costo nivelado de generación')
    st.caption('Escenario del propietario de una turbina instalada. Usa los productos y el año del comparativo superior; no modifica el DCF del negocio ni el equilibrio del mix.')
    if products.empty:st.info('Selecciona una turbina para construir su escenario LCOE.');return
    a,b,c,d=st.columns([1.4,1,1,1],vertical_alignment='bottom')
    with a:factor=st.slider('Factor de planta neto (%)',0.,100.,value=30.,step=.5,key='option4_lcoe_factor',help='Energía neta / (potencia nominal × 8760). Incluye disponibilidad, pérdidas y restricciones; no se descuentan otra vez.')/100
    with b:life=st.number_input('Vida útil LCOE (años)',min_value=1,max_value=60,value=20,step=1,key='option4_lcoe_life')
    with c:rate=st.number_input('Tasa real LCOE (%)',min_value=0.,max_value=100.,value=8.,step=.5,key='option4_lcoe_rate',help='Supuesto independiente de la tasa del DCF corporativo. Costos en moneda constante del año de referencia.')
    with d:om_percent=st.number_input('Supuesto O&M (% equipo/año)',min_value=0.,max_value=100.,value=2.,step=.25,key='option4_lcoe_om_percent',help='Hipótesis ilustrativa para iniciar la tabla. La celda O&M anual se puede sustituir por una cotización propia; una edición manual tiene prioridad. El porcentaje usa la referencia de la fuente, no los CAPEX modificados en la tabla.')
    if any(value is None for value in [life,rate,om_percent]):
        st.info('Completa vida útil, tasa real y supuesto O&M para calcular el escenario.');return
    basis=st.radio('Referencia inicial del CAPEX del equipo',['Precio de venta','Costo de fabricación'],horizontal=True,key='option4_lcoe_basis')
    st.caption('Inicio ilustrativo: factor neto 30 %, vida 20 años, tasa real 8 % y O&M fijo 2 % del precio de referencia del equipo. No son especificaciones certificadas ni cotizaciones de mantenimiento. El precio de venta es una referencia de compra; fabricación es una aproximación interna y no una oferta al cliente.')
    source_field='Precio / equipo' if basis=='Precio de venta' else 'Fabricación / equipo'
    context_key=str(year)+'|'+basis
    all_overrides=dict(st.session_state.get('option4_lcoe_overrides',{}));overrides=all_overrides.get(context_key,{})
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
    prefix='option4_lcoe_editor_'+hashlib.sha1(context_key.encode()).hexdigest()[:10]
    editor_key=prefix+'_'+currency_code()+'_'+str(exchange_rate())+'_'+'_'.join(frame['Turbina'])
    config={'Turbina':st.column_config.TextColumn(width=100)}
    for field in FIELDS:
        variable=field=='O&M variable / kWh'
        config[field]=st.column_config.NumberColumn(field+' · '+currency_code() if not variable else 'O&M variable · '+currency_code()+'/kWh',min_value=0.,step=.0001 if variable else .01,format='%.4f' if variable else '%.2f',width=190)
    edited=st.data_editor(frame,hide_index=True,use_container_width=True,num_rows='fixed',disabled=['Turbina'],column_config=config,key=editor_key,row_height=40)
    # Store only actual user edits, in native USD. A refreshed source still updates unedited defaults.
    for i,row in edited.iterrows():
        cap=str(int(products.iloc[i]['Potencia kW']))
        for field in FIELDS:
            value,original=_float(row[field]),_float(frame.loc[i,field])
            if not ((math.isnan(value) and math.isnan(original)) or math.isclose(value,original,rel_tol=1e-10,abs_tol=1e-10)):
                overrides.setdefault(cap,{})[field]=value/factor_money
    all_overrides[context_key]=overrides;st.session_state['option4_lcoe_overrides']=all_overrides
    st.button('Restaurar costos de referencia LCOE',key='option4_lcoe_restore',on_click=_reset_inputs,args=(context_key,))
    with st.expander('Supuestos avanzados · degradación, O&M y reposición'):
        a,b,c,d=st.columns(4,vertical_alignment='bottom')
        with a:degradation=st.number_input('Degradación energética anual (%)',min_value=0.,max_value=20.,value=0.,step=.1,key='option4_lcoe_degradation')
        with b:om_growth=st.number_input('Crecimiento real O&M fijo (%)',min_value=-10.,max_value=30.,value=0.,step=.25,key='option4_lcoe_growth')
        with c:replacement_percent=st.number_input('Reposición (% CAPEX instalado)',min_value=0.,max_value=1000.,value=0.,step=1.,key='option4_lcoe_replacement')
        with d:
            key='option4_lcoe_replacement_year'
            previous=st.session_state.get(key)
            if key not in st.session_state or st.session_state.get('option4_lcoe_year_limit')!=life or (previous is not None and previous>life):
                st.session_state[key]=min(previous if previous is not None else 10,life)
            st.session_state['option4_lcoe_year_limit']=life
            replacement_year=st.number_input('Año de reposición LCOE',min_value=1,max_value=int(life),value=None,step=1,key=key,disabled=not replacement_percent)
        retirement_percent=st.number_input('Retiro final (% CAPEX instalado)',min_value=0.,max_value=1000.,value=0.,step=1.,key='option4_lcoe_retirement')
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
    table=pd.DataFrame(matrix);st.dataframe(table[['Indicador',*[entry['name'] for entry in results],'Unidad']],hide_index=True,use_container_width=True,row_height=34,height=490,column_config={'Indicador':st.column_config.TextColumn(width=320),'Unidad':st.column_config.TextColumn(width=150)},key='option4_lcoe_results')
    fig=go.Figure();factors=sorted(set([v/100 for v in range(5,81,5)]+[factor]))
    for entry,color in zip(results,['#315E7D','#3B8F96']):
        values=[levelized_cost(**{**entry['args'],'capacity_factor':v})['lcoe'] for v in factors]
        fig.add_trace(go.Scatter(x=[v*100 for v in factors],y=[displayed(v) for v in values],mode='lines+markers',name=entry['name'],line=dict(color=color,width=2.5),customdata=[lcoe_text(v) for v in values],hovertemplate='Factor neto %{x:.1f}%<br>%{customdata} / kWh<extra>%{fullData.name}</extra>'))
    fig.add_vline(x=factor*100,line_dash='dot',line_color='#8296A7');fig.update_layout(title='Sensibilidad del LCOE al factor de planta neto');fig.update_xaxes(title_text='Factor de planta neto (%)');fig.update_yaxes(title_text=currency_code()+'/kWh',rangemode='tozero',tickformat='.3f' if currency_code()=='USD' else '.1f');plot(fig,'lcoe_sensitivity',290)
    context('Alcance del resultado','LCOE indicativo, antes de impuestos y en moneda constante de '+str(year)+'. Usa energía neta: no se restan pérdidas ni disponibilidad nuevamente. Instalación y costos de sitio no cotizados, O&M supuesto y reposiciones de cero hacen que el escenario sea preliminar. El OPEX específico del fabricante no se utiliza como mantenimiento del activo. Los resultados pertenecen únicamente a este escenario de generación.')
    with st.expander('Fórmula, referencias y flujos anuales LCOE'):
        st.latex(r'\mathrm{LCOE}=\frac{CAPEX_0+\sum_{t=1}^{N}\frac{O\&M_t+Reposicion_t+Retiro_t}{(1+r)^t}}{\sum_{t=1}^{N}\frac{P\,8760\,FP_{neto}\,(1-d)^{t-1}}{(1+r)^t}}')
        st.markdown('[Metodología de costos y energía descontados · NLR/NREL]('+SOURCE+'). Se utiliza degradación geométrica anual desde el segundo año, con combustible cero para eólica. No se incluyen impuestos, subsidios, ingresos por venta de energía, intereses de deuda ni valor residual. La tasa real descuenta costos y energía al cierre de cada año; CAPEX inicial en año 0.')
        reference=products[['Turbina','Precio / equipo','Fabricación / equipo','OPEX específico / equipo']].copy()
        financial_table(reference,['Precio / equipo','Fabricación / equipo','OPEX específico / equipo'])
        st.caption('Referencias por equipo del modelo comercial. El OPEX específico es del fabricante; se presenta para trazabilidad y no como O&M del propietario.')
        names=[entry['name'] for entry in results];key='option4_lcoe_flow_product'
        if key in st.session_state and st.session_state[key] not in names:st.session_state[key]=names[0]
        name=st.selectbox('Turbina del flujo anual LCOE',names,key=key)
        chosen=next(entry for entry in results if entry['name']==name)
        financial_table(chosen['result']['flows'],['CAPEX inicial','O&M fijo','O&M variable','Reposición','Retiro','Costo total','VP costos'])
