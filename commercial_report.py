"""Vector PDF report of the exact commercial selection, without browser dependencies."""
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
import math

import pandas as pd
import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, LongTable, PageBreak, Flowable

NAVY = '#183448'
GOLD = '#B99847'
TEAL = '#0F766E'
RUST = '#9F3A28'
MUTED = '#526578'
PALETTE = ['#244A6C', '#0F766E', '#2E90A5', '#B7791F', '#718096', '#735D96', '#CBD5E1']
COMMERCIAL = 'Comercial anterior'


def _fonts():
    directory = Path(reportlab.__file__).parent / 'fonts'
    for name, filename in [('ReportVera', 'Vera.ttf'), ('ReportVeraBold', 'VeraBd.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(directory / filename)))
    pdfmetrics.registerFontFamily('ReportVera', normal='ReportVera', bold='ReportVeraBold', italic='ReportVera', boldItalic='ReportVeraBold')


def _text(value):
    return 'Sin informar' if pd.isna(value) or str(value).strip() == '' else str(value)


def _decimal(value, digits=1):
    if pd.isna(value):
        return 'Sin informar'
    return f'{value:,.{digits}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def _money(value, currency):
    return 'Sin informar' if pd.isna(value) else ('US$ ' if currency == 'USD' else '$') + _decimal(value, 2 if currency == 'USD' else 0)


def _sum(frame, column):
    return pd.to_numeric(frame[column], errors='coerce').sum(min_count=1)


class SelectionCharts(Flowable):
    """Two fully vector charts with readable legends and exact amounts."""
    def __init__(self, data, currency, width):
        super().__init__()
        self.data, self.currency, self.width, self.height = data, currency, width, 232

    def draw(self):
        c, w = self.canv, self.width
        half = (w - 24) / 2
        def text(x, y, value, size=9, color=NAVY, bold=False):
            c.setFillColor(colors.HexColor(color)); c.setFont('ReportVeraBold' if bold else 'ReportVera', size)
            c.drawString(x, y, str(value))
        for x in [0, half + 24]:
            c.setFillColor(colors.white); c.setStrokeColor(colors.HexColor('#DEE6EB'))
            c.roundRect(x, 0, half, self.height, 9, stroke=1, fill=1)
        text(14, 211, 'Composición comercial por línea', 10, bold=True)
        groups = self.data.assign(_line=self.data['Paquete / línea'].fillna('').replace('', 'Sin línea asignada')).groupby('_line', sort=False)[COMMERCIAL].sum(min_count=1).sort_values(ascending=False)
        known = groups.dropna()
        positive = known[known.gt(0)]
        if len(positive) > 5:
            positive = pd.concat([positive.iloc[:4], pd.Series({'Otras líneas': positive.iloc[4:].sum()})])
        total = known.sum(min_count=1)
        if positive.empty or known.lt(0).any() or pd.isna(total) or total <= 0:
            text(16, 145, 'Sin base positiva para un gráfico de torta.', 8, MUTED)
        else:
            cx, cy, radius, angle = 86, 112, 66, 90
            for index, (label, value) in enumerate(positive.items()):
                sweep = 360 * value / total
                c.setFillColor(colors.HexColor(PALETTE[index % len(PALETTE)]))
                c.wedge(cx-radius, cy-radius, cx+radius, cy+radius, angle, sweep, stroke=0, fill=1)
                if value / total >= .06:
                    mid = math.radians(angle + sweep/2)
                    c.setFont('ReportVeraBold', 8); c.setFillColor(colors.white)
                    c.drawCentredString(cx + 54*math.cos(mid), cy + 54*math.sin(mid)-3, _decimal(100*value/total, 0)+'%')
                angle += sweep
            c.setFillColor(colors.white); c.circle(cx, cy, 40, stroke=0, fill=1)
            c.setFillColor(colors.HexColor(NAVY)); c.setFont('ReportVeraBold', 9)
            c.drawCentredString(cx, cy+2, _money(total, self.currency))
            c.setFont('ReportVera', 7); c.drawCentredString(cx, cy-12, self.currency+' · selección')
            y = 188
            for index, (label, value) in enumerate(positive.items()):
                c.setFillColor(colors.HexColor(PALETTE[index % len(PALETTE)])); c.roundRect(165, y-2, 6, 6, 1, fill=1, stroke=0)
                lines = simpleSplit(str(label), 'ReportVeraBold', 8, half-188)
                for line in lines[:2]:
                    text(178, y, line, 8, bold=True); y -= 10
                text(178, y, _money(value, self.currency)+' · '+_decimal(100*value/total)+'%', 7.5, MUTED)
                y -= 15
        x = half + 24
        text(x+14, 211, 'Comercial y presupuesto vigente', 10, bold=True)
        rows = self.data.assign(_line=self.data['Paquete / línea'].fillna('').replace('', 'Sin línea asignada')).groupby('_line', sort=False)[[COMMERCIAL, 'Presupuesto vigente']].sum(min_count=1)
        rows = rows.sort_values(COMMERCIAL, ascending=False, na_position='last')
        if len(rows) > 3:
            rest = rows.iloc[2:].sum(min_count=1)
            rows = pd.concat([rows.iloc[:2], pd.DataFrame([rest], index=['Otras líneas'])])
        numeric = rows.apply(pd.to_numeric, errors='coerce')
        maximum = numeric.abs().max().max()
        maximum = float(maximum) if pd.notna(maximum) and maximum > 0 else 1
        has_negative = numeric.lt(0).any().any()
        bar_width = 96 if has_negative else 180
        origin = x+112 if has_negative else x+16
        y = 177
        for label, row in rows.iterrows():
            for line in simpleSplit(str(label), 'ReportVeraBold', 8, half-30)[:2]:
                text(x+15, y, line, 8, bold=True); y -= 10
            for field, color in [(COMMERCIAL, TEAL), ('Presupuesto vigente', GOLD)]:
                value = row[field]
                if pd.notna(value):
                    length = bar_width * abs(value)/maximum
                    c.setFillColor(colors.HexColor(color))
                    c.rect(origin-length if value < 0 else origin, y-4, length, 6, fill=1, stroke=0)
                text(x+half-138, y-3, _money(value, self.currency), 7.5, MUTED)
                y -= 12
            y -= 6
        text(x+16, 13, 'Comercial', 8, TEAL, True)
        text(x+110, 13, 'Presupuesto vigente', 8, '#8A681F', True)


def build_commercial_pdf(details, context):
    """All amounts are already in the selected currency; never convert twice."""
    _fonts()
    currency = context['currency']
    data = details.copy()
    output = BytesIO()
    page_width, page_height = landscape(A4)
    width = page_width - 64
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('ReportTitle', fontName='ReportVeraBold', fontSize=23, leading=29, textColor=colors.HexColor(NAVY), spaceAfter=7))
    styles.add(ParagraphStyle('SectionTitle', fontName='ReportVeraBold', fontSize=14, leading=19, textColor=colors.HexColor(NAVY), spaceAfter=10))
    styles.add(ParagraphStyle('ReportBody', fontName='ReportVera', fontSize=9, leading=13, textColor=colors.HexColor(MUTED), spaceAfter=6))
    styles.add(ParagraphStyle('Cell', fontName='ReportVera', fontSize=8, leading=11, textColor=colors.HexColor(NAVY)))
    styles.add(ParagraphStyle('CellRight', parent=styles['Cell'], alignment=TA_RIGHT))
    styles.add(ParagraphStyle('HeaderCell', parent=styles['Cell'], fontName='ReportVeraBold', textColor=colors.white, fontSize=7.5, leading=10))
    def paragraph(value, style='ReportBody'):
        return Paragraph(escape(_text(value)).replace('\n', '<br/>'), styles[style])
    project, selection = context['project'], context['selection']
    total, budget = _sum(data, COMMERCIAL), _sum(data, 'Presupuesto vigente')
    known = int(data[COMMERCIAL].notna().sum())
    hours = context['hours']
    stamp = context['generated_at']
    doc = SimpleDocTemplate(output, pagesize=(page_width, page_height), leftMargin=32, rightMargin=32, topMargin=43, bottomMargin=36,
        title=f'Análisis comercial · {project} · {selection}', author='Control integral del proyecto', allowSplitting=1)
    def page_frame(c, document):
        c.setStrokeColor(colors.HexColor(GOLD)); c.setLineWidth(1.2); c.line(32, page_height-25, page_width-32, page_height-25)
        c.setFont('ReportVera', 7); c.setFillColor(colors.HexColor(MUTED))
        c.drawString(32, page_height-19, 'CONTROL INTEGRAL · INFORME DE SELECCIÓN COMERCIAL')
        c.drawRightString(page_width-32, page_height-19, project)
        c.drawString(32, 19, f'{currency} · {stamp} · Hora de Santiago')
        c.drawRightString(page_width-32, 19, f'Página {document.page}')
    story = [paragraph(project, 'ReportTitle'), paragraph(selection, 'SectionTitle')]
    selected_count = '1 partida seleccionada' if len(data) == 1 else f'{len(data)} partidas seleccionadas'
    meta = f"Alcance: {context['mode']} · {selected_count} · {known} con monto comercial · Solo Aplica en Costos"
    story.append(paragraph(meta))
    date_note = f"Corte del documento: {context.get('cutoff') or 'Sin informar'} · Datos consultados: {context.get('consulted_at') or 'Sin informar'}"
    story.append(paragraph(date_note))
    if currency == 'USD':
        story.append(paragraph('Conversión de visualización: 1 USD = '+_decimal(context['fx_rate'], 2)+' CLP. La fuente original está en CLP.'))
    cards = []
    for label, value, color in [('HH informadas', _decimal(hours)+' HH' if pd.notna(hours) else 'Sin informar', TEAL),
        ('Monto comercial · '+currency, _money(total, currency), RUST), ('Presupuesto vigente · '+currency, _money(budget, currency), NAVY)]:
        cards.append(Paragraph('<font size="9">'+escape(label)+'</font><br/><br/><font name="ReportVeraBold" size="17" color="'+color+'">'+escape(value)+'</font>', styles['ReportBody']))
    card_table = Table([cards], colWidths=[width/3]*3, rowHeights=65)
    card_table.setStyle(TableStyle([('BACKGROUND',(0,0),(0,0),colors.HexColor('#F0FDFA')),('BACKGROUND',(1,0),(1,0),colors.HexColor('#FFF1ED')),('BACKGROUND',(2,0),(2,0),colors.HexColor('#F5F8FB')),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#DCE5EA')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),13)]))
    story += [card_table, Spacer(1, 10)]
    if context.get('missing_hours', 0):
        missing_note = '1 partida HH sin cantidad informada.' if context['missing_hours'] == 1 else f"{context['missing_hours']} partidas HH sin cantidad informada."
        story.append(paragraph(missing_note+' No se estiman horas ni se suman cantidades de insumos como HH.'))
    story += [SelectionCharts(data, currency, width), Spacer(1, 8), paragraph('Los gráficos representan exclusivamente las partidas seleccionadas. Los importes faltantes no se interpretan como cero. El subtotal informado no equivale a un precio de venta. La agrupación de otras líneas afecta solo al gráfico; el detalle conserva todas las partidas.')]
    story += [PageBreak(), paragraph('Detalle económico de las partidas', 'SectionTitle'), paragraph('Descripciones completas y valores de Costos. Orden natural por ID; importes expresados en '+currency+'.')]
    economic_fields = ['ID', 'Actividad / entregable', 'Criterio', 'Cantidad', 'Costo por unidad · CLP', COMMERCIAL, 'Presupuesto vigente', 'Variación %']
    headers = ['ID', 'Actividad / entregable', 'Criterio', 'Cantidad', 'Costo por unidad\n'+currency, 'Monto comercial\n'+currency, 'Presupuesto vigente\n'+currency, 'Variación %']
    def table(rows, widths, commercial_col=None):
        result = LongTable(rows, colWidths=widths, repeatRows=1, hAlign='LEFT', splitInRow=1)
        commands = [('BACKGROUND',(0,0),(-1,0),colors.HexColor(NAVY)), ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),1,colors.HexColor(GOLD)),('INNERGRID',(0,1),(-1,-1),.3,colors.HexColor('#E2E7EB')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#F7F9FB')])]
        if commercial_col is not None:
            commands.append(('BACKGROUND',(commercial_col,1),(commercial_col,-1),colors.HexColor('#FFF1ED')))
        result.setStyle(TableStyle(commands))
        return result
    rows = [[paragraph(value, 'HeaderCell') for value in headers]]
    for _, row in data.iterrows():
        cells = []
        for field in economic_fields:
            value = row.get(field)
            if field in ['Costo por unidad · CLP', COMMERCIAL, 'Presupuesto vigente']:
                value = _money(value, currency)
            elif field == 'Variación %':
                value = ('+' if pd.notna(value) and value >= 0 else '')+_decimal(value)+'%' if pd.notna(value) else 'Sin cálculo'
            cells.append(paragraph(value, 'CellRight' if field in economic_fields[3:] else 'Cell'))
        rows.append(cells)
    story.append(table(rows, [34, width-34-47-55-88-98-100-59, 47,55,88,98,100,59], 5))
    story += [Spacer(1, 9), paragraph('Variación = (presupuesto vigente − monto comercial) / monto comercial × 100. Positivo: presupuesto superior. Sin cálculo si falta un importe o el comercial es cero.')]
    story += [PageBreak(), paragraph('Líneas, participaciones y conciliación', 'SectionTitle'), paragraph('Se conserva la misma selección y orden de IDs del detalle económico. Los porcentajes usan los denominadores completos de la turbina, aunque se filtre una línea o un hito.')]
    headers = ['ID','Línea del sistema','% del paquete','% del proyecto','Registros conciliados']
    rows = [[paragraph(value, 'HeaderCell') for value in headers]]
    for _, row in data.iterrows():
        cells = [row['ID'], row.get('Paquete / línea')]
        cells += [_decimal(row.get(field), 2)+'%' if pd.notna(row.get(field)) else 'Sin cálculo' for field in ['% del paquete','% del proyecto']]
        cells += [row.get('Registros conciliados')]
        rows.append([paragraph(value, 'Cell') for value in cells])
    story.append(table(rows, [45, width-45-100-105-185,100,105,185]))
    story += [Spacer(1, 12), paragraph('Bases del análisis', 'SectionTitle'), paragraph('% del paquete: monto comercial del ID / total comercial de su mismo sistema y línea en la turbina completa. % del proyecto: monto comercial del ID / total comercial de la turbina completa. Se incluyen solo partidas Aplica de Costos; una base nula o cero queda sin cálculo.'), paragraph('Costo por unidad: Presupuesto referencia de Costos. Cantidad y Registros conciliados: Costos, vinculados por ID. Criterio: Plan. Los estados de conciliación se reproducen como están publicados; no constituyen una validación adicional.')]
    if context.get('source_url'):
        story.append(Paragraph('<link href="'+escape(context['source_url'], {'"':'&quot;'})+'" color="'+TEAL+'">Abrir documento fuente publicado</link>', styles['ReportBody']))
    doc.build(story, onFirstPage=page_frame, onLaterPages=page_frame)
    return output.getvalue()
