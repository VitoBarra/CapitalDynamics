from dataclasses import replace
import math
import unittest

from monetary import (BANK, GOV, PRODUCER, COMPARISON_NAMES, MonetaryConfig, MonetarySimulation,
                      comparison_config, restore_monetary_simulation)
from types import SimpleNamespace


class MonetaryTests(unittest.TestCase):
    def test_investment_observations_measure_capital_not_destroyed_money(self):
        sim = self.economy(investment_risk=1, failed_investment_loss=.5)
        sim.goods_remaining = 100
        money = sim.broad_money
        assets = sum(p.assets for p in sim.population)
        expected = 3 * sim.config.init_wealth * sim.config.private_investment_fraction * sim.config.base_eff
        sim.invest()
        self.assertEqual(sim.flows['Failed private investments'], 3)
        self.assertAlmostEqual(sim.flows['Private capital added'], expected / 2)
        self.assertAlmostEqual(sim.flows['Private capital shortfall'], expected / 2)
        self.assertAlmostEqual(sum(p.assets for p in sim.population) - assets, expected / 2)
        self.assertAlmostEqual(sim.broad_money, money)
        sim.reset_flows()
        sim.goods_remaining = 0
        sim.invest()
        self.assertEqual(sim.flows['Failed private investments'], 0)
        self.assertEqual(sim.flows['Private capital shortfall'], 0)

    def test_annual_finance_ledger_reconciles_and_includes_year_zero(self):
        sim = self.economy(monetary_financing=True, issuance_per_step=2)
        self.assertEqual(sim.history[0]['Opening government money'], 0)
        self.assertEqual(sim.history[0]['Government balance error'], 0)
        for _ in range(5):
            opening = sim.accounts[GOV]
            sim.advance()
            row = sim.history[-1]
            self.assertEqual(row['Opening government money'], opening)
            self.assertAlmostEqual(row['Total government spending'], sum(sim.spent.values()))
            self.assertAlmostEqual(row['Government money'], opening + row['Tax revenue'] + row['Borrowing proceeds']
                                   + row['Money issued'] + row['Estate revenue'] - row['Total government spending'])
            self.assert_balanced(sim)

    def test_new_tax_defaults_and_existing_session_rates(self):
        self.assertEqual(MonetaryConfig().tau_base, 0)
        self.assertEqual(MonetaryConfig().tau_max, .6)
        previous = self.economy(tau_base=.005, tau_max=.04)
        previous.advance(2)
        old = SimpleNamespace(**previous.__dict__)
        restored = restore_monetary_simulation(old)
        self.assertIs(restored.history, previous.history)
        self.assertIs(restored.rng, previous.rng)
        self.assertIs(restored.population, previous.population)
        self.assertEqual(restored.config.tau_base, .005)
        self.assertEqual(restored.config.tau_max, .04)
        self.assertEqual(restored.step_count, 2)
        restored.advance()
        self.assertEqual(restored.step_count, 3)

    def test_tax_and_health_observations_are_recorded_without_changing_accounts(self):
        sim = self.economy(monetary_financing=True, issuance_per_step=2)
        sim.advance()
        last = sim.history[-1]
        self.assertEqual(last['Public healthcare users'] + last['Private healthcare users'], 3)
        self.assertEqual(last['Observed mortality'], 0)
        self.assertEqual(last['Minimum applied tax rate'], 0)
        self.assertIn('UBI per person', last)
        self.assertIn('Pension eligible', last)
        self.assertAlmostEqual(last['Government balance error'], 0)
        self.assertAlmostEqual(last['Money balance error'], 0)

    def economy(self, **changes):
        config = MonetaryConfig(pop_size=3, birth_prob_max=0, death_base_prob=0, aging_risk_rate=0,
                                healthcare_choice_mode='Public only')
        sim = MonetarySimulation(replace(config, **changes))
        for p in sim.population:
            p.age = 30
        return sim

    def assert_balanced(self, sim):
        self.assertAlmostEqual(sum(x['Net worth'] for x in sim.balance_sheets()), sim.capacity * sim.price, places=7)
        self.assertTrue(all(v >= -1e-8 and math.isfinite(v) for v in sim.accounts.values()))
        for key in ('Money balance error', 'Base money balance error', 'Government balance error'):
            self.assertAlmostEqual(sim.history[-1].get(key, 0), 0, places=7)

    def test_transfers_conserve_money(self):
        sim = self.economy()
        money, reserves = sim.broad_money, sim.reserves
        self.assertEqual(sim.transfer(sim.population[0].account, GOV, .25, 'Test'), .25)
        self.assertEqual(sim.broad_money, money)
        self.assertEqual(sim.reserves, reserves)
        self.assert_balanced(sim)
        with self.assertRaises(ValueError):
            sim.transfer(GOV, PRODUCER, -1, 'Invalid')

    def test_lending_creates_money_and_matching_debt_not_net_wealth(self):
        sim = self.economy(lending_enabled=True)
        person = sim.population[0]
        money, wealth, equity = sim.broad_money, sim.net_wealth(person), sim.bank_equity
        self.assertEqual(sim.originate_loan(person, 2), 2)
        self.assertEqual(sim.broad_money, money + 2)
        self.assertEqual(sim.debt(person), 2)
        self.assertEqual(sim.net_wealth(person), wealth)
        self.assertEqual(sim.bank_equity, equity)
        self.assert_balanced(sim)

    def test_zero_interest_principal_repayment_destroys_money(self):
        sim = self.economy(lending_enabled=True, policy_rate=0, loan_spread=0, loan_term=1)
        person = sim.population[0]
        before = sim.broad_money
        sim.originate_loan(person, 2)
        sim.step_count = 1
        sim.service_loans()
        self.assertFalse(sim.loans)
        self.assertEqual(sim.broad_money, before)
        self.assertEqual(sim.flows['Loan principal repaid'], 2)
        self.assert_balanced(sim)

    def test_interest_payment_increases_bank_equity(self):
        sim = self.economy(lending_enabled=True, policy_rate=.1, loan_spread=0)
        sim.originate_loan(sim.population[0], 2)
        equity = sim.bank_equity
        sim.step_count = 1
        sim.service_loans()
        self.assertAlmostEqual(sim.bank_equity, equity + .2)
        self.assert_balanced(sim)

    def test_default_writes_down_bank_not_other_deposits(self):
        sim = self.economy(lending_enabled=True, default_after=1, policy_rate=0, loan_spread=0)
        person = sim.population[0]
        sim.originate_loan(person, 2)
        sim.transfer(person.account, PRODUCER, sim.accounts[person.account], 'Spend all money')
        money, equity = sim.broad_money, sim.bank_equity
        sim.step_count = 1
        sim.service_loans()
        self.assertFalse(sim.loans)
        self.assertEqual(sim.bank_equity, equity - 2)
        self.assertEqual(sim.broad_money, money)
        self.assertEqual(sim.flows['Loan defaults'], 2)
        self.assert_balanced(sim)

    def test_credit_is_disabled_or_constrained(self):
        sim = self.economy()
        self.assertEqual(sim.originate_loan(sim.population[0], 1), 0)
        sim.update_policy(lending_enabled=True, borrowing_limit=0)
        self.assertEqual(sim.originate_loan(sim.population[0], 1), 0)
        sim.update_policy(borrowing_limit=10, capital_ratio=1)
        self.assertLessEqual(sim.originate_loan(sim.population[0], 100), sim.config.initial_bank_capital)
        zero = self.economy(initial_bank_capital=0, lending_enabled=True)
        self.assertEqual(zero.credit_room(), 0)

    def test_household_bond_purchase_moves_existing_money(self):
        sim = self.economy()
        person = sim.population[0]
        money, wealth = sim.broad_money, sim.net_wealth(person)
        self.assertEqual(sim.sell_bond(person.account, .5), .5)
        self.assertEqual(sim.broad_money, money)
        self.assertEqual(sim.accounts[GOV], .5)
        self.assertEqual(sim.net_wealth(person), wealth)
        self.assert_balanced(sim)

    def test_bank_bond_purchase_creates_matching_treasury_deposit(self):
        sim = self.economy()
        money, equity = sim.broad_money, sim.bank_equity
        self.assertEqual(sim.sell_bond(BANK, 2), 2)
        self.assertEqual(sim.broad_money, money + 2)
        self.assertEqual(sim.bank_equity, equity)
        self.assert_balanced(sim)

    def test_bond_maturity_shortfall_is_explicit_and_pro_rata(self):
        sim = self.economy(bond_term=1, bond_rate=0)
        p, q = sim.population[:2]
        sim.sell_bond(p.account, .5)
        sim.sell_bond(q.account, .5)
        sim.step_count = 1
        sim.service_bonds(.4)
        self.assertFalse(sim.bonds)
        self.assertAlmostEqual(sim.flows['Bond principal repaid'], .4)
        self.assertAlmostEqual(sim.flows['Bond principal defaults'], .6)
        self.assertAlmostEqual(sim.flows['Debt service shortfall'], .6)
        self.assertAlmostEqual(sim.accounts[p.account], sim.accounts[q.account])
        self.assert_balanced(sim)

    def test_debt_ceiling_limits_new_borrowing(self):
        sim = self.economy(debt_ceiling=.5)
        self.assertEqual(sim.sell_bond(BANK, 10), .5)
        self.assertEqual(sim.sell_bond(BANK, 10), 0)

    def test_money_printing_does_not_create_capacity(self):
        sim = self.economy()
        capacity, money, base = sim.capacity, sim.broad_money, sim.reserves
        sim.issue_money(10)
        self.assertEqual(sim.capacity, capacity)
        self.assertEqual(sim.broad_money, money + 10)
        self.assertEqual(sim.reserves, base + 10)
        self.assert_balanced(sim)

    def test_printing_can_raise_prices_without_increasing_output(self):
        settings = dict(direct_redistribution_fraction=1, pension_budget_fraction=0,
            healthcare_spending_fraction=0, investment_budget_fraction=0, debt_service_fraction=0,
            private_investment_fraction=0, delta=0)
        baseline = self.economy(**settings)
        printing = self.economy(**settings, monetary_financing=True, issuance_per_step=50)
        baseline.advance()
        printing.advance()
        self.assertEqual(baseline.output, printing.output)
        self.assertEqual(baseline.capacity, printing.capacity)
        self.assertGreater(printing.price, baseline.price)
        self.assert_balanced(printing)

    def test_insolvency_freezes_new_credit(self):
        sim = self.economy(lending_enabled=True, policy_rate=0, loan_spread=0, default_after=1)
        person, other, _ = sim.population
        sim.originate_loan(person, 20)
        sim.transfer(person.account, PRODUCER, sim.accounts[person.account], 'Unrecoverable expenditure')
        sim.step_count = 1
        sim.service_loans()
        self.assertAlmostEqual(sim.bank_equity, 0)
        self.assertEqual(sim.originate_loan(other, 1), 0)
        self.assert_balanced(sim)

    def test_base_and_broad_caps_have_distinct_meanings(self):
        sim = self.economy(lending_enabled=True)
        sim.update_policy(money_cap_type='Base money', money_cap=sim.reserves)
        self.assertEqual(sim.issue_money(10), 0)
        self.assertGreater(sim.originate_loan(sim.population[0], 1), 0)
        sim.update_policy(money_cap_type='Broad money', money_cap=sim.broad_money)
        self.assertEqual(sim.issue_money(10), 0)
        self.assertEqual(sim.originate_loan(sim.population[1], 1), 0)
        before = sim.config
        with self.assertRaises(ValueError):
            sim.update_policy(money_cap=1)
        self.assertEqual(sim.config, before)

    def test_estates_settle_debt_before_inheritance(self):
        sim = self.economy(lending_enabled=True)
        parent, child, _ = sim.population
        child.parent_id = parent.person_id
        sim.originate_loan(parent, 2)
        sim.transfer(parent.account, PRODUCER, sim.accounts[parent.account], 'No liquid estate')
        before = sim.capacity
        sim.settle_estates({parent.person_id})
        self.assertFalse(sim.loans)
        self.assertNotIn(parent.account, sim.accounts)
        self.assertEqual(sim.capacity, before)
        self.assertGreater(child.assets, sim.config.logistic_capacity / 3)
        self.assert_balanced(sim)

    def test_illiquid_estate_default_and_simultaneous_deaths(self):
        sim = self.economy(lending_enabled=True)
        for p in sim.population:
            sim.originate_loan(p, 1)
            sim.transfer(p.account, GOV, sim.accounts[p.account], 'No household liquidity')
        sim.transfer(PRODUCER, GOV, sim.accounts[PRODUCER], 'No liquidation buyer')
        sim.settle_estates({p.person_id for p in sim.population})
        self.assertEqual(sim.flows['Loan defaults'], 3)
        self.assertFalse(sim.population)
        self.assertFalse(sim.loans)
        self.assert_balanced(sim)

    def test_all_presets_balance_and_respect_caps_over_time(self):
        for name in COMPARISON_NAMES:
            with self.subTest(name=name):
                sim = MonetarySimulation(comparison_config(name))
                for _ in range(30):
                    sim.advance()
                    self.assert_balanced(sim)
                    if sim.config.money_cap:
                        self.assertLessEqual(sim.capped_supply, sim.config.money_cap + 1e-7)

    def test_no_credit_no_printing_conserves_total_money(self):
        sim = self.economy()
        money = sim.broad_money
        sim.advance(20)
        self.assertAlmostEqual(sim.broad_money, money)
        self.assert_balanced(sim)

    def test_resumption_is_deterministic(self):
        config = comparison_config('Expandable credit')
        whole, resumed = MonetarySimulation(config, seed=7), MonetarySimulation(config, seed=7)
        whole.advance(20)
        resumed.advance(7)
        MonetarySimulation(config, seed=100).advance(3)
        resumed.advance(13)
        self.assertEqual(list(whole.history), list(resumed.history))
        self.assertEqual(whole.person_rows(), resumed.person_rows())

    def test_policy_validation_is_atomic_and_contracts_keep_terms(self):
        sim = self.economy(lending_enabled=True)
        sim.originate_loan(sim.population[0], 1)
        original = sim.config
        for changes in ({'healthcare_spending_fraction': .99}, {'policy_rate': float('nan')},
                        {'loan_term': 0}, {'pop_size': 100}, {'lending_enabled': 'yes'}, {'money_cap_type': 'Other'}):
            with self.assertRaises(ValueError):
                sim.update_policy(**changes)
            self.assertEqual(sim.config, original)
        sim.update_policy(policy_rate=.1)
        self.assertEqual(sim.loans[0].rate, original.policy_rate + original.loan_spread)
        self.assertEqual(sim.policy_changes[-1]['Effective step'], 1)

    def test_extinction_and_history_limits(self):
        sim = self.economy(death_base_prob=1)
        sim.advance(10)
        self.assertEqual(sim.step_count, 1)
        self.assertFalse(sim.population)
        self.assert_balanced(sim)
        bounded = MonetarySimulation(history_limit=3)
        bounded.advance(5)
        self.assertEqual([r['Step'] for r in bounded.history], [3, 4, 5])

    def test_pension_indexing_and_unused_allocation(self):
        sim = self.economy(retirement_age=18, pension_per_person=1, index_pensions=True)
        sim.price = 2
        sim.transfer(PRODUCER, GOV, 100, 'Funding')
        sim.prepare_budget()
        sim.pay_policies()
        self.assertEqual(sim.spent['Pensions'], 6)
        self.assertGreater(sim.budget_allocations['Pensions'], sim.spent['Pensions'])
        self.assertAlmostEqual(sim.spent['Healthcare'], sim.policy_budget * sim.config.healthcare_spending_fraction)
