"""Read-only valuation model, sourced exclusively from the published 00–09 workbook."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo
import csv
from io import StringIO
import math
import re
import time

import pandas as pd
import requests
import streamlit as st

SOURCE = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSLGE7e12WDJ2MiiGFqFOieTuXl4ilhBgbLv2I3sQEAJCOVpVeRTjxK-lmdUZ5gjg/pub'
SHEETS = {
 '00 Evaluación':'1695395322', '00 Datos de entrada':'1345496271', '01 Resumen':'2051462092',
 '02 Inversión y socios':'884604672', '03 Supuestos':'1255500890', '04 Resultados y flujo':'456269474',
 '05 Balance y cobros':'137275516', '06 Caja mensual':'1385031919', '07 Ventas y producción':'2097377197',
 '08 Gastos operativos':'1746715691', '09 Activos y arranque':'1897913965',
}


def number(value):
    text = str(value).strip().replace('\xa0','').replace(' ','')
    if text in ('-','–','—'): return 0.0  # Published accounting zero, never a blank.
    if text.lower() in ('','nan','none','n.a.','n.d.','n/a'): return float('nan')
    negative = text.startswith('(') and text.endswith(')')
    percentage = '%' in text
    text = text.strip('()').replace('USD','').replace('CLP','').replace('US$','').replace('$','').replace('%','').rstrip('x')
    try:
        result = float(text.replace('.','').replace(',','.')) if ',' in text or re.fullmatch(r'-?\d{1,3}(\.\d{3})+',text) else float(text)
        result = -result if negative else result
        return result/100 if percentage else result
    except ValueError: return float('nan')


class Sheet:
    def __init__(self,name,rows): self.name,self.rows=name,rows
    def cell(self,address):
        match=re.fullmatch(r'([A-Z]+)(\d+)',address)
        col=0
        for c in match[1]:col=col*26+ord(c)-64
        row=int(match[2])-1
        return self.rows[row][col-1] if row<len(self.rows) and col<=len(self.rows[row]) else ''
    def find(self,label,column='C'):
        normalized=lambda text:' '.join(str(text).split()).casefold()
        hits=[i for i in range(1,len(self.rows)+1) if normalized(self.cell(f'{column}{i}'))==normalized(label)]
        if not hits: raise ValueError(f'{self.name}: no se encontró «{label}». Revisa los encabezados publicados.')
        return hits[0]
    def value(self,label,value_col='E',label_col='C',numeric=True):
        row=self.find(label,label_col);value=self.cell(f'{value_col}{row}')
        return number(value) if numeric else value
    def ref(self,label,value_col='E',label_col='C'):return f'{self.name}!{value_col}{self.find(label,label_col)}'


def parse_deal(sheet):
    """Preserve every published deal term, including notes and cell references."""
    blocks={'Condiciones de la operación','Precio y participación accionaria',
            'Aplicación de los fondos en FW','Valorización del modelo y precio negociado'}
    block=None;records=[];criteria=[]
    for row in range(1,len(sheet.rows)+1):
        label=sheet.cell(f'C{row}').strip()
        if label in blocks:block=label;continue
        if label=='Criterios de lectura':block='Criterios';continue
        if block=='Criterios' and label:criteria.append(label);continue
        value=sheet.cell(f'E{row}').strip()
        if block in blocks and label and value:
            unit=sheet.cell(f'F{row}').strip()
            if value.endswith('%'):unit='%'
            records.append({'Bloque':block,'Concepto':label,'Valor fuente':value,
                'Valor':number(value),'Unidad':unit,'Observación':sheet.cell(f'H{row}'),
                'Referencia':f'{sheet.name}!E{row}'})
    return pd.DataFrame(records),criteria


def parse_model(raw):
    sheets={name:Sheet(name,raw[name]) for name in SHEETS}
    evaluation,inputs,summary,deal,assumptions,results,balance,monthly,operations,opex,assets=[sheets[name] for name in SHEETS]
    source_errors=[{'Pestaña':name,'Fila':i,'Error':value} for name,rows in raw.items() for i,row in enumerate(rows,1) for value in row if re.match(r'^#(?:REF!|DIV/0!|VALUE!|NAME\?|N/A|NUM!|ERROR!)',value)]
    def ev(label):return evaluation.value(label,'C','B')
    scalars={
      'dcf':ev('DCF antes de capital nuevo · USD'), 'npv_cash':ev('VAN de caja sin terminal · USD'),
      'npv_economic':ev('VAN económico sin terminal · USD'),'irr_economic':ev('TIR económica sin terminal'),
      'terminal_weight':ev('Peso del terminal en el VAN'),'pre_money':ev('Valor previo implícito negociado · USD'),
      'post_money':ev('Valor posterior implícito negociado · USD'),'sales_y1':ev('Ventas año 1 · USD'),
      'ebitda_y1':ev('EBITDA año 1 · USD'),'ebitda_margin_y1':ev('Margen EBITDA año 1'),
      'fcff_y1':ev('Flujo libre año 1 · USD'),'cash_y0':ev('Caja libre año 0 tras aporte/puente · USD'),
      'bridge':ev('Puente adicional máximo · USD'),'advances_y1':ev('Anticipos pendientes año 1 · USD'),
      'rate':inputs.value('Tasa de descuento aplicada ↗','C','B'),'growth':inputs.value('Crecimiento terminal','C','B'),
      'model_fx':inputs.value('Tipo de cambio','C','B'),'first_year':inputs.value('Primer año de operación','C','B'),
      'advance_rate':inputs.value('Anticipo de clientes','C','B'),'advance_days':inputs.value('Días entre anticipo y entrega','C','B'),
      'investment_total':deal.value('Pago total del inversionista'),'primary':deal.value('Aporte de capital a FW'),
      'secondary':deal.value('Compra de acciones a fundadores'),'investor_share':deal.value('Participación final del inversionista'),
      'primary_share':deal.value('Participación por emisión de acciones nuevas'),'secondary_share':deal.value('Participación adquirida a fundadores'),
      'founder_share':deal.value('Participación final accionistas actuales'),'cash_target':deal.value('Caja objetivo después del arranque'),
      'cash_required':deal.value('Uso de caja de arranque, neto de anticipos'),'target_funding':deal.value('Aporte total para conservar caja objetivo'),
      'economic_investment':assets.value('Inversión económica inicial'),'assets_in_kind':assets.value('Activos fijos iniciales'),
      'preop':assets.value('Gastos preoperacionales iniciales'),'spares':assets.value('Repuestos de planta iniciales'),
      'historical_wc':assets.value('Capital de trabajo histórico (solo referencia)'),
      'terminal_cf':results.value('Flujo terminal normalizado'),'terminal_value':results.value('Valor terminal del proyecto','O'),
      'valuation_date':assumptions.value('Fecha referencial de valorización (informativa)',numeric=False),
    }
    required=['dcf','npv_cash','npv_economic','rate','growth','model_fx','first_year','primary','secondary']
    if any(not math.isfinite(scalars[key]) for key in required):raise ValueError('Faltan valores esenciales en las salidas o supuestos de la valorización.')
    if scalars['model_fx']<=0:raise ValueError('El tipo de cambio del modelo debe ser positivo.')
    scenario=inputs.value('Escenario','C','B',False);production=inputs.value('Modo de producción','C','B',False)
    status=deal.value('Estado de la operación',numeric=False)
    mapping={
      'sales':'Ingresos consolidados','sales_80':'Ingresos 80 kW','sales_10':'Ingresos 10 kW','cogs':'Costo de ventas',
      'opex':'OPEX total detallado','ebitda':'EBITDA','ebitda_margin':'Margen EBITDA','ebit':'EBIT','net_income':'Utilidad neta',
      'tax':'Impuesto estimado','da':'Depreciación total','ct_change':'Variación de capital de trabajo',
      'fcff':'Flujo libre del proyecto (FCFF)','pv_fcff':'FCFF descontado','economic_cf':'Flujo económico con activos aportados',
      'capex':'CAPEX pagado por FW','advance_change':'Aumento / disminución de anticipos de clientes','vat_change':'Variación IVA neto (activo menos pasivo)',
    }
    annual=pd.DataFrame({'Año':['Año 0',*[str(int(scalars['first_year'])+i) for i in range(10)]],'Año modelo':list(range(11))})
    def add_series(sheet,cols):
        for key,label in cols.items():
            row=sheet.find(label);annual[key]=[number(sheet.cell(f'{chr(69+i)}{row}')) for i in range(11)]
    # Fail clearly if the published timeline changes instead of mixing periods.
    header=results.find('Partida')
    years=[results.cell(f'{chr(69+i)}{header}') for i in range(11)]
    if years!=annual['Año'].tolist():raise ValueError('El eje anual publicado cambió; no se puede alinear Año 0 y los diez años operativos.')
    add_series(results,mapping)
    add_series(balance,{'cash_free':'Caja libre tras aporte y puente','cash_total':'Caja total proyectada','cash_unfunded':'Caja acumulada antes de aportes','advances':'Saldo final por equipos pendientes de entrega','assets':'Total activos','liabilities':'Total pasivos','equity':'Patrimonio al cierre (capital proyectado)','collections':'Total de dinero recibido de clientes durante el año'})
    add_series(operations,{'units_80':'Unidades vendidas 80 kW','units_10':'Unidades vendidas 10 kW','units_total':'Unidades vendidas totales','demand_80':'Unidades proyectadas 80 kW','demand_10':'Unidades proyectadas 10 kW','capacity':'Capacidad propia de referencia','external':'Unidades a ampliar / externalizar','cost_80':'Costo de ventas 80 kW','cost_10':'Costo de ventas 10 kW','opex_80':'Gastos específicos 80 kW','opex_10':'Gastos específicos 10 kW','opex_common':'Gastos comunes de FW','unit_cost_80':'Costo unitario 80 kW','unit_cost_10':'Costo unitario 10 kW','external_cost_80':'Fabricación terceros adicional 80 kW','external_cost_10':'Fabricación terceros adicional 10 kW'})
    add_series(assets,{'assets_book':'Valor contable de activos','asset_da':'Depreciación total','capex_later':'CAPEX posterior total'})
    mheader=monthly.find('Mes');mcols=[value for value in monthly.rows[mheader-1] if value]
    mrows=[]
    for row in monthly.rows[mheader:]:
        if len(row)>4 and re.fullmatch(r'\d+',row[3].strip()) and re.fullmatch(r'\d+',row[4].strip()):
            record=dict(zip(mcols,row[2:]));model_year=int(row[3]);month=int(row[4])
            record={key:(value if key=='Mes' else number(value)) for key,value in record.items()}
            record['Fecha']=pd.Timestamp(year=int(scalars['first_year'])-1+model_year,month=month,day=1)
            mrows.append(record)
    months=pd.DataFrame(mrows)
    required_months=['Flujo neto USD','Caja sin puente','Caja tras aporte y puente','Capital inversionista']
    if months.empty or any(key not in months for key in required_months):raise ValueError('La estructura de Caja mensual no contiene las columnas esperadas.')
    # 2037 is a supporting year for terminal/advance calculations, beyond the ten-year DCF horizon.
    months['Apoyo terminal']=months['Año modelo'].gt(10)
    opex_records=[]
    for r,row in enumerate(opex.rows,1):
        if len(row)>20 and re.fullmatch(r'OP-\d+',row[2]):
            for i,year in enumerate(annual['Año'][1:]):
                opex_records.append({'ID':row[2],'Área':row[3],'Concepto':row[4],'Destino':row[5], 'Año':year,
                    'Cantidad año 1':number(row[6]),'Tarifa fuente CLP':number(row[7]),'Períodos año 1':number(row[8]),
                    'USD':number(row[9+i])/scalars['model_fx'],'Estado':row[20], 'Criterio':row[21] if len(row)>21 else '', 'Fuente':f'08 Gastos operativos!{column_name(10+i)}{r}'})
    for label in ['Regalía / licencia (USD)','Consumo y reposición repuestos (USD)','Carga empleador adicional (USD)']:
        r=opex.find(label)
        for i,year in enumerate(annual['Año'][1:]):
            opex_records.append({'ID':'AJ-'+str(r),'Área':'Ajustes publicados','Concepto':label,'Destino':'Común','Año':year,'USD':number(opex.cell(f'{column_name(10+i)}{r}')),'Estado':'Supuesto del modelo','Fuente':f'08 Gastos operativos!{column_name(10+i)}{r}'})
    asset_records=[]
    for r,row in enumerate(assets.rows,1):
        if len(row)>19 and re.fullmatch(r'CAP-\d+',row[2]):
            asset_records.append({'ID':row[2],'Área':row[3],'Activo / alcance':row[4],'Naturaleza':row[5],'Asignación':row[6],
                'Cantidad':number(row[7]),'Unitario fuente USD':number(row[8]),'Costo aplicado USD':number(row[15]),
                'Vida útil':number(row[13]),'Origen / estado':row[19],'Fuente':f'09 Activos y arranque!P{r}'})
    sensitivity=[]
    # Locate the native sensitivity matrix by its label rather than a screenshot's position.
    sensitivity_row=assumptions.find('VAN caja con terminal: precio × tasa','J')
    for r in range(sensitivity_row+3,sensitivity_row+6):
        for col in ('L','M','N'):
            sensitivity.append({'Tasa':number(assumptions.cell(f'K{r}')),'Precio x':number(assumptions.cell(f'{col}{sensitivity_row+2}')),'DCF USD':number(assumptions.cell(f'{col}{r}')),'Fuente':f'03 Supuestos!{col}{r}'})
    pending=[]
    for r in range(1,len(evaluation.rows)+1):
        label,state=evaluation.cell(f'G{r}'),evaluation.cell(f'H{r}')
        if label and ('pendiente' in state.casefold()):pending.append({'Condición':label,'Estado publicado':state,'Fuente':f'00 Evaluación!H{r}'})
    provenance=[]
    for label in ['DCF antes de capital nuevo · USD','VAN de caja sin terminal · USD','VAN económico sin terminal · USD','TIR económica sin terminal','Peso del terminal en el VAN']:
        r=evaluation.find(label,'B');provenance.append({'Indicador':label,'Valor publicado':evaluation.cell(f'C{r}'),'Fuente':f'00 Evaluación!C{r}'})
    model=dict(scalars=scalars,scenario=scenario,production=production,status=status,annual=annual,monthly=months,
        opex=pd.DataFrame(opex_records),assets=pd.DataFrame(asset_records),sensitivity=pd.DataFrame(sensitivity),pending=pd.DataFrame(pending),provenance=pd.DataFrame(provenance),raw=raw,formula_errors=pd.DataFrame(source_errors),sheets=sheets)
    model['deal_details'],model['deal_criteria']=parse_deal(deal)
    model['checks']=audit_model(model)
    return model


def column_name(number):
    result=''
    while number:number,remainder=divmod(number-1,26);result=chr(65+remainder)+result
    return result


def audit_model(model):
    s,a=model['scalars'],model['annual'];checks=[]
    def check(name,actual,expected,tolerance,source,unit='USD'):
        difference=actual-expected
        status='Sin dato' if pd.isna(difference) else 'Conciliado' if abs(difference)<=tolerance else 'Revisar'
        checks.append({'Control':name,'Publicado / calculado':actual,'Referencia':expected,'Diferencia':difference,'Tolerancia':tolerance,'Unidad':unit,'Estado':status,'Fuente':source})
    check('Completitud de series financieras',int(a[['sales','cogs','opex','ebitda','fcff','assets','liabilities','equity']].isna().sum().sum()),0,0,'04 Resultados y flujo · 05 Balance y cobros',unit='celdas')
    check('DCF = VAN explícito + terminal descontado',s['dcf'],s['npv_cash']+s['terminal_value']/(1+s['rate'])**10,25,'00 Evaluación C18/C21 · 04 Resultados y flujo O65')
    check('VAN económico descuenta activos en especie',s['npv_economic'],s['npv_cash']-s['assets_in_kind'],5,'00 Evaluación C18:C19 · 09 Activos y arranque E8')
    check('Valor terminal normalizado (Gordon)',s['terminal_value'],s['terminal_cf']/(s['rate']-s['growth']) if s['rate']>s['growth'] else float('nan'),25,'03 Supuestos E10/E12 · 04 Resultados y flujo E111/O65')
    check('DCF coincide con resumen original',s['dcf'],model['sheets']['01 Resumen'].value('Valor patrimonial indicativo'),5,'00 Evaluación C21 · 01 Resumen E33')
    check('Precio de operación = primario + secundario',s['investment_total'],s['primary']+s['secondary'],5,'02 Inversión y socios E7:E9')
    check('Precio previo + primario = precio posterior',s['post_money'],s['pre_money']+s['primary'],5,'02 Inversión y socios E19:E20/E8')
    check('Inversión inicial sin CT histórico duplicado',s['economic_investment'],s['assets_in_kind']+s['preop']+s['spares'],5,'09 Activos y arranque E7:E11')
    classified=model['assets'];fixed=classified[classified['Naturaleza'].eq('Activo fijo')]['Costo aplicado USD'].sum(min_count=1)
    check('Inventario valorizado de activos en especie',s['assets_in_kind'],fixed,30,'09 Activos y arranque P18:P64 · E8')
    check('Caja año 0 = aporte menos uso de caja',s['cash_y0'],s['primary']-s['cash_required'],5,'02 Inversión y socios E31:E33')
    check('Balance: activos = pasivos + patrimonio',float((a['assets']-a['liabilities']-a['equity']).abs().max()),0,5,'05 Balance y cobros filas 63/67/69')
    check('EBITDA = ventas − fabricación − OPEX',float((a['sales']-a['cogs']-a['opex']-a['ebitda']).abs().iloc[1:].max()),0,5,'04 Resultados y flujo filas 8/9/12/14')
    check('OPEX detalle y ajustes = OPEX anual',float((model['opex'].groupby('Año')['USD'].sum().reindex(a['Año'][1:]).to_numpy()-a['opex'].iloc[1:].to_numpy()).__abs__().max()),0,10,'08 Gastos operativos J10:S39 y filas 65–67 · 04 fila 12')
    monthly=model['monthly'][~model['monthly']['Apoyo terminal']].groupby('Año modelo')['Flujo neto USD'].sum()
    check('Caja mensual concilia con flujo anual',float((monthly.reindex(a['Año modelo']).to_numpy()-a['fcff'].to_numpy()).__abs__().max()),0,25,'06 Caja mensual W · 04 Resultados y flujo fila 56')
    return pd.DataFrame(checks)


@st.cache_data(ttl=60,max_entries=8,show_spinner=False)
def load_valuation(refresh_nonce=0,source_url=SOURCE):
    token=f'{refresh_nonce}_{time.time_ns()}'
    def download(item):
        name,gid=item
        response=requests.get(source_url,params={'output':'csv','gid':gid,'_cb':token},headers={'Cache-Control':'no-cache'},timeout=(10,45))
        response.raise_for_status()
        if '<html' in response.text[:300].lower():raise ValueError(f'{name}: la publicación devolvió HTML en lugar de datos CSV.')
        return name,list(csv.reader(StringIO(response.content.decode('utf-8-sig'))))
    with ThreadPoolExecutor(max_workers=5) as pool:raw=dict(pool.map(download,SHEETS.items()))
    model=parse_model(raw)
    model.pop('sheets')  # Retain serializable values, provenance and source tables in cache.
    model['fetched_at']=datetime.now(ZoneInfo('America/Santiago')).strftime('%d-%m-%Y %H:%M:%S')
    return model
