"""Shared owner LCOE scenario for the interactive overview and its PDF."""
from lcoe_finance import levelized_cost
from valuation80_unit import commercial_unit80


def summary_lcoe80(model,capacity_factor,fx=None):
    values=commercial_unit80(model,fx)
    capex=float(values['Precio de venta'])
    result=levelized_cost(capacity_kw=80,capacity_factor=capacity_factor,capex=capex,
        fixed_om=capex*.02,variable_om=0.,years=20,rate=.08)
    result.update(capex=capex,fixed_om=capex*.02,years=20,rate=.08)
    return result
