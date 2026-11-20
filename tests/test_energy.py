from dataclasses import replace
import unittest

from capital_dynamics.energy import ENERGY
from capital_dynamics.monetary import MonetaryConfig, MonetarySimulation


class EnergyTests(unittest.TestCase):
    def economy(self, **changes):
        cfg = MonetaryConfig(pop_size=6, initial_money_per_person=5, initial_capacity=20,
            firm_count=2, firm_productivity_dispersion=0, initial_demand_fraction=1, inventory_target=0,
            productivity_growth=0, technology_breakthrough_probability=0, research_spending_fraction=0,
            birth_prob_max=0, death_base_prob=0, aging_risk_rate=0, tau_max=0, delta=0,
            education_budget_fraction=0, private_investment_fraction=0, investment_budget_fraction=0,
            healthcare_choice_mode="Public only", work_skill_gain=0, skill_depreciation=0,
            energy_supply=20, energy_intensity=1, energy_base_price=.1,
            energy_scarcity_response=0, energy_shock_probability=0, energy_income_fraction=0)
        sim = MonetarySimulation(replace(cfg, **changes))
        for p in sim.population:
            p.age = 30
        return sim

    def balanced(self, sim):
        self.assertAlmostEqual(sum(r["Net worth"] for r in sim.balance_sheets()), sim.real_asset_value, places=7)
        for name in ("Money balance error", "Base money balance error", "Government balance error",
                     "Inventory balance error", "Energy balance error", "Energy input balance error"):
            self.assertAlmostEqual(sim.history[-1][name], 0, places=7)
        self.assertTrue(all(value >= -1e-8 for value in sim.accounts.values()))
        self.assertLessEqual(sim.energy.used, sim.energy.available + 1e-8)

    def test_production_requires_paid_physical_energy(self):
        sim = self.economy()
        money, base = sim.broad_money, sim.reserves
        sim.advance()
        self.assertAlmostEqual(sim.output, 12)
        self.assertAlmostEqual(sim.flows["Energy used"], sim.output)
        self.assertAlmostEqual(sim.flows["Energy spending"], 1.2)
        self.assertAlmostEqual(sim.accounts[ENERGY], 1.2)
        self.assertAlmostEqual(sim.flows["Energy unused"], 8)
        self.assertAlmostEqual(sim.broad_money, money)
        self.assertEqual(sim.reserves, base)
        self.balanced(sim)

    def test_shortages_reduce_new_output_and_hiring(self):
        ample, short = self.economy(), self.economy(energy_supply=4)
        ample.advance()
        short.advance()
        self.assertAlmostEqual(short.output, 4)
        self.assertLess(short.output, ample.output)
        self.assertLess(short.flows["Employed"], ample.flows["Employed"])
        self.assertAlmostEqual(short.flows["Energy coverage"], 1 / 3)
        self.assertAlmostEqual(short.flows["Energy-limited planned output"], 8)
        self.balanced(short)

    def test_energy_is_reserved_pro_rata_not_first_come_first_served(self):
        sim = self.economy(energy_supply=3)
        sim.energy.allocate({0: 8, 1: 4})
        self.assertEqual(sim.energy.quotas, {0: 2, 1: 1})
        other = self.economy(energy_supply=3)
        other.energy.allocate({1: 4, 0: 8})
        self.assertEqual(sim.energy.quotas, other.energy.quotas)

    def test_zero_supply_stops_dependent_new_production(self):
        sim = self.economy(energy_supply=0)
        sim.advance()
        self.assertEqual(sim.output, 0)
        self.assertEqual(sim.flows["Employed"], 0)
        self.assertEqual(sim.flows["Energy used"], 0)
        self.assertEqual(sim.flows["Energy spending"], 0)
        self.assertEqual(sim.flows["Energy coverage"], 0)
        self.balanced(sim)

    def test_old_inventories_can_be_sold_without_new_energy(self):
        sim = self.economy(energy_supply=0, consumption_fraction=1, inventory_spoilage=0)
        sim.goods_remaining = 20
        sim.advance()
        self.assertEqual(sim.output, 0)
        self.assertGreater(sim.flows["Real consumption"], 0)
        self.assertEqual(sim.flows["Energy spending"], 0)
        self.balanced(sim)

    def test_zero_intensity_removes_only_the_energy_requirement(self):
        sim = self.economy(energy_supply=0, energy_intensity=0)
        sim.advance()
        self.assertEqual(sim.output, 12)
        self.assertEqual(sim.flows["Energy used"], 0)
        self.assertIsNone(sim.flows["Energy coverage"])
        self.balanced(sim)

    def test_payroll_and_energy_must_both_be_affordable(self):
        sim = self.economy(initial_producer_money=7, energy_base_price=1)
        sim.advance()
        self.assertEqual(sim.output, 0)  # Each firm's €2.80 cannot fund a €1 wage plus €2 energy.
        self.assertEqual(sim.flows["Wages"], 0)
        self.assertEqual(sim.accounts[ENERGY], 0)
        self.balanced(sim)

    def test_business_working_capital_can_fund_energy_and_payroll(self):
        sim = self.economy(initial_producer_money=2, firm_count=1, energy_base_price=1, business_lending=True)
        firm = sim.market.active[0]
        firm.last_profit, firm.last_sales = 100, 100
        sim.advance()
        self.assertGreater(sim.flows["Business loans originated"], 0)
        self.assertAlmostEqual(sim.output, 12)
        self.assertAlmostEqual(sim.flows["Energy spending"], 12)
        self.balanced(sim)

    def test_unused_quotas_are_not_charged_or_credited_as_output(self):
        sim = self.economy(initial_producer_money=0)
        sim.advance()
        self.assertGreater(sim.flows["Energy demand"], 0)
        self.assertEqual(sim.flows["Energy used"], 0)
        self.assertEqual(sim.flows["Energy unused"], 20)
        self.assertEqual(sim.flows["Energy spending"], 0)

    def test_higher_input_cost_reduces_profit_and_can_raise_goods_prices(self):
        cheap = self.economy(energy_base_price=.1, wage_fraction=.8)
        dear = self.economy(energy_base_price=.8, wage_fraction=.8)
        cheap.advance()
        dear.advance()
        self.assertEqual(cheap.output, dear.output)
        self.assertGreater(dear.flows["Energy spending"], cheap.flows["Energy spending"])
        self.assertLess(dear.flows["Firm profits"], cheap.flows["Firm profits"])
        self.assertGreater(dear.inflation, cheap.inflation)
        self.assertGreater(dear.inflation, 0)
        self.balanced(dear)

    def test_scarcity_can_raise_prices_even_as_jobs_fall(self):
        ample = self.economy(energy_scarcity_response=2)
        short = self.economy(energy_supply=4, energy_scarcity_response=2)
        ample.advance()
        short.advance()
        self.assertGreater(short.energy.price, ample.energy.price)
        self.assertLess(short.flows["Employed"], ample.flows["Employed"])
        self.assertGreater(short.inflation, 0)

    def test_income_recycles_existing_deposits_after_goods_purchases(self):
        retained = self.economy(energy_income_fraction=0)
        shared = self.economy(energy_income_fraction=1)
        retained.advance()
        shared.advance()
        self.assertAlmostEqual(retained.flows["Real consumption"], shared.flows["Real consumption"])
        self.assertAlmostEqual(retained.broad_money, shared.broad_money)
        self.assertEqual(shared.accounts[ENERGY], 0)
        self.assertAlmostEqual(shared.flows["Energy income"], shared.flows["Energy spending"])
        payments = [t for t in shared.transactions if t["Purpose"] == "Energy income"]
        self.assertEqual(len(payments), 6)
        self.assertAlmostEqual(sum(t["Amount"] for t in payments), shared.flows["Energy spending"])

    def test_queued_shock_has_exact_duration_and_recovers(self):
        sim = self.economy(energy_shock_duration=2, energy_shock_severity=.5)
        sim.energy.shock_pending = True
        states = []
        for _ in range(3):
            sim.advance()
            states.append((sim.flows["Energy shock active"], sim.flows["Energy available"]))
            self.balanced(sim)
        self.assertEqual(states, [(True, 10), (True, 10), (False, 20)])
        self.assertFalse(sim.energy.shock_pending)
        self.assertEqual(len(sim.energy.events), 1)

    def test_total_shock_does_not_destroy_deposits_or_productive_capital(self):
        sim = self.economy(energy_shock_severity=1)
        sim.energy.shock_pending = True
        capital, money = sim.capacity, sim.broad_money
        sim.advance()
        self.assertEqual(sim.output, 0)
        self.assertEqual(sim.capacity, capital)
        self.assertAlmostEqual(sim.broad_money, money)
        self.balanced(sim)

    def test_random_shocks_are_seeded_and_do_not_stack(self):
        a, b = self.economy(energy_shock_probability=1), self.economy(energy_shock_probability=1)
        for sim in (a, b):
            sim.advance(4)
        self.assertEqual(list(a.energy.events), list(b.energy.events))
        self.assertEqual([event["Year"] for event in a.energy.events], [1, 3])
        self.assertEqual(a.market.rows(), b.market.rows())

    def test_queued_shock_can_refresh_an_active_disruption(self):
        sim = self.economy()
        sim.energy.shock_pending = True
        sim.advance()
        sim.update_policy(energy_shock_duration=3)
        sim.energy.shock_pending = True
        sim.advance()
        self.assertEqual(sim.energy.shock_remaining, 2)
        self.assertEqual(len(sim.energy.events), 2)

    def test_growth_and_live_baseline_supply_preserve_supply_index(self):
        sim = self.economy(energy_supply_growth=.1)
        sim.advance(2)
        self.assertAlmostEqual(sim.flows["Energy available"], 20 * 1.1 ** 2)
        sim.update_policy(energy_supply=40)
        sim.advance()
        self.assertAlmostEqual(sim.flows["Energy available"], 40 * 1.1 ** 3)

    def test_energy_rng_does_not_consume_demographic_or_technology_draws(self):
        a, b = self.economy(), self.economy()
        a.energy.allocate({0: 10})
        self.assertEqual(a.rng.rand(), b.rng.rand())
        self.assertEqual(a.technology_rng.random(), b.technology_rng.random())

    def test_invalid_policies_and_requests_are_rejected(self):
        for change in ({"energy_supply":-1}, {"energy_base_price":0}, {"energy_shock_severity":1.1},
                       {"energy_shock_duration":0}, {"energy_shock_duration":1.5},
                       {"energy_income_fraction":2}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.economy(**change)
        sim = self.economy()
        with self.assertRaises(ValueError):
            sim.energy.allocate({0: -1})
        with self.assertRaises(ValueError):
            sim.energy.purchase(sim.market.active[0], float("nan"))
