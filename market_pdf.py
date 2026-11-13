"""Editorial market report with four vector charts matching the application data."""
from html import escape
from io import BytesIO
import math

from reportlab.graphics.shapes import Drawing, Line, Rect, String, Circle, Wedge
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak)

from market_analytics import analytics_data, usd, percent, NAVY, TEAL, GOLD, CORAL

INK=colors.HexColor(NAVY)
MUTED=colors.HexColor('#627588')
LINE=colors.HexColor('#DCE5ED')
PALE=colors.HexColor('#F3F7FA')
WHITE=colors.white


def label(drawing,x,y,text,size=8,color=INK,bold=False,anchor='start'):
    drawing.add(String(x,y,str(text),fontName='Helvetica-Bold' if bold else 'Helvetica',
        fontSize=size,fillColor=color,textAnchor=anchor))


def dashboard_drawings(data,width):
    """Same four data views as the app, drawn as resolution-independent PDF vectors."""
    height=157
    price=Drawing(width,height)
    left,right,bottom,top=116,width-18,24,145
    maximum=math.ceil(max(r['high'] for r in data['price_refs'])/500)*500
    def px(value):return left+(right-left)*value/maximum
    for value in range(0,int(maximum)+1,500):
        x=px(value)
        price.add(Line(x,bottom,x,top,strokeColor=PALE,strokeWidth=.6))
        label(price,x,bottom-12,str(value),7,MUTED,anchor='middle')
    fw_x=px(data['price_kw'])
    price.add(Line(fw_x,bottom,fw_x,top,strokeColor=INK,strokeWidth=.7,strokeDashArray=[2,2]))
    for index,row in enumerate(data['price_refs']):
        y=top-8-index*31
        price.add(Line(left,y,right,y,strokeColor=LINE,strokeWidth=.5))
        label(price,left-8,y-3,row['label'],7.6,anchor='end')
        x1,x2=px(row['low']),px(row['high'])
        color=colors.HexColor(NAVY if row['fw'] else GOLD)
        price.add(Line(x1,y,x2,y,strokeColor=color,strokeWidth=3))
        if x1!=x2:
            for x in (x1,x2):price.add(Line(x,y-6,x,y+6,strokeColor=color,strokeWidth=2))
        price.add(Circle((x1+x2)/2,y,3.7,fillColor=color,strokeColor=None))
        value=usd(row['low'],2) if x1==x2 else usd(row['low'])+'–'+usd(row['high'])
        label(price,(x1+x2)/2,y+9,value,6.8,color,anchor='middle')
    label(price,(left+right)/2,0,'USD por kW nominal · precios netos / EXW',7.4,MUTED,anchor='middle')

    maturity=Drawing(width,height)
    left,right,bottom,top=134,width-17,24,145
    def tx(value):return left+(right-left)*(value-1)/8
    for value in range(1,10):
        x=tx(value)
        label(maturity,x,bottom-12,value,7,MUTED,anchor='middle')
    for index,row in enumerate(data['maturity']):
        y=top-10-index*46
        maturity.add(Line(left,y,right,y,strokeColor=LINE,strokeWidth=.5))
        label(maturity,left-9,y-3,row['label'],7.3,anchor='end')
        x1,x2=tx(row['low']),tx(row['high'])
        color=INK if row['label'].startswith('FW') else colors.HexColor(GOLD)
        maturity.add(Line(x1,y,x2,y,strokeColor=color,strokeWidth=3))
        for x in (x1,x2):maturity.add(Line(x,y-6,x,y+6,strokeColor=color,strokeWidth=2))
        maturity.add(Circle((x1+x2)/2,y,3.7,fillColor=color,strokeColor=None))
        value=str(row['low']) if row['low']==row['high'] else f'{row["low"]}–{row["high"]}'
        label(maturity,(x1+x2)/2,y+9,'TRL '+value,7,color,anchor='middle')
    label(maturity,(left+right)/2,0,'Escala TRL · rangos y valores reportados',7.4,MUTED,anchor='middle')

    geography=Drawing(width,height)
    palette=[NAVY,TEAL,GOLD,CORAL,'#718096','#CBD5E1']
    cx,cy,radius=82,81,64
    start=90
    total=data['competitor_count']
    for index,(country,count) in enumerate(data['countries'].items()):
        angle=count/total*360
        color=colors.HexColor(palette[index%len(palette)])
        geography.add(Wedge(cx,cy,radius,start-angle,start,fillColor=color,strokeColor=WHITE,strokeWidth=1.5))
        start-=angle
        y=137-index*23
        geography.add(Rect(168,y-3,7,7,fillColor=color,strokeColor=None))
        label(geography,181,y-2,country,8)
        label(geography,width-12,y-2,percent(count/total),8,bold=True,anchor='end')
    geography.add(Circle(cx,cy,radius*.67,fillColor=WHITE,strokeColor=None))
    label(geography,cx,cy+1,total,25,bold=True,anchor='middle')
    label(geography,cx,cy-14,'REFERENCIAS',6.5,MUTED,anchor='middle')
    label(geography,width/2,0,'Una fila de fabricante/modelo = una referencia',7.4,MUTED,anchor='middle')

    bridge=Drawing(width,height)
    left,right,bottom,top=39,width-12,28,136
    maximum=data['price']*1.2
    def by(value):return bottom+(top-bottom)*value/maximum
    for value in range(0,math.ceil(maximum/20000)*20000,20000):
        y=by(value)
        if y>top:continue
        bridge.add(Line(left,y,right,y,strokeColor=LINE,strokeWidth=.5))
        label(bridge,left-5,y-2,f'{value/1000:.0f}k',7,MUTED,anchor='end')
    values=[data['cost'],data['opex_cost']-data['cost'],data['spread'],data['price']]
    bases=[0,data['cost'],data['opex_cost'],0]
    tops=[data['cost'],data['opex_cost'],data['price'],data['price']]
    names=[['Costo','informado'],['OPEX','añadido'],['Diferencia','al precio'],['Precio','neto']]
    spacing=(right-left)/4
    bar=spacing*.68
    for index,(value,base,top_value,name) in enumerate(zip(values,bases,tops,names)):
        x=left+spacing*index+(spacing-bar)/2
        color=INK if index in (0,3) else colors.HexColor(TEAL)
        bridge.add(Rect(x,by(base),bar,by(top_value)-by(base),fillColor=color,strokeColor=None))
        label(bridge,x+bar/2,by(top_value)+6,usd(value),6.7,anchor='middle')
        label(bridge,x+bar/2,15,name[0],7.3,MUTED,anchor='middle')
        label(bridge,x+bar/2,5,name[1],7.3,MUTED,anchor='middle')
        if index<2:
            bridge.add(Line(x+bar,by(top_value),x+spacing,by(top_value),strokeColor=MUTED,strokeWidth=.6,strokeDashArray=[2,2]))
    label(bridge,left,146,'USD por equipo · snapshot del estudio',7.3,MUTED)
    return [
        ('Precio por potencia nominal',price,'Cap. 5 · R&X: distribuidor; GH: ex-works, OEM por verificar; Greef: kit híbrido 10 kW, oferta vencida. Alcances sin homologar.'),
        ('Madurez y distancia a la validación',maturity,'Cap. 3–4 · FW: evaluación provisional del estudio. Wind Harvest: declaración del fabricante. No son auditorías homogéneas ni intervalos estadísticos.'),
        ('Composición geográfica de la muestra',geography,'Cap. 4 · Porcentajes de las referencias revisadas; no representan cuotas de mercado, ventas ni capacidad instalada. FW no integra esta muestra externa.'),
        ('Del costo informado al precio FW',bridge,'Cap. 5 · Concepto de 80 kW. Costo + OPEX añadido + diferencia aritmética = precio neto. La diferencia no equivale a utilidad neta.')]


