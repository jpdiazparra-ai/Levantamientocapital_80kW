"""Traceable unit cost indicators, preserving the published cell values."""
from valuation_data import Sheet, number
from valuation_finance import complete_sum


def commercial_unit80(model,fx=None):
    """Unit economics at the sidebar FX; published annual cash flows stay intact."""
    unit=model['evaluation']['unit'].set_index('Concepto')['Valor'].to_dict()
    if fx is None:return unit
    import math
    if not math.isfinite(fx) or fx<=0:raise ValueError('Tipo de cambio inválido.')
    inputs=Sheet('00 Datos de entrada',model['raw']['00 Datos de entrada'])
    assumptions=Sheet('03 Supuestos',model['raw']['03 Supuestos'])
    row=inputs.find('Precio de venta inicial','B')
    initial=number(inputs.cell(f'C{row}'))
    unit_name=next((inputs.cell(f'{col}{row}').strip().upper() for col in ['D','E']
        if any(code in inputs.cell(f'{col}{row}').upper() for code in ['USD','CLP'])),None)
    if unit_name is None:raise ValueError('Precio de venta inicial: falta indicar USD o CLP en la unidad publicada.')
    scenario=assumptions.value('Precio')
    additional=assumptions.value('Multiplicador adicional de precio')
    price=(initial if 'USD' in unit_name else initial/fx)*scenario*additional
    gross=price-unit['Fabricación media por equipo entregado']
    unit.update({'Precio de venta':price,'Margen bruto por equipo':gross,
        'Margen bruto':gross/price if price>0 else float('nan'),
        'Contribución antes de estructura operativa':gross-unit['Costo de entrega y flota por equipo']})
    return unit


def sale_prices80(model,fx):
    price=commercial_unit80(model,fx)['Precio de venta']
    vat=Sheet('03 Supuestos',model['raw']['03 Supuestos']).value('IVA referencial')
    return dict(net=price,net_kw=price/80,vat_rate=vat,gross=price*(1+vat),gross_kw=price*(1+vat)/80)


def unit_cost_inputs80(model):
    sheet=Sheet('07 Ventas y producción',model['raw']['07 Ventas y producción'])
    # Match known meanings rather than row numbers; renamed selling prices stay
    # distinguishable from costs, and unknown or ambiguous labels stay missing.
    normalize=lambda text:' '.join(str(text).split()).casefold()
    references={};labels={}
    def value(key,column,*expected):
        hits=[row for row in range(1,len(sheet.rows)+1)
            if normalize(sheet.cell(f'C{row}')) in {normalize(label) for label in expected}]
        if len(hits)!=1:return float('nan')
        row=hits[0];references[key]=f'07!{column}{row}';labels[key]=sheet.cell(f'C{row}').strip()
        return number(sheet.cell(f'{column}{row}'))
    base=value('base','E','Costo base presupuestado')
    opex=value('opex','E','Opex total')
    margin=value('margin','D','Costo equivalente con margen proveedor')
    final=value('with_margin','E','Costo unitario aplicado al caso + opex unitario','Precio Venta','Precio de venta')
    before=complete_sum([base,opex])
    return dict(base=base,opex=opex,margin=margin,before_margin=before,with_margin=final,
        margin_amount=final-before,references=references,labels=labels,
        final_is_price=normalize(labels.get('with_margin','')) in ['precio venta','precio de venta'])
