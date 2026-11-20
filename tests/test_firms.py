from dataclasses import replace
import math
import unittest

from capital_dynamics.monetary import GOV, PRODUCER, MonetaryConfig, MonetarySimulation


class FirmMarketTests(unittest.TestCase):
    def economy(self, **changes):
        cfg = MonetaryConfig(pop_size=6, firm_count=2, initial_capacity=20,
            initial_money_per_person=10, initial_producer_money=100,
            firm_productivity_dispersion=0, productivity_growth=0,
            technology_breakthrough_probability=0, research_spending_fraction=0,
            tau_max=0, birth_prob_max=0, death_base_prob=0, aging_risk_rate=0,
            ubi_budget_fraction=0, pension_budget_fraction=0,
            healthcare_spending_fraction=0, investment_budget_fraction=0,
            education_budget_fraction=0, technology_skill_penalty=0,
            private_investment_fraction=0, delta=0, healthcare_choice_mode="Public only",
            policy_rate=0, loan_spread=0)
        sim = MonetarySimulation(replace(cfg, **changes))
        for person in sim.population:
            person.age = 30
        return sim

    def balanced(self, sim):
        self.assertAlmostEqual(sum(r["Net worth"] for r in sim.balance_sheets()), sim.real_asset_value, places=7)
        self.assertTrue(all(math.isfinite(x) and x >= -1e-8 for x in sim.accounts.values()))

    def test_startups_are_funded_by_transfers_not_extra_endowments(self):
        sim = self.economy()
        money, reserves = sim.broad_money, sim.reserves
        sim.advance()
        self.assertAlmostEqual(sim.broad_money, money)
        self.assertEqual(sim.reserves, reserves)
        startup = [x for x in sim.transactions if x["Purpose"] == "Firm startup capital"]
        self.assertAlmostEqual(sum(x["Amount"] for x in startup), 80)
        self.assertEqual(len(startup), 2)
        self.balanced(sim)

    def test_unsold_inventory_reduces_next_production_and_hiring(self):
        sim = self.economy(consumption_fraction=0, inventory_spoilage=0, firm_entry_fraction=0)
        sim.advance()
        first_output, first_employed = sim.output, sim.flows["Employed"]
        stock = sim.goods_remaining
        sim.advance()
        self.assertEqual(sim.flows["Opening inventories"], stock)
        self.assertLess(sim.output, first_output)
        self.assertLess(sim.flows["Employed"], first_employed)
        self.assertAlmostEqual(sim.goods_remaining, stock + sim.output)
        self.balanced(sim)

    def test_inventory_can_be_sold_when_no_new_goods_are_produced(self):
        sim = self.economy(consumption_fraction=0, inventory_spoilage=.1)
        sim.advance()
        stock = sim.goods_remaining
        for p in sim.population:
            p.age = 70
        sim.update_policy(consumption_fraction=1)
        sim.advance()
        self.assertEqual(sim.output, 0)
        self.assertGreater(sim.flows["Real consumption"], 0)
        self.assertAlmostEqual(sim.flows["Inventory spoilage"], stock * .1)
        self.assertAlmostEqual(sim.flows["Inventory balance error"], 0)
        self.assertIsNone(sim.flows["Unemployment rate"])
        self.balanced(sim)

    def test_buyers_prefer_cheaper_goods_and_use_actual_quantities(self):
        sim = self.economy()
        a, b = sim.market.active
        a.price, b.price = 1, 2
        a.inventory = b.inventory = 10
        person = sim.population[0]
        money = sim.broad_money
        paid, units = sim.market.buy({person.account: 3}, "Test purchase")[person.account]
        self.assertAlmostEqual(paid, 3)
        self.assertAlmostEqual(a.sales, 2.4)
        self.assertAlmostEqual(b.sales, .6)
        self.assertAlmostEqual(units, 2.7)
        self.assertNotAlmostEqual(units, paid / sim.price)
        self.assertAlmostEqual(sim.broad_money, money)
        self.balanced(sim)

    def test_stockouts_redirect_budgets_and_buyers_share_rationing(self):
        sim = self.economy()
        a, b = sim.market.active
        a.price, b.price = 1, 2
        a.inventory, b.inventory = 1, 3
        p, q = sim.population[:2]
        purchases = sim.market.buy({p.account: 10, q.account: 10}, "Rationed purchase")
        self.assertEqual(purchases[p.account], purchases[q.account])
        self.assertAlmostEqual(purchases[p.account][0], 3.5)
        self.assertAlmostEqual(purchases[p.account][1], 2)
        self.assertAlmostEqual(sim.goods_remaining, 0)
        self.assertAlmostEqual(a.sales + b.sales, 7)
        self.balanced(sim)

    def test_no_sales_share_composition_inflation(self):
        sim = self.economy(inflation_response=0, firm_markup=0, wage_fraction=0,
                           consumption_fraction=0, inventory_spoilage=0)
        a, b = sim.market.active
        a.price, b.price = .5, 2
        sim.advance()
        self.assertAlmostEqual(sim.inflation, 0)
        a.expected_sales, b.expected_sales = 100, 1
        sim.advance()
        self.assertAlmostEqual(sim.inflation, 0)
        self.assertAlmostEqual(sim.price, 1)

    def test_wage_bargaining_uses_inflation_and_labor_scarcity(self):
        sim = self.economy(wage_inflation_indexation=.5, wage_productivity_share=0,
                           wage_bargaining_strength=.1, target_unemployment=.06)
        sim.market.previous_inflation = .1
        sim.market.previous_unemployment = 0
        old = [f.wage for f in sim.market.active]
        sim.market.begin_year()
        for f, wage in zip(sim.market.active, old):
            self.assertAlmostEqual(f.wage, wage * 1.056)
        self.balanced(sim)

    def test_productivity_can_reduce_labor_required_for_the_same_orders(self):
        a = self.economy(firm_count=1, inventory_target=0, wage_productivity_share=0)
        b = self.economy(firm_count=1, inventory_target=0, wage_productivity_share=0)
        b.market.firms[0].technology = 2
        a.market.begin_year()
        b.market.begin_year()
        self.assertAlmostEqual(a.output, b.output)
        self.assertLess(b.flows["Employed"], a.flows["Employed"])

    def test_jobs_have_distinct_employers_and_retirees_cannot_be_hired(self):
        sim = self.economy()
        sim.population[0].age = 17
        sim.population[1].age = sim.config.retirement_age
        sim.advance()
        employed = [p for p in sim.population if p.employer is not None]
        self.assertTrue(all(18 <= p.age - 1 < sim.config.retirement_age for p in employed))
        self.assertEqual(sim.flows["Labor force"], 4)
        self.assertEqual(sim.flows["Employed"], len(employed))
        self.assertEqual(sim.flows["Unemployed"], 4 - len(employed))
        self.assertAlmostEqual(sim.flows["Unemployment rate"], (4 - len(employed)) / 4)

    def test_paid_research_has_a_real_cash_cost_and_can_create_discoveries(self):
        sim = self.economy(research_spending_fraction=.5, research_effectiveness=100,
                           technology_gain_min=.1, technology_gain_max=.1)
        money = sim.broad_money
        sim.advance()
        paid = sum(t["Amount"] for t in sim.transactions if t["Purpose"] == "Research wages")
        self.assertGreater(paid, 0)
        self.assertAlmostEqual(paid, sim.flows["Research spending"])
        self.assertEqual(sim.technology_breakthroughs, 0)  # One-year research lag.
        sim.advance()
        self.assertEqual(sim.flows["Research breakthroughs"], 2)
        self.assertEqual(sim.technology_breakthroughs, 2)
        self.assertAlmostEqual(sim.technology_index, 1.1 ** 2)
        self.assertAlmostEqual(sim.flows["Productivity growth realized"], .21)
        self.assertEqual(sim.flows["Technology breakthrough event"], 1)
        self.assertAlmostEqual(sim.broad_money, money)
        self.balanced(sim)

    def test_no_research_spending_means_no_research_discoveries(self):
        sim = self.economy(research_effectiveness=100)
        sim.advance(4)
        self.assertEqual(sim.technology_breakthroughs, 0)

    def test_adoption_closes_only_part_of_the_technology_gap(self):
        sim = self.economy(technology_adoption_rate=.2)
        sim.technology_index = 2
        sim.market.innovate()
        for firm in sim.market.active:
            self.assertAlmostEqual(firm.technology, 1.2)
        sim.market.innovate()
        for firm in sim.market.active:
            self.assertAlmostEqual(firm.technology, 1.36)

    def test_research_accelerates_adoption_without_free_breakthroughs(self):
        sim = self.economy(technology_adoption_rate=.1, research_effectiveness=0,
                           research_adoption_effectiveness=1)
        a, b = sim.market.active
        sim.technology_index = 2
        a.last_research, a.last_sales = 1, 2
        sim.market.innovate()
        self.assertGreater(a.technology, b.technology)
        self.assertEqual(sim.technology_breakthroughs, 0)

    def credit_firm(self, sim):
        f = sim.market.active[0]
        f.last_sales, f.last_profit = 100, 50
        return f

    def test_business_credit_creates_deposits_and_matching_bank_assets(self):
        sim = self.economy(business_lending=True)
        f = self.credit_firm(sim)
        money, equity = sim.broad_money, sim.bank_equity
        self.assertEqual(sim.originate_firm_loan(f, 4), 4)
        self.assertEqual(sim.accounts[f.account], 4)
        self.assertEqual(sim.broad_money, money + 4)
        self.assertEqual(sim.bank_equity, equity)
        self.assertEqual(sim.prudential_equity, equity)
        self.balanced(sim)

    def test_business_credit_needs_income_and_bank_capacity(self):
        sim = self.economy(business_lending=True)
        f = sim.market.active[0]
        self.assertEqual(sim.originate_firm_loan(f, 4), 0)
        self.credit_firm(sim)
        sim.update_policy(money_cap_type="Broad money", money_cap=sim.broad_money)
        self.assertEqual(sim.originate_firm_loan(f, 4), 0)
        with self.assertRaises(ValueError):
            sim.originate_firm_loan(f, -1)

    def test_business_repayment_destroys_deposits_without_losing_equity(self):
        sim = self.economy(business_lending=True, firm_loan_term=1)
        f = self.credit_firm(sim)
        money = sim.broad_money
        sim.originate_firm_loan(f, 4)
        sim.step_count = 1
        sim.service_firm_loans()
        self.assertFalse(sim.firm_loans)
        self.assertEqual(sim.broad_money, money)
        self.assertEqual(sim.flows["Business principal repaid"], 4)
        self.assertTrue(f.active)
        self.balanced(sim)

    def test_failure_resolves_multiple_loans_once_and_hits_bank_not_deposits(self):
        sim = self.economy(business_lending=True, firm_loan_term=1)
        f = self.credit_firm(sim)
        sim.originate_firm_loan(f, 2)
        sim.originate_firm_loan(f, 2)
        sim.transfer(f.account, PRODUCER, 4, "Spend loan")
        equity, money = sim.bank_equity, sim.broad_money
        sim.step_count = 1
        sim.service_firm_loans()
        self.assertFalse(sim.firm_loans)
        self.assertFalse(f.active)
        self.assertEqual(sim.flows["Firm failures"], 1)
        self.assertEqual(sim.flows["Business principal losses"], 4)
        self.assertEqual(sim.broad_money, money)
        self.assertEqual(sim.bank_equity, equity - 4)
        self.balanced(sim)

    def test_liquidation_moves_goods_and_scraps_only_the_unsold_remainder(self):
        sim = self.economy()
        a, b = sim.market.active
        a.inventory = 10
        sim.transfer(PRODUCER, b.account, 8, "Rival funding")
        money, capital = sim.broad_money, sim.capacity
        sim.market.fail(a)
        self.assertFalse(a.active)
        self.assertGreater(b.inventory, 0)
        self.assertAlmostEqual(b.inventory + sim.flows["Inventory scrapped"], 10)
        self.assertEqual(sim.accounts[a.account], 0)
        self.assertAlmostEqual(sim.broad_money, money)
        self.assertEqual(sim.capacity, capital)
        self.balanced(sim)

    def test_replacement_entry_is_funded_and_receives_a_new_identifier(self):
        sim = self.economy()
        sim.market.fail(sim.market.active[0])
        money = sim.broad_money
        sim.market.enter(sim.population)
        self.assertEqual(len(sim.market.active), 2)
        self.assertEqual(sim.market.active[-1].firm_id, 2)
        self.assertGreater(sim.accounts[sim.market.active[-1].account], 0)
        self.assertAlmostEqual(sim.broad_money, money)
        self.balanced(sim)

    def test_insufficient_funds_do_not_magically_create_a_replacement(self):
        sim = self.economy(firm_entry_fraction=0)
        sim.market.fail(sim.market.active[0])
        sim.market.enter(sim.population)
        self.assertEqual(len(sim.market.active), 1)

    def test_cash_distressed_loss_making_firms_exit(self):
        sim = self.economy(firm_count=1, firm_failure_years=1, firm_entry_fraction=0)
        f = sim.market.active[0]
        sim.transfer(PRODUCER, f.account, .1, "Small funding")
        f.payroll = 1
        sim.market.close_year()
        self.assertFalse(f.active)
        self.assertEqual(sim.flows["Firm failures"], 1)

    def test_firm_and_inventory_histories_are_reproducible(self):
        a, b = self.economy(), self.economy()
        a.advance(10)
        b.advance(10)
        self.assertEqual(a.market.rows(), b.market.rows())
        self.assertEqual(list(a.history), list(b.history))

    def test_living_standards_use_actual_goods_not_index_deflated_spending(self):
        sim = self.economy()
        a, b = sim.market.active
        a.price, b.price = 1, 2
        a.inventory = b.inventory = 100
        sim.consume()
        row = sim.living_standards()
        self.assertAlmostEqual(row["Real consumption per person"],
                               sim.flows["Real consumption"] / len(sim.population))
        self.assertNotAlmostEqual(row["Real consumption per person"], row["Consumption per person"] / sim.trade_price)

    def test_parameters_and_initial_only_firm_count_are_validated(self):
        for change in ({"firm_count":0}, {"firm_count":1.5}, {"inventory_spoilage":1.1},
                       {"research_spending_fraction":-1}, {"firm_failure_years":0}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.economy(**change)
        with self.assertRaises(ValueError):
            self.economy().update_policy(firm_count=3)