def build_report(document,source):
    data=analytics_data(document)
    output=BytesIO()
    page=landscape(A4)
    doc=SimpleDocTemplate(output,pagesize=page,leftMargin=38,rightMargin=38,topMargin=39,bottomMargin=37,
        title='Estudio de mercado VAWT · Posición competitiva FW Axial',author='FW Axial Energy')
    styles=getSampleStyleSheet()
    definitions=[
        ('Title',dict(fontName='Helvetica-Bold',fontSize=28,leading=33,textColor=INK,spaceAfter=10)),
        ('Heading',dict(fontName='Helvetica-Bold',fontSize=18,leading=23,textColor=INK,spaceAfter=10,keepWithNext=True)),
        ('Sub',dict(fontName='Helvetica-Bold',fontSize=11,leading=15,textColor=INK,spaceBefore=10,spaceAfter=6,keepWithNext=True)),
        ('Eyebrow',dict(fontName='Helvetica-Bold',fontSize=8,leading=11,textColor=colors.HexColor('#476D70'),spaceAfter=8)),
        ('Body',dict(fontName='Helvetica',fontSize=9,leading=13.5,textColor=INK,spaceAfter=7)),
        ('Note',dict(fontName='Helvetica',fontSize=7.3,leading=10,textColor=MUTED,spaceAfter=5)),
        ('Cell',dict(fontName='Helvetica',fontSize=8,leading=11.5,textColor=INK)),
        ('TH',dict(fontName='Helvetica-Bold',fontSize=8,leading=11,textColor=WHITE)),
        ('KPI',dict(fontName='Helvetica-Bold',fontSize=20,leading=25,textColor=INK)),
        ('ChartTitle',dict(fontName='Helvetica-Bold',fontSize=10.5,leading=14,textColor=INK,spaceAfter=5))]
    for name,kwargs in definitions:styles.add(ParagraphStyle('FW'+name,**kwargs))
    def p(text,style='Body'):return Paragraph(escape(text),styles['FW'+style])
    def table(rows,width=None):
        columns=max(map(len,rows))
        content=[[p(value,'TH' if index==0 else 'Cell') for value in row]+['']*(columns-len(row)) for index,row in enumerate(rows)]
        result=Table(content,colWidths=[(width or doc.width)/columns]*columns,repeatRows=1,hAlign='LEFT')
        result.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),INK),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[WHITE,PALE]),('LINEBELOW',(0,0),(-1,0),2,colors.HexColor(TEAL)),
            ('LINEBELOW',(0,1),(-1,-1),.3,LINE),('LEFTPADDING',(0,0),(-1,-1),10),
            ('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        return result
    def chapter(eyebrow,title):return [p(eyebrow,'Eyebrow'),p(title,'Heading')]
    def blocks(items):
        flow=[]
        for block in items:
            kind=block['kind']
            if kind=='table':flow.extend([table(block['rows']),Spacer(1,12)])
            else:
                text=('• ' if kind=='bullet' else '')+block['text']
                flow.append(p(text,'Sub' if kind=='subheading' else 'Body'))
        return flow
    sections=document['sections']
    def section(prefix):return next(s for s in sections if s['title'].startswith(prefix))
    preface=[b['text'] for b in document['preface'] if b['kind']=='paragraph']
    date=next((text for text in preface if text.startswith('Fecha de corte:')),'')
    thesis=next((text.removeprefix('Conclusión ejecutiva.').strip() for text in preface if text.startswith('Conclusión ejecutiva.')),'')
    banner=Drawing(doc.width,82)
    banner.add(Rect(0,0,doc.width,82,fillColor=INK,strokeColor=None))
    banner.add(Rect(0,78,doc.width,4,fillColor=colors.HexColor(GOLD),strokeColor=None))
    label(banner,20,57,'FW AXIAL ENERGY / INTELIGENCIA DE MERCADO',9,colors.HexColor('#B8D4D1'),True)
    label(banner,20,23,'VAWT · oportunidad y posición competitiva',24,WHITE,True)
    story=[banner,Spacer(1,12),p(date,'Note')]
    cards=[('PRECIO NETO · 80 kW',usd(data['price']),'Precio del concepto en el estudio'),
        ('PRECIO POR kW',usd(data['price_kw'],2),'Precio neto / potencia nominal'),
        ('DIFERENCIA / PRECIO',percent(data['spread_ratio']),'Sobre costo + OPEX; no utilidad neta'),
        ('PRECIOS EXTERNOS',f'{data["priced_competitors"]} de {data["competitor_count"]}','Referencias USD de la muestra')]
    kpis=Table([[[p(name,'Note'),p(value,'KPI'),p(note,'Note')] for name,value,note in cards]],colWidths=[doc.width/4]*4)
    kpis.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PALE),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    story.extend([kpis,Spacer(1,12),p('La tesis: competir con evidencia y servicio','Sub'),p(thesis)])
    context=data.get('context')
    if context:
        story.extend([p('El contexto eólico tiene escala; el nicho VAWT aún requiere validación','Sub'),
            p(f'{context["global_gw"]} GW nuevos en el mundo ({context["global_year"]}) · {context["latam_gw"]} GW acumulados en Latinoamérica ({context["latam_year"]}) · ≈ {context["brazil_share"]}% del acumulado regional en Brasil.'),
            p('Fuente: GWEC citado en el capítulo 2. Eólica total dominada por HAWT; estas métricas no cuantifican demanda ni participación VAWT.','Note')])
    decisions=[['AHORA / 10 kW','SIGUIENTE / 80 kW','PARA VENDER'],
        ['Cerrar FAT/SAT, medir curva y disponibilidad en campo. TRL 5–6 provisional.',
         'Congelar diseño, revisar cargas y ensayar un prototipo integrado. TRL 3–4 provisional.',
         'Homologar tres ofertas OEM y una HAWT por sitio, alcance, AEP, garantía y costo instalado.']]
    story.extend([table(decisions),PageBreak()])

    # All four charts share one editorial dashboard page, matching the app.
    story.extend(chapter('MAPA COMPETITIVO / CUATRO LECTURAS','Dónde estamos frente a las referencias'))
    drawings=dashboard_drawings(data,(doc.width-24)/2)
    rows=[]
    for pair in (drawings[:2],drawings[2:]):
        rows.append([[p(title,'ChartTitle'),drawing,Spacer(1,5),p(note,'Note')] for title,drawing,note in pair])
    dashboard=Table(rows,colWidths=[doc.width/2]*2)
    dashboard.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),
        ('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),9),
        ('BOX',(0,0),(0,0),.5,LINE),('BOX',(1,0),(1,0),.5,LINE),('BOX',(0,1),(0,1),.5,LINE),('BOX',(1,1),(1,1),.5,LINE)]))
    story.extend([dashboard,PageBreak()])

    # Decision-oriented order; complete documentary content remains available.
    order=[('01 / VALIDACIÓN TÉCNICA','Qué debe demostrar FW antes de escalar','3.'),
        ('02 / RUTA COMERCIAL','Cómo convertir el piloto en una oferta defendible','6.'),
        ('03 / COMPETENCIA','Fabricantes, modelos y evidencia disponible','4.'),
        ('04 / ECONOMÍA Y ALCANCE','Precios comparables y condiciones de compra','5.'),
        ('05 / DEMANDA Y SEGMENTOS','Dónde buscar los primeros clientes','2.'),
        ('06 / CONTROL DE RIESGOS','Preguntas que deben cerrar la inversión','7.'),
        ('07 / CONCLUSIONES','Criterios para la decisión comercial','8.'),
        ('ANEXO / MÉTODO','Cómo interpretar el respaldo documental','1.'),
        ('ANEXO / SÍNTESIS DE LA FUENTE','Lecturas ejecutivas del documento publicado','Síntesis'),
        ('ANEXO / TRAZABILIDAD','Fuentes y referencias documentales','Fuentes')]
    for index,(eyebrow,title,prefix) in enumerate(order):
        if index:story.append(PageBreak())
        original=section(prefix)
        story.extend(chapter(eyebrow,title))
        story.append(p('Respaldo de origen: '+original['title'],'Note'))
        story.extend(blocks(original['blocks']))
    story.extend([Spacer(1,10),p('Documento publicado: '+source,'Note')])
    def decoration(canvas,current):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(TEAL));canvas.rect(0,page[1]-5,page[0],5,stroke=0,fill=1)
        canvas.setStrokeColor(LINE);canvas.line(doc.leftMargin,27,page[0]-doc.rightMargin,27)
        canvas.setFillColor(INK);canvas.setFont('Helvetica-Bold',7)
        canvas.drawString(doc.leftMargin,16,'FW AXIAL ENERGY / ESTUDIO DE MERCADO VAWT')
        canvas.setFont('Helvetica',7);canvas.drawRightString(page[0]-doc.rightMargin,16,f'{current.page:02d}')
        canvas.restoreState()
    doc.build(story,onFirstPage=decoration,onLaterPages=decoration)
    return output.getvalue()
