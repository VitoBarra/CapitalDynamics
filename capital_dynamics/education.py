"""Cash-funded schooling, university and adult retraining with delayed returns."""
from collections import deque
import math
import random

EDUCATION = "Education"
TEACHER = -1  # Firm identifiers are non-negative.
EPS = 1e-9


class EducationSystem:
    def __init__(self, sim):
        self.sim = sim
        self.rng = random.Random(sim.seed + 4)
        self.events = deque(maxlen=1000)
        self.teachers = []
        self.students = []
        self.school = []
        self.training_demand = 0

    def prepare_year(self):
        """Opening provider cash funds teachers before goods-sector recruitment.

        This year's treasury allocation arrives later, so new appropriations
        primarily expand next year's teaching capacity instead of instant skills.
        """
        sim, cfg = self.sim, self.sim.config
        self.school = [p for p in sim.population if 6 <= p.age < 18]
        for p in sim.population:
            p.education_teacher = False
            p.fulltime_student = False
            p.education_track = "School" if 6 <= p.age < 18 else "None"
            if p.age >= cfg.retirement_age:
                p.university_enrolled = False
            if 18 <= p.age < cfg.retirement_age:
                p.skill = max(1, p.skill * (1 - cfg.skill_depreciation))
            eligible = (18 <= p.age < 23 and p.school_years >= 12
                        and not p.university_decided and not p.university_enrolled)
            if eligible and sim.accounts[EDUCATION] > EPS:
                p.university_decided = True
                p.university_enrolled = self.rng.random() < cfg.university_enrollment_fraction
            if p.university_enrolled:
                p.fulltime_student = True
                p.education_track = "University"
        self.students = [p for p in sim.population if p.fulltime_student]
        candidates = [p for p in sim.population if 18 <= p.age < cfg.retirement_age
                      and not p.fulltime_student and p.school_years >= 12]
        self.rng.shuffle(candidates)
        candidates.sort(key=lambda p: p.skill, reverse=True)
        learners = len(self.school) + len(self.students) * 1.5 + self.training_demand
        desired = math.ceil(learners / cfg.students_per_teacher) if learners else 0
        wage = cfg.teacher_salary * cfg.initial_money_per_person * sim.trade_price
        affordable = int((sim.accounts[EDUCATION] + EPS) / wage) if wage > EPS else 0
        self.teachers = candidates[:min(desired, affordable)]
        for person in self.teachers:
            person.education_teacher = True
            person.employer = TEACHER
            paid = sim.transfer(EDUCATION, person.account, wage, "Education salaries")
            person.income += paid
            person.income_received += paid
            sim.flows["Education salaries"] += paid
        sim.flows["Teachers"] = len(self.teachers)
        sim.flows["School students"] = len(self.school)
        sim.flows["University students"] = len(self.students)
        sim.flows["Full-time students"] = len(self.students)

    def deliver(self):
        sim, cfg = self.sim, self.sim.config
        unemployed = [p for p in sim.population if 18 <= p.age < cfg.retirement_age
                      and p.employer is None and not p.fulltime_student]
        trainees = [p for p in unemployed if p.training_progress > 0
                    or self.rng.random() < cfg.retraining_participation]
        self.training_demand = len(trainees)
        for person in trainees:
            person.education_track = "Training"
        # Goods are education inputs consumed this year, not productive capital.
        budget = sim.accounts[EDUCATION] * cfg.education_materials_fraction if self.teachers else 0.0
        sim.nominal_demand += budget
        paid, units = sim.market.buy({EDUCATION: budget}, "Education materials")[EDUCATION]
        sim.flows["Education materials"] = paid
        sim.flows["Real education goods"] = units
        learners = len(self.school) + 1.5 * len(self.students) + len(trainees)
        teaching = min(1, len(self.teachers) * cfg.students_per_teacher / learners) if learners else 0.0
        resources = sim.flows["Education salaries"] + paid
        need = learners * cfg.education_cost_per_student * cfg.initial_money_per_person * sim.trade_price
        funding = min(1, resources / need) if need > EPS else 0.0
        quality = min(teaching, funding)
        sim.flows["Education quality"] = quality if learners else None
        sim.flows["Education funding coverage"] = funding if learners else None
        sim.flows["Education resources per learner"] = resources / learners if learners else None
        sim.flows["Adult trainees"] = len(trainees)
        for p in self.school:
            previous = p.school_years
            p.school_years = min(12, p.school_years + quality)
            self.gain_skill(p, cfg.school_skill_gain * quality)
            p.technology_skill += cfg.technology_adoption_rate * quality * max(0, sim.technology_index - p.technology_skill)
            if previous < 12 <= p.school_years:
                sim.flows["School completions"] += 1
                self.event("Secondary completion", p)
        for p in self.students:
            p.university_progress += quality
            p.university_stalled = p.university_stalled + 1 if quality < .25 else 0
            if p.university_progress + EPS >= cfg.university_duration:
                self.gain_skill(p, cfg.university_skill_gain)
                p.technology_skill = max(p.technology_skill, sim.technology_index)
                p.university_enrolled = False
                p.university_completed = True
                sim.flows["University graduates"] += 1
                self.event("University graduation", p)
            elif p.university_stalled >= 3:
                p.university_enrolled = False
                sim.flows["University dropouts"] += 1
                self.event("University dropout (funding/capacity)", p)
        for p in trainees:
            p.training_progress += quality
            previous = p.school_years
            p.school_years = min(12, p.school_years + quality)
            if previous < 12 <= p.school_years:
                sim.flows["School completions"] += 1
                self.event("Adult secondary completion", p)
            if p.training_progress + EPS >= cfg.retraining_duration:
                p.training_progress = 0.0
                self.gain_skill(p, cfg.retraining_skill_gain)
                p.technology_skill = max(p.technology_skill, sim.technology_index)
                sim.flows["Training completions"] += 1
                self.event("Training completion", p)
        self.learn_from_work()
        # Gains occur after hiring/production; they can help only future output.
        adults = [p for p in sim.population if 18 <= p.age < cfg.retirement_age]
        sim.flows["Mean worker skill"] = sum(p.skill for p in adults) / len(adults) if adults else None
        sim.flows["Mean work experience"] = sum(p.work_experience for p in adults) / len(adults) if adults else None
        sim.flows["Secondary attainment"] = sum(p.school_years >= 12 for p in adults) / len(adults) if adults else None
        sim.flows["University attainment"] = sum(p.university_completed for p in adults) / len(adults) if adults else None

    def worker_multiplier(self, person, firm):
        cfg = self.sim.config
        mismatch = max(0, 1 - person.technology_skill / max(firm.technology, EPS))
        return (1 + cfg.skill_productivity_effect * (person.skill - 1)) * (
            1 - cfg.technology_skill_penalty * mismatch)

    def learn_from_work(self):
        """Completed jobs build general skills and familiarity with used tools."""
        sim, cfg = self.sim, self.sim.config
        for person in sim.population:
            if (person.employer is None or person.fulltime_student
                    or not 18 <= person.age < cfg.retirement_age):
                continue
            person.work_experience += 1
            sim.flows["Work experience added"] += 1
            room = max(0, cfg.skill_ceiling - person.skill)
            gain = cfg.work_skill_gain * room / max(cfg.skill_ceiling - 1, EPS)
            before = person.skill
            self.gain_skill(person, gain)
            sim.flows["Work skill gain"] += person.skill - before
            target = (sim.technology_index if person.employer == TEACHER
                      else sim.market.firms[person.employer].technology)
            person.technology_skill += cfg.work_technology_learning * max(0, target - person.technology_skill)

    def gain_skill(self, person, amount):
        # Lowering a policy ceiling blocks new gains, not confiscates old skills.
        person.skill += min(amount, max(0, self.sim.config.skill_ceiling - person.skill))

    def event(self, kind, person):
        self.events.append({"Year": self.sim.step_count + 1, "Event": kind, "Person": person.person_id})
