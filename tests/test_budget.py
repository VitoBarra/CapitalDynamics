import itertools
import unittest

from budget import allocate, allocation_rows, validate_allocations
from simulation import Simulation, SimulationConfig, restore_simulation


class BudgetTests(unittest.TestCase):
    def test_every_share_uses_same_total(self):
        self.assertEqual(allocate(100, [.25, .2, .3, .15]),
                         {'UBI': 25, 'Pensions': 20, 'Healthcare': 30, 'Public investment': 15})
        rows = allocation_rows(100, [.25, .2, .3, .15], {'UBI': 25, 'Pensions': 10})
        self.assertAlmostEqual(sum(row['Allocation (% of total budget)'] for row in rows), 100)
        self.assertEqual(rows[1]['Unused'], 10)
        self.assertAlmostEqual(rows[0]['Actual (% of expenditure)'], 25 / 35 * 100)

    def test_invalid_and_zero_allocations(self):
        for shares in ([1, 1, 0, 0], [-1, 0, 0, 0], [float('nan'), 0, 0, 0]):
            with self.assertRaises(ValueError):
                validate_allocations(shares)
        self.assertTrue(all(v == 0 for v in allocate(0, [.2, .2, .2, .2]).values()))
        self.assertEqual(allocation_rows(0, [0, 0, 0, 0], {})[-1]['Allocation (% of total budget)'], 100)

    def test_payments_do_not_depend_on_order_or_unused_pensions(self):
        for order in itertools.permutations(('pay_ubi', 'pay_pensions', 'update_healthcare')):
            sim = Simulation(SimulationConfig(pop_size=1, budget_mode='Total budget', retirement_age=0,
                pension_per_person=1, direct_redistribution_fraction=.25, pension_budget_fraction=.2,
                healthcare_spending_fraction=.3, investment_budget_fraction=.15))
            sim.government_budget = 100
            sim.prepare_budget()
            for method in order:
                getattr(sim, method)()
            self.assertEqual(sim.ubi_spending, 25)
            self.assertEqual(sim.pension_spending, 1)
            self.assertEqual(sim.healthcare_spending, 30)
            self.assertEqual(sim.government_budget, 44)

    def test_total_policy_changes_are_atomic(self):
        sim = Simulation(SimulationConfig(budget_mode='Total budget'))
        before = sim.config
        with self.assertRaises(ValueError):
            sim.update_policy(healthcare_spending_fraction=.9)
        self.assertEqual(sim.config, before)
        sim.update_policy(healthcare_spending_fraction=.8, direct_redistribution_fraction=0,
                          pension_budget_fraction=0)
        sim.advance(2)
        self.assertAlmostEqual(sim.history[-1]['Government balance error'], 0)

    def test_old_sessions_are_not_silently_reinterpreted(self):
        sim = Simulation()
        sim.advance(2)
        del sim.policy_budget
        restored = restore_simulation(sim)
        self.assertEqual(restored.config.budget_mode, 'Sequential (legacy)')
        self.assertEqual(restored.step_count, 2)
        restored.update_policy(budget_mode='Total budget')
        restored.advance()
        self.assertEqual(restored.history[-1]['Budget mode'], 'Total budget')
