"""10 kW project costs with the same eligibility rules as the 80 kW case."""
from valuation_costs import SOURCE, cost_report_data as _cost_report_data, load_cost_report as _load_cost_report


def cost_report_data(plan_rows, cost_rows):
    return _cost_report_data(plan_rows, cost_rows, capacity_kw=10)


def load_cost_report(revision):
    return _load_cost_report(revision, capacity_kw=10)
