from dataclasses import replace
import unittest

from capital_dynamics.monetary import MonetaryConfig, MonetarySimulation


class TechnologyTests(unittest.TestCase):
    def economy(self, seed=42, **changes):
        config = MonetaryConfig(pop_size=1, initial_capacity=100, productivity=2,
            productivity_growth=0, technology_breakthrough_probability=0,
            research_spending_fraction=0, firm_count=1, firm_productivity_dispersion=0,
            initial_demand_fraction=1, inventory_target=0, technology_adoption_rate=1,
            delta=0, private_investment_fraction=0, investment_budget_fraction=0,
            birth_prob_max=0, death_base_prob=0, aging_risk_rate=0,
            healthcare_choice_mode="Public only")
        sim = MonetarySimulation(replace(config, **changes), seed=seed)
        sim.population[0].age = 30
        return sim

    def test_gradual_growth_compounds_before_production(self):
        sim = self.economy(productivity_growth=.02)
        self.assertEqual(sim.history[0]["Technology index"], 1)
        for year in range(1, 5):
            sim.advance()
            self.assertAlmostEqual(sim.technology_index, 1.02 ** year)
            self.assertAlmostEqual(sim.market.active[0].technology, 1.02 ** year)
            self.assertLessEqual(sim.output, 2 * 1.02 ** year)
            self.assertAlmostEqual(sim.history[-1]["Productivity growth realized"], .02)
        self.assertEqual(sim.technology_breakthroughs, 0)

    def test_breakthroughs_are_permanent_and_compound_with_trend(self):
        sim = self.economy(productivity_growth=.01, technology_breakthrough_probability=1,
                           technology_gain_min=.1, technology_gain_max=.1)
        sim.advance(3)
        self.assertEqual(sim.technology_breakthroughs, 3)
        self.assertAlmostEqual(sim.technology_index, (1.01 * 1.1) ** 3)
        self.assertAlmostEqual(sim.history[-1]["Productivity growth realized"], .111)
        self.assertEqual([event["Year"] for event in sim.technology_events], [1, 2, 3])
        index = sim.technology_index
        sim.update_policy(productivity_growth=0, technology_breakthrough_probability=0)
        sim.advance()
        self.assertEqual(sim.technology_index, index)
        self.assertEqual(sim.history[-1]["Technology productivity gain"], 0)
        self.assertEqual(sim.history[-1]["Technology breakthrough event"], 0)
        sim.update_policy(productivity=3)
        self.assertAlmostEqual(sim.effective_productivity, 3 * index)

    def test_disabled_technology_stays_constant(self):
        sim = self.economy()
        sim.advance(5)
        self.assertEqual(sim.effective_productivity, 2)
        self.assertFalse(sim.technology_events)
        self.assertEqual(sim.technology_breakthroughs, 0)

    def test_seeded_events_are_reproducible_and_gains_stay_in_bounds(self):
        options = dict(technology_breakthrough_probability=.5, technology_gain_min=.03, technology_gain_max=.12)
        a, b, c = (self.economy(seed=seed, **options) for seed in (42, 42, 43))
        for sim in (a, b, c):
            sim.advance(20)
        self.assertEqual(list(a.technology_events), list(b.technology_events))
        self.assertEqual(a.technology_index, b.technology_index)
        self.assertNotEqual(list(a.technology_events), list(c.technology_events))
        self.assertTrue(a.technology_events)
        self.assertTrue(all(.03 <= event["Technology productivity gain"] <= .12 for event in a.technology_events))

    def test_technology_draws_do_not_consume_demographic_rng(self):
        a, b = self.economy(), self.economy(technology_breakthrough_probability=1)
        b.advance_technology()
        self.assertEqual(a.rng.rand(), b.rng.rand())

    def test_innovation_cannot_create_money_or_relax_the_capital_limit(self):
        sim = self.economy(initial_capacity=1, technology_breakthrough_probability=1)
        money, reserves, capital = sim.broad_money, sim.reserves, sim.capacity
        sim.advance()
        self.assertEqual(sim.output, 1)
        self.assertEqual(sim.capacity, capital)
        self.assertEqual(sim.broad_money, money)
        self.assertEqual(sim.reserves, reserves)
        row = sim.history[-1]
        for name in ("Money balance error", "Base money balance error", "Government balance error"):
            self.assertAlmostEqual(row[name], 0)
        self.assertAlmostEqual(sum(x["Net worth"] for x in sim.balance_sheets()), sim.real_asset_value)

    def test_invalid_growth_probability_and_gain_ranges_are_rejected(self):
        for changes in ({"productivity_growth":-.01}, {"productivity_growth":1.1},
                        {"technology_breakthrough_probability":1.1}, {"technology_gain_min":.3, "technology_gain_max":.1},
                        {"technology_gain_max":float("nan")}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.economy(**changes)

    def test_zero_base_productivity_stays_zero(self):
        sim = self.economy(productivity=0, technology_breakthrough_probability=1)
        sim.advance()
        self.assertEqual(sim.output, 0)
        self.assertEqual(sim.effective_productivity, 0)
