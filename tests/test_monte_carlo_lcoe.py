"""Monte Carlo matches the discounted owner model and preserves reproducibility."""
import unittest

import numpy as np
import pandas as pd

from lcoe_finance import levelized_cost
from monte_carlo_lcoe import simulate_lcoe


class MonteCarloLCOETests(unittest.TestCase):
    def args(self):
        return dict(capacity_kw=80., base_capex=100000., years=20,
            ranges=dict(capex_multiplier=(.8, 1., 1.2), om_fraction=(.01, .02, .03),
                capacity_factor=(.3, .35, .4), rate=(.06, .08, .1)), samples=1000, seed=2026)

    def test_fixed_ranges_match_reference_including_zero_rate(self):
        for rate in (0., 1e-12, .08):
            args=self.args()
            args['ranges']=dict(capex_multiplier=(1.,)*3, om_fraction=(.02,)*3,
                capacity_factor=(.35,)*3, rate=(rate,)*3)
            result=simulate_lcoe(**args)
            expected=levelized_cost(capacity_kw=80, capacity_factor=.35, capex=100000,
                fixed_om=2000, variable_om=0., years=20, rate=rate)['lcoe']
            for key in ('p10', 'p50', 'p90', 'mean'):
                self.assertAlmostEqual(result[key], expected)
            self.assertTrue(np.allclose(result['frame']['LCOE · USD/kWh'], expected))

    def test_individual_draws_reconcile_with_discounted_cash_flows(self):
        result=simulate_lcoe(**self.args())
        for _, row in result['frame'].iloc[:12].iterrows():
            expected=levelized_cost(capacity_kw=80, capacity_factor=row['Factor de planta · %']/100,
                capex=row['CAPEX · USD/kW']*80, fixed_om=row['O&M anual · USD/kW/año']*80,
                variable_om=0., years=20, rate=row['Tasa real · %']/100)
            self.assertAlmostEqual(row['LCOE · USD/kWh'], expected['lcoe'])
            self.assertAlmostEqual(row['Generación anual · kWh'], expected['energy_y1'])

    def test_reproducible_quantiles_and_sample_bounds(self):
        a=simulate_lcoe(**self.args())
        b=simulate_lcoe(**self.args())
        pd.testing.assert_frame_equal(a['frame'], b['frame'])
        self.assertLess(a['p10'], a['p50'])
        self.assertLess(a['p50'], a['p90'])
        self.assertTrue(a['frame']['CAPEX · USD/kW'].between(1000., 1500.).all())
        self.assertTrue(a['frame']['Factor de planta · %'].between(30., 40.).all())
        c=simulate_lcoe(**{**self.args(), 'seed': 80})
        self.assertFalse(a['frame'].equals(c['frame']))

    def test_capex_scaling_and_power_normalization(self):
        args=self.args()
        baseline=simulate_lcoe(**args)
        doubled=simulate_lcoe(**{**args, 'base_capex': 200000.})
        self.assertAlmostEqual(doubled['p50'], 2*baseline['p50'])
        smaller=simulate_lcoe(**{**args, 'base_capex': 12500., 'capacity_kw': 10.})
        np.testing.assert_allclose(smaller['frame']['LCOE · USD/kWh'],
            baseline['frame']['LCOE · USD/kWh'])

    def test_invalid_ranges_do_not_produce_plausible_results(self):
        for field, bounds in [('capacity_factor', (0., .2, .3)), ('rate', (-.1, .05, .1)),
                ('om_fraction', (.01, .02, 2.)), ('capex_multiplier', (1., .8, 1.2)),
                ('rate', (.05, float('nan'), .1))]:
            args=self.args()
            args['ranges'][field]=bounds
            with self.subTest(field=field, bounds=bounds), self.assertRaises(ValueError):
                simulate_lcoe(**args)
        for overrides in [{'base_capex': float('nan')}, {'years': 1.5}, {'samples': 1}, {'seed': -1}]:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                simulate_lcoe(**{**self.args(), **overrides})


if __name__ == '__main__':
    unittest.main()
