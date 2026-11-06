"""Executive vector PDF: documented 80 kW scope and consolidated financial case."""
from io import BytesIO, StringIO
from xml.sax.saxutils import escape
import csv
import re
import math

import pandas as pd
import requests
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, TableStyle, LongTable
from reportlab.pdfgen.canvas import Canvas
from commercial_report import _fonts
from valuation_data import SOURCE as FINANCIAL_SOURCE
from valuation_finance import unit_economics, financial_diagnostics, projection_diagnostics, divide, complete_sum

PROJECT_SOURCE='https://docs.google.com/spreadsheets/d/e/2PACX-1vQOSK1DE0sEuK5Cl-bIahOjtdP6qsBobzqSlekorQCY9gRpwhRDzHYxh9c-Q-mKoQ/pub'
PLAN_GID='1622224524'
INK='#203E58';BLUE='#315E7D';TEAL='#3B8F96';MUTED='#627588';PALE='#F0F5F9';LINE='#DCE5ED';RUST='#AD6551'
W,H=landscape(A4);M=30;CW=W-2*M
FONT='ReportVera';BOLD='ReportVeraBold'


def parse_technical(rows):
    header=next((i for i,row in enumerate(rows) if 'ID' in row and 'Actividad / entregable' in row and 'Hito objetivo' in row),None)
    if header is None:raise ValueError('Plan no contiene los encabezados técnicos esperados.')
    records=[dict(zip(rows[header],row)) for row in rows[header+1:]]
    records=[r for r in records if re.fullmatch(r'A\d+',r.get('ID','').strip()) and re.search(r'(?<!\d)80\s*k\s*w\b',r.get('Hito objetivo',''),re.I)]
    if not records:raise ValueError('Plan no contiene actividades identificadas con Hito objetivo 80 kW.')
    return pd.DataFrame(records).sort_values('ID',key=lambda s:s.str.extract(r'(\d+)',expand=False).astype(int)).reset_index(drop=True)


@st.cache_data(ttl=60,max_entries=4,show_spinner=False)
def load_technical(revision):
    response=requests.get(PROJECT_SOURCE,params={'output':'csv','gid':PLAN_GID,'_cb':revision},headers={'Cache-Control':'no-cache'},timeout=(8,30))
    response.raise_for_status()
    return parse_technical(list(csv.reader(StringIO(response.content.decode('utf-8-sig')))))


def decimal(value,digits=1):
    return 'Sin dato' if pd.isna(value) or not math.isfinite(float(value)) else f'{value:,.{digits}f}'.replace(',','X').replace('.',',').replace('X','.')


