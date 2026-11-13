"""Readable capital comparisons, monthly cash and responsible-entity allocations."""
import html
import textwrap
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from display_currency import amount, currency_label, currency_code, chart_scale, chart_units, currency_column_config, currency_export

NAVY = '#244A6C'
VALID = '#0F766E'
PENDING = '#B7791F'
MONTHS = ['ene','feb','mar','abr','may','jun','jul','ago','sept','oct','nov','dic']


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
        fig.update_xaxes(title=chart_units()+' · misma escala',range=[0,limit or 1],showgrid=True)
        fig.update_yaxes(showgrid=False,title=None)
    else:
        fig.update_yaxes(title=chart_units(),showgrid=True)
        fig.update_xaxes(showgrid=False,title=None)
    return fig


def render(fig, key):
    st.plotly_chart(fig,use_container_width=True,config={'displaylogo':False,'displayModeBar':'hover',
        'modeBarButtonsToRemove':['lasso2d','select2d']},key='option4_'+key)


def header(title, value, note, comparison=False):
    extra = ' option-finance-comparison-head' if comparison else ''
    st.html('<div class="option-finance-chart-head' + extra + '"><div><strong>'+html.escape(title)+'</strong>'
        '<span>'+html.escape(note)+'</span></div><b>'+html.escape(value)+'</b></div>')


def comparison_figures(summary, dimension):
    values=summary[['Caja pendiente de cubrir','Caja por validar','Caja validada']]
    maximum=values.max().max()
    limit=max(1,float(maximum)/chart_scale()*1.32) if pd.notna(maximum) else 1
    labels=summary[dimension].astype(str).tolist()
    height=max(270,110+len(summary)*48)
    known=summary[summary['Caja pendiente de cubrir'].notna()]
    reference=go.Figure()
    if not known.empty:
        texts=[amount(value,True)+' · '+f'{share:.1f}%'.replace('.',',') if pd.notna(share) else amount(value,True)
            for value,share in zip(known['Caja pendiente de cubrir'],known['Participación %'])]
        reference.add_bar(x=known['Caja pendiente de cubrir']/chart_scale(),y=known[dimension].astype(str),orientation='h',width=.38,
            marker=dict(color=NAVY,cornerradius=4),text=texts,textposition='outside',cliponaxis=False,
            textfont=dict(size=11,color='#0F2435'),
            customdata=[[amount(value),f'{share:.1f}%'.replace('.',',') if pd.notna(share) else 'Sin base',int(count),wrap(label)]
                for value,share,count,label in zip(known['Caja pendiente de cubrir'],known['Participación %'],known['Actividades'],known[dimension])],
            hovertemplate='<b>%{customdata[3]}</b><br>Pendiente: %{customdata[0]}<br>Participación: %{customdata[1]}<br>Actividades: %{customdata[2]}<extra></extra>')
    cash=go.Figure()
    available=[field for field in ['Caja validada','Caja por validar'] if summary[field].notna().any()]
    for field,color in [('Caja validada',VALID),('Caja por validar',PENDING)]:
        known=summary[summary[field].notna()]
        if not known.empty:
            cash.add_bar(x=known[field]/chart_scale(),y=known[dimension].astype(str),orientation='h',name=field,
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
        with st.container(border=False,key=f'capital_{key}_reference_panel'):
            header('Caja pendiente de cubrir',amount(summary['Caja pendiente de cubrir'].sum(min_count=1)),
                'Monto y participación de cada categoría', comparison=True)
            st.html('<div class="option-finance-legend option-finance-comparison-legend"><span><i style="background:'+NAVY+'"></i>Saldo pendiente total</span></div>')
            if reference.data:render(reference,f'capital_{key}_reference')
            else:st.html(f'<div class="option-finance-chart-empty" style="height:{reference.layout.height}px">No hay saldos pendientes de caja informados.</div>')
            st.html('<div class="option-finance-comparison-footer">Porcentajes sobre la caja pendiente de cubrir de la selección.</div>')
    with right:
        with st.container(border=False,key=f'capital_{key}_cash_panel'):
            header('Desglose de caja pendiente',amount(summary[['Caja por validar','Caja validada']].sum(axis=1,min_count=1).sum(min_count=1)),
                'Validada y por validar se presentan por separado', comparison=True)
            st.html('<div class="option-finance-legend option-finance-comparison-legend"><span><i style="background:'+VALID+'"></i>Validada</span><span><i style="background:'+PENDING+'"></i>Por validar</span></div>')
            if cash.data:render(cash,f'capital_{key}_cash')
            else:st.html(f'<div class="option-finance-chart-empty" style="height:{cash.layout.height}px">No hay importes de caja informados.</div>')
            footer = 'Sin importes de caja validada informados en esta selección.' if summary['Caja validada'].isna().all() else 'La validación se muestra por separado de los importes pendientes de revisar.'
            st.html('<div class="option-finance-comparison-footer">'+html.escape(footer)+'</div>')


def calendar_cash_rows(cash):
    """Retain the source's scheduling exclusions when total pending cash is larger."""
    result=cash.copy()
    fields={'Pendiente validado CLP':'Caja calendarizada validada CLP',
        'Referencia por validar CLP':'Caja calendarizada por validar CLP'}
    if all(source in result for source in fields.values()):
        for target,source in fields.items():result[target]=result[source]
    return result


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
            yshift=level*44, xanchor='center', yanchor='bottom',
            text=f'<b>{label}</b><br>{date:%d-%m-%Y}', showarrow=False,
            bordercolor=color, borderwidth=1, borderpad=4, bgcolor='#FFFFFF',
            font=dict(family='Arial, sans-serif',size=10,color=color), align='center',
            hovertext=f'{html.escape(str(row["ID"]))} · Fin previsto actual de Plan')
    padding = pd.Timedelta(days=max(18, span*.055))
    fig.update_xaxes(range=[first-padding,last+padding],tickmode='array',tickvals=dates.tolist(),
        ticktext=[MONTHS[value.month-1]+'<br>'+str(value.year) for value in dates])
    original_height = 420+92+max_level*58-50
    top = 72 + max_level*44
    fig.update_layout(height=round(original_height*.8),margin=dict(l=12,r=25,t=top,b=52))


