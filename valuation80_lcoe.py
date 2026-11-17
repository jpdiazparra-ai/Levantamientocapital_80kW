"""Shared owner LCOE scenario for the interactive overview and its PDF."""
from lcoe_finance import levelized_cost
from valuation80_unit import sale_prices80


def summary_lcoe80(model,capacity_factor,fx=None,equipment_cost=None):
    prices=sale_prices80(model,fx,equipment_cost=equipment_cost)
    capex=float(prices['net'])
    result=levelized_cost(capacity_kw=80,capacity_factor=capacity_factor,capex=capex,
        fixed_om=capex*.02,variable_om=0.,years=20,rate=.08)
    result.update(price_source=prices['source'],capex=capex,fixed_om=capex*.02,years=20,rate=.08)
    return result
