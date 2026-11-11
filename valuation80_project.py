"""Native CLP cost and disbursement evidence from Capital Strategy, for the 80 kW PDF."""
import pandas as pd
import streamlit as st

from valuation_costs import load_cost_report, SOURCE

CASH_FIELDS=['Pendiente validado CLP','Referencia por validar CLP']


def calendar_plot_data80(data):
    """Continuous monthly axis through both explicit 80 kW milestone dates."""
    markers=data.get('milestones',pd.DataFrame(columns=['Paquete / línea','Fin previsto actual'])).copy()
    markers=markers.loc[markers['Paquete / línea'].fillna('').str.contains(
        r'\bhito\s+(?:piloto|producto)\s+80\s*kw\b',case=False,regex=True)]
    markers['Fin previsto actual']=pd.to_datetime(markers['Fin previsto actual'])
    markers=markers.groupby('Paquete / línea',as_index=False)['Fin previsto actual'].max().sort_values('Fin previsto actual')
    monthly=data['monthly'].copy()
    bounds=list(monthly['_month'])+list(markers['Fin previsto actual'].dropna())
    if bounds:
        months=pd.date_range(min(bounds).to_period('M').to_timestamp(),max(bounds).to_period('M').to_timestamp(),freq='MS')
        monthly=monthly.set_index('_month').reindex(months).rename_axis('_month').reset_index()
    return monthly,markers


def project_calendar80(tasks,cash,cutoff):
    """Same calendar rules as capital_view, scoped to the 80 kW project in Plan."""
    if tasks['ID'].duplicated().any() or cash['ID actividad'].duplicated().any():
        raise ValueError('IDs duplicados: no se pueden agregar los desembolsos de 80 kW.')
    scope=tasks.loc[tasks['Proyecto'].fillna('').str.contains(r'(?<!\d)80\s*kw\b',case=False,regex=True)]
    if scope.empty:raise ValueError('Plan no contiene el proyecto de 80 kW para el calendario.')
    selected=cash.loc[cash['ID actividad'].isin(scope['ID'])].copy()
    first_month=pd.Timestamp(cutoff).to_period('M').to_timestamp()
    selected['_month']=selected['_date'].dt.to_period('M').dt.to_timestamp()
    selected['_month']=selected['_month'].mask(selected['_month'].lt(first_month),first_month)
    monthly=selected.dropna(subset=['_month']).groupby('_month')[CASH_FIELDS].sum(min_count=1).reset_index()
    monthly['Total CLP']=monthly[CASH_FIELDS].sum(axis=1,min_count=1)
    unknown=selected.loc[selected['_date'].isna()]
    markers=scope.loc[scope['Paquete / línea'].fillna('').str.contains(
        r'\bhito\s+(?:piloto|producto)\s+80\s*kw\b',case=False,regex=True),['Paquete / línea','Fin previsto actual']].drop_duplicates()
    return dict(monthly=monthly,cash=selected,cutoff=pd.Timestamp(cutoff),
        missing_dates=len(unknown),undated_total=unknown[CASH_FIELDS].sum(axis=1,min_count=1).sum(min_count=1),
        overdue_count=int(selected['_date'].lt(first_month).sum()),
        validated=monthly[CASH_FIELDS[0]].sum(min_count=1),pending=monthly[CASH_FIELDS[1]].sum(min_count=1),
        total=monthly['Total CLP'].sum(min_count=1),source_url=SOURCE,milestones=markers)


@st.cache_data(ttl=60,max_entries=4,show_spinner=False)
def load_project80(revision):
    # Import at call time: analysis_option renders valuation80_view itself.
    from analysis_option import load_workbook
    tasks,cash,cutoff,fetched=load_workbook(revision)
    result=project_calendar80(tasks,cash,cutoff)
    result['costs']=load_cost_report(revision)
    result['fetched_at']=fetched
    return result
