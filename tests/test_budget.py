import unittest

from capital_dynamics.budget import ALLOCATION_FIELDS, POLICIES, allocate, allocation_rows, validate_allocations
from capital_dynamics.monetary import GOV, PRODUCER, MonetaryConfig, MonetarySimulation


class BudgetTests(unittest.TestCase):
    def test_every_share_uses_same_total(self):
        shares = [.25, .2, .3, .15]
        self.assertEqual(allocate(100, shares),
                         {'UBI': 25, 'Pensions': 20, 'Healthcare': 30, 'Public investment': 15})
        rows = allocation_rows(100, shares, {'UBI': 25, 'Pensions': 10})
        self.assertAlmostEqual(sum(row['Allocation (% of total budget)'] for row in rows), 100)
        self.assertEqual(rows[1]['Unused'], 10)
        self.assertAlmostEqual(rows[0]['Actual (% of expenditure)'], 25 / 35 * 100)

    def test_invalid_and_zero_allocations(self):
        for shares in ([1, 1, 0, 0], [-1, 0, 0, 0], [float('nan'), 0, 0, 0], [.2] * 5):
            with self.assertRaises(ValueError):
                validate_allocations(shares)
        self.assertTrue(all(v == 0 for v in allocate(0, [.2] * 4).values()))
        self.assertEqual(allocation_rows(0, [0] * 4, {})[-1]['Allocation (% of total budget)'], 100)
        self.assertEqual(len(ALLOCATION_FIELDS), len(POLICIES))

    def test_unused_pension_envelope_does_not_increase_other_payments(self):
        sim = MonetarySimulation(MonetaryConfig(pop_size=1, retirement_age=18, pension_per_person=1,
            ubi_budget_fraction=.25, pension_budget_fraction=.2,
            healthcare_spending_fraction=.3, investment_budget_fraction=.15))
        sim.population[0].age = 70
        sim.transfer(PRODUCER, GOV, 100, 'Funding')
        sim.prepare_budget()
        sim.pay_policies()
        self.assertEqual(sim.spent['UBI'], 25)
        self.assertEqual(sim.spent['Pensions'], 1)
        self.assertEqual(sim.spent['Healthcare'], 30)
        self.assertEqual(sim.accounts[GOV], 44)

    def test_total_policy_changes_are_atomic(self):
        sim = MonetarySimulation()
        before = sim.config
        with self.assertRaises(ValueError):
            sim.update_policy(healthcare_spending_fraction=.9)
        self.assertEqual(sim.config, before)
        sim.update_policy(healthcare_spending_fraction=.8, ubi_budget_fraction=0,
                          pension_budget_fraction=0, investment_budget_fraction=.15)
        sim.advance(2)
        self.assertAlmostEqual(sim.history[-1]['Government balance error'], 0)
