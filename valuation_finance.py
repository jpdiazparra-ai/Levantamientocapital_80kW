"""Auditable financial analytics over the published valuation cash flows (native USD)."""
import math
import numpy as np
import pandas as pd


def divide(numerator,denominator):
    return numerator/denominator if pd.notna(numerator) and pd.notna(denominator) and denominator>0 else float('nan')


def complete_sum(values):
    values=pd.to_numeric(pd.Series(values),errors='coerce')
    return values.sum() if len(values) and values.notna().all() else float('nan')


def discounted_flows(flows,rate):
    values=np.asarray(flows,dtype=float)
    if rate<=-1 or not math.isfinite(rate) or not np.isfinite(values).all():
        raise ValueError('Se requieren flujos completos y una tasa mayor a −100 %.')
    return values/np.power(1+rate,np.arange(len(values)))


def payback(flows,rate=0):
    try:values=discounted_flows(flows,rate)
    except ValueError:return float('nan')
    if len(values)<2 or values[0]>=0:return float('nan')
    accumulated=values.cumsum()
    for i in range(1,len(values)):
        if accumulated[i]>=0 and accumulated[i-1]<0 and values[i]>0:
            return i-1+abs(accumulated[i-1])/values[i]
    return float('nan')


def financial_diagnostics(model):
    s,a=model['scalars'],model['annual']
    try:
        economic=discounted_flows(a['economic_cf'],s['rate'])
        positive=economic[economic>0].sum();negative=-economic[economic<0].sum()
    except ValueError:positive=negative=float('nan')
    first=a[a['Año modelo'].gt(0)].iloc[0]
    return {'DCF/Ventas año 1':divide(s['dcf'],first['sales']),
        'DCF/EBITDA año 1':divide(s['dcf'],first['ebitda']),
        'Índice de rentabilidad económico':divide(positive,negative),
        'Payback económico simple':payback(a['economic_cf']),
        'Payback económico descontado':payback(a['economic_cf'],s['rate']),
        'Spread tasa − crecimiento':s['rate']-s['growth'],
        'Precio previo / DCF':divide(s['pre_money'],s['dcf']),
        'Terminal / DCF':s['terminal_weight']}


def unit_economics(model,year):
    row=model['annual'].loc[model['annual']['Año'].eq(str(year))].iloc[0]
    base=complete_sum([row['cost_10'],row['cost_80']])
    extras=complete_sum([row.get('external_cost_10',0),row.get('external_cost_80',0)])
    total=row['cogs']
    # Source editions may include additional subcontracting within product costs
    # or separately. Allocate only when the published consolidated COGS reconcile.
    use_extras=pd.notna(base) and pd.notna(total) and abs(total-base)>5 and pd.notna(extras) and abs(total-base-extras)<=5
    cost_gap=total-base-(extras if use_extras else 0)
    records=[]
    for cap in (10,80):
        units=row[f'units_{cap}'];sales=row[f'sales_{cap}']
        cost=row[f'cost_{cap}']+(row.get(f'external_cost_{cap}',0) if use_extras else 0)
        opex=row[f'opex_{cap}'];gross=sales-cost if pd.notna(cost_gap) and abs(cost_gap)<=5 else float('nan');contribution=gross-opex
        records.append({'Turbina':f'{cap} kW','Potencia kW':cap,'Entregas':units,'Ventas':sales,
            'Fabricación total':cost,'OPEX específico total':opex,'Contribución total':contribution,
            'Precio / equipo':divide(sales,units),'Fabricación / equipo':divide(cost,units),
            'Margen bruto / equipo':divide(gross,units),'Margen bruto %':divide(gross,sales),
            'OPEX específico / equipo':divide(opex,units),'Contribución / equipo':divide(contribution,units),
            'Margen contribución %':divide(contribution,sales),'kW entregados':units*cap})
    return pd.DataFrame(records),cost_gap


def mix_analysis(products,share_80,volume,common_opex,capacity):
    if not 0<=share_80<=1 or not math.isfinite(volume) or volume<0:
        raise ValueError('El mix debe estar entre 0 y 100 % y el volumen no puede ser negativo.')
    by_power=products.set_index('Potencia kW')
    weighted_price=weighted_contribution=0.
    for cap,weight in [(10,1-share_80),(80,share_80)]:
        if weight==0:continue
        price=by_power.at[cap,'Precio / equipo'];contribution=by_power.at[cap,'Contribución / equipo']
        if pd.isna(price) or pd.isna(contribution):
            return {key:float('nan') for key in ['sales','contribution','ebitda','break_even_units','break_even_sales','safety_margin','operating_leverage','external']}
        weighted_price+=weight*price;weighted_contribution+=weight*contribution
    sales=weighted_price*volume;contribution=weighted_contribution*volume;ebitda=contribution-common_opex
    break_even=divide(common_opex,weighted_contribution)
    return {'sales':sales,'contribution':contribution,'ebitda':ebitda,
        'break_even_units':break_even,'break_even_sales':break_even*weighted_price,
        'safety_margin':divide(volume-break_even,volume),
        'operating_leverage':divide(contribution,ebitda),
        'external':max(volume-capacity,0) if pd.notna(capacity) else float('nan')}


def reprice_dcf(model,rate,growth,include_terminal=True):
    if not math.isfinite(rate) or rate<=0:raise ValueError('La tasa de descuento debe ser positiva.')
    if include_terminal and (not math.isfinite(growth) or rate<=growth):
        raise ValueError('La tasa de descuento debe ser mayor que el crecimiento terminal.')
    s,a=model['scalars'],model['annual'];horizon=len(a)-1
    if include_terminal and not math.isfinite(s['terminal_cf']):raise ValueError('El flujo terminal normalizado no está disponible en la fuente.')
    cash=discounted_flows(a['fcff'],rate)
    economic=discounted_flows(a['economic_cf'],rate)
    terminal=s['terminal_cf']/(rate-growth) if include_terminal else 0.
    pv_terminal=terminal/(1+rate)**horizon
    value=float(cash.sum()+pv_terminal)
    return {'dcf':value,'npv_cash':float(cash.sum()),'npv_economic':float(economic.sum()),
        'terminal_value':terminal,'pv_terminal':pv_terminal,'terminal_weight':divide(pv_terminal,value),
        'periods':pd.DataFrame({'Año':a['Año'],'Flujo publicado USD':a['fcff'].to_numpy(),'Factor':1/np.power(1+rate,np.arange(len(a))),'VP explícito USD':cash})}


def projection_diagnostics(frame):
    sales=complete_sum(frame['sales']);ebitda=complete_sum(frame['ebitda']);fcff=complete_sum(frame['fcff'])
    periods=len(frame)-1;first,last=frame.iloc[0],frame.iloc[-1]
    cagr=(last['sales']/first['sales'])**(1/periods)-1 if periods>0 and first['sales']>0 and last['sales']>0 else float('nan')
    return {'sales':sales,'ebitda':ebitda,'margin':divide(ebitda,sales),'fcff':fcff,
        'cash_close':last['cash_free'],'cagr':cagr,'cash_conversion':divide(fcff,ebitda),
        'external_share':divide(complete_sum(frame['external']),complete_sum(frame['units_total']))}
