from dataclasses import replace
import unittest

from capital_dynamics.education import TEACHER
from capital_dynamics.monetary import MonetaryConfig, MonetarySimulation, Resident


class WorkExperienceTests(unittest.TestCase):
    def economy(self, **changes):
        cfg = MonetaryConfig(pop_size=3, firm_count=1, firm_productivity_dispersion=0,
            birth_prob_max=0, death_base_prob=0, aging_risk_rate=0,
            productivity_growth=0, technology_breakthrough_probability=0,
            research_spending_fraction=0, skill_depreciation=0, education_budget_fraction=0,
            university_enrollment_fraction=0, retraining_participation=0, tau_max=0,
            healthcare_choice_mode="Public only")
        sim = MonetarySimulation(replace(cfg, **changes))
        for p in sim.population:
            p.age = 30
        return sim

    def test_work_accumulates_experience_and_diminishing_skill_gains(self):
        sim = self.economy()
        p = sim.population[0]
        p.employer = 0
        sim.education.learn_from_work()
        first = p.skill - 1
        self.assertEqual(p.work_experience, 1)
        self.assertAlmostEqual(first, .02)
        before = p.skill
        sim.education.learn_from_work()
        self.assertEqual(p.work_experience, 2)
        self.assertGreater(p.skill, before)
        self.assertLess(p.skill - before, first)
        self.assertAlmostEqual(p.skill, 1.0398)

    def test_unemployment_full_time_study_and_retirement_do_not_add_experience(self):
        sim = self.economy()
        a, b, c = sim.population
        a.employer = None
        b.employer, b.fulltime_student = 0, True
        c.employer, c.age = 0, sim.config.retirement_age
        sim.education.learn_from_work()
        self.assertTrue(all(p.work_experience == 0 and p.skill == 1 for p in sim.population))

    def test_experience_pauses_then_resumes_after_unemployment(self):
        sim = self.economy()
        p = sim.population[0]
        p.employer = 0
        sim.education.learn_from_work()
        p.employer = None
        old = p.skill
        sim.education.learn_from_work()
        self.assertEqual(p.work_experience, 1)
        self.assertEqual(p.skill, old)
        p.employer = 0
        sim.education.learn_from_work()
        self.assertEqual(p.work_experience, 2)

    def test_work_learns_used_technology_not_an_unadopted_frontier(self):
        sim = self.economy()
        a, b, _ = sim.population
        a.employer, b.employer = 0, TEACHER
        sim.market.firms[0].technology = 1.5
        sim.technology_index = 3
        sim.education.learn_from_work()
        self.assertAlmostEqual(a.technology_skill, 1.05)
        self.assertAlmostEqual(b.technology_skill, 1.2)
        self.assertEqual(b.work_experience, 1)

    def test_disabled_learning_still_records_actual_years_worked(self):
        sim = self.economy(work_skill_gain=0, work_technology_learning=0)
        p = sim.population[0]
        p.employer = 0
        sim.market.firms[0].technology = 2
        sim.education.learn_from_work()
        self.assertEqual(p.work_experience, 1)
        self.assertEqual(p.skill, 1)
        self.assertEqual(p.technology_skill, 1)

    def test_ceiling_limits_new_learning_without_erasing_existing_skills(self):
        sim = self.economy(skill_ceiling=1)
        p = sim.population[0]
        p.employer, p.skill = 0, 2
        sim.education.learn_from_work()
        self.assertEqual(p.skill, 2)
        self.assertEqual(sim.flows["Work skill gain"], 0)

    def test_learning_is_after_production_and_does_not_create_money(self):
        a, b = self.economy(work_skill_gain=0), self.economy(work_skill_gain=.04)
        before = b.broad_money
        a.advance()
        b.advance()
        self.assertEqual(a.output, b.output)
        self.assertEqual(a.flows["Wages"], b.flows["Wages"])
        self.assertAlmostEqual(a.broad_money, b.broad_money)
        self.assertAlmostEqual(b.broad_money, before)
        employed = [p for p in b.population if p.employer is not None]
        self.assertTrue(employed)
        self.assertTrue(all(p.work_experience == 1 and p.skill > 1 for p in employed))
        self.assertEqual(b.history[-1]["Work experience added"], len(employed))
        self.assertGreater(b.history[-1]["Work skill gain"], 0)
        self.assertAlmostEqual(b.history[-1]["Mean work experience"], len(employed) / 3)
        self.assertAlmostEqual(sum(row["Net worth"] for row in b.balance_sheets()), b.real_asset_value)

    def test_newborns_do_not_inherit_parental_work_experience(self):
        child = Resident(99, 0, 0, parent_id=0)
        self.assertEqual(child.work_experience, 0)
        self.assertEqual(child.skill, 1)

    def test_invalid_learning_settings_are_rejected(self):
        for changes in ({"work_skill_gain":-.01}, {"work_technology_learning":1.1},
                        {"work_skill_gain":float("inf")}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.economy(**changes)
