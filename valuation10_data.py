"""Independent, read-only financial model for Block 4 / Sub block 4 (10 kW)."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from io import StringIO
from zoneinfo import ZoneInfo
import csv
import math
import re
import time

import pandas as pd
import requests
import streamlit as st

from valuation_data import Sheet, column_name, number, parse_deal
from valuation_finance import complete_sum, discounted_flows

SOURCE = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vR8FDvZc18fkzHLW2Pcy5Z9WMRE_JWfdN9RfXDgojcr87S5jGYYvtC-l5302cwZRw/pub'
SHEETS = {
    '00 Evaluación': '2040412809', '00 Datos de entrada': '289150328',
    '02 Inversión y socios': '1435795527', '03 Supuestos': '1910601062',
    '04 Resultados y flujo': '1803842147', '05 Balance y cobros': '1788932491',
    '06 Caja mensual': '339796947', '07 Ventas y producción': '466170804',
    '08 Gastos operativos': '1440050881', '09 Activos y arranque': '1921474156',
    '10 Controles': '32730923',
}


def parse_evaluation10(rows):
    """Keep the executive page's published figures and its own five-year horizon."""
    sheet = Sheet('00 Evaluación', rows)
    def fields(spec, label_col='B', value_col='C'):
        return pd.DataFrame([{'Concepto': label, 'Valor': sheet.value(label,value_col,label_col),
            'Unidad': unit, 'Fuente': sheet.ref(label,value_col,label_col)} for label,unit in spec])
    results=fields([(label,unit) for label,unit in [
        ('Ventas netas · año 1','USD'),('EBITDA · año 1','USD'),('Margen EBITDA · año 1','%'),
        ('Flujo libre operativo · año 1','USD'),('Anticipos por entregar al cierre · año 1','USD'),
        ('Aumento de anticipos / flujo libre · año 1','%'),('VAN operativo sin terminal','USD'),
        ('VAN económico sin terminal','USD'),('TIR económica sin terminal','%'),
        ('Recuperación de caja descontada','años'),('DCF patrimonial previo al aporte','USD'),
        ('Valor terminal / valor operativo','%')]])
    funding=fields([(label,'%' if label=='Participación final del inversionista' else 'USD') for label in [
        'Participación final del inversionista','Consumo neto de caja · año 0','Caja libre al cierre · año 0',
        'Caja objetivo al cierre · año 0','Brecha para caja objetivo · año 0','Puente teórico máximo requerido',
        'Valor previo implícito negociado','Valor posterior implícito negociado']], 'G','H')
    primary_row=sheet.find('Capital primario / pago secundario','G')
    funding=pd.concat([pd.DataFrame([{'Concepto':label,'Valor':number(sheet.cell(f'{col}{primary_row}')),
        'Unidad':'USD','Fuente':f'00 Evaluación!{col}{primary_row}'} for label,col in [('Capital primario','H'),('Pago secundario','I')]]),funding],ignore_index=True)
    unit=fields([(label,'%' if label=='Margen bruto' else 'equipos' if label=='Equipos entregados' else 'USD/equipo') for label in [
        'Equipos entregados','Precio de venta','Fabricación media por equipo entregado','Margen bruto por equipo',
        'Margen bruto','Costo de entrega y flota por equipo','Contribución antes de estructura operativa']])
    section_row=sheet.find('04   PROYECCIÓN DE LOS PRIMEROS CINCO AÑOS','B')
    header=section_row+1
    year_cols=[(column_name(i+1),value) for i,value in enumerate(rows[header-1]) if re.fullmatch(r'20\d{2}',value)]
    if len(year_cols)!=5:raise ValueError('00 Evaluación: no se identificaron los cinco años del resumen.')
    mapping={'demand_10':'Demanda proyectada · equipos','capacity':'Capacidad propia · equipos','units_10':'Entregas · equipos',
        'external':'Equipos de fabricación externa','unserved':'Demanda sin atender · equipos','sales':'Ventas netas · USD',
        'ebitda':'EBITDA · USD','ebitda_margin':'Margen EBITDA','fcff':'Flujo libre operativo · USD','capex':'CAPEX pagado por FW · USD',
        'advances':'Anticipos pendientes · USD','cash_free':'Caja libre al cierre · USD'}
    projection=pd.DataFrame({'Año':[year for _,year in year_cols]})
    for field,label in mapping.items():
        row=sheet.find(label,'B')
        projection[field]=[number(sheet.cell(f'{col}{row}')) for col,_ in year_cols]
    conditions=pd.DataFrame([{'Condición':label,'Estado publicado':sheet.value(label,'H','G',False),
        'Fuente':sheet.ref(label,'H','G')} for label in ['Fabricación integral','Capacidad y costo de terceros','Anticipos contractuales']])
    return dict(results=results,funding=funding,unit=unit,projection=projection,conditions=conditions,
        contribution_ratio=sheet.value('Aumento de anticipos / flujo libre · año 1','C','B'),
        recovery_years=sheet.value('Recuperación de caja descontada','C','B'),
        funding_date=sheet.value('Fecha del aporte a FW','H','G',False),
        terminal_method=sheet.value('Valor terminal','H','G',False))


