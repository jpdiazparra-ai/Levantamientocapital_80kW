"""Selectable capital systems and traceable activity/cash drill-down."""
import hashlib
import html
from pathlib import Path

import pandas as pd
import streamlit as st
from display_currency import amount, currency_code, currency_export

MONEY = ['Caja pendiente de cubrir','Presupuesto referencia','Presupuesto vigente','Caja por validar','Caja validada']


def system_details(tasks, cash, categories, selected):
    """Keep activity budgets once per ID; aggregate cash separately before joining."""
    scope=tasks.loc[categories.eq(selected)].copy()
    payments=cash.loc[cash['ID actividad'].isin(scope['ID'])].copy()
    scope=scope.loc[scope['ID'].isin(payments['ID actividad'])].copy()
    balances=payments.groupby('ID actividad')[['Referencia por validar CLP','Pendiente validado CLP']].sum(min_count=1)
    balances=balances.rename(columns={'Referencia por validar CLP':'Caja por validar','Pendiente validado CLP':'Caja validada'})
    fields=['ID','Proyecto','Hito objetivo','Paquete / línea','Actividad / entregable','Responsable persona',
        'Presupuesto referencia','Presupuesto vigente','Base aprobada','Registros conciliados','Estado por avance',
        'Evidencia / aceptación','Sustento / observaciones','Acción requerida']
    detail=scope.reindex(columns=fields).merge(balances,left_on='ID',right_index=True,how='left',validate='one_to_one')
    for source,col in [('Plan','_source_plan_row'),('Costos','_source_costs_row')]:
        rows=scope.set_index('ID')[col] if col in scope else pd.Series(dtype=float)
        detail['Referencia '+source]=detail['ID'].map(lambda value: f'{source} · fila {int(rows[value])} · ID {value}'
            if value in rows and pd.notna(rows[value]) else f'{source} · ID {value}')
    detail['Caja pendiente de cubrir']=detail[['Caja validada','Caja por validar']].sum(axis=1,min_count=1)
    detail['Datos de referencia']=detail['Presupuesto referencia'].map(lambda value:'Sin informar' if pd.isna(value) else 'Informado')
    detail=detail.sort_values('Caja pendiente de cubrir',ascending=False,na_position='last').reset_index(drop=True)
    return detail,payments


def package_details(detail):
    """Aggregate each system's published packages, keeping source IDs auditable."""
    grouped=detail.copy()
    grouped['Paquete / línea']=grouped['Paquete / línea'].fillna('').astype(str).str.strip().replace('','Sin paquete / línea informado')
    def joined(values):
        return ' · '.join(dict.fromkeys(str(value).strip() for value in values if pd.notna(value) and str(value).strip())) or 'Sin informar'
    rows=[]
    for package,part in grouped.groupby('Paquete / línea',sort=False):
        record={'Paquete / línea':package,**{field:part[field].sum(min_count=1) for field in MONEY},
            'Registros de origen':len(part),'Referencias informadas':int(part['Presupuesto referencia'].notna().sum()),
            'IDs de origen':joined(part['ID'])}
        record['Cobertura %']=record['Referencias informadas']/len(part)*100
        for field in ['Proyecto','Hito objetivo','Responsable persona','Base aprobada','Registros conciliados',
                'Estado por avance','Referencia Plan','Referencia Costos']:
            record[field]=joined(part[field])
        rows.append(record)
    return pd.DataFrame(rows).sort_values('Caja pendiente de cubrir',ascending=False,na_position='last').reset_index(drop=True)


def table_config():
    return {**{field:st.column_config.NumberColumn(field+' · '+currency_code(),width='medium') for field in MONEY},
        'ID':st.column_config.TextColumn('ID actividad',width='small'),
        'Paquete / línea':st.column_config.TextColumn('Paquete / línea',width='large'),
        'IDs de origen':st.column_config.TextColumn('IDs de origen',width='medium',help='Registros que componen el total de esta línea o paquete.'),
        'Participación %':st.column_config.ProgressColumn('Peso en la selección',min_value=0,max_value=100,format='%.1f%%',width='medium'),
        'Cobertura %':st.column_config.ProgressColumn('Referencias informadas',min_value=0,max_value=100,format='%.0f%%',width='medium')}


def money_style(frame):
    return frame.style.format({field:amount for field in MONEY if field in frame},na_rep='Sin informar').set_properties(
        **{'font-size':'12px','color':'#17334A'})


