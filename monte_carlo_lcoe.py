"""Reproducible uncertainty propagation for the constant-real-cost owner LCOE."""
import math

import numpy as np
import pandas as pd


PARAMETERS = ('capex_multiplier', 'om_fraction', 'capacity_factor', 'rate')


def simulate_lcoe(*, capacity_kw, base_capex, years, ranges, samples=10000, seed=2026):
    """Independent triangular inputs; annual O&M is linked to sampled CAPEX.

    Monetary amounts are USD internally. Each draw is one lifetime scenario,
    with constant annual energy/O&M and year-end discounting, as in levelized_cost.
    Ranges are (minimum, mode, maximum), with a constant allowed in all slots.
    """
    if not all(isinstance(v, (int, float, np.number)) and math.isfinite(v)
               for v in (capacity_kw, base_capex, years)):
        raise ValueError('Completa potencia, CAPEX y vida útil con valores finitos.')
    if capacity_kw <= 0 or base_capex < 0 or not 1 <= years <= 100 or int(years) != years:
        raise ValueError('Revisa potencia, CAPEX y vida útil (1–100 años enteros).')
    if isinstance(samples, bool) or not isinstance(samples, (int, np.integer)) or not 100 <= samples <= 100000:
        raise ValueError('El número de simulaciones debe ser un entero entre 100 y 100.000.')
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)) or seed < 0:
        raise ValueError('La semilla debe ser un entero no negativo.')
    validated = {}
    for name in PARAMETERS:
        try:
            low, mode, high = map(float, ranges[name])
        except (KeyError, TypeError, ValueError):
            raise ValueError('Cada variable requiere mínimo, más probable y máximo.') from None
        if not all(math.isfinite(v) for v in (low, mode, high)) or not 0 <= low <= mode <= high:
            raise ValueError('Usa rangos finitos: 0 ≤ mínimo ≤ más probable ≤ máximo.')
        if name == 'capacity_factor' and (low <= 0 or high > 1):
            raise ValueError('El factor de planta debe ser mayor que 0 % y como máximo 100 %.')
        if name in ('om_fraction', 'rate') and high > 1:
            raise ValueError('Mantenimiento y tasa deben estar entre 0 % y 100 %.')
        validated[name] = (low, mode, high)

    rng = np.random.default_rng(seed)
    draws = {name: np.full(samples, low) if low == high else rng.triangular(low, mode, high, samples)
             for name, (low, mode, high) in validated.items()}
    capex = base_capex * draws['capex_multiplier']
    om = capex * draws['om_fraction']
    energy = capacity_kw * 8760 * draws['capacity_factor']
    # Sum of year-end discount factors, evaluated without cancellation near r=0.
    rate = draws['rate']
    annuity = np.full(samples, float(years))
    positive = rate > 0
    annuity[positive] = -np.expm1(-years * np.log1p(rate[positive])) / rate[positive]
    lcoe = (capex / annuity + om) / energy
    if not np.isfinite(lcoe).all():
        raise ValueError('Los rangos exceden el límite numérico del cálculo.')
    frame = pd.DataFrame({
        'Simulación': np.arange(1, samples + 1),
        'CAPEX · USD/kW': capex / capacity_kw,
        'O&M anual · USD/kW/año': om / capacity_kw,
        'Factor de planta · %': draws['capacity_factor'] * 100,
        'Tasa real · %': rate * 100,
        'O&M · % CAPEX/año': draws['om_fraction'] * 100,
        'Generación anual · kWh': energy,
        'LCOE · USD/kWh': lcoe,
        'LCOE · USD/MWh': lcoe * 1000,
    })
    p10, p50, p90 = np.quantile(lcoe, [.1, .5, .9])
    return dict(frame=frame, p10=float(p10), p50=float(p50), p90=float(p90),
        mean=float(lcoe.mean()), ranges=validated, seed=int(seed), samples=int(samples),
        base_capex=float(base_capex), capacity_kw=float(capacity_kw), years=int(years))