def parse_components10(sheet):
    """Read the published detail by its table structure, without fixed component names."""
    columns=['Componente','USD base / equipo','Origen','Fuente']
    normalize=lambda value:' '.join(str(value).split()).casefold()
    header=next((i for i,row in enumerate(sheet.rows,1)
                 if len(row)>2 and normalize(row[2])=='componente / criterio'),None)
    if header is None:return pd.DataFrame(columns=columns)
    headings=sheet.rows[header-1]
    value_col=next((column_name(i+1) for i,value in enumerate(headings)
                    if 'usd' in normalize(value) and 'equipo' in normalize(value)),None)
    origin_col=next((column_name(i+1) for i,value in enumerate(headings) if normalize(value)=='origen'),None)
    if value_col is None:return pd.DataFrame(columns=columns)
    records=[]
    for row in range(header+1,len(sheet.rows)+1):
        label=sheet.cell(f'C{row}').strip()
        if normalize(label)=='costo base presupuestado':break
        value=sheet.cell(f'{value_col}{row}')
        if label and value.strip():
            records.append({'Componente':label,'USD base / equipo':number(value),
                'Origen':sheet.cell(f'{origin_col}{row}') if origin_col else '',
                'Fuente':f'{sheet.name}!{value_col}{row}'})
    # A published unresolved balance is retained as a reference, never invented.
    balance=next((i for i,row in enumerate(sheet.rows,1) if len(row)>2 and
                  normalize(row[2])=='saldo de costo base por desglosar'),None)
    if balance is not None:
        records.append({'Componente':sheet.cell(f'C{balance}').strip(),
            'USD base / equipo':number(sheet.cell(f'{value_col}{balance}')),
            'Origen':sheet.cell(f'{origin_col}{balance}') if origin_col else '',
            'Fuente':f'{sheet.name}!{value_col}{balance}'})
    return pd.DataFrame(records,columns=columns)


