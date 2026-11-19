from dataclasses import replace
import unittest

from capital_dynamics.monetary import GOV, PRODUCER, MonetaryConfig, MonetarySimulation


class CreditRiskTests(unittest.TestCase):
    def economy(self, **changes):
        config = MonetaryConfig(pop_size=2, initial_capacity=100, lending_enabled=True,
            birth_prob_max=0, death_base_prob=0, aging_risk_rate=0, healthcare_choice_mode="Public only")
        sim = MonetarySimulation(replace(config, **changes))
        for person in sim.population:
            person.age = 30
            person.last_repayment_income = 100
            person.income_observed = True
        return sim

    def assert_consolidated(self, sim):
        self.assertAlmostEqual(sum(row["Net worth"] for row in sim.balance_sheets()), sim.capacity * sim.price)
        self.assertTrue(all(value >= -1e-9 for value in sim.accounts.values()))

    def test_collateral_and_cash_without_repayment_income_do_not_justify_lending(self):
        sim = self.economy()
        person = sim.population[0]
        person.last_repayment_income = 0
        self.assertGreater(sim.borrowing_room(person), 0)
        self.assertGreater(sim.accounts[person.account], 0)
        self.assertEqual(sim.originate_loan(person, 1), 0)
        person.income_observed = False
        person.income = 2
        person.tax_paid = 1
        self.assertEqual(sim.verified_income(person), 1)
        self.assertGreater(sim.originate_loan(person, 1), 0)

    def test_affordability_counts_existing_commitments_and_stresses(self):
        sim = self.economy()
        person = sim.population[0]
        person.last_repayment_income = 1
        capacity = 1 * (1 - sim.config.income_stress_fraction) * sim.config.debt_service_limit
        first = sim.originate_loan(person, 1)
        self.assertEqual(first, 1)
        second = sim.originate_loan(person, 100)
        self.assertGreater(second, 0)
        self.assertLess(second, 1)
        self.assertLessEqual(sim.scheduled_debt_service(person), capacity + 1e-9)
        self.assertEqual(sim.originate_loan(person, 1), 0)

    def test_history_prices_new_risk_without_repricing_existing_contracts(self):
        sim = self.economy()
        p, q = sim.population
        q.default_count = 3
        self.assertGreater(sim.loan_quote(q)[1], sim.loan_quote(p)[1])
        sim.originate_loan(q, 1)
        original_rate = sim.loans[0].rate
        self.assertGreater(sim.loans[0].risk_score, 0)
        sim.update_policy(policy_rate=.1, borrower_risk_spread=.1)
        self.assertEqual(sim.loans[0].rate, original_rate)

    def test_arrears_and_default_cooldown_prevent_fresh_credit(self):
        sim = self.economy()
        person = sim.population[0]
        sim.originate_loan(person, 1)
        sim.loans[0].missed = 1
        self.assertEqual(sim.originate_loan(person, 1), 0)
        sim.loans.clear()
        # Remove the created deposit to keep this fixture's financial stocks aligned.
        sim.bank_payment(person.account, 1, "Test fixture debt cancellation")
        person.last_default_year = 1
        self.assertEqual(sim.originate_loan(person, 1), 0)
        sim.step_count = 4
        self.assertGreater(sim.originate_loan(person, 1), 0)

    def test_discounted_recovery_uses_liquid_buyer_and_preserves_capital(self):
        sim = self.economy(pop_size=1, initial_capacity=4, initial_producer_money=1,
                           loan_term=1, policy_rate=0, loan_spread=0, collateral_recovery_haircut=.5)
        person = sim.population[0]
        self.assertEqual(sim.originate_loan(person, 4), 4)
        sim.transfer(person.account, GOV, sim.accounts[person.account], "Spend all cash")
        before, money, equity = sim.capacity, sim.broad_money, sim.bank_equity
        sim.step_count = 1
        sim.service_loans()
        self.assertFalse(sim.loans)
        self.assertAlmostEqual(sim.flows["Loan recoveries"], 1)
        self.assertAlmostEqual(sim.flows["Loan defaults"], 3)
        self.assertAlmostEqual(sim.flows["Loan principal losses"], 3)
        self.assertAlmostEqual(person.assets, 2)
        self.assertAlmostEqual(sim.producer_assets, 2)
        self.assertAlmostEqual(sim.capacity, before)
        self.assertAlmostEqual(sim.broad_money, money - 1)
        self.assertAlmostEqual(sim.bank_equity, equity - 3)
        self.assertEqual(person.default_count, 1)
        self.assert_consolidated(sim)

    def test_bond_liquidation_transfers_face_value_not_issuer_debt(self):
        sim = self.economy(pop_size=1, initial_capacity=0, initial_money_per_person=10,
                           loan_term=1, policy_rate=0, loan_spread=0, collateral_recovery_haircut=.5)
        person = sim.population[0]
        sim.sell_bond(person.account, 4)
        sim.originate_loan(person, 2)
        sim.transfer(person.account, GOV, sim.accounts[person.account], "Spend all cash")
        debt = sim.government_debt
        sim.step_count = 1
        sim.service_loans()
        self.assertEqual(sim.flows["Loan recoveries"], 2)
        self.assertEqual(sim.flows["Loan defaults"], 0)
        self.assertEqual(sim.government_debt, debt)
        self.assertAlmostEqual(sum(b.principal for b in sim.bonds if b.holder == PRODUCER), 4)
        self.assert_consolidated(sim)

    def test_unpaid_interest_is_not_distributable_or_lending_capital(self):
        sim = self.economy(initial_bank_capital=1, capital_ratio=.1, policy_rate=.1, loan_spread=0,
                           bank_dividend_fraction=1, default_after=10)
        person = sim.population[0]
        self.assertEqual(sim.originate_loan(person, 10), 10)
        sim.transfer(person.account, GOV, sim.accounts[person.account], "Spend all cash")
        sim.step_count = 1
        sim.service_loans()
        self.assertAlmostEqual(sim.unpaid_interest, 1)
        self.assertAlmostEqual(sim.bank_equity, 2)
        self.assertAlmostEqual(sim.prudential_equity, 1)
        self.assertEqual(sim.credit_room(), 0)
        sim.trade_price = sim.price
        sim.distribute_income()
        self.assertEqual(sim.flows["Bank distributions"], 0)
        self.assert_consolidated(sim)

    def test_new_credit_policy_validation_is_atomic(self):
        sim = self.economy()
        before = sim.config
        for changes in ({"debt_service_limit": 1.1}, {"income_stress_fraction": -1},
                        {"collateral_recovery_haircut": 1.1}, {"default_cooldown": 1.5},
                        {"borrower_risk_spread": float("nan")}):
            with self.assertRaises(ValueError):
                sim.update_policy(**changes)
            self.assertEqual(sim.config, before)
