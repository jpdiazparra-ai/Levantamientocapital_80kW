"""Scrollable timeline with sticky dates and task columns, without pagination."""
import html
import urllib.parse
import pandas as pd

COLORS = {'Completado':'#15803D', 'En curso':'#D97706', 'Pendiente':'#64748B', 'Sin avance':'#94A3B8'}
MONTHS = ['ene','feb','mar','abr','may','jun','jul','ago','sept','oct','nov','dic']


def timeline_document(rows, level, mode, compare_base):
    today = pd.Timestamp.now(tz='America/Santiago').normalize().tz_localize(None)
    start, finish = rows['_start'].min(), rows['_end'].max()
    if mode == 'Previsión actual' and compare_base:
        finish = max(finish, rows['_base_end'].max())
    start, finish = min(start, today), max(finish, today)
    padding = pd.Timedelta(days=max(8, (finish-start).days * .05))
    start, finish = start-padding, finish+padding
    span = (finish-start).total_seconds()
    def position(value):
        return max(0, min(100, (value-start).total_seconds()/span*100))
    # Monthly divisions, reducing labels on long schedules while retaining guides.
    ticks = pd.date_range(start.to_period('M').to_timestamp(), finish, freq='MS')
    ticks = [value for value in ticks if value >= start]
    stride = max(1, (len(ticks)+11)//12)
    labels = ''.join(f'<span class="date-tick" style="left:{position(value):.5f}%">{MONTHS[value.month-1]} {value.year}</span>' for index,value in enumerate(ticks) if index % stride == 0)
    guides = ''.join(f'<line x1="{position(value)*10:.4f}" x2="{position(value)*10:.4f}" y1="0" y2="1"/>' for value in ticks)
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1" preserveAspectRatio="none"><g stroke="#E5EBF0" stroke-width="1">'+guides+'</g></svg>'
    background = 'url("data:image/svg+xml,'+urllib.parse.quote(svg)+'")'
    today_position = position(today)
    body = []
    for _,row in rows.iterrows():
        left, right = position(row['_start']), position(row['_end'])
        state = str(row['_state'])
        color = COLORS.get(state, '#64748B')
        progress = row.get('_progress')
        progress_text = '—' if pd.isna(progress) else f'{progress:.0f}%'
        baseline = ''
        if mode == 'Previsión actual' and compare_base and pd.notna(row['_base_end']):
            base_right=position(row['_base_end'])
            baseline=f'<span class="baseline" style="left:{left:.5f}%;width:{max(0,base_right-left):.5f}%"></span>'
        milestone=row['_start']==row['_end']
        tooltip=html.escape(row['_tooltip'],quote=True)
        label=html.escape(str(row['_label']))
        if level == 'Actividades':
            task_id = html.escape(str(row['ID']))
            task_name = html.escape(str(row['Actividad / entregable']))
            name_html = f'<div class="task-main"><span class="task-id">{task_id}</span><span class="task-name">{task_name}</span></div>'
        else:
            name_html = f'<div class="task-main"><i class="task-dot" style="background:{color}"></i><span class="task-name">{label}</span></div>'
        bar=f'<button class="bar {"milestone" if milestone else ""}" style="left:{left:.5f}%;width:{max(0,right-left):.5f}%;--state:{color}" data-tooltip="{tooltip}" aria-label="{label}"></button>'
        context = str(row.get('Sistema',''))
        if level=='Actividades':context += ' · '+str(row.get('Paquete / línea',''))
        else:context=f'{int(row.get("Actividades",1))} actividades · {state}'
        body.append(
            '<div class="timeline-row"><div class="task-cell">'
            f'{name_html}<small>{html.escape(context)}</small></div>'
            f'<div class="track"><span class="today-line" style="left:{today_position:.5f}%"></span>{baseline}{bar}'
            f'<span class="progress" style="left:{min(right,96):.5f}%">{progress_text}</span></div></div>'
        )
    row_height=86 if level=='Actividades' else 66 if level=='Paquetes / líneas' else 56
    viewport=min(740, max(260, 64+len(rows)*row_height+18))
    document='''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{box-sizing:border-box}body{margin:0;color:#334155;font-family:Arial,sans-serif;font-size:12px;background:#FFF}
.timeline-scroll{height:VAR_HEIGHTpx;overflow:auto;border:1px solid #D8E3EB;border-radius:14px;scrollbar-width:thin;scrollbar-color:#A9BCC9 #F1F5F9;isolation:isolate}
.timeline-table{min-width:960px;--label-width:320px}
.timeline-header,.timeline-row{display:grid;grid-template-columns:var(--label-width) minmax(640px,1fr)}
.timeline-header{position:sticky;top:0;z-index:30;height:64px;background:#F1F5F9;border-bottom:1px solid #D8E3EB}
.column-title{position:sticky;left:0;z-index:32;background:#F1F5F9;padding:17px 16px;border-right:1px solid #D8E3EB;font-weight:700;color:#0F2435;line-height:1.6}
.column-title small{display:block;font-size:10px;font-weight:400;color:#64748B}
.date-header{position:relative;overflow:hidden}.date-tick{position:absolute;bottom:10px;white-space:nowrap;color:#475569;font-size:11px;transform:translateX(-50%)}
.today-tag{position:absolute;top:6px;transform:translateX(-50%);white-space:nowrap;padding:4px 6px;background:#0F2435;color:#FFF;border-radius:4px;font-size:10px;z-index:2}
.timeline-row{height:VAR_ROWpx;background:#FFF}.timeline-row:nth-child(even){background:#F5F8FA}.timeline-row:hover{background:#ECF7F4}
.task-cell{position:sticky;left:0;z-index:10;background:inherit;border-right:1px solid #D8E3EB;border-bottom:1px solid #E8EDF1;padding:10px 14px;display:flex;flex-direction:column;justify-content:center;gap:5px;overflow:hidden}
.task-main{display:flex;align-items:flex-start;gap:9px;min-width:0}.task-id{flex-shrink:0;min-width:37px;padding:4px 5px;border:1px solid #D8E3EB;border-radius:5px;background:#FFF;color:#244A6C;font-size:10px;font-weight:700;text-align:center;font-variant-numeric:tabular-nums}.task-dot{flex-shrink:0;width:7px;height:7px;border-radius:50%;margin-top:5px}.task-name{min-width:0;flex:1;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden;font-size:12px;font-weight:500;line-height:1.4;color:#0F2435;overflow-wrap:anywhere}.task-cell small{font-size:9px;color:#64748B;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.track{position:relative;background-image:VAR_BACKGROUND;background-size:100% 100%;border-bottom:1px solid #E8EDF1}
.bar{position:absolute;top:calc(50% - 11px);height:22px;min-width:3px;border:0;border-radius:4px;background:var(--state);cursor:pointer;z-index:4;padding:0}
.bar:hover,.bar:focus-visible{outline:2px solid #0F2435;outline-offset:3px;filter:brightness(1.06)}
.bar.milestone{min-width:10px!important;width:10px!important;height:10px;top:calc(50% - 5px);transform:translateX(-5px) rotate(45deg);border-radius:1px}
.baseline{position:absolute;top:calc(50% + 16px);border-top:2px dotted #475569;z-index:3;min-width:2px}
.today-line{position:absolute;top:0;bottom:0;border-left:2px dashed #0891B2;z-index:2;pointer-events:none}
.progress{position:absolute;top:calc(50% - 7px);margin-left:7px;font-size:11px;font-weight:650;white-space:nowrap;color:#0F2435;pointer-events:none;z-index:5}
.tooltip{display:none;position:fixed;z-index:100;max-width:min(340px,calc(100vw - 24px));padding:13px 15px;border:1px solid #D8E3EB;border-radius:9px;background:#FFF;box-shadow:0 8px 28px #0F24352A;font-size:12px;line-height:1.55;color:#0F2435;pointer-events:none;overflow-wrap:anywhere;max-height:calc(100vh - 16px);overflow:hidden}
.scroll-hint{margin:8px 2px 0;color:#64748B;font-size:10px;line-height:1.5}
@media(max-width:760px){.timeline-table{--label-width:235px;min-width:875px}.task-cell{padding:8px 10px}.task-name{font-size:11px}}
</style></head><body>
<div class="timeline-scroll" tabindex="0" aria-label="Cronograma completo con desplazamiento"><div class="timeline-table">
<div class="timeline-header"><div class="column-title">Actividad / grupo<small>VAR_COUNT filas · orden de lectura seleccionado</small></div><div class="date-header">VAR_DATES<span class="today-tag" style="left:VAR_TODAY%">Hoy · VAR_TODAY_DATE</span></div></div>
VAR_BODY
</div></div><div class="scroll-hint">Desplázate dentro del cronograma para recorrer todas las filas. Las fechas y la columna de actividades permanecen visibles. Pasa el cursor o enfoca una barra para consultar su detalle.</div>
<div class="tooltip" role="tooltip" id="timeline-tooltip"></div>
<script>
const tooltip=document.getElementById('timeline-tooltip');
const scroller=document.querySelector('.timeline-scroll');
function hide(){tooltip.style.display='none'}
function show(event){const bar=event.currentTarget;tooltip.innerHTML=bar.dataset.tooltip;tooltip.style.display='block';const rect=bar.getBoundingClientRect();const x=event.clientX??rect.right;const y=event.clientY??rect.top;let left=Math.min(x+14,innerWidth-tooltip.offsetWidth-10);let top=y+16;if(top+tooltip.offsetHeight>innerHeight-8)top=y-tooltip.offsetHeight-12;tooltip.style.left=Math.max(8,left)+'px';tooltip.style.top=Math.max(8,top)+'px'}
document.querySelectorAll('.bar').forEach(bar=>{bar.addEventListener('pointerenter',show);bar.addEventListener('pointermove',show);bar.addEventListener('pointerleave',hide);bar.addEventListener('focus',show);bar.addEventListener('blur',hide)});
scroller.addEventListener('scroll',hide);document.addEventListener('keydown',event=>{if(event.key==='Escape')hide()});
</script></body></html>'''
    replacements={'VAR_HEIGHT':str(viewport),'VAR_ROW':str(row_height),'VAR_BACKGROUND':background,'VAR_COUNT':str(len(rows)),'VAR_DATES':labels,'VAR_TODAY':f'{today_position:.5f}','VAR_TODAY_DATE':today.strftime('%d-%m-%Y'),'VAR_BODY':''.join(body)}
    # Replace template tokens in one pass; source text never becomes a token.
    import re
    document=re.sub(r'VAR_[A-Z_]+',lambda match:replacements[match.group(0)],document)
    return document, viewport+48
