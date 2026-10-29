"""Readable capital comparisons, monthly cash and responsible-entity allocations."""
import html
import textwrap
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

NAVY = '#244A6C'
VALID = '#0F766E'
PENDING = '#B7791F'
MONTHS = ['ene','feb','mar','abr','may','jun','jul','ago','sept','oct','nov','dic']


def amount(value, compact=False):
    if pd.isna(value):
        return 'Sin informar'
    if compact and abs(value) >= 1_000_000:
        return '$' + f'{value/1e6:,.1f}'.replace(',', 'X').replace('.', ',').replace('X', '.') + ' MM'
    return '$' + f'{value:,.0f}'.replace(',', '.')


def wrap(value):
    return '<br>'.join(html.escape(line) for line in textwrap.wrap(str(value), width=29))


def figure_style(fig, height=320, limit=None, horizontal=True):
    fig.update_layout(height=height, font=dict(family='Arial, sans-serif', size=12, color='#475569'),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='#FFFFFF', showlegend=False,
        margin=dict(l=12,r=120 if horizontal else 25,t=25,b=50), bargap=.45,
        hoverlabel=dict(bgcolor='#FFFFFF',bordercolor='#D8E3EB',align='left',font=dict(size=12,color='#0F2435')),
        hovermode='closest', uniformtext=dict(minsize=10,mode='show'))
    fig.update_xaxes(automargin=True, zeroline=False, showline=False,
        gridcolor='#EDF2F6', title_font=dict(size=11,color='#64748B'), tickfont=dict(size=10))
    fig.update_yaxes(automargin=True, zeroline=False, showline=False,
        gridcolor='#EDF2F6', title_font=dict(size=11,color='#64748B'), tickfont=dict(size=11))
    if horizontal:
        fig.update_xaxes(title='Millones de CLP · misma escala',range=[0,limit or 1],showgrid=True)
        fig.update_yaxes(showgrid=False,title=None)
    else:
        fig.update_yaxes(title='Millones de CLP',showgrid=True)
        fig.update_xaxes(showgrid=False,title=None)
    return fig


def render(fig, key):
    st.plotly_chart(fig,use_container_width=True,config={'displaylogo':False,'displayModeBar':'hover',
        'modeBarButtonsToRemove':['lasso2d','select2d']},key='option4_'+key)


def header(title, value, note):
    st.html('<div class="option-finance-chart-head"><div><strong>'+html.escape(title)+'</strong>'
        '<span>'+html.escape(note)+'</span></div><b>'+html.escape(value)+'</b></div>')


def comparison_figures(summary, dimension):
    values=summary[['Presupuesto referencia','Caja por validar','Caja validada']]
    maximum=values.max().max()
    limit=max(1,float(maximum)/1e6*1.32) if pd.notna(maximum) else 1
    labels=summary[dimension].astype(str).tolist()
    height=max(270,110+len(summary)*48)
    known=summary[summary['Presupuesto referencia'].notna()]
    reference=go.Figure()
    if not known.empty:
        texts=[amount(value,True)+' · '+f'{share:.1f}%'.replace('.',',') if pd.notna(share) else amount(value,True)
            for value,share in zip(known['Presupuesto referencia'],known['Participación %'])]
        reference.add_bar(x=known['Presupuesto referencia']/1e6,y=known[dimension].astype(str),orientation='h',width=.38,
            marker=dict(color=NAVY,cornerradius=4),text=texts,textposition='outside',cliponaxis=False,
            textfont=dict(size=11,color='#0F2435'),
            customdata=[[amount(value),f'{share:.1f}%'.replace('.',',') if pd.notna(share) else 'Sin base',int(count),wrap(label)]
                for value,share,count,label in zip(known['Presupuesto referencia'],known['Participación %'],known['Actividades'],known[dimension])],
            hovertemplate='<b>%{customdata[3]}</b><br>Referencia: %{customdata[0]}<br>Participación: %{customdata[1]}<br>Actividades: %{customdata[2]}<extra></extra>')
    cash=go.Figure()
    available=[field for field in ['Caja validada','Caja por validar'] if summary[field].notna().any()]
    for field,color in [('Caja validada',VALID),('Caja por validar',PENDING)]:
        known=summary[summary[field].notna()]
        if not known.empty:
            cash.add_bar(x=known[field]/1e6,y=known[dimension].astype(str),orientation='h',name=field,
                width=.26 if len(available)>1 else .38,marker=dict(color=color,cornerradius=4),
                text=[amount(value,True) for value in known[field]],textposition='outside',cliponaxis=False,
                textfont=dict(size=11,color='#0F2435'),
                customdata=[[amount(value),wrap(label)] for value,label in zip(known[field],known[dimension])],
                hovertemplate='<b>%{customdata[1]}</b><br>'+field+': %{customdata[0]}<extra></extra>')
    for fig in [reference,cash]:
        fig.update_yaxes(categoryorder='array',categoryarray=labels,autorange='reversed',
            tickmode='array',tickvals=labels,ticktext=[wrap(value) for value in labels])
        figure_style(fig,height,limit)
    cash.update_layout(barmode='group',bargroupgap=.15)
    return reference,cash


