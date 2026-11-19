from dataclasses import fields
import math
import random
import unittest

import numpy as np

from capital_dynamics.monetary import GOV, PRODUCER, MonetaryConfig, MonetarySimulation


class ModelValidationTests(unittest.TestCase):
    def test_bond_collateral_funds_annual_private_investment(self):
        config = MonetaryConfig(pop_size=1, initial_capacity=0, lending_enabled=True,
            private_investment_fraction=0, investment_budget_fraction=0, investment_risk=0)
        sim = MonetarySimulation(config)
        person = sim.population[0]
        person.age = 30
        person.last_repayment_income = 100
        person.income_observed = True
        sim.sell_bond(person.account, .5)
        sim.goods_remaining = 10
        before = sim.broad_money
        sim.invest()
        self.assertAlmostEqual(sim.flows["Loans originated"], .1)
        self.assertAlmostEqual(person.assets, .1 * config.base_eff)
        self.assertAlmostEqual(sim.broad_money, before + .1)
        self.assertLessEqual(sim.debt(person), .5)

    def test_shared_collateral_room_deducts_existing_debt(self):
        sim = MonetarySimulation(MonetaryConfig(pop_size=1, initial_capacity=0, lending_enabled=True))
        person = sim.population[0]
        person.age = 30
        person.last_repayment_income = 100
        person.income_observed = True
        sim.sell_bond(person.account, .5)
        self.assertAlmostEqual(sim.originate_loan(person, .4), .4)
        self.assertAlmostEqual(sim.borrowing_room(person), .1)
        self.assertAlmostEqual(sim.originate_loan(person, 10), .1)
        self.assertEqual(sim.originate_loan(person, .1), 0)

    def test_mortality_uses_same_cohort_ages_and_actual_care_choices(self):
        sim = MonetarySimulation(MonetaryConfig(pop_size=3, birth_prob_max=0))
        for person, age in zip(sim.population, [10, 50, 80]):
            person.age = age
        sim.mortality_multiplier = .7
        sim.population[-1].healthcare_choice = "Private"
        expected = sim.mortality_observations()
        self.assertAlmostEqual(expected["Unfunded mortality"],
                               np.mean([sim.death_probability(age, funded=False) for age in [10, 50, 80]]))
        self.assertAlmostEqual(expected["Public care mortality"],
                               np.mean([sim.death_probability(age) for age in [10, 50, 80]]))
        self.assertAlmostEqual(expected["Expected mortality"],
                               np.mean([sim.death_probability(10), sim.death_probability(50),
                                        sim.private_death_probability(80)]))
        # Force one known death and no births: averages must not be recomputed
        # from survivors or their incremented ages.
        class Draws:
            def __init__(self):
                self.values = iter([1, 1, 0, 1, 1])
            def rand(self):
                return next(self.values)
        sim.rng = Draws()
        sim.demographics()
        for name, value in expected.items():
            self.assertAlmostEqual(sim.flows[name], value)
        self.assertEqual(sim.flows["Observed mortality"], 1 / 3)
        self.assertEqual([p.age for p in sim.population], [11, 51])

    def test_year_zero_has_risk_but_no_observed_death_interval(self):
        sim = MonetarySimulation()
        row = sim.history[0]
        self.assertIsNone(row["Observed mortality"])
        self.assertGreater(row["Unfunded mortality"], sim.config.death_base_prob)
        self.assertEqual(row["Expected mortality"], row["Public care mortality"])
        self.assertNotIn("Baseline mortality", row)
        self.assertNotIn("Public mortality", row)
        sim.advance()
        self.assertIsNotNone(sim.history[-1]["Observed mortality"])

    def test_accounting_goods_and_capital_identities_under_varied_policies(self):
        rng = random.Random(83)
        for seed in range(12):
            shares = [rng.random() for _ in range(5)]
            denominator = sum(shares) + 1
            shares = [x / denominator for x in shares]
            config = MonetaryConfig(pop_size=6, birth_prob_max=0, lending_enabled=True,
                government_borrowing=True, monetary_financing=True, issuance_per_step=2,
                bond_term=2, loan_term=2, delta=rng.choice([0, .2, 1]),
                death_base_prob=rng.choice([0, .01, .2]),
                investment_risk=rng.random(), failed_investment_loss=rng.random(),
                capital_ratio=rng.choice([0, .1, 1]), reserve_ratio=rng.choice([0, .1, 1]),
                ubi_budget_fraction=shares[0], pension_budget_fraction=shares[1],
                healthcare_spending_fraction=shares[2], investment_budget_fraction=shares[3],
                debt_service_fraction=shares[4])
            sim = MonetarySimulation(config, seed=seed)
            for _ in range(40):
                before = sim.capacity
                opening_prudential_equity = sim.prudential_equity
                if not sim.step():
                    break
                row = sim.history[-1]
                with self.subTest(seed=seed, year=sim.step_count):
                    self.assertAlmostEqual(sum(x["Net worth"] for x in sim.balance_sheets()),
                                           sim.capacity * sim.price, places=7)
                    self.assertAlmostEqual(sim.output, row["Real consumption"] + row["Real investment"]
                                           + sim.goods_remaining, places=7)
                    self.assertAlmostEqual(sim.capacity, before * (1 - config.delta)
                                           + sim.spent["Public investment"] / sim.trade_price * config.base_eff
                                           + row["Private capital added"], places=7)
                    for key in ("Money balance error", "Base money balance error", "Government balance error"):
                        self.assertAlmostEqual(row[key], 0, places=7)
                    self.assertTrue(all(math.isfinite(x) and x >= -1e-8 for x in sim.accounts.values()))
                    self.assertAlmostEqual(sim.prudential_equity - opening_prudential_equity,
                                           row["Bank realized profit"] - row["Bank distributions"], places=7)

    def test_config_contains_no_retired_regime_or_alias_fields(self):
        names = {field.name for field in fields(MonetaryConfig)}
        self.assertTrue({"initial_money_per_person", "initial_capacity", "ubi_budget_fraction"} <= names)
        self.assertFalse({"budget_mode", "init_wealth", "logistic_capacity", "direct_redistribution_fraction"} & names)
        with self.assertRaises(TypeError):
            MonetaryConfig(logistic_capacity=100)