def parse_model10(raw):
    missing = set(SHEETS) - set(raw)
    if missing:
        raise ValueError('Faltan pestañas del modelo 10 kW: ' + ', '.join(sorted(missing)))
    sheets = {name: Sheet(name, raw[name]) for name in SHEETS}
    ev, inputs, deal, assumptions, results, balance, monthly, operations, opex, assets, controls = sheets.values()
    scalar_spec = {
        'dcf': (ev, 'DCF patrimonial previo al aporte', 'C', 'B'),
        'npv_cash': (ev, 'VAN operativo sin terminal', 'C', 'B'),
        'npv_economic': (ev, 'VAN económico sin terminal', 'C', 'B'),
        'irr_economic': (ev, 'TIR económica sin terminal', 'C', 'B'),
        'terminal_weight': (ev, 'Valor terminal / valor operativo', 'C', 'B'),
        'sales_y1': (ev, 'Ventas netas · año 1', 'C', 'B'),
        'ebitda_y1': (ev, 'EBITDA · año 1', 'C', 'B'),
        'ebitda_margin_y1': (ev, 'Margen EBITDA · año 1', 'C', 'B'),
        'fcff_y1': (ev, 'Flujo libre operativo · año 1', 'C', 'B'),
        'cash_y0': (ev, 'Caja libre al cierre · año 0', 'H', 'G'),
        'bridge': (ev, 'Puente teórico máximo requerido', 'H', 'G'),
        'advances_y1': (ev, 'Anticipos por entregar al cierre · año 1', 'C', 'B'),
        'rate': (inputs, 'Tasa de descuento aplicada ↗', 'C', 'B'),
        'growth': (inputs, 'Crecimiento terminal', 'C', 'B'),
        'model_fx': (inputs, 'Tipo de cambio', 'C', 'B'),
        'first_year': (inputs, 'Primer año de operación', 'C', 'B'),
        'advance_rate': (inputs, 'Anticipo de clientes', 'C', 'B'),
        'advance_days': (inputs, 'Días entre anticipo y entrega', 'C', 'B'),
        'investment_total': (deal, 'Pago total del inversionista', 'E', 'C'),
        'primary': (deal, 'Aporte de capital a FW', 'E', 'C'),
        'secondary': (deal, 'Compra de acciones a fundadores', 'E', 'C'),
        'investor_share': (deal, 'Participación final del inversionista', 'E', 'C'),
        'primary_share': (deal, 'Participación por emisión de acciones nuevas', 'E', 'C'),
        'secondary_share': (deal, 'Participación adquirida a fundadores', 'E', 'C'),
        'founder_share': (deal, 'Participación final accionistas actuales', 'E', 'C'),
        'pre_money': (deal, 'Valor patrimonial previo implícito', 'E', 'C'),
        'post_money': (deal, 'Valor patrimonial post inversión implícito', 'E', 'C'),
        'cash_target': (deal, 'Caja objetivo después del arranque', 'E', 'C'),
        'cash_required': (deal, 'Consumo neto de caja en año 0', 'E', 'C'),
        'target_funding': (deal, 'Financiamiento total para lograr la caja objetivo', 'E', 'C'),
        'cash_gap': (deal, 'Brecha de caja objetivo tras aporte y puente', 'E', 'C'),
        'economic_investment': (assets, 'Inversión económica de arranque', 'E', 'C'),
        'assets_in_kind': (assets, 'Activos fijos iniciales', 'E', 'C'),
        'preop': (assets, 'Desarrollo y gastos preoperacionales', 'E', 'C'),
        'spares': (assets, 'Inventario inicial total', 'E', 'C'),
        'production_stock': (assets, 'Stock inicial de producción', 'E', 'C'),
        'plant_spares': (assets, 'Reserva inicial de repuestos de planta', 'E', 'C'),
        'historical_wc': (assets, 'Capital de trabajo histórico (solo referencia)', 'E', 'C'),
        'terminal_cf': (results, 'Flujo terminal normalizado', 'E', 'C'),
        'terminal_value': (results, 'Valor terminal del proyecto', 'O', 'C'),
    }
    scalars = {key: sheet.value(label, value_col, label_col) for key, (sheet, label, value_col, label_col) in scalar_spec.items()}
    for key in ('dcf', 'npv_cash', 'npv_economic', 'rate', 'growth', 'model_fx', 'first_year', 'primary', 'secondary'):
        if not math.isfinite(scalars[key]):
            raise ValueError('Falta un valor esencial del caso 10 kW: ' + key)
    if scalars['model_fx'] <= 0 or scalars['first_year'] != int(scalars['first_year']):
        raise ValueError('Tipo de cambio o calendario inválido en el modelo 10 kW.')
    scalars['valuation_date'] = assumptions.value('Fecha base del DCF', numeric=False)
    provenance = [{'Indicador': label, 'Valor publicado': sheet.cell(f'{value_col}{sheet.find(label, label_col)}'),
                   'Fuente': sheet.ref(label, value_col, label_col)} for sheet, label, value_col, label_col in scalar_spec.values()]
    annual = pd.DataFrame({'Año': ['Año 0', *[str(int(scalars['first_year']) + i) for i in range(10)]], 'Año modelo': range(11)})
    def series(sheet, mapping):
        header = sheet.find('Partida')
        if [sheet.cell(f'{column_name(5+i)}{header}') for i in range(11)] != annual['Año'].tolist():
            raise ValueError(sheet.name + ': el calendario no coincide con Año 0 y los diez años de operación.')
        for key, label in mapping.items():
            row = sheet.find(label)
            annual[key] = [number(sheet.cell(f'{column_name(5+i)}{row}')) for i in range(11)]
    series(results, {'sales': 'Ingresos consolidados', 'cogs': 'Costo de ventas', 'opex': 'OPEX total detallado',
        'ebitda': 'EBITDA', 'ebitda_margin': 'Margen EBITDA', 'ebit': 'EBIT', 'net_income': 'Utilidad neta',
        'tax': 'Impuesto estimado', 'da': 'Depreciación total', 'ct_change': 'Variación de capital de trabajo',
        'fcff': 'Flujo libre operativo sin deuda', 'pv_fcff': 'Flujo libre descontado',
        'economic_cf': 'Flujo económico con activos aportados', 'capex': 'CAPEX pagado por FW',
        'advance_change': 'Aumento / disminución de anticipos de clientes', 'vat_change': 'Variación IVA neto (activo menos pasivo)'})
    series(balance, {'cash_free': 'Caja libre tras aporte y puente teórico', 'cash_total': 'Caja total proyectada',
        'cash_unfunded': 'Caja acumulada antes de aportes', 'advances': 'Saldo final por equipos pendientes de entrega',
        'assets': 'Total activos', 'liabilities': 'Total pasivos', 'equity': 'Patrimonio al cierre (capital proyectado)',
        'collections': 'Total de dinero recibido de clientes durante el año'})
    series(operations, {'units_10': 'Equipos entregados', 'demand_10': 'Demanda proyectada', 'capacity': 'Capacidad propia',
        'external': 'Equipos de fabricación externa', 'unserved': 'Demanda sin atender', 'cost_10': 'Costo total de ventas',
        'sales_10': 'Ventas netas', 'unit_cost_10': 'Costo unitario base aplicado', 'external_cost_10': 'Sobrecosto de fabricación externa'})
    series(opex, {'opex_common': 'Estructura operativa', 'opex_10': 'Costos por entrega y flota'})
    series(assets, {'assets_book': 'Valor contable de activos', 'asset_da': 'Depreciación total', 'capex_later': 'CAPEX posterior total'})
    annual['units_total'] = annual['units_10']
    # Retain blank columns when mapping the monthly CSV: column H is reserved.
    header = monthly.find('Mes')
    columns = monthly.rows[header-1]
    records = []
    for r in monthly.rows[header:]:
        if len(r) > 4 and r[3].strip().isdigit() and r[4].strip().isdigit():
            record = {name: value if name == 'Mes' else number(value) for name, value in zip(columns, r) if name}
            record['Fecha'] = pd.Timestamp(year=int(scalars['first_year'])-1+int(r[3]), month=int(r[4]), day=1)
            records.append(record)
    months = pd.DataFrame(records).rename(columns={'Caja con aporte, sin puente': 'Caja sin puente',
        'Caja libre con puente teórico': 'Caja tras aporte y puente', 'OPEX USD por mes': 'OPEX USD'})
    required_months = ['Flujo neto USD', 'Capital inversionista', 'Caja sin puente', 'Caja tras aporte y puente']
    if months.empty or any(field not in months for field in required_months):
        raise ValueError('Caja mensual 10 kW: faltan flujos o saldos esenciales.')
    months['Apoyo terminal'] = months['Año modelo'].gt(10)
    opex_records = []
    for r, row in enumerate(opex.rows, 1):
        if len(row) > 20 and re.fullmatch(r'OP-\d+', row[2]):
            for i, year in enumerate(annual['Año'][1:]):
                opex_records.append({'ID': row[2], 'Área': row[3], 'Concepto': row[4], 'Destino': row[5], 'Año': year,
                    'USD': number(row[9+i])/scalars['model_fx'], 'Estado': row[20], 'Fuente': f'{opex.name}!{column_name(10+i)}{r}'})
    for label in ('Regalía / licencia (USD)', 'Reposición de repuestos de planta (USD)', 'Carga empleador adicional (USD)'):
        r = opex.find(label)
        for i, year in enumerate(annual['Año'][1:]):
            opex_records.append({'ID': f'AJ-{r}', 'Área': 'Ajustes publicados', 'Concepto': label, 'Destino': 'Estructura',
                'Año': year, 'USD': number(opex.cell(f'{column_name(10+i)}{r}')), 'Estado': 'Supuesto del modelo',
                'Fuente': f'{opex.name}!{column_name(10+i)}{r}'})
    asset_records = []
    for r, row in enumerate(assets.rows, 1):
        if len(row) > 19 and re.fullmatch(r'(?:CAP|INV)-\d+', row[2]):
            asset_records.append(dict(zip(['ID', 'Área', 'Activo / alcance', 'Naturaleza', 'Asignación'], row[2:7])) |
                {'Cantidad': number(row[7]), 'Costo aplicado USD': number(row[15]), 'Vida útil': number(row[13]),
                 'Origen / estado': row[19], 'Fuente': f'{assets.name}!P{r}'})
    native_checks = []
    for r, row in enumerate(controls.rows, 1):
        if len(row) > 7 and row[7] in ('OK', 'Pendiente', 'Sin déficit', 'n.a.', 'Financiar', 'Revisar'):
            native_checks.append({'Control': row[2], 'Actual': number(row[3]), 'Esperado': number(row[4]),
                'Diferencia': number(row[5]), 'Tolerancia': number(row[6]), 'Estado publicado': row[7],
                'Ubicación': row[8] if len(row)>8 else '', 'Fuente': f'{controls.name}!C{r}:J{r}'})
    native_checks = pd.DataFrame(native_checks)
    pending = native_checks[~native_checks['Estado publicado'].isin(['OK', 'Sin déficit', 'n.a.'])].copy()
    sensitivity = []
    r = assumptions.find('Valor patrimonial indicativo antes del aporte (USD) · precio × tasa', 'J')
    for row in range(r+3, r+6):
        for col in ('L', 'M', 'N'):
            sensitivity.append({'Tasa': number(assumptions.cell(f'K{row}')), 'Precio x': number(assumptions.cell(f'{col}{r+2}')),
                'DCF USD': number(assumptions.cell(f'{col}{row}')), 'Fuente': f'{assumptions.name}!{col}{row}'})
    components = parse_components10(operations)
    development = []
    first = assets.find('Fase')
    for r in range(first+1, assets.find('Desarrollo base incluido en CAP-001 y CAP-002')):
        if assets.cell(f'C{r}'):
            development.append({'Fase': assets.cell(f'C{r}'), 'Responsable': assets.cell(f'D{r}'),
                'Hito y entregable': assets.cell(f'E{r}'), 'USD base': number(assets.cell(f'I{r}')),
                'Alcance': assets.cell(f'J{r}'), 'Fuente': f'{assets.name}!I{r}'})
    model = dict(scalars=scalars, annual=annual, monthly=months, opex=pd.DataFrame(opex_records), assets=pd.DataFrame(asset_records),
        native_checks=native_checks, pending=pending, sensitivity=pd.DataFrame(sensitivity), provenance=pd.DataFrame(provenance),
        components=components, development=pd.DataFrame(development), raw=raw, products=(10,),
        scenario=inputs.value('Escenario', 'C', 'B', False), production=inputs.value('Modo de producción', 'C', 'B', False),
        status=deal.value('Estado de la operación', numeric=False), source_url=SOURCE,
        formula_errors=pd.DataFrame([{'Pestaña': name, 'Celda': f'{column_name(j)}{i}', 'Error': value}
            for name, rows in raw.items() for i, row in enumerate(rows, 1) for j, value in enumerate(row, 1)
            if re.match(r'^#(?:REF!|DIV/0!|VALUE!|NAME\?|N/A|NUM!|ERROR!)', value)]))
    model['evaluation'] = parse_evaluation10(raw['00 Evaluación'])
    model['deal_details'], model['deal_criteria'] = parse_deal(deal)
    # Normalize labels only in the presentation table; keep original text and references auditable.
    model['deal_details']['Concepto'] = model['deal_details']['Concepto'].replace({
        'Consumo neto de caja en año 0': 'Uso de caja de arranque, neto de anticipos',
        'Financiamiento total para lograr la caja objetivo': 'Aporte total para conservar caja objetivo',
        'Brecha de caja objetivo tras aporte y puente': 'Aporte adicional para caja objetivo',
        'DCF patrimonial antes del aporte': 'Valor DCF antes de fondos nuevos'})
    model['checks'] = audit_model10(model)
    return model