def render_capital_comparison(summary,dimension,key):
    reference,cash=comparison_figures(summary,dimension)
    left,right=st.columns(2,gap='large')
    with left:
        with st.container(border=True,key=f'capital_{key}_reference_panel'):
            header('Presupuesto de referencia',amount(summary['Presupuesto referencia'].sum(min_count=1)),
                'Monto y participación de cada categoría')
            if reference.data:render(reference,f'capital_{key}_reference')
            else:st.info('No hay presupuestos de referencia informados.')
    with right:
        with st.container(border=True,key=f'capital_{key}_cash_panel'):
            header('Caja pendiente de cubrir',amount(summary[['Caja por validar','Caja validada']].sum(axis=1,min_count=1).sum(min_count=1)),
                'Validada y por validar se presentan por separado')
            st.html('<div class="option-finance-legend"><span><i style="background:'+VALID+'"></i>Validada</span><span><i style="background:'+PENDING+'"></i>Por validar</span></div>')
            if cash.data:render(cash,f'capital_{key}_cash')
            else:st.info('No hay importes de caja informados.')
            if summary['Caja validada'].isna().all():st.caption('Caja validada: sin importes informados en esta selección.')
    st.caption('Ambos gráficos usan la misma escala. MM = millones de pesos chilenos. Los valores vacíos no se interpretan como cero.')


def add_calendar_milestones(fig, visible, milestones):
    if milestones is None or milestones.empty:
        return
    markers = milestones.dropna(subset=['Fin previsto actual']).copy()
    markers = markers.drop_duplicates(['Paquete / línea', 'Fin previsto actual']).sort_values('Fin previsto actual')
    if markers.empty:
        return
    first = min(visible['_month'].min(), markers['Fin previsto actual'].min()).to_period('M').to_timestamp()
    last = max(visible['_month'].max(), markers['Fin previsto actual'].max()).to_period('M').to_timestamp() + pd.offsets.MonthEnd(0)
    dates = pd.date_range(first, last, freq='MS')
    span = max((last-first).days, 1)
    palette = ['#244A6C', '#2563EB', '#D97706', '#0891B2', '#B45309']
    occupied = []
    max_level = 0
    for index, (_, row) in enumerate(markers.iterrows()):
        date = row['Fin previsto actual']
        relative = (date-first).days / span
        level = next((i for i, previous in enumerate(occupied) if relative-previous >= .19), len(occupied))
        if level == len(occupied):
            occupied.append(relative)
        else:
            occupied[level] = relative
        max_level = max(max_level, level)
        color = palette[index % len(palette)]
        label = '<br>'.join(html.escape(line) for line in textwrap.wrap(str(row['Paquete / línea']), width=25))
        fig.add_shape(type='line', x0=date, x1=date, xref='x', y0=0, y1=1, yref='paper',
            line=dict(color=color, width=1.4, dash='dot'), layer='above')
        fig.add_annotation(x=date, xref='x', y=1.02, yref='paper',
            yshift=level*58, xanchor='center', yanchor='bottom',
            text=f'<b>{label}</b><br>{date:%d-%m-%Y}', showarrow=False,
            bordercolor=color, borderwidth=1, borderpad=6, bgcolor='#FFFFFF',
            font=dict(family='Arial, sans-serif',size=10,color=color), align='center',
            hovertext=f'{html.escape(str(row["ID"]))} · Fin previsto actual de Plan')
    padding = pd.Timedelta(days=max(18, span*.055))
    fig.update_xaxes(range=[first-padding,last+padding],tickmode='array',tickvals=dates.tolist(),
        ticktext=[MONTHS[value.month-1]+'<br>'+str(value.year) for value in dates])
    top = 92 + max_level*58
    fig.update_layout(height=420+top-50,margin=dict(l=12,r=25,t=top,b=65))


def calendar_figure(monthly, milestones=None):
    visible=monthly[monthly[['Pendiente validado CLP','Referencia por validar CLP']].notna().any(axis=1)].copy()
    total=visible[['Pendiente validado CLP','Referencia por validar CLP']].sum(axis=1,min_count=1)
    fig=go.Figure()
    for field,name,color in [('Pendiente validado CLP','Validado',VALID),('Referencia por validar CLP','Por validar',PENDING)]:
        if visible[field].notna().any():
            fig.add_bar(x=visible['_month'],y=visible[field]/1e6,name=name,
                marker=dict(color=color,cornerradius=4),customdata=[[amount(value)] for value in visible[field]],
                hovertemplate='<b>%{x|%m/%Y}</b><br>'+name+': %{customdata[0]}<extra></extra>')
    if fig.data:
        fig.add_scatter(x=visible['_month'],y=total/1e6,mode='text',
            text=[amount(value,True) for value in total],textposition='top center',
            textfont=dict(size=10,color='#0F2435'),hoverinfo='skip',showlegend=False,cliponaxis=False)
        figure_style(fig,height=420,horizontal=False)
        fig.update_layout(barmode='stack',bargap=.35,margin=dict(l=12,r=25,t=50,b=65))
        fig.update_yaxes(range=[0,max(1,float(total.max())/1e6*1.23)])
        fig.update_xaxes(tickmode='array',tickvals=visible['_month'].tolist(),
            ticktext=[MONTHS[value.month-1]+'<br>'+str(value.year) for value in visible['_month']],tickangle=0)
        add_calendar_milestones(fig, visible, milestones)
    return fig,visible,total


