"""Runtime XLSX export of the exact commercial report selection."""
from io import BytesIO
from numbers import Real

import pandas as pd
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name


COMMERCIAL = 'Comercial anterior'
MONEY = {COMMERCIAL, 'Presupuesto vigente', 'Costo por unidad · CLP',
         'Monto comercial · CLP', 'Monto no comercial · CLP'}


def build_commercial_excel(details, context):
    """Amounts are already in display currency; preserve blanks and source text."""
    output = BytesIO()
    book = xlsxwriter.Workbook(output, {'in_memory': True,
        'strings_to_formulas': False, 'strings_to_urls': False})
    currency = context['currency']
    money_code = '"US$ "#,##0' if currency == 'USD' else '"$"#,##0'
    title = book.add_format({'font_size': 18, 'bold': True, 'font_color': '#183448'})
    note = book.add_format({'font_color': '#526578', 'text_wrap': True, 'valign': 'top'})
    body = book.add_format({'font_size': 11, 'valign': 'top', 'text_wrap': True})
    monetary = book.add_format({'num_format': money_code, 'valign': 'top'})
    decimal = book.add_format({'num_format': '#,##0.00', 'valign': 'top'})
    # Source percentages use 0–100 rather than Excel's fractional convention.
    percent = book.add_format({'num_format': '0.00"%"', 'valign': 'top'})
    total_format = book.add_format({'bold': True, 'bg_color': '#EAF5F3', 'num_format': money_code})

    def label(column):
        if column == COMMERCIAL:
            return 'Monto comercial · ' + currency
        if column in MONEY:
            return column.replace('CLP', currency) + (' · ' + currency if column == 'Presupuesto vigente' else '')
        return column

    def cell(sheet, row, col, value, fmt=None):
        if pd.isna(value):
            sheet.write_blank(row, col, None, fmt)
        elif isinstance(value, Real) and not isinstance(value, bool):
            sheet.write_number(row, col, float(value), fmt)
        else:
            sheet.write_string(row, col, str(value), fmt or body)

    summary = book.add_worksheet('Resumen')
    detail = book.add_worksheet('Detalle')
    for sheet in (summary, detail):
        sheet.hide_gridlines(2)
        sheet.set_default_row(24)
        sheet.set_landscape()
        sheet.fit_to_pages(1, 0)
        sheet.set_paper(9)
    summary.set_column('A:A', 38)
    summary.set_column('B:C', 23)
    summary.set_column('D:I', 18)
    summary.merge_range('A1:I2', 'Costo comercial · ' + context['project'], title)
    metadata = [
        ('Alcance', context['mode']), ('Selección', context['selection']),
        ('Moneda', currency), ('Tipo de cambio · CLP/USD', context.get('fx_rate')),
        ('Generado', context.get('generated_at')), ('Corte de la fuente', context.get('cutoff')),
        ('Datos consultados', context.get('consulted_at')), ('Fuente', context.get('source_url')),
    ]
    for row, (key, value) in enumerate(metadata, 3):
        summary.write_string(row, 0, key, body)
        summary.merge_range(row, 1, row, 8, '', note)
        cell(summary, row, 1, value, note)
    summary.merge_range('A12:I13',
        'Subtotal de importes informados. Las celdas vacías significan sin informar, no cero. '
        'Solo partidas Aplica del alcance seleccionado. HH suma cantidades con criterio HH. '
        'Los porcentajes del detalle conservan las bases del PDF: paquete y turbina completa.', note)

    # Keep the exact detail fields used by the PDF, including missing amounts.
    detail.merge_range('A1:H2', 'Detalle · ' + context['project'], title)
    detail.merge_range('A3:H3', context['mode'] + ' · ' + currency, note)
    detail.merge_range('A4:H4', 'Fuente y fecha de consulta: ver Resumen. Celdas vacías = sin informar.', note)
    header_row = 5
    detail.set_row(header_row, 42)
    columns = []
    for col, field in enumerate(details.columns):
        fmt = monetary if field in MONEY else percent if '%' in field else decimal if field == 'Cantidad' else body
        columns.append({'header': label(field), 'format': fmt})
        width = 56 if field == 'Actividad / entregable' else 32 if field in ('Sistema', 'Paquete / línea') else 24
        detail.set_column(col, col, 12 if field in ('ID', 'Criterio') else width)
        for row, value in enumerate(details[field], header_row + 1):
            cell(detail, row, col, value, fmt)
    if len(details):
        detail.add_table(header_row, 0, header_row + len(details), len(columns) - 1,
            {'name': 'DetalleComercial', 'style': 'Table Style Medium 2', 'columns': columns})
    detail.freeze_panes(header_row + 1, 2)
    detail.repeat_rows(header_row)
    for offset, (_, record) in enumerate(details.iterrows(), header_row + 1):
        lines = max((len(str(record.get(field, ''))) // width + 1
            for field, width in [('Actividad / entregable', 52), ('Sistema', 30),
                                 ('Paquete / línea', 30)]), default=1)
        detail.set_row(offset, min(96, max(24, lines * 16)))

    systems = pd.DataFrame(context['system_summary'])
    fields = ['Sistema', 'Monto comercial · CLP', 'Monto no comercial · CLP', 'HH',
              'Partidas informadas', 'Actividades', 'Participación %', 'Cobertura %']
    start = 15
    summary.set_row(start, 42)
    summary_columns = []
    for col, field in enumerate(fields):
        fmt = monetary if field in MONEY else percent if '%' in field else decimal
        summary_columns.append({'header': label(field), 'format': body if col == 0 else fmt})
        for row, value in enumerate(systems[field], start + 1):
            cell(summary, row, col, value, body if col == 0 else fmt)
    if len(systems):
        summary.add_table(start, 0, start + len(systems), len(fields) - 1,
            {'name': 'ResumenSistemas', 'style': 'Table Style Medium 2', 'columns': summary_columns})
        for row in range(start + 1, start + len(systems) + 1):
            summary.set_row(row, 36)
    total_row = start + len(systems) + 2
    summary.write_string(total_row, 0, 'TOTAL INFORMADO', body)
    # Cross-sheet formulas reconcile both report totals to the exported detail.
    for col, field in [(1, COMMERCIAL), (2, 'Presupuesto vigente')]:
        detail_col = xl_col_to_name(details.columns.get_loc(field))
        values = pd.to_numeric(details[field], errors='coerce')
        cached = values.sum(min_count=1)
        if pd.notna(cached):
            summary.write_formula(total_row, col,
                f'=SUM(Detalle!{detail_col}{header_row+2}:{detail_col}{header_row+1+len(details)})',
                total_format, float(cached))
        else:
            summary.write_blank(total_row, col, None, total_format)
    summary.freeze_panes(start + 1, 1)
    if len(systems):
        chart = book.add_chart({'type': 'bar'})
        chart.add_series({'name': 'Monto comercial · ' + currency,
            'categories': ['Resumen', start + 1, 0, start + len(systems), 0],
            'values': ['Resumen', start + 1, 1, start + len(systems), 1],
            'fill': {'color': '#244A6C'}, 'border': {'none': True}})
        chart.set_title({'name': 'Costo informado por sistema · ' + currency})
        chart.set_legend({'none': True})
        chart.set_x_axis({'num_format': money_code})
        chart.set_y_axis({'reverse': True})
        chart.set_size({'width': 840, 'height': max(300, min(600, 35 * len(systems)))})
        summary.insert_chart(total_row + 3, 0, chart)
    book.close()
    return output.getvalue()
