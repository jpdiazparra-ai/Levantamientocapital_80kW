"""Shared owner LCOE scenario for the interactive overview and its PDF."""
from lcoe_finance import levelized_cost
from valuation10_unit import sale_prices10


def summary_lcoe10(model,capacity_factor,fx=None):
    prices=sale_prices10(model,fx)
    capex=float(prices['net'])
    result=levelized_cost(capacity_kw=10,capacity_factor=capacity_factor,capex=capex,
        fixed_om=capex*.02,variable_om=0.,years=20,rate=.08)
    result.update(price_source=prices['source'],capex=capex,fixed_om=capex*.02,years=20,rate=.08)
    return result
