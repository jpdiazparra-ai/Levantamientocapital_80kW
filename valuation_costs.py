"""80 kW cost baseline using the same eligibility and quantity rules as Sub block 1."""
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
import csv
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
from commercial_analysis import commercial_project_rows,commercial_product_scope,commercial_breakdown,commercial_selection_totals,commercial_budget_variation

SOURCE='https://docs.google.com/spreadsheets/d/e/2PACX-1vQOSK1DE0sEuK5Cl-bIahOjtdP6qsBobzqSlekorQCY9gRpwhRDzHYxh9c-Q-mKoQ/pub'
SHEETS={'Plan':'1622224524','Costos':'1070657893'}
COMMERCIAL='Comercial anterior'


def _table(rows):
    header=next((i for i,row in enumerate(rows) if 'ID' in row and 'Hito objetivo' in row),None)
    if header is None:raise ValueError('Faltan ID e Hito objetivo en la fuente de costos.')
    frame=pd.DataFrame(rows[header+1:],columns=rows[header]).loc[:,lambda d:d.columns!='']
    frame=frame.loc[frame.ID.fillna('').str.strip().ne('')].copy()
    if frame.ID.duplicated().any():raise ValueError('Hay IDs duplicados en Plan o Costos; no se pueden agregar costos.')
    return frame.rename(columns={c:'Criterio' for c in frame if c.casefold()=='criterio'})


def cost_report_data(plan_rows,cost_rows,capacity_kw=80):
    # Reuse the app parser, including its missing-value convention for accounting dashes.
    from analysis_option import number
    plan,costs=_table(plan_rows),_table(cost_rows)
    required=['Costo para producto',COMMERCIAL,'Presupuesto vigente']
    if any(c not in costs for c in required):raise ValueError('Costos no contiene clasificación y montos del análisis comercial.')
    plan=plan.drop(columns=['Presupuesto referencia','Presupuesto vigente',COMMERCIAL,'Costo para producto','Registros conciliados'],errors='ignore')
    shared=[c for c in costs if c in plan and c!='ID']
    tasks=plan.merge(costs.drop(columns=shared),on='ID',how='left',validate='one_to_one')
    tasks['_cost_hito_objetivo']=tasks.ID.map(costs.set_index('ID')['Hito objetivo'])
    for c in [COMMERCIAL,'Presupuesto vigente']:
        tasks[c]=tasks[c].map(number)
    selected=commercial_product_scope(commercial_project_rows(tasks,f'Turbina de {capacity_kw} kW'))
    # An eligible Costos ID must never disappear because its Plan row is absent.
    eligible=costs[costs['Costo para producto'].fillna('').str.strip().str.casefold().eq('aplica') & costs['Hito objetivo'].fillna('').str.contains(rf'(?<!\d){capacity_kw}\s*kw\b',case=False,regex=True)]
    missing=set(eligible.ID)-set(selected.ID)
    if missing:raise ValueError(f'Partidas Aplica de {capacity_kw} kW sin correspondencia en Plan: '+', '.join(sorted(missing)))
    if selected.empty:raise ValueError(f'No hay partidas Aplica de {capacity_kw} kW para el desglose de costos.')
    for field in ['Sistema','Paquete / línea']:
        selected[field]=selected[field].fillna('').replace('','Sin clasificar')
    systems=commercial_breakdown(selected,'Sistema')
    lines=[]
    for (system,line),group in selected.groupby(['Sistema','Paquete / línea'],sort=False,dropna=False):
        totals=commercial_selection_totals(group)
        lines.append({'Sistema':system,'Línea':line,'Comercial':totals[COMMERCIAL],'Presupuesto':totals['Presupuesto vigente'],
            'HH':totals['HH'],'HH pendientes':totals['HH pendientes'],'Partidas':len(group),'Informadas':group[COMMERCIAL].notna().sum()})
    lines=pd.DataFrame(lines).sort_values('Comercial',ascending=False,na_position='last',kind='stable')
    totals=commercial_selection_totals(selected);totals.update(Partidas=len(selected),Informadas=int(selected[COMMERCIAL].notna().sum()),Líneas=len(lines),Sistemas=len(systems))
    totals['Variación %']=commercial_budget_variation(pd.DataFrame({COMMERCIAL:[totals[COMMERCIAL]],'Presupuesto vigente':[totals['Presupuesto vigente']]})).iloc[0]
    return {'scope':selected,'systems':systems,'lines':lines.reset_index(drop=True),'totals':totals}


@st.cache_data(ttl=60,max_entries=4,show_spinner=False)
def load_cost_report(revision,capacity_kw=80):
    def fetch(item):
        name,gid=item
        response=requests.get(SOURCE,params={'output':'csv','gid':gid,'_cb':revision},headers={'Cache-Control':'no-cache'},timeout=(8,30))
        response.raise_for_status()
        return name,list(csv.reader(StringIO(response.content.decode('utf-8-sig'))))
    with ThreadPoolExecutor(max_workers=2) as pool:raw=dict(pool.map(fetch,SHEETS.items()))
    result=cost_report_data(raw['Plan'],raw['Costos'],capacity_kw=capacity_kw)
    result['fetched_at']=datetime.now(ZoneInfo('America/Santiago')).strftime('%d-%m-%Y %H:%M:%S')
    return result