def render_system_detail(summary,tasks,cash,categories,source,sheets,selection):
    st.html('<style>'+Path(__file__).with_name('assets').joinpath('capital_detail.css').read_text()+'</style>')
    groups=summary['Sistema'].tolist()
    table=summary[['Sistema','Caja pendiente de cubrir','Caja validada','Caja por validar','Participación %']].copy()
    table['Registros de caja']=summary['Actividades de caja'].to_numpy()
    st.html('<div class="capital-detail-heading"><div><span>EXPLORADOR DE CAPITAL</span><h4>Sistemas y trazabilidad</h4>'
        '<p>Selecciona una fila para desplegar las líneas o paquetes y sus saldos que componen el sistema.</p></div>'
        '<b>'+html.escape(selection)+' · '+currency_code()+'</b></div>')
    identity=repr((selection,sorted(tasks['ID'].astype(str)),groups)).encode()
    key='option4_capital_system_table_'+hashlib.sha1(identity).hexdigest()[:12]
    selected_key='option4_capital_system_selected_group'
    def remember_system():
        rows=st.session_state[key]['selection']['rows']
        st.session_state[selected_key]=groups[rows[0]] if rows and rows[0]<len(groups) else None
    event=st.dataframe(money_style(table),hide_index=True,use_container_width=True,
        height=min(520,40+40*len(table)),row_height=40,column_config=table_config(),
        key=key,on_select=remember_system,selection_mode='single-row')
    rows=event['selection']['rows']
    if selected_key not in st.session_state and rows:
        st.session_state[selected_key]=groups[rows[0]]
    selected=st.session_state.get(selected_key)
    if selected not in groups:
        st.html('<div class="capital-detail-empty">Selecciona un sistema en la tabla para consultar sus líneas o paquetes y referencias de origen.</div>')
        return
    detail,payments=system_details(tasks,cash,categories,selected)
    if detail.empty:
        st.info('Este sistema no tiene saldos incluidos en la caja pendiente de cubrir.')
        return
    packages=package_details(detail)
    row=summary.loc[summary['Sistema'].eq(selected)].iloc[0]
    with st.container(border=True,key='capital_system_drilldown'):
        st.html('<div class="capital-detail-heading"><div><span>DESGLOSE DEL SISTEMA</span><h4>'+html.escape(selected)+'</h4></div>'
            '<b>'+str(len(packages))+' líneas / paquetes</b></div>')
        cards=[('Caja pendiente de cubrir',amount(row['Caja pendiente de cubrir'])),
            ('Caja validada',amount(row['Caja validada'])),('Caja por validar',amount(row['Caja por validar'])),
            ('Líneas / paquetes',str(len(packages)))]
        st.html('<div class="capital-detail-kpis">'+''.join('<article><span>'+html.escape(label)+'</span><strong>'+html.escape(value)+'</strong></article>' for label,value in cards)+'</div>')
        st.markdown('##### Líneas y paquetes del sistema')
        st.caption('Una fila por paquete o línea con registros incluidos en caja pendiente. Total pendiente = caja validada + caja por validar, igual al gráfico del sistema. Los pagos ya realizados quedan fuera; los importes faltantes conservan su estado sin informar.')
        order=['Paquete / línea','Caja pendiente de cubrir','Caja validada','Caja por validar',
            'Registros de origen','Proyecto','Hito objetivo','Responsable persona',
            'Base aprobada','Registros conciliados','Estado por avance','IDs de origen','Referencia Plan','Referencia Costos']
        st.dataframe(money_style(packages[order]),hide_index=True,use_container_width=True,
            column_config=table_config(),row_height=40,height=min(500,40+40*len(packages)))
        st.markdown('##### Registros de caja del sistema')
        st.caption('Solo los registros incluidos en el análisis de caja. Su ausencia no acredita saldo cero ni pago completo.')
        if payments.empty:st.info('Este sistema no tiene registros de caja incluidos en la selección.')
        else:
            payments=payments.copy()
            payments['Paquete / línea']=payments['ID actividad'].map(detail.set_index('ID')['Paquete / línea']).fillna('').astype(str).str.strip().replace('','Sin paquete / línea informado')
            display=payments.reindex(columns=['Paquete / línea','ID actividad','Fecha FC / desembolso',
                'Pendiente validado CLP','Referencia por validar CLP','Validación del saldo','Estado de pago',
                'Respaldo / observaciones','Alerta caja']).rename(columns={
                    'Pendiente validado CLP':'Caja validada','Referencia por validar CLP':'Caja por validar'})
            display['Caja pendiente de cubrir']=display[['Caja validada','Caja por validar']].sum(axis=1,min_count=1)
            display=display[['Paquete / línea','Caja pendiente de cubrir','Caja validada','Caja por validar',*[c for c in display if c not in ['Paquete / línea','Caja pendiente de cubrir','Caja validada','Caja por validar']]]]
            st.dataframe(money_style(display),hide_index=True,use_container_width=True,row_height=40,
                column_config=table_config(),height=min(400,40+40*len(display)))
        st.html('<div class="capital-detail-source"><b>Ruta de trazabilidad</b><span>Sistema → Paquete / línea → IDs de origen → Plan / Costos</span></div>')
        st.caption('Actividades, responsables y evidencia: Plan. Importes, aprobación, conciliación y saldos: Costos. Caja validada y por validar mantienen sus estados; una referencia informada no implica aprobación.')
        meta=tasks.attrs
        if meta.get('document_cutoff') or meta.get('consulted_at'):
            st.caption('Corte: '+str(meta.get('document_cutoff','Sin informar'))+' · Consulta: '+str(meta.get('consulted_at','Sin informar'))+' · Santiago')
        left,right=st.columns(2)
        with left:
            st.link_button('Consultar Plan',source+'html#gid='+sheets['Plan'])
            st.download_button('Descargar líneas y paquetes',currency_export(packages[order]).to_csv(index=False).encode('utf-8-sig'),
                file_name='capital_sistema_lineas_paquetes.csv',mime='text/csv',key='option4_capital_system_activities_csv')
        with right:
            st.link_button('Consultar Costos',source+'html#gid='+sheets['Costos'])
            st.download_button('Descargar registros de caja',currency_export(payments.drop(columns=[c for c in payments if c.startswith('_')])).to_csv(index=False).encode('utf-8-sig'),
                file_name='capital_sistema_caja.csv',mime='text/csv',key='option4_capital_system_cash_csv')
