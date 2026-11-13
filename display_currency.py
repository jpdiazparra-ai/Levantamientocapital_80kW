"""Session-specific display currency; all published source amounts remain CLP."""
import math
import pandas as pd
import streamlit as st

TASK_MONEY_COLUMNS = {
    'Presupuesto referencia', 'Cambios aprobados', 'Presupuesto vigente',
    'AC monetario', 'Aportes valorizados', 'AC económico', 'Pagos realizados',
    'Pagos registrados al corte', 'Compromiso pendiente', 'ETC actualizado',
    'EAC económico', 'VAC al cierre', 'EV', 'PV', 'Pendiente de pago',
    'AC anterior sin validar', 'Comercial anterior', 'Monto total a pagar caja CLP',
    'Saldo pendiente caja CLP', 'Caja programada CLP', 'Caja por validar CLP', 'Caja sin fecha CLP',
}
CASH_MONEY_COLUMNS = {
    'Saldo pendiente CLP', 'Caja programada CLP', 'Referencia por validar CLP',
    'Pendiente validado CLP', 'Caja sin fecha CLP',
    'Caja calendarizada validada CLP', 'Caja calendarizada por validar CLP',
}
DISPLAY_MONEY_COLUMNS = TASK_MONEY_COLUMNS | CASH_MONEY_COLUMNS | {
    'Monto comercial · CLP', 'Costo por unidad · CLP', 'Caja por validar', 'Caja validada',
    'Monto comercial · USD', 'Costo por unidad · USD',
    'Monto no comercial · CLP', 'Monto no comercial · USD', 'Saldo fuera de programación',
}


def currency_code():
    return 'USD' if st.session_state.get('option4_currency', 'USD') == 'USD' else 'CLP'


def exchange_rate():
    rate = float(st.session_state.get('option4_fx_rate', 980.0))
    if not math.isfinite(rate) or rate <= 0:
        raise ValueError('El tipo de cambio CLP/USD debe ser mayor que cero.')
    return rate


def currency_label(text):
    return str(text).replace('CLP', currency_code())


def currency_number_format():
    return 'US$ %.2f' if currency_code() == 'USD' else '$ %.0f'


def amount(value, compact=False):
    if pd.isna(value):
        return 'Sin informar'
    usd = currency_code() == 'USD'
    prefix = 'US$ ' if usd else '$'
    divisor, suffix = (1e6, ' MM') if compact and abs(value) >= 1e6 else (1e3, ' mil') if compact and usd and abs(value) >= 1e3 else (1, '')
    decimals = 1 if divisor > 1 else 2 if usd else 0
    return prefix + f'{value/divisor:,.{decimals}f}'.replace(',', 'X').replace('.', ',').replace('X', '.') + suffix


def chart_scale():
    return 1e3 if currency_code() == 'USD' else 1e6


def chart_units():
    return 'Miles de USD' if currency_code() == 'USD' else 'Millones de CLP'


def convert_workbook(tasks, cash, parse_number):
    """Convert copies once at the view boundary, never cached CLP source frames."""
    result_tasks, result_cash = tasks.copy(), cash.copy()
    if currency_code() == 'USD':
        rate = exchange_rate()
        for frame, columns in [(result_tasks, TASK_MONEY_COLUMNS), (result_cash, CASH_MONEY_COLUMNS)]:
            for column in columns.intersection(frame.columns):
                frame[column] = frame[column].map(parse_number) / rate
    return result_tasks, result_cash


def currency_column_config(frame):
    return {column: st.column_config.NumberColumn(
        currency_label(column) if 'CLP' in column or 'USD' in column else column + ' · ' + currency_code(),
        format=currency_number_format())
        for column in DISPLAY_MONEY_COLUMNS.intersection(frame.columns)}


def currency_export(frame):
    if currency_code() != 'USD':
        return frame
    return frame.rename(columns={column: currency_label(column) if 'CLP' in column else column + ' (USD)'
        for column in DISPLAY_MONEY_COLUMNS.intersection(frame.columns)})
