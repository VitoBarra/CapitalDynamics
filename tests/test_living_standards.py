import unittest

from capital_dynamics.monetary import MonetaryConfig, MonetarySimulation


class LivingStandardsTests(unittest.TestCase):
    def test_personal_income_threshold_consumption_and_pension_cohorts(self):
        sim = MonetarySimulation(MonetaryConfig(pop_size=4))
        sim.trade_price = 2
        for p, age, income, tax, interest, consumption in zip(
            sim.population, [30, 50, 65, 70], [10, 20, 5, 15], [1, 2, 0, 1], [1, 3, 0, 0], [4, 6, 2, 8]
        ):
            p.age, p.income_received, p.tax_paid, p.interest_paid, p.consumption_paid = age, income, tax, interest, consumption
        sim.population[1].income = 20
        sim.population[2].pension_received = 5
        sim.population[3].pension_received = 15
        row = sim.living_standards()
        self.assertEqual(row["Median disposable income"], 11)
        self.assertEqual(row["Median real disposable income"], 5.5)
        self.assertAlmostEqual(row["Low-income threshold"], 6.6)
        self.assertEqual(row["Relative low-income share"], .25)
        self.assertEqual(row["Non-positive income share"], 0)
        self.assertEqual(row["Consumption per person"], 5)
        self.assertEqual(row["Real consumption per person"], 2.5)
        self.assertEqual(row["Pension replacement ratio"], .5)
        self.assertEqual(row["Income observation population"], 4)

    def test_missing_cohorts_and_non_positive_median_are_not_fake_zero_rates(self):
        sim = MonetarySimulation(MonetaryConfig(pop_size=2))
        sim.trade_price = 1
        for p in sim.population:
            p.age = 30
            p.tax_paid = 1
        row = sim.living_standards()
        self.assertEqual(row["Median disposable income"], -1)
        self.assertIsNone(row["Relative low-income share"])
        self.assertIsNone(row["Low-income threshold"])
        self.assertIsNone(row["Pension replacement ratio"])
        self.assertEqual(row["Non-positive income share"], 1)

    def test_annual_income_uses_cash_receipts_not_loan_proceeds_or_principal(self):
        sim = MonetarySimulation(MonetaryConfig(pop_size=3, lending_enabled=True, tau_max=0,
            birth_prob_max=0, death_base_prob=0, aging_risk_rate=0))
        for p in sim.population:
            p.age = 50
        self.assertIsNone(sim.history[0]["Median disposable income"])
        sim.advance(2)
        earned = {"Wages", "UBI", "Pension", "Producer dividends", "Healthcare income",
                  "Bond interest paid", "Bank distribution creates deposits against bank equity"}
        for p in sim.population:
            latest = [t for t in sim.transactions if t["Step"] == sim.step_count]
            receipts = sum(t["Amount"] for t in latest if t["To"] == p.account and t["Purpose"] in earned)
            tax = sum(t["Amount"] for t in latest if t["From"] == p.account and t["Purpose"] == "Net wealth tax")
            interest = sum(t["Amount"] for t in latest if t["From"] == p.account and t["Purpose"] == "Loan interest")
            self.assertAlmostEqual(p.last_disposable_income, receipts - tax - interest)
            self.assertAlmostEqual(p.last_repayment_income,
                                   receipts - tax - p.bank_distribution_received)
            self.assertTrue(p.income_observed)
        self.assertGreater(sim.history[1]["Loans originated"], 0)
        self.assertGreater(sum(p.bank_distribution_received for p in sim.population), 0)
        self.assertEqual(sim.history[-1]["Income observation population"], 3)
        self.assertAlmostEqual(sim.history[-1]["Consumption per person"], sim.flows["Consumption"] / 3)

    def test_income_observations_are_frozen_before_extinction(self):
        sim = MonetarySimulation(MonetaryConfig(pop_size=3, death_base_prob=1))
        sim.advance()
        self.assertEqual(sim.history[-1]["Population"], 0)
        self.assertEqual(sim.history[-1]["Income observation population"], 3)
        self.assertIsNotNone(sim.history[-1]["Median disposable income"])
