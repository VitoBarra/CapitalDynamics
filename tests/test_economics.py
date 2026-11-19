from dataclasses import replace
import unittest

import numpy as np

from capital_dynamics.economics import (
    age_dependent_birth_prob, gini_coefficient, mortality_probability,
    relative_wealth, tax_rates_at_relative_wealth, wealth_tax_rates,
)
from capital_dynamics.monetary import MonetaryConfig


class EconomicsTests(unittest.TestCase):
    def test_tax_schedule_is_independent_of_currency_scale(self):
        config = MonetaryConfig()
        for scale in (1e-12, 1e-4, 1, 1e4, 1e12):
            with self.subTest(scale=scale):
                np.testing.assert_allclose(wealth_tax_rates(np.array([1, 1.5, 2]) * scale, config),
                                           [0, .15, .6])

    def test_equal_and_empty_wealth(self):
        for values in ([0, 0], [1e-15, 1e-15], [10, 10], []):
            np.testing.assert_array_equal(relative_wealth(values), np.zeros(len(values)))
            np.testing.assert_array_equal(wealth_tax_rates(values, MonetaryConfig(tau_base=.05)),
                                          np.full(len(values), .05))

    def test_tax_endpoints_and_progressivity(self):
        config = MonetaryConfig(tau_base=.01, tau_max=.2, tau_gamma=2)
        np.testing.assert_allclose(tax_rates_at_relative_wealth([0, .5, 1], config), [.01, .0575, .2])

    def test_inequality_and_birth_boundaries(self):
        self.assertEqual(gini_coefficient([1, 1, 1]), 0)
        self.assertAlmostEqual(gini_coefficient([0, 0, 3]), 2 / 3)
        self.assertEqual(gini_coefficient([]), 0)
        self.assertEqual(gini_coefficient([0, 0]), 0)
        self.assertEqual(age_dependent_birth_prob(13, .03), 0)
        self.assertEqual(age_dependent_birth_prob(69, .03), 0)
        self.assertAlmostEqual(age_dependent_birth_prob(30, .03), .03)

    def test_age_and_care_change_full_mortality_hazard(self):
        config = MonetaryConfig()
        self.assertGreater(mortality_probability(80, config), mortality_probability(20, config))
        self.assertGreater(mortality_probability(0, config), mortality_probability(10, config))
        for age in (0, 20, 80, 120, 10000):
            risk = mortality_probability(age, config)
            self.assertGreater(risk, 0)
            self.assertLess(risk, 1)
            self.assertLessEqual(mortality_probability(age, config, .5), risk)
        self.assertLess(mortality_probability(80, config, .5), mortality_probability(80, config))
        self.assertEqual(mortality_probability(80, config, 0), 0)
        self.assertEqual(mortality_probability(80, replace(config, death_base_prob=1)), 1)
