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


class ComparisonBars(Flowable):
    """Paginated vector charts; every selected comparison row is included."""
    def __init__(self, frame, context, width, normalized=False):
        super().__init__()
        self.frame, self.context, self.width, self.normalized = frame, context, width, normalized
        self.height = 48 + 55*len(frame)

    def draw(self):
        from textwrap import shorten
        c, width = self.canv, self.width
        c.setStrokeColor(colors.HexColor('#DEE6EB'));c.setFillColor(colors.white)
        c.roundRect(0,0,width,self.height,8,fill=1,stroke=1)
        c.setFont('ReportVeraBold',9)
        c.setFillColor(colors.HexColor(NAVY))
        title = 'Variación del costo por kW · 80 frente a 10 kW' if self.normalized else self.context['metric']
        c.drawString(13,self.height-20,title)
        if not self.normalized:
            for x,label,color in [(250,'Turbina de 10 kW',NAVY),(400,'Turbina de 80 kW',GOLD)]:
                c.setFillColor(colors.HexColor(color));c.rect(x,self.height-22,7,7,fill=1,stroke=0)
                c.setFont('ReportVera',8);c.drawString(x+12,self.height-21,label)
        fields = ['Variación por kW %'] if self.normalized else [self.context['metric_field']+' 10',self.context['metric_field']+' 80']
        values = self.frame[fields].apply(pd.to_numeric,errors='coerce')
        maximum = values.abs().max().max()
        maximum = float(maximum) if pd.notna(maximum) and maximum > 0 else 1
        negative = self.normalized or values.lt(0).any().any()
        origin, length = (410,165) if negative else (215,365)
        if self.normalized:
            c.setStrokeColor(colors.HexColor('#CBD5E1'));c.line(origin,12,origin,self.height-38)
        y=self.height-54
        for _,row in self.frame.iterrows():
            label = row['Sistema']+(' · '+str(row['Paquete / línea']) if 'Paquete / línea' in self.frame else '')
            label = shorten(str(label),width=110,placeholder='…')
            style=ParagraphStyle('ChartLabel',fontName='ReportVera',fontSize=8,leading=10,textColor=colors.HexColor(NAVY))
            p=Paragraph(escape(label),style);_,height=p.wrap(185,60);p.drawOn(c,12,y+8-height)
            for i,field in enumerate(fields):
                value=row[field];bar_y=y-i*14
                color=TEAL if self.normalized and pd.notna(value) and value<0 else GOLD if self.normalized or i else NAVY
                if pd.notna(value):
                    size=length*abs(value)/maximum;c.setFillColor(colors.HexColor(color))
                    c.rect(origin-size if value<0 else origin,bar_y-4,size,8,fill=1,stroke=0)
                if self.normalized:
                    display=(_decimal(value)+'%') if pd.notna(value) else 'Sin cálculo'
                elif self.context['metric_field'] in ('HH','HH/kW'):
                    display=_decimal(value,2)+' '+self.context['metric_field'] if pd.notna(value) else 'Sin informar'
                else:
                    display=_money(value,self.context['currency'])+('/kW' if self.context['metric_field']=='Costo/kW' and pd.notna(value) else '')
                c.setFillColor(colors.HexColor(MUTED));c.setFont('ReportVera',8);c.drawString(610,bar_y-2,display)
            y-=55


