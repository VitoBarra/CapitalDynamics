from dataclasses import replace
import unittest

from capital_dynamics.education import EDUCATION, TEACHER
from capital_dynamics.monetary import GOV, PRODUCER, MonetaryConfig, MonetarySimulation


class EducationTests(unittest.TestCase):
    def economy(self, **changes):
        cfg = MonetaryConfig(pop_size=5, initial_money_per_person=10, firm_count=1,
            initial_capacity=100, productivity_growth=0, technology_breakthrough_probability=0,
            research_spending_fraction=0, firm_productivity_dispersion=0,
            birth_prob_max=0, death_base_prob=0, aging_risk_rate=0, tau_max=0,
            healthcare_choice_mode="Public only", delta=0, private_investment_fraction=0,
            ubi_budget_fraction=0, pension_budget_fraction=0, healthcare_spending_fraction=0,
            investment_budget_fraction=0, education_budget_fraction=0,
            university_enrollment_fraction=0, education_materials_fraction=0,
            education_cost_per_student=.05, skill_depreciation=0, retraining_participation=1)
        sim = MonetarySimulation(replace(cfg, **changes))
        for person, age in zip(sim.population, (10, 17, 30, 30, 30)):
            person.age = age
            person.school_years = min(12, max(0, age - 6))
        sim.population[2].skill = 2  # Qualified, preferred teacher candidate.
        return sim

    def fund(self, sim, amount=30):
        sim.transfer(PRODUCER, EDUCATION, amount, "Test education funding")

    def balanced(self, sim):
        self.assertAlmostEqual(sum(row["Net worth"] for row in sim.balance_sheets()), sim.real_asset_value, places=7)
        for name in ("Money balance error", "Base money balance error", "Government balance error",
                     "Government debt balance error", "Inventory balance error"):
            self.assertAlmostEqual(sim.history[-1][name], 0, places=7)
        self.assertTrue(all(x >= -1e-8 for x in sim.accounts.values()))

    def test_education_is_a_real_shared_budget_and_provider_account(self):
        sim = self.economy(education_budget_fraction=1)
        sim.transfer(PRODUCER, GOV, 50, "Treasury funds")
        money = sim.broad_money
        sim.advance()
        self.assertEqual(sim.flows["Teachers"], 0)  # Current appropriation arrives after hiring.
        self.assertEqual(sim.spent["Education"], 50)
        self.assertEqual(sim.accounts[EDUCATION], 50)
        self.assertEqual(sim.population[0].skill, 1)
        sim.advance()
        self.assertGreater(sim.flows["Teachers"], 0)
        self.assertGreater(sim.population[0].skill, 1)
        self.assertAlmostEqual(sim.broad_money, money)
        self.balanced(sim)

    def test_schooling_requires_teachers_and_actual_funding(self):
        sim = self.economy()
        old = sim.population[0].school_years
        sim.advance()
        self.assertEqual(sim.flows["Education quality"], 0)
        self.assertEqual(sim.population[0].school_years, old)
        self.assertEqual(sim.population[0].skill, 1)

    def test_teachers_are_paid_and_cannot_also_work_for_firms(self):
        sim = self.economy()
        self.fund(sim)
        money = sim.broad_money
        sim.advance()
        teacher = sim.population[2]
        self.assertEqual(teacher.employer, TEACHER)
        self.assertTrue(teacher.education_teacher)
        self.assertAlmostEqual(sim.flows["Education salaries"], 5)
        self.assertEqual(teacher.income, 5)
        self.assertEqual(sim.flows["Employed"],
                         sum(p.employer is not None for p in sim.population))
        self.assertEqual(sum(f.employees for f in sim.market.active) + sim.flows["Teachers"], sim.flows["Employed"])
        self.assertAlmostEqual(sim.broad_money, money)
        self.balanced(sim)

    def test_funded_school_progress_and_secondary_completion(self):
        sim = self.economy()
        self.fund(sim)
        sim.advance()
        self.assertEqual(sim.flows["Education quality"], 1)
        self.assertEqual(sim.flows["School completions"], 1)
        self.assertEqual(sim.population[1].school_years, 12)
        self.assertAlmostEqual(sim.population[0].skill, 1.03)
        self.assertTrue(any(e["Event"] == "Secondary completion" for e in sim.education.events))

    def test_university_withdraws_students_from_labor_and_takes_years(self):
        sim = self.economy(university_enrollment_fraction=1, university_duration=3)
        student = sim.population[3]
        student.age = 18
        sim.population[1].university_decided = True  # Keep the other graduate in the labor force.
        self.fund(sim)
        sim.advance(2)
        self.assertTrue(student.fulltime_student)
        self.assertIsNone(student.employer)
        self.assertEqual(sim.flows["Labor force"], 3)  # One former school pupil reached 18.
        self.assertFalse(student.university_completed)
        self.assertEqual(student.skill, 1)
        sim.advance()
        self.assertTrue(student.university_completed)
        self.assertFalse(student.university_enrolled)
        self.assertEqual(sim.flows["University graduates"], 1)
        self.assertAlmostEqual(student.skill, 1.4)
        self.assertTrue(student.fulltime_student)  # Completed-year cohort remains a student.
        sim.advance()
        self.assertFalse(student.fulltime_student)
        self.balanced(sim)

    def test_persistent_underfunding_causes_dropout_not_free_graduation(self):
        sim = self.economy()
        p = sim.population[3]
        p.age = 19
        p.university_enrolled = p.university_decided = True
        sim.advance(3)
        self.assertFalse(p.university_enrolled)
        self.assertFalse(p.university_completed)
        self.assertEqual(p.skill, 1)
        self.assertEqual(sim.flows["University dropouts"], 1)
        self.assertEqual(sim.flows["University graduates"], 0)

    def test_unemployed_retraining_has_a_lag_and_updates_technology_familiarity(self):
        sim = self.economy(initial_demand_fraction=0, consumption_fraction=0,
                           retraining_duration=2, retraining_skill_gain=.2)
        self.fund(sim)
        sim.technology_index = 2
        trainee = sim.population[3]
        sim.advance()
        self.assertEqual(trainee.education_track, "Training")
        self.assertEqual(trainee.skill, 1)
        self.assertEqual(trainee.training_progress, 1)
        self.assertEqual(trainee.technology_skill, 1)
        sim.advance()
        self.assertAlmostEqual(trainee.skill, 1.2)
        self.assertEqual(trainee.technology_skill, 2)
        self.assertEqual(trainee.training_progress, 0)
        self.assertGreater(sim.flows["Training completions"], 0)
        self.assertIsNone(trainee.employer)  # Qualification is not a job guarantee.
        self.balanced(sim)

    def test_training_progress_pauses_during_employment(self):
        sim = self.economy()
        p = sim.population[3]
        p.training_progress = .5
        p.employer = 0
        sim.education.deliver()
        self.assertEqual(p.training_progress, .5)

    def test_materials_are_paid_goods_inputs_not_phantom_capital(self):
        sim = self.economy(education_materials_fraction=.3)
        self.fund(sim)
        sim.goods_remaining = 100
        capital, money = sim.capacity, sim.broad_money
        sim.advance()
        self.assertGreater(sim.flows["Real education goods"], 0)
        self.assertGreater(sim.flows["Education materials"], 0)
        self.assertEqual(sim.capacity, capital)
        self.assertAlmostEqual(sim.broad_money, money)
        self.balanced(sim)

    def test_resources_and_teacher_capacity_jointly_limit_quality(self):
        sim = self.economy(students_per_teacher=1, education_cost_per_student=100)
        self.fund(sim, 5)
        sim.advance()
        self.assertGreater(sim.flows["Teachers"], 0)
        self.assertLess(sim.flows["Education quality"], 1)
        self.assertLess(sim.flows["Education funding coverage"], 1)
        self.assertLess(sim.population[0].school_years, 5)

    def test_skills_change_productivity_wages_and_hiring_order(self):
        sim = self.economy(initial_demand_fraction=.1, inventory_target=0)
        skilled = sim.population[3]
        skilled.skill = 3
        sim.advance()
        self.assertEqual(skilled.employer, 0)
        self.assertGreater(skilled.income, sim.market.firms[0].wage)
        self.assertEqual(sim.market.firms[0].employees, 1)
        self.assertGreater(sim.education.worker_multiplier(skilled, sim.market.firms[0]), 1)
        self.balanced(sim)

    def test_technology_familiarity_reduces_mismatch(self):
        sim = self.economy()
        p, firm = sim.population[3], sim.market.active[0]
        firm.technology = 2
        old = sim.education.worker_multiplier(p, firm)
        p.technology_skill = 2
        self.assertGreater(sim.education.worker_multiplier(p, firm), old)

    def test_skills_are_not_money_or_inherited_financial_assets(self):
        sim = self.economy()
        p = sim.population[3]
        before = sim.net_wealth(p), sim.broad_money, sim.real_asset_value
        sim.education.gain_skill(p, .4)
        self.assertEqual((sim.net_wealth(p), sim.broad_money, sim.real_asset_value), before)
        sim.update_policy(skill_ceiling=1)
        sim.education.gain_skill(p, .4)
        self.assertAlmostEqual(p.skill, 1.4)

    def test_skill_depreciation_has_a_baseline_floor(self):
        sim = self.economy(skill_depreciation=.1)
        p = sim.population[3]
        p.skill = 2
        sim.education.prepare_year()
        self.assertAlmostEqual(p.skill, 1.8)
        self.assertEqual(sim.population[4].skill, 1)

    def test_university_students_cannot_borrow_on_old_employment_income(self):
        sim = self.economy(lending_enabled=True)
        p = sim.population[3]
        p.income_observed, p.last_repayment_income = True, 100
        p.fulltime_student = True
        self.assertEqual(sim.loan_quote(p)[0], 0)

    def test_education_random_stream_is_reproducible_and_separate(self):
        a, b = self.economy(), self.economy()
        for sim in (a, b):
            self.fund(sim)
            sim.advance(4)
        self.assertEqual(list(a.education.events), list(b.education.events))
        self.assertEqual(a.person_rows(), b.person_rows())
        before = a.rng.get_state()[1].copy()
        a.education.rng.random()
        self.assertTrue((before == a.rng.get_state()[1]).all())

    def test_bad_education_settings_are_rejected_atomically(self):
        sim = self.economy()
        old = sim.config
        for change in ({"teacher_salary":0}, {"students_per_teacher":0}, {"university_duration":1.5},
                       {"retraining_duration":0}, {"skill_ceiling":.5}, {"education_materials_fraction":1.1}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                sim.update_policy(**change)
            self.assertEqual(sim.config, old)