def calendar_figure(monthly, milestones=None):
    visible=monthly[monthly[['Pendiente validado CLP','Referencia por validar CLP']].notna().any(axis=1)].copy()
    total=visible[['Pendiente validado CLP','Referencia por validar CLP']].sum(axis=1,min_count=1)
    fig=go.Figure()
    for field,name,color in [('Pendiente validado CLP','Validado',VALID),('Referencia por validar CLP','Por validar',PENDING)]:
        if visible[field].notna().any():
            fig.add_bar(x=visible['_month'],y=visible[field]/chart_scale(),name=name,
                marker=dict(color=color,cornerradius=4),customdata=[[amount(value)] for value in visible[field]],
                hovertemplate='<b>%{x|%m/%Y}</b><br>'+name+': %{customdata[0]}<extra></extra>')
    if fig.data:
        fig.add_scatter(x=visible['_month'],y=total/chart_scale(),mode='text',
            text=[amount(value,True) for value in total],textposition='top center',
            textfont=dict(size=10,color='#0F2435'),hoverinfo='skip',showlegend=False,cliponaxis=False)
        figure_style(fig,height=336,horizontal=False)
        fig.update_layout(barmode='stack',bargap=.35,margin=dict(l=12,r=25,t=40,b=52))
        fig.update_yaxes(range=[0,max(1,float(total.max())/chart_scale()*1.23)])
        fig.update_xaxes(tickmode='array',tickvals=visible['_month'].tolist(),
            ticktext=[MONTHS[value.month-1]+'<br>'+str(value.year) for value in visible['_month']],tickangle=0)
        add_calendar_milestones(fig, visible, milestones)
    return fig,visible,total


def render_calendar(monthly, milestones=None, criteria=()):
    fig,visible,total=calendar_figure(monthly, milestones)
    with st.container(border=False,key='capital_calendar_panel'):
        header('Caja mes a mes',amount(total.sum(min_count=1)),
            'Total mensual · caja validada y por validar')
        st.html('<div class="option-finance-legend"><span><i style="background:'+VALID+'"></i>Validada</span><span><i style="background:'+PENDING+'"></i>Por validar</span></div>')
        if fig.data:
            render(fig,'cash')
        else:st.info('La selección no tiene desembolsos calendarizados con montos informados.')
        with st.expander('Criterios y fuentes del calendario'):
            if fig.data:
                peak=total.idxmax();month=visible.loc[peak,'_month']
                st.markdown(f'**Mayor necesidad mensual:** {MONTHS[month.month-1]} {month.year} · **{amount(total.loc[peak])}**.')
            st.caption('Las cifras sobre las barras corresponden al total mensual de caja validada y por validar.')
            if monthly['Pendiente validado CLP'].isna().all():
                st.caption('No hay importes validados informados; las barras ámbar corresponden a montos por validar.')
            if milestones is not None and not milestones.empty:
                st.caption('Líneas verticales: hitos de Paquete / línea. Los recuadros muestran su Fin previsto actual en Plan y respetan los filtros de la selección.')
            for note in criteria:st.caption(note)