def render_calendar(monthly, milestones=None):
    fig,visible,total=calendar_figure(monthly, milestones)
    with st.container(border=True,key='capital_calendar_panel'):
        header('Caja mes a mes',amount(total.sum(min_count=1)),
            'Total mensual · caja validada y por validar')
        st.html('<div class="option-finance-legend"><span><i style="background:'+VALID+'"></i>Validada</span><span><i style="background:'+PENDING+'"></i>Por validar</span></div>')
        if fig.data:
            render(fig,'cash')
            peak=total.idxmax();month=visible.loc[peak,'_month']
            st.caption(f'Mayor necesidad mensual: {MONTHS[month.month-1]} {month.year} · {amount(total.loc[peak])}. Los importes escritos sobre las barras son los totales del mes.')
        else:st.info('La selección no tiene desembolsos calendarizados con montos informados.')
        if monthly['Pendiente validado CLP'].isna().all():st.caption('No hay importes validados informados; las barras ámbar corresponden a montos por validar.')
        if milestones is not None and not milestones.empty:
            st.caption('Líneas verticales: hitos de Paquete / línea. Los recuadros muestran su Fin previsto actual en Plan y respetan los filtros de la selección.')


def render_responsible_funds(tasks,cash,summary_function):
    st.subheader('Fondos por responsable')
    field=st.radio('Agrupar responsables por',['Entidad responsable','Responsable persona'],horizontal=True,key='option4_capital_responsible_field')
    scope=tasks.copy()
    scope[field]=scope[field].fillna('').astype(str).str.strip().replace('','Sin responsable asignado')
    summary=summary_function(scope,cash,field)
    summary['_total']=summary[['Caja validada','Caja por validar']].sum(axis=1,min_count=1)
    summary=summary.sort_values('_total',ascending=False,na_position='last')
    labels=summary[field].tolist()
    fig=go.Figure()
    for value,color in [('Caja validada',VALID),('Caja por validar',PENDING)]:
        known=summary[summary[value].notna()]
        if not known.empty:
            fig.add_bar(x=known[value]/1e6,y=known[field],orientation='h',name=value,
                marker=dict(color=color,cornerradius=4),width=.42,
                customdata=[[amount(money),wrap(label)] for money,label in zip(known[value],known[field])],
                hovertemplate='<b>%{customdata[1]}</b><br>'+value+': %{customdata[0]}<extra></extra>')
    known=summary[summary['_total'].notna()]
    if fig.data:
        fig.add_scatter(x=known['_total']/1e6,y=known[field],mode='text',
            text=[amount(value,True) for value in known['_total']],textposition='middle right',
            hoverinfo='skip',cliponaxis=False,textfont=dict(size=11,color='#0F2435'))
        limit=max(1,float(known['_total'].max())/1e6*1.3)
        figure_style(fig,height=max(300,110+len(summary)*46),limit=limit)
        fig.update_layout(barmode='stack')
        fig.update_xaxes(title='Millones de CLP · caja pendiente')
        fig.update_yaxes(categoryorder='array',categoryarray=labels,autorange='reversed')
        with st.container(border=True,key='capital_responsible_panel'):
            header('Asignación de caja pendiente',amount(summary['_total'].sum(min_count=1)),
                'Responsable de la actividad según Plan')
            st.html('<div class="option-finance-legend"><span><i style="background:'+VALID+'"></i>Validada</span><span><i style="background:'+PENDING+'"></i>Por validar</span></div>')
            render(fig,'capital_responsible')
    else:st.info('No hay fondos informados para los responsables de esta selección.')
    st.caption('Esta distribución identifica al responsable de la actividad; no confirma quién aportará el financiamiento. Respeta los filtros de proyecto, hito, sistema y estado.')
    with st.expander('Detalle de fondos por responsable'):
        st.dataframe(summary.drop(columns='_total'),hide_index=True,use_container_width=True)
        st.download_button('Descargar fondos por responsable',summary.drop(columns='_total').to_csv(index=False).encode('utf-8-sig'),
            file_name='fondos_por_responsable.csv',mime='text/csv',key='option4_responsible_download')