def audit_model10(model):
    s, a = model['scalars'], model['annual']
    checks = []
    def check(name, actual, expected, tolerance, source, unit='USD'):
        difference = actual-expected
        checks.append({'Control': name, 'Publicado / calculado': actual, 'Referencia': expected, 'Diferencia': difference,
            'Tolerancia': tolerance, 'Unidad': unit, 'Estado': 'Sin dato' if pd.isna(difference) else 'Conciliado' if abs(difference)<=tolerance else 'Revisar', 'Fuente': source})
    def deviation(values):
        return values.abs().max() if values.notna().all() else float('nan')
    required=['sales','cogs','opex','ebitda','fcff','economic_cf','assets','liabilities','equity','units_10','demand_10','capacity']
    check('Completitud de series', int(a[required].isna().sum().sum()), 0, 0, '04–09', 'celdas')
    check('VAN explícito reconstruido', complete_sum(discounted_flows(a['fcff'], s['rate'])), s['npv_cash'], 10, '04 flujo libre · 00 VAN operativo')
    check('DCF = VAN explícito + VP terminal', s['dcf'], s['npv_cash']+s['terminal_value']/(1+s['rate'])**10, 25, '00 Evaluación · 04 O65')
    check('VAN económico incluye activos', s['npv_economic'], s['npv_cash']-s['assets_in_kind'], 5, '00 Evaluación · 09 E8')
    check('Terminal normalizado Gordon', s['terminal_value'], s['terminal_cf']/(s['rate']-s['growth']) if s['rate']>s['growth'] else float('nan'), 25, '03 tasa/g · 04 E111/O65')
    check('Inversión primaria y secundaria', s['investment_total'], s['primary']+s['secondary'], 5, '02 E7:E9')
    check('Precio previo + primario = posterior', s['post_money'], s['pre_money']+s['primary'], 5, '02 E19:E20/E8')
    check('Participaciones suman 100 %', s['primary_share']+s['secondary_share']+s['founder_share'], 1, .001, '02 E21:E23', 'proporción')
    check('Inversión económica de arranque', s['economic_investment'], s['assets_in_kind']+s['preop']+s['spares'], 5, '09 E7:E10')
    check('Inventario inicial separado', s['spares'], s['production_stock']+s['plant_spares'], 5, '09 E10/E12:E13')
    fixed = model['assets'].loc[lambda f:f['Naturaleza'].eq('Activo fijo'), 'Costo aplicado USD']
    check('Activos en especie conciliados', complete_sum(fixed), s['assets_in_kind'], 30, '09 registro P · E8')
    check('Balance anual', deviation(a['assets']-a['liabilities']-a['equity']), 0, 5, '05 activos/pasivos/patrimonio')
    check('EBITDA operativo', deviation((a['sales']-a['cogs']-a['opex']-a['ebitda']).iloc[1:]), 0, 5, '04 ventas/costos/OPEX/EBITDA')
    check('Fabricación 10 kW = costo consolidado', deviation(a['cost_10']-a['cogs']), 0, 5, '07 costo total · 04 costo de ventas')
    detail = model['opex'].groupby('Año')['USD'].agg(complete_sum).reindex(a['Año'][1:]).reset_index(drop=True)
    check('OPEX detalle y ajustes', deviation(detail-a['opex'].iloc[1:].reset_index(drop=True)), 0, 10, '08 J:S y ajustes · 04 OPEX')
    check('OPEX estructura + entrega/flota', deviation(a['opex_common']+a['opex_10']-a['opex']), 0, 5, '08 filas 52:54')
    months = model['monthly'].loc[lambda f:~f['Apoyo terminal']]
    totals = months.groupby('Año modelo')['Flujo neto USD'].agg(complete_sum).reindex(range(11)).reset_index(drop=True)
    check('Flujo mensual = anual', deviation(totals-a['fcff']), 0, 25, '06 flujo neto · 04 flujo libre')
    check('Aporte primario recibido una vez', complete_sum(months['Capital inversionista']), s['primary'], 5, '06 capital inversionista · 02 E8')
    check('Brecha de reserva al cierre', s['cash_gap'], max(s['cash_target']-s['cash_y0'], 0), 5, '02 E14/E33/E36')
    return pd.DataFrame(checks)


@st.cache_data(ttl=60, max_entries=8, show_spinner=False)
def load_valuation10(refresh_nonce=0, source_url=SOURCE, sheets=tuple(SHEETS.items())):
    token = f'{refresh_nonce}_{time.time_ns()}'
    def download(item):
        name, gid = item
        response = requests.get(source_url, params={'output': 'csv', 'gid': gid, '_cb': token}, headers={'Cache-Control': 'no-cache'}, timeout=(10,45))
        response.raise_for_status()
        if '<html' in response.text[:300].lower():
            raise ValueError(name + ': se recibió HTML en lugar de CSV.')
        return name, list(csv.reader(StringIO(response.content.decode('utf-8-sig'))))
    with ThreadPoolExecutor(max_workers=5) as pool:
        raw = dict(pool.map(download, sheets))
    model = parse_model10(raw)
    model['source_url'] = source_url
    model['fetched_at'] = datetime.now(ZoneInfo('America/Santiago')).strftime('%d-%m-%Y %H:%M:%S')
    return model