class Report:
    def __init__(self,model,currency,fx):
        self.model=model;self.currency=currency;self.fx=fx if currency=='CLP' else 1
        self.body=ParagraphStyle('body',fontName=FONT,fontSize=8.2,leading=11.4,textColor=colors.HexColor(INK),spaceAfter=0)
    def money(self,value,compact=False):
        if pd.isna(value):return 'Sin dato'
        value=value*self.fx;unit=1e6 if compact and abs(value)>=1e6 else 1e3 if compact and abs(value)>=1e3 else 1
        return ('US$ ' if self.currency=='USD' else '$')+decimal(value/unit,1 if unit>1 else 2 if self.currency=='USD' else 0)+(' MM' if unit==1e6 else ' mil' if unit==1e3 else '')
    def pct(self,value):return decimal(value*100)+'%' if pd.notna(value) else 'Sin dato'
    def p(self,text,size=8.2,color=INK,bold=False):
        style=ParagraphStyle('p',parent=self.body,fontName=BOLD if bold else FONT,fontSize=size,leading=size*1.36,textColor=colors.HexColor(color))
        return Paragraph(escape(str(text)),style)
    def para(self,c,x,y,width,text,size=8.2,color=INK,bold=False):
        p=self.p(text,size,color,bold);_,height=p.wrap(width,H);p.drawOn(c,x,y-height);return y-height
    def line(self,c,y):c.setStrokeColor(colors.HexColor(LINE));c.line(M,y,W-M,y)
    def header(self,c,number,title,subtitle):
        c.setFillColor(colors.HexColor(BLUE));c.rect(0,H-7,W,7,fill=1,stroke=0)
        self.para(c,M,H-23,CW,'FW AXIAL ENERGY  /  MEMORANDO TÉCNICO Y FINANCIERO',8.5,BLUE,True)
        self.para(c,M,H-43,CW-42,title,21,INK,True)
        self.para(c,W-M-32,H-33,32,number,20,TEAL,True)
        self.para(c,M,H-77,CW,subtitle,8,MUTED);self.line(c,H-99)
    def footer(self,c,page):
        self.line(c,27)
        self.para(c,M,21,CW-60,f'Caso publicado: {self.model["scenario"]} · {self.model["production"]} · Estado del aporte: {self.model["status"]} | Consultado: {self.model["fetched_at"]} | {self.currency}',6.4,MUTED)
        self.para(c,W-75,21,45,f'{page:02d}',7,BLUE,True)
    def table(self,rows,widths,size=7.5,header=True):
        cells=[[self.p(v,size,BLUE if i==0 and header else INK,i==0 and header) for v in row] for i,row in enumerate(rows)]
        t=LongTable(cells,colWidths=widths,repeatRows=1 if header else 0,hAlign='LEFT')
        commands=[('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor(LINE))]
        if header:commands.append(('BACKGROUND',(0,0),(-1,0),colors.HexColor(PALE)))
        for i in range(1,len(rows)):
            if i%2==0:commands.append(('BACKGROUND',(0,i),(-1,i),colors.HexColor('#F8FAFC')))
        t.setStyle(TableStyle(commands));return t
    def draw_table(self,c,x,y,rows,widths,size=7.5):
        t=self.table(rows,widths,size);_,height=t.wrap(sum(widths),H);t.drawOn(c,x,y-height);return y-height
    def kpis(self,c,y,items):
        width=CW/len(items);dense=len(items)>4;box=72 if dense else 64
        for i,(label,value,note) in enumerate(items):
            x=M+i*width;c.setFillColor(colors.HexColor(PALE if i==0 else '#FAFBFC'));c.rect(x,y-box,width-2,box,fill=1,stroke=0)
            self.para(c,x+10,y-8,width-20,label,7,MUTED,True)
            self.para(c,x+10,y-(30 if dense else 24),width-20,value,10.5 if dense else 14,INK,True)
            self.para(c,x+10,y-(51 if dense else 45),width-20,note,6.2 if dense else 6.4,MUTED)
        return y-box-12
    def bullets(self,c,x,y,width,items,size=8.2,gap=7):
        for title,text in items:
            c.setFillColor(colors.HexColor(TEAL));c.circle(x+2,y-5,2,fill=1,stroke=0)
            y=self.para(c,x+12,y,width-12,title+' — '+text,size)-gap
        return y


def technical_page(c,r,technical):
    r.header(c,'01','Turbina de 80 kW · alcance documentado','Ingeniería e integración industrial | Síntesis técnica de Plan · detalle por ID disponible en la fuente')
    y=H-111
    r.kpis(c,y,[('Potencia identificada','80 kW','Denominación del proyecto; no ensayo de potencia'),('Sistemas en Plan',str(technical['Sistema'].nunique()),'Alcance técnico y de ejecución'),('Actividades trazables',str(len(technical)),'Hitos que contienen 80 kW'),('Configuración','V80','Especificaciones sujetas a planos y validación')])
    y-=83;left=440;right=CW-left-22;xright=M+left+22
    r.para(c,M,y,left,'ARQUITECTURA Y ALCANCE POR COMPONENTE',9,BLUE,True);y-=20
    byid=technical.set_index('ID');groups=[('Rotor y palas FRP',['A336']),('Estructura y vigas',['A521','A526']),('Mástil e interfaces',['A533','A562']),('Apoyo rotor–mástil',['A581','A582']),('Conversión eléctrica',['A554']),('Controlador y seguridad',['A532']),('Inversor e interfaz eléctrica',['A555'])]
    rows=[['Subsistema','Especificación publicada / referencias']]
    for label,ids in groups:
        descriptions=[]
        for ident in ids:
            if ident in byid.index:
                text=str(byid.loc[ident,'Actividad / entregable']);limit=230 if ident=='A521' else 170 if ident=='A526' else 185 if len(ids)==1 else 100
                if len(text)>limit:text=text[:limit].rsplit(' ',1)[0]+'… (ver texto íntegro en Plan)'
                descriptions.append(ident+': '+text)
        rows.append([label,' '.join(descriptions) if descriptions else 'Sin especificación disponible para los IDs de referencia; revisar Plan.'])
    r.draw_table(c,M,y,rows,[110,left-110],7.1)
    yr=H-194
    r.para(c,xright,yr,right,'CADENA FUNCIONAL',9,BLUE,True);yr-=21
    for i,label in enumerate(['Rotor / aspas','Transmisión y apoyos','Generador + conversión','Control, protección e integración']):
        c.setFillColor(colors.HexColor(PALE));c.roundRect(xright,yr-31,right,31,4,fill=1,stroke=0)
        r.para(c,xright+10,yr-9,right-20,label,8,INK,True)
        yr-=39
    yr-=3;r.para(c,xright,yr,right,'Esquema funcional; no representa planos ni certificación del equipo.',7,MUTED);yr-=31
    yr=r.bullets(c,xright,yr,right,[('Control documental','Las actividades describen alcance y componentes previstos; no acreditan fabricación, ensayo ni recepción.'),('Desempeño por confirmar','No se documenta aquí curva de potencia medida de 80 kW, AEP por sitio, diámetro/altura final de rotor ni disponibilidad contractual.'),('Interfaz de red','Las normas citadas en la descripción del inversor son declaraciones de la partida; verificar certificados y requisitos de conexión aplicables.')],7.5)
    r.para(c,M,44,CW,'Fuente técnica: Plan del documento de control del proyecto. No se extrapolan dimensiones, velocidades de viento ni curvas del modelo de 10 kW.',7,MUTED)
    r.footer(c,1)


def five_year_summary(model):
    frame=model['annual'].loc[model['annual']['Año modelo'].gt(0)].iloc[:5]
    if frame.empty:raise ValueError('No hay años operativos para el resumen financiero.')
    result=projection_diagnostics(frame)
    result.update(start=frame.iloc[0]['Año'],end=frame.iloc[-1]['Año'],years=len(frame))
    return result


def financial_bullets(model,products,r):
    s=model['scalars'];a=model['annual'];first=a.iloc[1];p=products.set_index('Potencia kW');d=financial_diagnostics(model);five=five_year_summary(model)
    return [
      ('Valor y retorno económico',f'DCF a diez años + terminal {r.money(s["dcf"],True)}; VAN económico sin terminal {r.money(s["npv_economic"],True)} y TIR económica {r.pct(s["irr_economic"])}. VAN/TIR usan diez años sin terminal; resultados consolidados de 10 y 80 kW, no la TIR del socio ni de un equipo aislado.'),
      ('Economía unitaria 80 kW · '+first['Año'],f'Fabricación media {r.money(p.at[80,"Fabricación / equipo"])}; margen bruto {r.pct(p.at[80,"Margen bruto %"])}; contribución {r.money(p.at[80,"Contribución / equipo"])} por equipo antes de OPEX común. La contribución 10 kW es {r.money(p.at[10,"Contribución / equipo"])}; revisar la sostenibilidad del mix. No es EBITDA por turbina.'),
      ('Operación '+five['start']+'–'+five['end'],f'EBITDA acumulado {r.money(five["ebitda"],True)}; margen ponderado {r.pct(five["margin"])}. Conversión FCFF/EBITDA {decimal(five["cash_conversion"],2)}x; la caja incorpora anticipos ({r.pct(s["advance_rate"])}, {decimal(s["advance_days"],0)} días), CT, IVA y CAPEX.'),
      ('Inversión y negociación',f'Aporte primario {r.money(s["primary"],True)} por participación final {r.pct(s["investor_share"])}; compra secundaria {r.money(s["secondary"],True)}. Precio previo {r.money(s["pre_money"],True)}, separado del DCF; estado {model["status"]}.'),
      ('Capital y liquidez',f'Activos fijos aportados {r.money(s["assets_in_kind"],True)}; preoperacionales {r.money(s["preop"],True)} e inventario inicial {r.money(s["spares"],True)}. Caja inicial {r.money(s["cash_y0"],True)} frente a reserva {r.money(s["cash_target"],True)}.'),
      ('Sensibilidad y condiciones',f'Tasa {r.pct(s["rate"])} y crecimiento terminal {r.pct(s["growth"])}; el terminal pesa {r.pct(s["terminal_weight"])} del DCF. Payback económico descontado {decimal(d["Payback económico descontado"],2)} años. Revisar soporte comercial, técnico y condiciones pendientes; no constituye recomendación de inversión.'),
    ]


def finance_page(c,r):
    model=r.model;s=model['scalars'];a=model['annual'];first=a.iloc[1];products,gap=unit_economics(model,first['Año'])
    r.header(c,'02','Indicadores clave · tesis financiera','Caso consolidado 10 + 80 kW | Horizonte '+a.iloc[1]['Año']+'–'+a.iloc[-1]['Año']+' | Año unitario de referencia: '+first['Año']+' | Cifras en '+r.currency)
    five=five_year_summary(model)
    y=r.kpis(c,H-111,[('DCF · diez años + terminal',r.money(s['dcf'],True),'Valor indicativo consolidado'),('VAN económico · diez años',r.money(s['npv_economic'],True),'Sin terminal; incluye especie'),('TIR económica · diez años',r.pct(s['irr_economic']),'Sin terminal; no TIR del socio'),('Activos fijos aportados',r.money(s['assets_in_kind'],True),'Valor inicial; no anual'),('CAPEX FW · diez años',r.money(complete_sum(a.iloc[1:]['capex']),True),'Pagado por FW, acumulado'),('Peso terminal / DCF',r.pct(s['terminal_weight']),'DCF completo; no flujo anual')])
    r.para(c,M,y,CW,'OPERACIÓN · '+five['start']+'–'+five['end']+' / '+str(five['years'])+' AÑOS',8,BLUE,True)
    width=CW/4;top=y-17
    for i,(label,value) in enumerate([('Ventas acumuladas',r.money(five['sales'],True)),('EBITDA acumulado',r.money(five['ebitda'],True)),('Margen EBITDA ponderado',r.pct(five['margin'])),('FCFF acumulado',r.money(five['fcff'],True))]):
        x=M+i*width;c.setFillColor(colors.HexColor(PALE));c.rect(x,top-42,width-2,42,fill=1,stroke=0)
        r.para(c,x+9,top-5,width-18,label,7,MUTED,True);r.para(c,x+9,top-21,width-18,value,11,INK,True)
    y=top-53
    rows=[['Economía por equipo · '+first['Año'],'10 kW','80 kW']]
    fields=[('Entregas','Entregas','n'),('Precio de venta','Precio / equipo','m'),('Fabricación media','Fabricación / equipo','m'),('Margen bruto','Margen bruto %','p'),('OPEX específico','OPEX específico / equipo','m'),('Contribución pre-OPEX común','Contribución / equipo','m')]
    for label,field,kind in fields:
        values=products.set_index('Potencia kW')[field]
        rows.append([label,*[(r.money(values.at[cap]) if kind=='m' else r.pct(values.at[cap]) if kind=='p' else decimal(values.at[cap],0)) for cap in (10,80)]])
    r.draw_table(c,M,y,rows,[155,135,135],7.2)
    x=M+447;width=CW-447
    r.para(c,x,y,width,'COMPOSICIÓN DEL VALOR DCF',8,BLUE,True)
    vals=[('VAN de caja explícito',s['npv_cash'],BLUE),('VP del terminal',s['dcf']-s['npv_cash'],TEAL)]
    top=y-29;maximum=max([abs(v) for _,v,_ in vals]+[1])
    for label,value,color in vals:
        r.para(c,x,top,width,label+' · '+r.money(value,True),8,INK,True)
        c.setFillColor(colors.HexColor(color));c.rect(x,top-28,width*max(value,0)/maximum,12,fill=1,stroke=0);top-=40
    r.para(c,x,top+1,width,'VAN económico = VAN de caja explícito menos activos aportados. El capital nuevo se mantiene fuera del DCF.',7.3,MUTED)
    y-=146;r.line(c,y+6)
    left_items=financial_bullets(model,products,r)
    r.bullets(c,M,y-5,CW,left_items,7.3,gap=4)
    r.footer(c,2)


def projection_page(c,r):
    s=r.model['scalars'];a=r.model['annual'];operating=a[a['Año modelo'].gt(0)]
    r.header(c,'03','Proyección financiera y capital','Horizonte completo '+operating.iloc[0]['Año']+'–'+operating.iloc[-1]['Año']+' | Importes en '+r.currency+' | Flujos anuales y saldos al cierre')
    rows=[['Indicador · '+r.currency,*operating['Año'].tolist()]]
    for field,label,kind in [('sales','Ventas','m'),('ebitda','EBITDA','m'),('ebitda_margin','Margen EBITDA','p'),('fcff','FCFF','m'),('capex','CAPEX pagado por FW','m'),('cash_free','Caja libre al cierre','m'),('advances','Anticipos pendientes','m'),('units_80','Entregas 80 kW','n'),('units_10','Entregas 10 kW','n'),('external','Ampliar / externalizar','n')]:
        rows.append([label,*[(r.money(v,True) if kind=='m' else r.pct(v) if kind=='p' else decimal(v,0)) for v in operating[field]]])
    y=r.draw_table(c,M,H-112,rows,[112]+[(CW-112)/len(operating)]*len(operating),6.5)-12
    y=r.para(c,M,y,CW,'Flujos se suman; caja y anticipos son saldos al cierre. El margen EBITDA de cada año no se suma ni se promedia de forma simple. CAPEX pagado por FW no incluye nuevamente los activos fijos aportados.',7.2,MUTED)-12
    rows=[['Capital, patrimonio y liquidez','Importe','Criterio / período']]
    for key,label,note in [('assets_in_kind','Activos fijos iniciales / especie','Valor inicial; no salida de caja nueva'),('preop','Gastos preoperacionales','Iniciales; separados del CAPEX fijo'),('spares','Inventario inicial de repuestos','Inicial; no CAPEX fijo'),('economic_investment','Inversión económica inicial','Activos + preoperacionales + inventario inicial'),('cash_required','Uso de caja de arranque','Año 0, neto de anticipos'),('target_funding','Aporte para conservar caja objetivo','Arranque + reserva objetivo'),('historical_wc','CT histórico, referencia','Excluido de inversión inicial; evita duplicación')]:rows.append([label,r.money(s[key]),note])
    y=r.draw_table(c,M,y,rows,[230,180,CW-410],7)-10
    r.para(c,M,y,CW,'CAPEX pagado por FW en diez años: '+r.money(complete_sum(operating['capex']))+'. La inversión económica inicial incluye conceptos que no son CAPEX contable.',7.2,MUTED)
    r.footer(c,3)


def assumptions_page(c,r,fx):
    m=r.model;s=m['scalars'];a=m['annual'];first=a.iloc[1]['Año'];period=a.iloc[1]['Año']+'–'+a.iloc[-1]['Año']
    r.header(c,'04','Cifras exactas, supuestos y fuentes','Valorización a diez años · operación a cinco años · economía unitaria del primer año | Caso publicado, sin ajustes del laboratorio')
    left=(CW-20)/2;rightx=M+left+20
    exact=[['Indicador financiero','Importe / tasa']]
    for key,label in [('dcf','DCF 10 años + terminal'),('npv_cash','VAN caja · 10 años, sin terminal'),('npv_economic','VAN económico · 10 años, sin terminal'),('sales_y1','Ventas · '+first),('ebitda_y1','EBITDA · '+first),('fcff_y1','FCFF · '+first)]:exact.append([label,r.money(s[key])])
    exact.append(['TIR económica · 10 años, sin terminal',r.pct(s['irr_economic'])])
    bottom_left=r.draw_table(c,M,H-112,exact,[left*.57,left*.43],7.1)
    rows=[['Supuesto / operación','Valor publicado']]
    for label,value in [('Tasa / crecimiento terminal',r.pct(s['rate'])+' / '+r.pct(s['growth'])),('Anticipo / días de entrega',r.pct(s['advance_rate'])+' / '+decimal(s['advance_days'],0)+' días'),('Producción / escenario',m['production']+' / '+m['scenario']),('Inversionista / accionistas actuales',r.pct(s['investor_share'])+' / '+r.pct(s['founder_share'])),('Precio previo / posterior',r.money(s['pre_money'],True)+' / '+r.money(s['post_money'],True)),('TC interno / TC de presentación',decimal(s['model_fx'],2)+' / '+decimal(fx,2)+' CLP/USD')]:rows.append([label,value])
    bottom_right=r.draw_table(c,rightx,H-112,rows,[left*.55,left*.45],7.1)
    y=min(bottom_left,bottom_right)-19
    if not m['pending'].empty:
        r.para(c,M,y,left,'CONDICIONES PENDIENTES PUBLICADAS',8,BLUE,True)
        pending=m['pending'].iloc[:8]
        rows=[['Condición','Estado']]+pending.iloc[:,:2].astype(str).values.tolist()
        end=r.draw_table(c,M,y-15,rows,[left*.58,left*.42],6.8)
        if len(m['pending'])>8:r.para(c,M,end-6,left,str(len(m['pending'])-8)+' condiciones adicionales en la trazabilidad del panel.',7,MUTED)
    r.para(c,rightx,y,left,'CRITERIOS DE LECTURA',8,BLUE,True)
    r.bullets(c,rightx,y-18,left,[('Horizontes','DCF: '+period+' más terminal. VAN y TIR económicos: diez años sin terminal; incluyen activos aportados y no equivalen al retorno del socio.'),('Operación','Resumen de los cinco primeros años. Margen ponderado = suma de EBITDA / suma de ventas; ventas, EBITDA y FCFF son flujos acumulados.'),('Economía unitaria','Referencia '+first+': fabricación y OPEX específico / entregas; contribución antes del OPEX común. No es EBITDA por equipo.'),('Trazabilidad','Los detalles técnicos por ID se consultan en Plan. No se estima AEP, LCOE o DSCR sin los datos necesarios.')],7.1)
    counts='; '.join(str(n)+' '+status.lower() for status,n in m['checks']['Estado'].value_counts().items())
    r.para(c,M,66,CW,'Conciliaciones: '+counts+'. Verifican consistencia matemática, no validez contractual ni desempeño certificado.',7,MUTED)
    p=Paragraph('Fuentes: <link href="'+FINANCIAL_SOURCE+'html" color="'+BLUE+'">Modelo financiero · 00–09</link> | <link href="'+PROJECT_SOURCE+'html" color="'+BLUE+'">Plan · especificaciones y actividades 80 kW por ID</link>.',r.body)
    _,height=p.wrap(CW,40);p.drawOn(c,M,41-height)
    r.footer(c,4)


def build_executive_pdf(model,technical,currency='USD',fx=925.):
    if currency not in ('USD','CLP') or not math.isfinite(fx) or fx<=0:raise ValueError('Moneda o tipo de cambio inválidos para el informe.')
    _fonts();r=Report(model,currency,fx);out=BytesIO();c=Canvas(out,pagesize=(W,H));c.setTitle('Turbina 80 kW · Memorando técnico y financiero');c.setAuthor('FW Axial Energy · Control integral del proyecto')
    # Exactly four designed pages; no overflowing appendix or hidden truncation.
    for render in [lambda:technical_page(c,r,technical),lambda:finance_page(c,r),lambda:projection_page(c,r),lambda:assumptions_page(c,r,fx)]:
        render();c.showPage()
    c.save()
    return out.getvalue()


@st.cache_data(ttl=60,max_entries=4,show_spinner=False)
def report_payload(model,currency,fx,layout_version=2):
    """Versioned cache: v2 exports exactly four designed pages."""
    technical=load_technical(model['fetched_at'])
    return build_executive_pdf(model,technical,currency,fx)
