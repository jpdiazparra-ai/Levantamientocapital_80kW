"""Pre-tax real LCOE: discounted owner costs divided by discounted net energy."""
import math
import numpy as np
import pandas as pd


def levelized_cost(capacity_kw,capacity_factor,capex,fixed_om,variable_om,years,rate,
                   degradation=0.,om_growth=0.,replacement_cost=0.,replacement_year=1,decommission_cost=0.):
    values=[capacity_kw,capacity_factor,capex,fixed_om,variable_om,years,rate,degradation,om_growth,replacement_cost,replacement_year,decommission_cost]
    if any(not isinstance(v,(int,float,np.number)) or not math.isfinite(v) for v in values):
        raise ValueError('Completa los costos y supuestos con valores numéricos finitos.')
    if capacity_kw<=0 or not 0<capacity_factor<=1:raise ValueError('La potencia y el factor de planta neto deben ser positivos; el factor no puede superar 100 %.')
    if int(years)!=years or not 1<=years<=100:raise ValueError('La vida útil debe ser un entero entre 1 y 100 años.')
    if rate<0 or not 0<=degradation<1 or om_growth<=-1:raise ValueError('Revisa la tasa real, la degradación y el crecimiento real de O&M.')
    if min(capex,fixed_om,variable_om,replacement_cost,decommission_cost)<0:raise ValueError('Los costos no pueden ser negativos.')
    if replacement_cost and (int(replacement_year)!=replacement_year or not 1<=replacement_year<=years):raise ValueError('El año de reposición debe estar dentro de la vida útil.')
    years=int(years);t=np.arange(years+1);energy=np.zeros(years+1);energy[1:]=capacity_kw*8760*capacity_factor*(1-degradation)**np.arange(years)
    initial=np.zeros(years+1);initial[0]=capex
    fixed=np.zeros(years+1);fixed[1:]=fixed_om*(1+om_growth)**np.arange(years)
    variable=energy*variable_om;replacement=np.zeros(years+1);retirement=np.zeros(years+1)
    if replacement_cost:replacement[int(replacement_year)]=replacement_cost
    retirement[-1]=decommission_cost;factor=(1+rate)**(-t.astype(float))
    components={'CAPEX inicial':initial,'O&M fijo':fixed,'O&M variable':variable,'Reposición':replacement,'Retiro':retirement}
    cash=sum(components.values());pv_energy=float((energy*factor).sum())
    if not math.isfinite(pv_energy) or pv_energy<=0:raise ValueError('No hay energía descontada positiva para calcular el LCOE.')
    pv={key:float((values*factor).sum()) for key,values in components.items()}
    pv_cost=float(sum(pv.values()))
    if not math.isfinite(pv_cost) or not np.isfinite(cash).all():raise ValueError('Los costos del escenario exceden el rango numérico del cálculo.')
    flows=pd.DataFrame({'Año':t,'Energía neta kWh':energy,**components,'Costo total':cash,'Factor descuento':factor,'VP costos':cash*factor,'VP energía kWh':energy*factor})
    return {'lcoe':pv_cost/pv_energy,'energy_y1':float(energy[1]),'pv_energy':pv_energy,'pv_costs':pv_cost,
        'annual_om_y1':float(fixed[1]+variable[1]),'components':pv,
        'lcoe_components':{key:value/pv_energy for key,value in pv.items()},'flows':flows}