def render_responsible_funds(tasks,cash,summary_function):
    with st.container(border=True, key='option4_analysis_responsible'):
        st.subheader('Fondos por responsable')
        st.caption('Distribución de caja validada y por validar según la asignación de Plan.')
        field=st.radio('Agrupar responsables por',['Entidad responsable','Responsable persona'],horizontal=True,key='option4_capital_responsible_field')
        scope=tasks.copy()
        scope[field]=scope[field].fillna('').astype(str).str.strip().replace('','Sin responsable asignado')
        summary=summary_function(scope,cash,field)
        summary['_total']=summary[['Caja validada','Caja por validar']].sum(axis=1,min_count=1)
        summary=summary.sort_values('_total',ascending=False,na_position='last')
        known=summary[summary['_total'].notna()].copy()
        labels=known[field].tolist()
        total=summary['_total'].sum(min_count=1)
        fig=go.Figure()
        for value,color in [('Caja validada',VALID),('Caja por validar',PENDING)]:
            available=known[known[value].notna()]
            if not available.empty:
                fig.add_bar(x=available[value]/chart_scale(),y=available[field],orientation='h',name=value,
                    marker=dict(color=color,cornerradius=4),width=.46,
                    customdata=[[amount(value),wrap(label)] for value,label in zip(available[value],available[field])],
                    hovertemplate='<b>%{customdata[1]}</b><br>'+value+': %{customdata[0]}<extra></extra>')
        if fig.data:
            fig.add_scatter(x=known['_total']/chart_scale(),y=known[field],mode='text',
                text=[amount(value,True) for value in known['_total']],textposition='middle right',
                hoverinfo='skip',cliponaxis=False,textfont=dict(size=11,color='#0F2435'))
            limit=max(1,float(known['_total'].max())/chart_scale()*1.3)
            height=max(290,100+len(known)*48)
            figure_style(fig,height=height,limit=limit)
            fig.update_layout(barmode='stack',margin=dict(l=12,r=95,t=15,b=45))
            fig.update_xaxes(title=chart_units()+' · caja pendiente')
            fig.update_yaxes(categoryorder='array',categoryarray=labels,autorange='reversed',
                tickmode='array',tickvals=labels,ticktext=[wrap(label) for label in labels])
            header('Asignación de caja pendiente',amount(total),'Responsable de la actividad según Plan')
            st.html('<div class="option-finance-legend"><span><i style="background:'+VALID+'"></i>Validada</span><span><i style="background:'+PENDING+'"></i>Por validar</span></div>')
            chart_col,detail_col=st.columns([1.5,1],gap='large')
            with chart_col:render(fig,'capital_responsible')
            with detail_col:
                leader=known.iloc[0]
                share=f'{leader["_total"]/total*100:.1f}%'.replace('.',',') if pd.notna(total) and total>0 else 'Sin base'
                st.html('<div class="option-responsible-insight"><span>MAYOR ASIGNACIÓN DE CAJA</span><strong>'
                    +html.escape(str(leader[field]))+'</strong><b>'+share+'</b><small>del total informado · '+html.escape(amount(leader['_total']))+'</small></div>')
                detail=pd.DataFrame({'Responsable':summary[field],
                    'Validada':[amount(value,True) if pd.notna(value) else '—' for value in summary['Caja validada']],
                    'Por validar':[amount(value,True) if pd.notna(value) else '—' for value in summary['Caja por validar']],
                    'Participación':[f'{value/total*100:.1f}%'.replace('.',',') if pd.notna(value) and pd.notna(total) and total>0 else '—' for value in summary['_total']]})
                st.dataframe(detail,hide_index=True,use_container_width=True,height=max(200,min(430,40+len(detail)*36)),
                    column_config={'Responsable':st.column_config.TextColumn(width=110),
                        'Validada':st.column_config.TextColumn(width=110,help='Importe abreviado. El detalle conserva los montos completos y su estado.'),
                        'Por validar':st.column_config.TextColumn(width=125,help='Importe abreviado pendiente de validar. Sin dato se muestra como guion.'),
                        'Participación':st.column_config.TextColumn(width=80)})
        else:st.info('No hay fondos informados para los responsables de esta selección.')
        with st.expander('Detalle y criterios de fondos por responsable'):
            st.caption('Esta distribución identifica al responsable de la actividad; no confirma quién aportará el financiamiento.')
            st.dataframe(summary.drop(columns='_total'),hide_index=True,use_container_width=True,column_config=currency_column_config(summary))
            st.download_button('Descargar fondos por responsable',currency_export(summary.drop(columns='_total')).to_csv(index=False).encode('utf-8-sig'),
                file_name='fondos_por_responsable.csv',mime='text/csv',key='option4_responsible_download')
