"""Shared owner LCOE scenario for the interactive overview and its PDF."""
from lcoe_finance import levelized_cost
from valuation10_unit import commercial_unit10


def summary_lcoe10(model,capacity_factor,fx=None):
    values=commercial_unit10(model,fx)
    capex=float(values['Precio de venta'])
    result=levelized_cost(capacity_kw=10,capacity_factor=capacity_factor,capex=capex,
        fixed_om=capex*.02,variable_om=0.,years=20,rate=.08)
    result.update(capex=capex,fixed_om=capex*.02,years=20,rate=.08)
    return result
