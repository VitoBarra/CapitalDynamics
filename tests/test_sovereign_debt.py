from dataclasses import fields, replace
import unittest

from capital_dynamics.budget import ALLOCATION_FIELDS
from capital_dynamics.monetary import BANK, GOV, PRODUCER, MonetaryConfig, MonetarySimulation


class SovereignDebtTests(unittest.TestCase):
    def economy(self, **changes):
        config = MonetaryConfig(pop_size=3, initial_money_per_person=20,
            birth_prob_max=0, death_base_prob=0, aging_risk_rate=0,
            sovereign_base_spread=0, sovereign_debt_sensitivity=0,
            sovereign_arrears_sensitivity=0, sovereign_risk_aversion=0,
            healthcare_choice_mode="Public only")
        sim = MonetarySimulation(replace(config, **changes))
        for p in sim.population:
            p.age = 50
            p.last_repayment_income = 100
            p.income_observed = True
        return sim

    def assert_balanced(self, sim):
        self.assertAlmostEqual(sum(row["Net worth"] for row in sim.balance_sheets()),
                               sim.real_asset_value, places=7)
        self.assertTrue(all(value >= -1e-8 for value in sim.accounts.values()))

    def test_debt_service_is_not_a_discretionary_allocation(self):
        self.assertEqual(len(ALLOCATION_FIELDS), 5)
        self.assertNotIn("debt_service_fraction", {field.name for field in fields(MonetaryConfig)})
        self.assertNotIn("principal_first", {field.name for field in fields(MonetaryConfig)})

    def test_mandatory_service_precedes_the_policy_budget(self):
        sim = self.economy(bond_term=1, bond_rate=.1)
        sim.sell_bond(sim.population[0].account, 10)
        sim.transfer(GOV, PRODUCER, 10, "Spend proceeds")
        sim.transfer(PRODUCER, GOV, 100, "Funding")
        sim.step_count = 1
        sim.prepare_budget()
        self.assertEqual(sim.flows["Debt service spent"], 11)
        self.assertEqual(sim.policy_budget, 89)
        self.assertAlmostEqual(sim.budget_allocations["UBI"], 89 * .25)
        sim.pay_policies()
        self.assertFalse(sim.bonds)
        self.assertNotIn("Debt service", sim.spent)
        self.assert_balanced(sim)

    def test_unpaid_mature_principal_and_coupons_carry_without_double_accrual(self):
        sim = self.economy(bond_term=1, bond_rate=.1)
        sim.sell_bond(sim.population[0].account, 10)
        sim.transfer(GOV, PRODUCER, 10, "Spend proceeds")
        sim.step_count = 1
        sim.service_bonds()
        self.assertAlmostEqual(sim.government_debt, 11)
        self.assertAlmostEqual(sim.bonds[0].arrears, 1)
        sim.service_bonds()
        self.assertAlmostEqual(sim.government_debt, 11)
        sim.step_count = 2
        sim.service_bonds()
        self.assertAlmostEqual(sim.government_debt, 12)
        self.assertAlmostEqual(sim.flows["Bond interest accrued"], 2)
        self.assertAlmostEqual(sim.flows["Debt service shortfall"], 12)
        self.assertEqual(sim.flows["Sovereign debt written off"], 0)
        self.assert_balanced(sim)

    def test_coupons_are_paid_pro_rata_and_partial_arrears_survive(self):
        sim = self.economy(bond_rate=.1)
        p, q = sim.population[:2]
        sim.sell_bond(p.account, 5)
        sim.sell_bond(q.account, 5)
        sim.transfer(GOV, PRODUCER, 9.6, "Spend proceeds")
        sim.step_count = 1
        sim.service_bonds()
        self.assertAlmostEqual(sim.flows["Bond interest paid"], .4)
        self.assertAlmostEqual(p.income_received, .2)
        self.assertAlmostEqual(q.income_received, .2)
        self.assertAlmostEqual(sum(b.arrears for b in sim.bonds), .6)
        self.assertAlmostEqual(sim.government_debt, 10.6)
        self.assert_balanced(sim)

    def test_principal_can_be_refinanced_at_the_nominal_ceiling(self):
        sim = self.economy(government_borrowing=True, borrowing_target=0, bond_term=1,
                           bond_rate=0, debt_ceiling=10, bank_bond_fraction=1)
        person = sim.population[0]
        sim.sell_bond(person.account, 10)
        sim.transfer(GOV, PRODUCER, 10, "Spend proceeds")
        sim.reset_flows()
        sim.step_count = 1
        sim.fund_government()
        self.assertAlmostEqual(sim.flows["Borrowing proceeds"], 10)
        self.assertAlmostEqual(sim.flows["Bond principal repaid"], 10)
        self.assertAlmostEqual(sim.flows["Refinanced principal"], 10)
        self.assertAlmostEqual(sim.government_debt, 10)
        self.assertEqual(sim.accounts[GOV], 0)
        self.assertEqual(sim.flows["Debt service shortfall"], 0)
        self.assertTrue(all(b.holder == BANK and b.maturity == 3 for b in sim.bonds))
        self.assert_balanced(sim)

    def test_without_willing_lenders_debt_is_not_erased(self):
        sim = self.economy(government_borrowing=True, borrowing_target=0, bond_term=1,
                           bond_rate=0, bank_bond_fraction=0, bond_purchase_fraction=0)
        sim.sell_bond(sim.population[0].account, 10)
        sim.transfer(GOV, PRODUCER, 10, "Spend proceeds")
        sim.reset_flows()
        sim.step_count = 1
        sim.fund_government()
        self.assertEqual(sim.government_debt, 10)
        self.assertEqual(sim.flows["Borrowing proceeds"], 0)
        self.assertEqual(sim.flows["Debt service shortfall"], 10)
        self.assert_balanced(sim)

    def test_ceiling_does_not_forgive_interest_or_fund_unmatched_spending(self):
        sim = self.economy(government_borrowing=True, borrowing_target=100, bond_term=1,
                           bond_rate=.1, debt_ceiling=10, bank_bond_fraction=1)
        sim.sell_bond(sim.population[0].account, 10)
        sim.transfer(GOV, PRODUCER, 10, "Spend proceeds")
        sim.reset_flows()
        sim.step_count = 1
        sim.fund_government()
        self.assertAlmostEqual(sim.flows["Borrowing proceeds"], 10)
        self.assertAlmostEqual(sim.government_debt, 11)  # Existing obligation, not new policy credit.
        self.assertAlmostEqual(sum(b.arrears for b in sim.bonds), 1)
        self.assertEqual(sim.accounts[GOV], 0)
        self.assertEqual(sim.sell_bond(BANK, 1), 0)
        self.assert_balanced(sim)

    def test_spread_reprices_old_bonds_not_their_fixed_coupons(self):
        sim = self.economy()
        person = sim.population[0]
        sim.sell_bond(person.account, 10)
        sim.sell_bond(BANK, 10)
        coupon = sim.bonds[0].rate
        money, equity = sim.broad_money, sim.bank_equity
        sim.update_policy(sovereign_base_spread=.1)
        self.assertEqual(sim.bonds[0].rate, coupon)
        self.assertLess(sim.bond_assets(person), 10)
        self.assertLess(sim.bank_equity, equity)
        self.assertLess(sim.prudential_equity, equity)
        self.assertEqual(sim.broad_money, money)
        self.assertEqual(sim.government_debt, 20)
        self.assert_balanced(sim)

    def test_premium_prices_cannot_create_distributable_bank_capital(self):
        sim = self.economy(bond_rate=.1, bank_dividend_fraction=1)
        sim.sell_bond(BANK, 10)
        sim.update_policy(bond_rate=.01)
        self.assertGreater(sim.bank_equity, sim.config.initial_bank_capital)
        self.assertAlmostEqual(sim.prudential_equity, sim.config.initial_bank_capital)
        sim.trade_price = sim.price
        sim.distribute_income()
        self.assertEqual(sim.flows["Bank distributions"], 0)
        self.assert_balanced(sim)

    def test_default_cancels_sovereign_claims_not_private_loans_or_deposits(self):
        sim = self.economy(lending_enabled=True, initial_bank_capital=5,
            private_investment_fraction=0, investment_budget_fraction=0, loan_demand=0, consumption_fraction=0, wage_fraction=0,
            producer_dividend_fraction=0, tau_max=0, delta=0, loan_term=100, policy_rate=0, loan_spread=0)
        person = sim.population[0]
        sim.originate_loan(person, .5)
        sim.sell_bond(person.account, 2)
        sim.sell_bond(BANK, 10)
        sim.sell_bond(PRODUCER, 2)
        sim.bonds[0].arrears = 1
        money, base, capacity = sim.broad_money, sim.reserves, sim.capacity
        sim.request_government_default()
        self.assertEqual(sim.sovereign_default_count, 0)
        sim.advance()
        self.assertEqual(sim.government_debt, 0)
        self.assertFalse(sim.bonds)
        self.assertAlmostEqual(sim.debt(person), .5)
        self.assertAlmostEqual(sim.broad_money, money)
        self.assertEqual(sim.reserves, base)
        self.assertEqual(sim.capacity, capacity)
        self.assertEqual(sim.sovereign_default_count, 1)
        self.assertEqual(sim.history[-1]["Sovereign debt written off"], 15)
        self.assertAlmostEqual(sim.bank_equity, -5)
        self.assertFalse(sim.sovereign_market_access)
        self.assertGreater(sim.sovereign_spread(), 0)
        for key in ("Money balance error", "Government balance error", "Government debt balance error"):
            self.assertAlmostEqual(sim.history[-1][key], 0, places=7)
        self.assert_balanced(sim)

    def test_exclusion_expires_but_reputation_penalty_persists(self):
        sim = self.economy(sovereign_reputation_recovery=0, sovereign_exclusion_years=2)
        sim.sell_bond(sim.population[0].account, 1)
        sim.request_government_default()
        sim.advance()
        self.assertEqual(sim.sell_bond(BANK, 1), 0)
        sim.advance(2)
        self.assertFalse(sim.sovereign_market_access)
        sim.advance()
        self.assertTrue(sim.sovereign_market_access)
        self.assertAlmostEqual(sim.sovereign_spread(), sim.config.sovereign_default_penalty)
        self.assertGreater(sim.sell_bond(sim.population[0].account, 1), 0)
        self.assertGreater(sim.bonds[-1].rate, sim.config.bond_rate)

    def test_coupon_claims_survive_inheritance_and_cancel_with_unclaimed_estates(self):
        for has_heir in (True, False):
            sim = self.economy()
            parent, child = sim.population[:2]
            if has_heir:
                child.parent_id = parent.person_id
            sim.sell_bond(parent.account, 1)
            sim.bonds[0].arrears = .2
            sim.settle_estates({parent.person_id})
            if has_heir:
                self.assertAlmostEqual(sim.government_debt, 1.2)
                self.assertAlmostEqual(sum(b.arrears for b in sim.bonds), .2)
                self.assertTrue(all(b.holder == child.account for b in sim.bonds))
            else:
                self.assertEqual(sim.government_debt, 0)
                self.assertAlmostEqual(sim.flows["Estate debt cancellation"], 1.2)
            self.assert_balanced(sim)

    def test_recording_zero_output_does_not_change_prices_after_close(self):
        sim = self.economy(government_borrowing=True, bank_bond_fraction=1, delta=1,
                           sovereign_debt_sensitivity=.02)
        sim.advance(3)
        row = sim.history[-1]
        self.assertEqual(row["Output"], 0)
        self.assertAlmostEqual(row["Government market debt"], sim.government_market_debt)
        self.assertAlmostEqual(row["Prudential bank equity"], sim.prudential_equity)

    def test_default_request_requires_outstanding_claims(self):
        sim = self.economy()
        with self.assertRaises(ValueError):
            sim.request_government_default()
        self.assertFalse(sim.sovereign_default_pending)
