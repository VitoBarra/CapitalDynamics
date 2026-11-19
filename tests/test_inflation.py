from dataclasses import replace
import unittest

from capital_dynamics.monetary import MonetaryConfig, MonetarySimulation


class InflationTests(unittest.TestCase):
    def economy(self, money, **changes):
        config = MonetaryConfig(pop_size=1, initial_money_per_person=money,
            initial_capacity=10, productivity=10, initial_producer_money=0,
            wage_fraction=0, tau_max=0, private_investment_fraction=0,
            ubi_budget_fraction=0, pension_budget_fraction=0,
            healthcare_spending_fraction=0, investment_budget_fraction=0,
            consumption_fraction=1, policy_rate=0, delta=0,
            birth_prob_max=0, death_base_prob=0, aging_risk_rate=0,
            healthcare_choice_mode="Public only")
        sim = MonetarySimulation(replace(config, **changes))
        sim.population[0].age = 30
        return sim

    def test_prices_fall_hold_or_rise_with_goods_demand(self):
        for money, coverage, inflation, unsold in (
                (5, .5, -.05, 5), (10, 1, 0, 0),
                (20, 2, .1, 0), (100, 10, .25, 0)):
            with self.subTest(money=money):
                sim = self.economy(money)
                sim.advance()
                row = sim.history[-1]
                self.assertAlmostEqual(row["Goods demand coverage"], coverage)
                self.assertAlmostEqual(row["Inflation"], inflation)
                self.assertAlmostEqual(row["Unsold goods"], unsold)
                self.assertAlmostEqual(row["Desired goods spending"], money)
                # Supply is valued before, not after, this year's price change.
                self.assertAlmostEqual(row["Output at trade prices"], 10)
                self.assertAlmostEqual(row["Price level"], 1 + inflation)
                self.assertAlmostEqual(sim.broad_money, money)

    def test_zero_supply_has_no_fictitious_finite_coverage(self):
        sim = self.economy(10, initial_capacity=0)
        self.assertIsNone(sim.history[0]["Goods demand coverage"])
        sim.advance()
        self.assertIsNone(sim.history[-1]["Goods demand coverage"])
        self.assertGreater(sim.inflation, 0)
        self.assertEqual(sim.history[-1]["Unsold goods"], 0)

    def test_goods_identity_and_price_rule_over_multiple_years(self):
        sim = MonetarySimulation(MonetaryConfig(pop_size=10))
        sim.advance(15)
        for row in list(sim.history)[1:]:
            self.assertAlmostEqual(row["Output"], row["Real consumption"]
                                   + row["Real investment"] + row["Unsold goods"])
            coverage = row["Goods demand coverage"]
            if coverage is not None:
                expected = max(-.1, min(.25, sim.config.inflation_response * (coverage - 1)))
                self.assertAlmostEqual(row["Inflation"], expected)