def build_comparison_pdf(frame, context):
    """Export the whole filtered comparison matrix and both charts as vector PDF."""
    _fonts()
    data=frame.copy().reset_index(drop=True)
    currency=context['currency'];width=landscape(A4)[0]-64
    output=BytesIO()
    styles={
        'title':ParagraphStyle('CompTitle',fontName='ReportVeraBold',fontSize=23,leading=29,textColor=colors.HexColor(NAVY),spaceAfter=10),
        'section':ParagraphStyle('CompSection',fontName='ReportVeraBold',fontSize=14,leading=19,textColor=colors.HexColor(NAVY),spaceAfter=9),
        'body':ParagraphStyle('CompBody',fontName='ReportVera',fontSize=9,leading=13,textColor=colors.HexColor(MUTED),spaceAfter=7),
        'cell':ParagraphStyle('CompCell',fontName='ReportVera',fontSize=8,leading=11,textColor=colors.HexColor(NAVY)),
        'head':ParagraphStyle('CompHead',fontName='ReportVeraBold',fontSize=7.5,leading=10,textColor=colors.white),
    }
    def p(value,style='body'):
        return Paragraph(escape(_text(value)).replace('\n','<br/>'),styles[style])
    def change(current,base):
        return (current-base)/base*100 if pd.notna(base) and base>0 and pd.notna(current) else float('nan')
    def percent(value):
        return _decimal(value)+'%' if pd.notna(value) else 'Sin cálculo'
    def table(rows,widths):
        t=LongTable(rows,colWidths=widths,repeatRows=1,splitInRow=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor(NAVY)),('LINEBELOW',(0,0),(-1,0),1,colors.HexColor(GOLD)),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('INNERGRID',(0,1),(-1,-1),.3,colors.HexColor('#E2E7EB')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F7F9FB')])]))
        return t
    doc=SimpleDocTemplate(output,pagesize=landscape(A4),leftMargin=32,rightMargin=32,topMargin=43,bottomMargin=36,title='Comparación técnica y comercial · Turbinas de 10 kW y 80 kW',author='Control integral del proyecto')
    def page_frame(c,document):
        page_width,page_height=landscape(A4)
        c.setStrokeColor(colors.HexColor(GOLD));c.line(32,page_height-25,page_width-32,page_height-25)
        c.setFillColor(colors.HexColor(MUTED));c.setFont('ReportVera',7)
        c.drawString(32,page_height-19,'CONTROL INTEGRAL · COMPARACIÓN DE TURBINAS · 10 kW / 80 kW')
        c.drawString(32,19,f"{currency} · {context['generated_at']} · Hora de Santiago")
        c.drawRightString(page_width-32,19,f'Página {document.page}')
    row_count_label = '1 fila seleccionada' if len(data) == 1 else f'{len(data)} filas seleccionadas'
    story=[p('Comparación de turbinas','title'),p('Turbina de 10 kW frente a Turbina de 80 kW','section'),p(context['selection']),p(f"Alcance: {context['mode']} · {context['level']} · {row_count_label} · Moneda: {currency}"),p(f"Corte: {context.get('cutoff') or 'Sin informar'} · Datos consultados: {context.get('consulted_at') or 'Sin informar'}")]
    if currency=='USD':
        story.append(p('Tipo de cambio: 1 USD = '+_decimal(context['fx_rate'],2)+' CLP. Los importes ya están convertidos una sola vez.'))
    totals={cap:_sum(data,f'Comercial {cap}') for cap in (10,80)}
    cards=[]
    for cap in (10,80):
        cards.append(Paragraph('<font size="10">TURBINA DE '+str(cap)+' kW · '+currency+'</font><br/><br/><font name="ReportVeraBold" size="19" color="'+NAVY+'">'+escape(_money(totals[cap],currency))+'</font><br/><font size="9">'+escape(_money(totals[cap]/cap,currency))+' / kW</font>',styles['body']))
    cards_table=Table([cards],colWidths=[width/2]*2,rowHeights=83)
    cards_table.setStyle(TableStyle([('BACKGROUND',(0,0),(0,0),colors.HexColor('#F2F6F9')),('BACKGROUND',(1,0),(1,0),colors.HexColor('#FCF8EC')),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#DEE6EB')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),14)]))
    story += [cards_table,Spacer(1,10),p('Variación total: '+percent(change(totals[80],totals[10]))+' · Variación del costo por kW: '+percent(change(totals[80]/80,totals[10]/10))+' · Diferencia comercial: '+_money(totals[80]-totals[10],currency))]
    rows=[[p('Indicador','head'),p('Turbina de 10 kW','head'),p('Turbina de 80 kW','head')]]
    metrics=[('Presupuesto vigente',lambda cap:_money(_sum(data,f'Presupuesto {cap}'),currency)),('HH informadas',lambda cap:_decimal(_sum(data,f'HH {cap}'))+' HH'),('HH informadas por kW',lambda cap:_decimal(_sum(data,f'HH {cap}')/cap,2)+' HH/kW'),('Partidas con monto / partidas totales',lambda cap:str(int(data[f'Informadas {cap}'].sum()))+' / '+str(int(data[f'Partidas {cap}'].sum()))),('Cobertura de montos',lambda cap:percent(data[f'Informadas {cap}'].sum()/data[f'Partidas {cap}'].sum()*100) if data[f'Partidas {cap}'].sum()>0 else 'Sin partidas'),('Partidas HH sin cantidad',lambda cap:str(int(data[f'HH pendientes {cap}'].sum())))]
    for label,formatter in metrics:
        rows.append([p(label,'cell'),p(formatter(10),'cell'),p(formatter(80),'cell')])
    story += [table(rows,[width*.40,width*.30,width*.30]),Spacer(1,9),p('Los indicadores reflejan solo la selección actual. Los montos faltantes no son cero. Una reducción por kW no prueba ahorro validado si difieren el alcance técnico o la cobertura de registros.')]
    for normalized in (False,True):
        heading='Variación normalizada por kW' if normalized else 'Comparación gráfica · '+context['metric']
        for start in range(0,len(data),6):
            chunk=data.iloc[start:start+6]
            story += [PageBreak(),p(heading,'section'),p(context['selection']+f' · Filas {start+1}–{start+len(chunk)} de {len(data)}'),ComparisonBars(chunk,context,width,normalized),Spacer(1,7),p('Negativo = menor costo informado por kW. Sin cálculo si falta un monto o la base de 10 kW no es positiva.' if normalized else 'Cada fila conserva la misma selección del gráfico en pantalla. Los nombres extensos se abrevian solo en gráficos; la matriz mantiene los nombres completos.')]
    groups=[
        ('Montos y presupuesto',['Comercial 10','Comercial 80','Diferencia comercial','Variación total %','Presupuesto 10','Presupuesto 80']),
        ('Normalización y participación',['Costo/kW 10','Costo/kW 80','Variación por kW %','Participación % 10','Participación % 80','Cambio participación · pp']),
        ('Mano de obra e intensidad técnica',['HH 10','HH 80','HH/kW 10','HH/kW 80','HH pendientes 10','HH pendientes 80']),
        ('Cobertura y comparabilidad',['Partidas 10','Partidas 80','Informadas 10','Informadas 80','Cobertura % 10','Cobertura % 80','Comparabilidad']),
    ]
    money={'Comercial 10','Comercial 80','Diferencia comercial','Presupuesto 10','Presupuesto 80','Costo/kW 10','Costo/kW 80'}
    for heading,fields in groups:
        story += [PageBreak(),p('Matriz · '+heading,'section'),p('Referencias R01, R02… conservadas en todas las secciones. Importes en '+currency+'. Las participaciones usan el total del alcance de cada turbina y no cambian al filtrar sistemas o líneas.')]
        headers=['Ref.','Sistema / línea',*[(field+'\n'+currency) if field in money else field for field in fields]]
        rows=[[p(value,'head') for value in headers]]
        for index,row in data.iterrows():
            label=row['Sistema']+(' · '+str(row['Paquete / línea']) if 'Paquete / línea' in data else '')
            cells=[f'R{index+1:02d}',label]
            for field in fields:
                value=row[field]
                if field in money:value=_money(value,currency)
                elif '%' in field:value=percent(value)
                elif field=='Cambio participación · pp':value=_decimal(value)+' pp' if pd.notna(value) else 'Sin cálculo'
                elif field.startswith('HH/kW'):value=_decimal(value,2)
                elif field in ('HH 10','HH 80'):value=_decimal(value)
                cells.append(value)
            rows.append([p(value,'cell') for value in cells])
        label_width=180 if len(fields)>6 else 220
        story.append(table(rows,[32,label_width,*([(width-32-label_width)/len(fields)]*len(fields))]))
    story += [Spacer(1,12),p('Bases y trazabilidad','section'),p('Fuente: Costos · Comercial anterior y Presupuesto vigente, solo Costo para producto = Aplica; cada turbina se asigna por Hito objetivo. Variación = (80 − 10) / 10 × 100; costo/kW divide por la potencia correspondiente. Las HH suman cantidades solo con criterio HH; las cantidades faltantes no se estiman. Se alinean nombres de sistema y sistema + línea, sin inferir equivalencia técnica entre nombres diferentes. Un sistema ausente se mantiene sin importe.'),p('La matriz se divide en cuatro secciones para conservar todas las columnas y los nombres completos, con encabezados repetidos al paginar.')]
    if context.get('source_url'):
        story.append(Paragraph('<link href="'+escape(context['source_url'], {'"':'&quot;'})+'" color="'+TEAL+'">Abrir documento fuente publicado</link>',styles['body']))
    doc.build(story,onFirstPage=page_frame,onLaterPages=page_frame)
    return output.getvalue()
