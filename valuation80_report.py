"""Seven-page executive PDF combining the 80 kW financial case and project cost evidence."""
from io import BytesIO
import math
import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import TableStyle
from reportlab.pdfgen.canvas import Canvas
from valuation80_lcoe import summary_lcoe80
from valuation80_unit import commercial_unit80, unit_cost_inputs80, sale_prices80
from valuation80_data import SOURCE
from valuation80_project import load_project80, CASH_FIELDS, calendar_plot_data80
from valuation_finance import complete_sum, divide
from valuation_report import Report, _fonts, W, H, M, CW, BLUE, MUTED, INK, TEAL, PALE, LINE, BOLD, decimal

RUST,SLATE='#AD6551','#9DAFC0'
GAP=18
HALF=(CW-GAP)/2


class ExecutiveReport80(Report):
    def cost_money(self,value,compact=False):
        return 'Sin dato' if pd.isna(value) else super().cost_money(value,compact)

    def kpis(self,c,y,items):
        width=CW/len(items)
        for i,(label,value,note) in enumerate(items):
            x=M+i*width
            c.setFillColor(colors.HexColor(PALE if i==0 else '#FAFBFC'));c.rect(x,y-64,width-2,64,fill=1,stroke=0)
            self.para(c,x+10,y-8,width-20,label,7,MUTED,True)
            size=min(14,14*(width-23)/max(stringWidth(str(value),BOLD,14),1))
            self.para(c,x+10,y-24,width-20,value,size,INK,True)
            self.para(c,x+10,y-45,width-20,note,6.4,MUTED)
        return y-76

    def header(self,c,number,title,subtitle):
        c.setFillColor(colors.HexColor(INK));c.rect(0,H-32,W,32,fill=1,stroke=0)
        self.para(c,M,H-11,CW-80,'FW AXIAL ENERGY  /  INFORME EJECUTIVO · 80 kW',8,'#FFFFFF',True)
        self.para(c,W-M-60,H-11,60,number+' / 07',8,'#FFFFFF',True)
        self.para(c,M,H-48,CW,title,23,INK,True)
        self.para(c,M,H-81,CW,subtitle,8,MUTED);self.line(c,H-102)

    def table(self,rows,widths,size=7.5,header=True):
        table=super().table(rows,widths,size,header)
        table.setStyle(TableStyle([('TOPPADDING',(0,0),(-1,-1),3.3),('BOTTOMPADDING',(0,0),(-1,-1),3.3)]))
        return table

    def panel(self,c,x,top,width,height,title,subtitle=''):
        c.setStrokeColor(colors.HexColor(LINE));c.setFillColor(colors.white)
        c.roundRect(x,top-height,width,height,5,fill=1,stroke=1)
        self.para(c,x+12,top-11,width-24,title,9,BLUE,True)
        if subtitle:self.para(c,x+12,top-27,width-24,subtitle,6.6,MUTED)

    def note(self,c,y,title,text,width=CW,x=M):
        paragraphs=[self.p(item,7.1,MUTED) for item in (text if isinstance(text,list) else [text])]
        heights=[p.wrap(width-26,H)[1] for p in paragraphs]
        box=sum(heights)+6*(len(paragraphs)-1)+37
        c.setFillColor(colors.HexColor(PALE));c.roundRect(x,y-box,width,box,4,fill=1,stroke=0)
        c.setFillColor(colors.HexColor(TEAL));c.rect(x,y-box,2,box,fill=1,stroke=0)
        self.para(c,x+12,y-9,width-24,title,7.4,BLUE,True)
        top=y-26
        for p,height in zip(paragraphs,heights):
            p.drawOn(c,x+12,top-height);top-=height+6
        return y-box

    def hbars(self,c,x,top,width,height,title,labels,values,palette=None,unit='money',subtitle=''):
        self.panel(c,x,top,width,height,title,subtitle)
        valid=[(str(label),float(value),i) for i,(label,value) in enumerate(zip(labels,values)) if pd.notna(value) and math.isfinite(float(value))]
        if not valid:return
        label_width=width*.38;left=x+label_width;right=x+width-85
        low=min(0,min(v for _,v,_ in valid));high=max(0,max(v for _,v,_ in valid));span=high-low or 1
        pos=lambda v:left+(v-low)/span*(right-left)
        c.setStrokeColor(colors.HexColor(LINE));c.setLineWidth(.5);c.line(pos(0),top-height+13,pos(0),top-43)
        step=(height-55)/len(valid);palette=palette or [BLUE,TEAL,SLATE,RUST]
        for j,(label,value,i) in enumerate(valid):
            y=top-45-j*step;bar_h=min(17,step*.55)
            self.para(c,x+12,y+3,label_width-20,label,6.9,MUTED)
            c.setFillColor(colors.HexColor(palette[i%len(palette)]))
            if value:c.rect(min(pos(0),pos(value)),y-bar_h,abs(pos(value)-pos(0)),bar_h,fill=1,stroke=0)
            shown=self.money(value,True) if unit=='money' else self.pct(value) if unit=='pct' else decimal(value,0)
            self.para(c,right+7,y+2,73,shown,7.2,INK,True)

    def trends(self,c,x,top,width,height,title,frame,fields,lines=False):
        self.panel(c,x,top,width,height,title,'Millones de '+self.currency+' · cifras nominales')
        left=x+43;right=x+width-15;bottom=top-height+28;ceiling=top-64
        values=[float(v)*self.fx/1e6 for field,_,_ in fields for v in frame[field] if pd.notna(v)]
        if not values:return
        high=max(max(values),0)*1.18 or 1;low=min(min(values),0)*1.15
        yp=lambda v:bottom+(v-low)/(high-low)*(ceiling-bottom)
        for tick in range(4):
            value=low+(high-low)*tick/3;y=yp(value)
            c.setStrokeColor(colors.HexColor(LINE));c.setLineWidth(.4);c.line(left,y,right,y)
            self.para(c,x+3,y+3,35,decimal(value,1),6.1,MUTED)
        step=(right-left)/max(len(frame),1)
        for j,(_,row) in enumerate(frame.iterrows()):self.para(c,left+j*step,bottom-8,step,row['Año'],6.2,MUTED)
        for i,(field,label,color) in enumerate(fields):
            lx=x+12+i*(width-24)/len(fields)
            c.setFillColor(colors.HexColor(color));c.rect(lx,top-47,6,6,fill=1,stroke=0)
            self.para(c,lx+10,top-40,(width-24)/len(fields)-14,label,6.2,MUTED);points=[]
            for j,(_,row) in enumerate(frame.iterrows()):
                if pd.isna(row[field]):points=[];continue
                value=float(row[field])*self.fx/1e6;xp=left+(j+.5)*step
                if lines and i>0:
                    if points:
                        c.setStrokeColor(colors.HexColor(color));c.setLineWidth(1.8);c.line(*points[-1],xp,yp(value))
                    c.setFillColor(colors.HexColor(color));c.circle(xp,yp(value),2,fill=1,stroke=0);points.append((xp,yp(value)))
                else:
                    bars=1 if lines else len(fields);bw=step*.64/bars
                    xp=left+j*step+step*.18+(0 if lines else i*bw)
                    c.setFillColor(colors.HexColor(color));c.rect(xp,min(yp(0),yp(value)),bw*.88,abs(yp(value)-yp(0)),fill=1,stroke=0)

    def ownership(self,c,x,top,width,height,share):
        self.panel(c,x,top,width,height,'Participación después de la operación','Participación final publicada · no es retorno del socio')
        if pd.isna(share) or not 0<=share<=1:return
        cx=x+width*.26;cy=top-height*.6;radius=height*.27
        c.setFillColor(colors.HexColor(SLATE));c.circle(cx,cy,radius,fill=1,stroke=0)
        c.setFillColor(colors.HexColor(BLUE));c.wedge(cx-radius,cy-radius,cx+radius,cy+radius,90,share*360,fill=1,stroke=0)
        c.setFillColor(colors.white);c.circle(cx,cy,radius*.71,fill=1,stroke=0)
        self.para(c,cx-radius*.56,cy+8,radius*1.3,self.pct(share),14,INK,True)
        self.para(c,x+width*.53,top-64,width*.43,'INVERSIONISTA',7,BLUE,True)
        self.para(c,x+width*.53,top-80,width*.43,self.pct(share),17,BLUE,True)
        self.para(c,x+width*.53,top-112,width*.43,'ACCIONISTAS ACTUALES',6.5,MUTED,True)
        self.para(c,x+width*.53,top-128,width*.43,self.pct(1-share),13,MUTED,True)


def report80_data(model,fx=None):
    """Keep 00's published unit values and five-year rounding intact."""
    e=model['evaluation']
    return dict(unit=commercial_unit80(model,fx),funding=e['funding'].set_index('Concepto')['Valor'].to_dict(),projection=e['projection'].copy())


def compact_table80(c,r,x,top,rows,widths,size=6.6):
    table=r.table(rows,widths,size)
    table.setStyle(TableStyle([('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2)]))
    _,height=table.wrap(sum(widths),H)
    if top-height<42:raise ValueError('El detalle excede el espacio disponible del PDF; se requiere ampliar la composición.')
    table.drawOn(c,x,top-height)
    return top-height


def calendar_page80(c,r,data):
    r.header(c,'05','80 kW · calendario de desembolsos','Estrategia de Capital y Costos · alcance 80 kW · corte '+data['cutoff'].strftime('%d-%m-%Y'))
    m=data['monthly'];valid,pending=CASH_FIELDS
    known=m.loc[m['Total CLP'].notna()]
    peak=known.loc[known['Total CLP'].idxmax()] if not known.empty else None
    y=r.kpis(c,H-114,[('Caja calendarizada',r.cost_money(data['total'],True),'Saldos incluidos del proyecto 80 kW'),
        ('Caja por validar',r.cost_money(data['pending'],True),'Incluida en el total, no se suma de nuevo'),
        ('Mayor necesidad mensual',r.cost_money(peak['Total CLP'],True) if peak is not None else 'Sin dato',peak['_month'].strftime('%m/%Y') if peak is not None else 'Sin calendario informado')])
    chart,markers=calendar_plot_data80(data)
    height=164
    legend='verde azulado: validada · ocre: por validar' if m[valid].notna().any() else 'ocre: caja por validar'
    r.panel(c,M,y,CW,height,'Caja mes a mes · 80 kW','Millones de '+r.currency+' · '+legend)
    left=M+50;right=W-M-16;bottom=y-height+28;ceiling=y-(78 if len(markers) else 52)
    if not known.empty:
        high=max(float(known['Total CLP'].max())/r.exchange_rate*r.fx/1e6*1.2,.001)
        pos=lambda v:bottom+v/high*(ceiling-bottom)
        for i in range(4):
            value=high*i/3;yp=pos(value);c.setStrokeColor(colors.HexColor(LINE));c.setLineWidth(.4);c.line(left,yp,right,yp)
            r.para(c,M+3,yp+3,43,decimal(value,2 if high<1 else 1),6,MUTED)
        step=(right-left)/len(chart)
        for i,(_,row) in enumerate(chart.iterrows()):
            xp=left+(i+.18)*step;base=0.
            for field,color in [(valid,TEAL),(pending,'#B28B4B')]:
                if pd.isna(row[field]):continue
                value=float(row[field])/r.exchange_rate*r.fx/1e6
                c.setFillColor(colors.HexColor(color));c.rect(xp,pos(base),step*.64,pos(base+value)-pos(base),fill=1,stroke=0);base+=value
            r.para(c,left+i*step,bottom-7,step,row['_month'].strftime('%m/%Y'),6.2,MUTED)
            if pd.notna(row['Total CLP']):r.para(c,left+i*step,pos(base)+9,step,r.cost_money(row['Total CLP'],True),5.7,INK,True)
    box_w=154;box_h=27;box_positions=[]
    for _,marker in markers.iterrows():
        date=marker['Fin previsto actual']
        month=date.to_period('M').to_timestamp() if pd.notna(date) else None
        positions=[i for i,value in enumerate(chart['_month']) if value==month]
        anchor=left+(positions[0]+.5)*(right-left)/len(chart) if positions else (left+right)/2
        box_positions.append(max(left,min(anchor-box_w/2,right-box_w)))
    if len(box_positions)==2 and box_positions[0]+box_w+10>box_positions[1]:
        start=max(left,min((sum(box_positions)+box_w)/2-box_w-5,right-2*box_w-10))
        box_positions=[start,start+box_w+10]
    for index,(_,marker) in enumerate(markers.iterrows()):
        color=TEAL if 'piloto' in marker['Paquete / línea'].casefold() else RUST
        box_x=box_positions[index];box_top=y-39
        c.setFillColor(colors.white);c.setStrokeColor(colors.HexColor(color));c.setLineWidth(.7)
        c.roundRect(box_x,box_top-box_h,box_w,box_h,3,fill=1,stroke=1)
        r.para(c,box_x+8,box_top-4,box_w-16,marker['Paquete / línea'],7,color,True)
        date=marker['Fin previsto actual']
        r.para(c,box_x+8,box_top-15,box_w-16,date.strftime('%d-%m-%Y') if pd.notna(date) else 'Sin fecha informada',6.8,color)
        if pd.notna(date) and len(chart):
            month=date.to_period('M').to_timestamp()
            positions=[i for i,value in enumerate(chart['_month']) if value==month]
            if positions:
                step=(right-left)/len(chart)
                xp=left+(positions[0]+.1+.8*(date.day-.5)/date.days_in_month)*step
                c.setStrokeColor(colors.HexColor(color));c.setLineWidth(.7);c.setDash(2,2)
                c.line(xp,bottom,xp,ceiling)
                c.line(xp,ceiling,box_x+box_w/2,box_top-box_h)
                c.setDash()
    y-=height+10
    rows=[['Mes de necesidad','Caja por validar','Total mensual']]
    for _,row in m.iterrows():rows.append([row['_month'].strftime('%m/%Y'),r.cost_money(row[pending]),r.cost_money(row['Total CLP'])])
    rows.append(['TOTAL CALENDARIZADO',r.cost_money(data['pending']),r.cost_money(data['total'])])
    y=compact_table80(c,r,M,y,rows,[CW/3]*3)-7
    note='Costos: saldos No pagado/Parcial con inclusión activa. Los vencidos previos al corte se agrupan en el mes de corte. El total conserva todos los saldos incluidos. '+str(data['missing_dates'])+' saldos sin fecha'
    if data['missing_dates']:note+=' ('+r.cost_money(data['undated_total'])+'), fuera del calendario'
    note+='. Recuadros: fin previsto actual de Hito Piloto y Hito Producto 80 kW en Plan. El eje incluye meses sin desembolsos hasta el último hito. Consulta: '+data['fetched_at']+'. Calendario de desarrollo, separado del flujo operativo del modelo financiero.'
    r.para(c,M,y,CW,note,6.5,MUTED)
    c.linkURL(data['source_url']+'html',(M,H-99,W-M,H-78),relative=0,thickness=0)


def opex_page80(c,r,model):
    first=model['annual'].loc[lambda frame:frame['Año modelo'].gt(0)].iloc[0]
    year=first['Año'];detail=model['opex'].loc[lambda frame:frame['Año'].eq(year)].copy()
    r.header(c,'06','80 kW · detalle de gastos operativos','08 Gastos operativos · presupuesto anual '+year+' · estructura, costos por entrega y flota')
    y=r.kpis(c,H-114,[('OPEX total · '+year,r.money(first['opex'],True),'Presupuesto anual publicado'),
        ('Estructura operativa',r.money(first['opex_common'],True),'Dotación, planta y gastos recurrentes'),
        ('Entrega y flota',r.money(first['opex_80'],True),'Gastos asociados a equipos y conectividad')])
    behavior=detail.groupby('Destino',sort=False)['USD'].agg(complete_sum)
    r.hbars(c,M,y,HALF,108,'Presupuesto por comportamiento',behavior.index,behavior.values,palette=[BLUE,TEAL,SLATE])
    areas=detail.groupby('Área')['USD'].agg(complete_sum).sort_values(ascending=False)
    labels=areas.index[:3].tolist();values=areas.iloc[:3].tolist()
    if len(areas)>3:labels.append('Otras áreas');values.append(complete_sum(areas.iloc[3:]))
    r.hbars(c,M+HALF+GAP,y,HALF,108,'Concentración del gasto por área',labels,values,palette=[BLUE,TEAL,SLATE,RUST]);y-=120
    states={'Presupuesto recibido':'Rec.','Presupuesto provisional':'Prov.','Por cotizar':'Cot.','No aplica':'N/A',
        'Estimado':'Est.','Por definir':'Def.','Supuesto del modelo':'Sup.'}
    size=6.2;widths=[38,HALF-159,91,30]
    def rows_for(frame):
        rows=[['ID','Concepto de gasto','Presupuesto · '+r.currency,'Est.']]
        for _,row in frame.iterrows():
            label=str(row['Concepto']);available=widths[1]-14
            if stringWidth(label,BOLD,size)>available:
                while label and stringWidth(label+'…',BOLD,size)>available:label=label[:-1]
                label=label.rstrip()+'…'
            rows.append([row['ID'],label,r.money(row['USD']),states.get(row['Estado'],row['Estado'])])
        return rows
    split=(len(detail)+1)//2
    bottom=compact_table80(c,r,M,y,rows_for(detail.iloc[:split]),widths,size)
    bottom=min(bottom,compact_table80(c,r,M+HALF+GAP,y,rows_for(detail.iloc[split:]),widths,size))
    note='Fuente: 08 Gastos operativos, '+str(len(detail))+' partidas y ajustes. Total detalle: '+r.money(complete_sum(detail['USD']))+'. Rec.: recibido; Prov.: provisional; Cot.: por cotizar; Est.: estimado; Def.: por definir; Sup.: supuesto; N/A: no aplica. Incluye ajustes una sola vez; los ceros pendientes de cotización no acreditan costo nulo.'
    r.para(c,M,bottom-6,CW,note,6.2,MUTED)
    from valuation80_data import SHEETS
    c.linkURL(SOURCE+'html#gid='+SHEETS['08 Gastos operativos'],(M,H-99,W-M,H-78),relative=0,thickness=0)


def project_cost_tables80(c,r,y,costs):
    """Replace the financial sheet's component guesses with traceable Sub block 1 totals."""
    t=costs['totals'];systems=costs['systems'];lines=costs['lines']
    left=CW*.5-GAP/2;right=left
    rows=[['Sistema · 80 kW','Informado¹','Vigente','Datos²']]
    for _,row in systems.iterrows():rows.append([row['Sistema'],r.cost_money(row['Monto comercial · CLP'],True),r.cost_money(row['Monto no comercial · CLP'],True),str(int(row['Partidas informadas']))+'/'+str(int(row['Actividades']))])
    rows.append(['TOTAL APLICA',r.cost_money(t['Comercial anterior'],True),r.cost_money(t['Presupuesto vigente'],True),str(t['Informadas'])+'/'+str(t['Partidas'])])
    bottom=compact_table80(c,r,M,y,rows,[left*.42,left*.23,left*.23,left*.12],6.4)
    rows=[['Principales paquetes / líneas','Informado¹','Datos²']]
    shown=lines.head(4);rest=lines.iloc[4:]
    for _,row in shown.iterrows():
        label=str(row['Sistema'])+' / '+str(row['Línea'])
        if len(label)>85:label=label[:82].rsplit(' ',1)[0]+'…'
        rows.append([label,r.cost_money(row['Comercial'],True),str(int(row['Informadas']))+'/'+str(int(row['Partidas']))])
    if len(rest):rows.append(['Otras '+str(len(rest))+' líneas',r.cost_money(rest['Comercial'].sum(min_count=1),True),str(int(rest['Informadas'].sum()))+'/'+str(int(rest['Partidas'].sum()))])
    rows.append(['TOTAL APLICA',r.cost_money(t['Comercial anterior'],True),str(t['Informadas'])+'/'+str(t['Partidas'])])
    bottom=min(bottom,compact_table80(c,r,M+left+GAP,y,rows,[right*.62,right*.25,right*.13],6.4))
    scope=costs['scope'];validated=scope['Registros conciliados'].fillna('').str.strip().eq('Validado').sum()
    note='¹ Informado = Comercial anterior de Costos; no se sustituye por fabricación del modelo financiero. ² Datos = partidas con monto / partidas Aplica. '+str(validated)+'/'+str(t['Partidas'])+' registros conciliados; '+str(t['Partidas']-t['Informadas'])+' sin monto comercial. Presupuesto vigente es una referencia distinta.'
    bottom=r.para(c,M,bottom-8,CW,note,6.4,MUTED)-5
    r.para(c,M,bottom,CW,'Fuente: Plan + Costos del subbloque 1 · Hito objetivo de Costos 80 kW y Costo para producto = Aplica · alcance Total, con fundaciones y montaje. Consulta: '+costs.get('fetched_at','según corte del reporte')+'. Estos importes no reemplazan ni se suman automáticamente al costo unitario proyectado.',6.4,MUTED)


def lcoe_page80(c,r,model,factor,result):
    r.header(c,'07','80 kW · costo nivelado de la energía',
        'Escenario del propietario · factor de planta neto seleccionado en pantalla: '+r.pct(factor)+' · moneda constante')
    unit=lambda value,mwh=False:decimal(value*r.fx*(1000 if mwh else 1),2 if mwh else 5)+' '+r.currency+('/MWh' if mwh else '/kWh')
    y=r.kpis(c,H-114,[('LCOE del escenario',unit(result['lcoe'],True),unit(result['lcoe'])),
        ('Generación neta anual',decimal(result['energy_y1']/1000,2)+' MWh','80 kW × 8.760 h × '+r.pct(factor)),
        ('CAPEX de referencia',r.money(result['capex'],True),'Precio inicial · moneda publicada'),
        ('O&M anual supuesto',r.money(result['fixed_om']),'2 % del precio · constante en términos reales')])
    height=156
    r.panel(c,M,y,HALF,height,'Sensibilidad al factor de planta neto','Escenario: FP '+r.pct(factor)+' · '+unit(result['lcoe'],True))
    left=M+47;right=M+HALF-15;bottom=y-height+28;ceiling=y-46
    factors=sorted(set([v/100 for v in range(5,101,5)]+[factor]))
    points=[(v,summary_lcoe80(model,v,r.exchange_rate)['lcoe']*r.fx*1000) for v in factors]
    high=max(value for _,value in points)*1.08
    xp=lambda v:left+v*(right-left)
    yp=lambda value:bottom+value/high*(ceiling-bottom)
    for tick in range(4):
        value=high*tick/3;cy=yp(value)
        c.setStrokeColor(colors.HexColor(LINE));c.setLineWidth(.4);c.line(left,cy,right,cy)
        r.para(c,M+4,cy+3,40,decimal(value,0),6,MUTED)
    for tick in [.2,.4,.6,.8,1.]:r.para(c,xp(tick)-10,bottom-6,28,decimal(tick*100,0)+'%',6,MUTED)
    c.setStrokeColor(colors.HexColor(TEAL));c.setLineWidth(1.8)
    for (a,av),(b,bv) in zip(points,points[1:]):c.line(xp(a),yp(av),xp(b),yp(bv))
    selected=result['lcoe']*r.fx*1000
    c.setStrokeColor(colors.HexColor(BLUE));c.setDash(2,2);c.line(xp(factor),bottom,xp(factor),yp(selected));c.setDash()
    c.setFillColor(colors.HexColor(BLUE));c.circle(xp(factor),yp(selected),3,fill=1,stroke=0)
    rows=[['Dato / supuesto','Valor y procedencia'],['Potencia nominal','80 kW · producto analizado'],
        ['Vida útil / tasa real','20 años / 8 % · supuestos ilustrativos'],
        ['O&M propietario','2 % anual del precio; no es el OPEX del fabricante'],
        ['Factor de planta neto',r.pct(factor)+' · selección interactiva del usuario'],
        ['Generación anual','80 × 8.760 × FP = '+decimal(result['energy_y1'],0)+' kWh']]
    r.draw_table(c,M+HALF+GAP,y,rows,[HALF*.36,HALF*.64],6.9)
    y-=height+12
    rows=[['Componente del cálculo','Valor presente · '+r.currency,'Aporte al LCOE · '+r.currency+'/MWh'],
        ['CAPEX inicial · año 0',r.money(result['capex']),decimal(result['lcoe_components']['CAPEX inicial']*r.fx*1000,2)],
        ['O&M fijo · años 1–20',r.money(result['components']['O&M fijo']),decimal(result['lcoe_components']['O&M fijo']*r.fx*1000,2)],
        ['TOTAL COSTOS DESCONTADOS',r.money(result['pv_costs']),decimal(result['lcoe']*r.fx*1000,2)],
        ['Energía neta descontada',decimal(result['pv_energy']/1000,2)+' MWh','Suma de energía anual / (1 + 8 %)^t']]
    y=r.draw_table(c,M,y,rows,[CW*.36,CW*.32,CW*.32],7)-10
    y=r.note(c,y,'Método y lectura del resultado',
        'LCOE = [CAPEX inicial + suma(t=1…20) O&M anual / (1 + 0,08)^t] / [suma(t=1…20) energía neta anual / (1 + 0,08)^t]. '
        'Costos al cierre de cada año; CAPEX al inicio. Energía anual constante; el FP ya incluye disponibilidad y pérdidas. '
        'El PDF conserva el FP seleccionado al prepararlo. La curva varía solo ese factor; precio, O&M, vida y tasa permanecen fijos.')-9
    r.para(c,M,y,CW,'Fuente monetaria: precio inicial de 00 Datos de entrada (USD directo; CLP / TC del panel), con multiplicadores de precio activos. El 2 % de O&M, los 20 años y el 8 % real son hipótesis, no datos confirmados del archivo ni la tasa DCF. '
        'Sin degradación, crecimiento real del O&M, O&M variable, reposiciones, retiro, valor residual ni impuestos. Costos de instalación y sitio no incluidos en el precio quedan por completar. '
        'Resultado indicativo del propietario; no usa costos de fabricación ni gastos operativos de la empresa como mantenimiento de la turbina. '
        'USD nativos; CLP se convierte una vez al TC de presentación '+decimal(r.exchange_rate,2)+' CLP/USD.',6.6,MUTED)


def build_report80(model,currency='USD',fx=925.,project_data=None,capacity_factor=.35):
    if currency not in ('CLP','USD') or not math.isfinite(fx) or fx<=0:raise ValueError('Moneda o tipo de cambio inválidos.')
    if project_data is None:raise ValueError('Faltan costos y calendario de desembolsos del subbloque 1.')
    lcoe=summary_lcoe80(model,capacity_factor,fx)
    _fonts();r=ExecutiveReport80(model,currency,fx)
    out=BytesIO();c=Canvas(out,pagesize=(W,H));c.setTitle('80 kW · Evaluación ejecutiva, inversión y operación')
    c.setAuthor('FW Axial Energy');c.setSubject('Evaluación 00 · caso exclusivo de 80 kW')
    s,e=model['scalars'],model['evaluation'];data=report80_data(model,fx);u,f,p=data['unit'],data['funding'],data['projection']
    operating=model['annual'].loc[lambda a:a['Año modelo'].gt(0)]
    def header(n,title,subtitle):r.header(c,f'{n:02d}',title,subtitle)
    def finish(n):r.footer(c,n);c.showPage()

    header(1,'80 kW · resultados y valorización','00 Evaluación · caso '+model['scenario']+' · producción '+model['production']+' · fecha base DCF '+str(s['valuation_date']))
    y=r.kpis(c,H-114,[('Ventas netas · año 1',r.money(s['sales_y1'],True),p.iloc[0]['Año']+' · entregas comerciales'),
        ('EBITDA · año 1',r.money(s['ebitda_y1'],True),'Margen '+r.pct(s['ebitda_margin_y1'])),('Flujo libre · año 1',r.money(s['fcff_y1'],True),'Incluye anticipos, CT e IVA'),('DCF previo al aporte',r.money(s['dcf'],True),'Terminal incluido · sin capital nuevo')])
    r.hbars(c,M,y,CW*.54,195,'Valor del proyecto y precio negociado',
        ['VAN operativo sin terminal','VAN económico sin terminal','DCF previo al aporte','Precio previo negociado'],
        [s['npv_cash'],s['npv_economic'],s['dcf'],s['pre_money']],palette=[SLATE,TEAL,BLUE,RUST],subtitle='Magnitudes distintas · '+currency+' de presentación')
    xr=M+CW*.54+GAP;wr=CW*.46-GAP
    r.panel(c,xr,y,wr,195,'Retorno económico y calidad del flujo')
    rows=[['Indicador','Publicado'],['TIR económica sin terminal',r.pct(s['irr_economic'])],
        ['Recuperación descontada de caja',decimal(e['recovery_years'],0)+(' año' if e['recovery_years']==1 else ' años')],
        ['Anticipos pendientes · año 1',r.money(s['advances_y1'],True)],['Aumento anticipos / flujo libre',r.pct(e['contribution_ratio'])],['Peso del terminal',r.pct(s['terminal_weight'])],['Tasa de descuento / crecimiento',r.pct(s['rate'])+' / '+r.pct(s['growth'])]]
    r.draw_table(c,xr+10,y-35,rows,[(wr-20)*.64,(wr-20)*.36],7)
    y-=209
    r.hbars(c,M,y,HALF,120,'Componentes del DCF · valor presente',['Flujos operativos Años 0–10','Terminal descontado'],[s['npv_cash'],s['terminal_value']/(1+s['rate'])**10],palette=[BLUE,TEAL])
    r.note(c,y,'Criterios técnicos de evaluación',[
        '1. La TIR económica incluye activos aportados; la recuperación publicada es de caja en años completos. El terminal aporta '+r.pct(s['terminal_weight'])+' del valor. Los anticipos son obligaciones de entrega y el capital propuesto no forma parte del DCF.',
        '2. El valor terminal usa crecimiento perpetuo: flujo normalizado / (tasa de descuento − crecimiento). Requiere tasa > crecimiento; una menor diferencia entre ambas eleva el valor terminal y su peso en el DCF.'
    ],width=HALF,x=M+HALF+GAP)
    finish(1)

    header(2,'80 kW · arranque e inversión','00 Evaluación + 02 Inversión y socios · aporte '+e['funding_date']+' · estado '+model['status'])
    y=r.kpis(c,H-114,[('Capital primario',r.money(f['Capital primario'],True),'Ingreso proyectado a FW'),('Consumo neto de arranque',r.money(f['Consumo neto de caja · año 0'],True),'Uso de caja · año 0'),('Caja libre de cierre',r.money(f['Caja libre al cierre · año 0'],True),'Después del financiamiento'),('Brecha para caja objetivo',r.money(f['Brecha para caja objetivo · año 0'],True),'Reserva objetivo '+r.money(s['cash_target'],True))])
    r.hbars(c,M,y,HALF,176,'Del financiamiento a la liquidez',['Aporte primario','Consumo neto de arranque','Caja libre al cierre','Brecha de reserva'],[f['Capital primario'],f['Consumo neto de caja · año 0'],f['Caja libre al cierre · año 0'],f['Brecha para caja objetivo · año 0']],palette=[BLUE,SLATE,TEAL,RUST],subtitle='Barras comparativas · no se suman entre sí')
    r.ownership(c,M+HALF+GAP,y,HALF,176,s['investor_share']);y-=187
    rows=[['Condición de la operación','Valor publicado','Referencia']]
    lookup=e['funding'].set_index('Concepto')['Fuente']
    for label in ['Capital primario','Pago secundario','Valor previo implícito negociado','Valor posterior implícito negociado','Puente teórico máximo requerido']:
        rows.append([label,r.money(f[label]),lookup[label]])
    y=r.draw_table(c,M,y,rows,[CW*.45,CW*.28,CW*.27],7)-9
    r.para(c,M,y,CW,'El pago secundario se destina a accionistas y queda fuera de FW. El puente es financiamiento por conseguir; se distingue de la brecha para conservar la reserva. La operación '+model['status']+' no acredita disponibilidad del capital ni fecha contractual de cierre.',7.2,MUTED)
    finish(2)

    header(3,'80 kW · trayectoria operativa y caja','00 Evaluación: '+p.iloc[0]['Año']+'–'+p.iloc[-1]['Año']+' · referencia anual completa de 04–06 bajo los gráficos')
    sales=complete_sum(p['sales']);ebitda=complete_sum(p['ebitda'])
    y=r.kpis(c,H-114,[('Ventas · cinco años',r.money(sales,True),'Suma de los años publicados'),('EBITDA · cinco años',r.money(ebitda,True),'Margen ponderado '+r.pct(divide(ebitda,sales))),('Flujo libre · cinco años',r.money(complete_sum(p['fcff']),True),'Suma de flujos anuales'),('Caja al quinto cierre',r.money(p.iloc[-1]['cash_free'],True),'Saldo final, no suma de caja')])
    r.trends(c,M,y,HALF,168,'Ventas y EBITDA · primeros cinco años',p,[('sales','Ventas',BLUE),('ebitda','EBITDA',TEAL)])
    r.trends(c,M+HALF+GAP,y,HALF,168,'Flujo anual y caja de cierre',p,[('fcff','Flujo libre anual',TEAL),('cash_free','Caja de cierre',BLUE)],lines=True);y-=179
    rows=[['Año','Unid.','Ventas','EBITDA','Flujo libre','CAPEX','Caja libre']]
    for _,row in operating.iterrows():rows.append([row['Año'],decimal(row['units_80'],0),*[r.money(row[field],True) for field in ['sales','ebitda','fcff','capex','cash_free']]])
    table=r.table(rows,[42,40,*[(CW-82)/5]*5],6.7)
    table.setStyle(TableStyle([('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2)]))
    _,height=table.wrap(CW,H);table.drawOn(c,M,y-height);y-=height+8
    r.para(c,M,y,CW,'Margen ponderado = suma EBITDA / suma ventas. Los flujos incorporan anticipos, IVA, capital de trabajo y CAPEX. Los anticipos no son utilidad. Las cifras quinquenales proceden de 00; el detalle de diez años procede de 04–06. Demanda, entregas y capacidad completa se revisan en la aplicación.',6.8,MUTED)
    finish(3)

    header(4,'80 kW · economía unitaria y costos','Precio: moneda publicada / TC del panel para CLP · precios con/sin IVA y por kW · costos: Estrategia de Capital y Costos')
    prices=sale_prices80(model,fx)
    y=r.kpis(c,H-114,[('Precio por equipo · sin IVA',r.money(prices['net']),'USD directo; CLP / TC del panel'),
        ('Precio por kW · sin IVA',r.money(prices['net_kw']),'Precio del equipo / 80 kW'),
        ('Precio por equipo · con IVA',r.money(prices['gross']),'IVA referencial '+r.pct(prices['vat_rate'])),
        ('Precio por kW · con IVA',r.money(prices['gross_kw']),'Precio con IVA / 80 kW')])
    unit_costs=unit_cost_inputs80(model)
    r.hbars(c,M,y,HALF,156,'Evolución del costo unitario',['Costo base','Costo base + OPEX','Precio calculado · 07' if unit_costs['final_is_price'] else 'Costo unitario + margen'],[unit_costs['base'],unit_costs['before_margin'],unit_costs['with_margin']],palette=[SLATE,BLUE,TEAL],subtitle='07 · componentes según sus etiquetas publicadas · importes no sumables')
    costs=project_data['costs'];systems=costs['systems']
    r.hbars(c,M+HALF+GAP,y,HALF,156,'Costos informados de 80 kW por sistema',systems['Sistema'],
        systems['Monto comercial · CLP']/fx,palette=[BLUE,TEAL,SLATE,RUST],subtitle='Comercial anterior · fuente CLP convertida una sola vez');y-=168
    project_cost_tables80(c,r,y,costs)
    finish(4)

    calendar_page80(c,r,project_data)
    finish(5)
    opex_page80(c,r,model)
    finish(6)
    lcoe_page80(c,r,model,capacity_factor,lcoe)
    finish(7)
    c.save();return out.getvalue()


@st.cache_data(ttl=60,max_entries=4,show_spinner=False)
def report80_payload(model,currency,fx,layout_version=11,capacity_factor=.35):
    """Version 11: selected net capacity factor is part of the PDF cache key."""
    project=load_project80(model['fetched_at'])
    return build_report80(model,currency,fx,project_data=project,capacity_factor=capacity_factor)
