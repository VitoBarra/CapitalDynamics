"""A small stock-flow-consistent euro-denominated monetary economy.

One commercial bank, a fiat issuer, competing goods firms and healthcare.
All non-bank money is held as deposits (including the treasury). Base money is
bank reserves; broad money is ALL non-bank deposits, including the treasury.
There is no physical cash, FX, deposit insurance, or automatic bank bailout.
"""
from collections import deque
from dataclasses import asdict, dataclass, fields, replace
import math
import random
from typing import Any

import numpy as np

from capital_dynamics.budget import ALLOCATION_FIELDS, allocate, validate_allocations
from capital_dynamics.calibration import RELATIVE_LOW_INCOME_FRACTION
from capital_dynamics.economics import age_dependent_birth_prob, gini_coefficient, mortality_probability, wealth_tax_rates
from capital_dynamics.firms import FirmLoan, FirmMarket
from capital_dynamics.education import EDUCATION, EducationSystem
from capital_dynamics.energy import ENERGY, EnergySystem

EPS = 1e-9
GOV, PRODUCER, HEALTH, BANK = "Government", "Production", "Healthcare", "Bank"


@dataclass(frozen=True)
class MonetaryConfig:
    # Monetary amounts are euros; capital and goods have separate real units.
    pop_size: int = 100
    initial_money_per_person: float = 1.0
    initial_capacity: float = 200.0
    tau_base: float = 0.0
    tau_max: float = 0.6
    tau_gamma: float = 2.0
    ubi_budget_fraction: float = 0.25
    pension_budget_fraction: float = 0.2
    healthcare_spending_fraction: float = 0.25
    investment_budget_fraction: float = 0.15
    education_budget_fraction: float = 0.10
    teacher_salary: float = 0.5
    students_per_teacher: float = 15.0
    education_cost_per_student: float = 0.1
    education_materials_fraction: float = 0.3
    school_skill_gain: float = 0.03
    university_enrollment_fraction: float = 0.3
    university_duration: int = 3
    university_skill_gain: float = 0.4
    retraining_participation: float = 0.3
    retraining_duration: int = 2
    retraining_skill_gain: float = 0.15
    skill_depreciation: float = 0.005
    work_skill_gain: float = 0.02
    work_technology_learning: float = 0.10
    skill_ceiling: float = 3.0
    skill_productivity_effect: float = 0.5
    skill_wage_premium: float = 0.4
    technology_skill_penalty: float = 0.2
    energy_supply: float = 30.0
    energy_supply_growth: float = 0.0
    energy_intensity: float = 0.25
    energy_base_price: float = 0.2
    energy_scarcity_response: float = 2.0
    energy_income_fraction: float = 0.8
    energy_shock_probability: float = 0.05
    energy_shock_severity: float = 0.5
    energy_shock_duration: int = 2
    retirement_age: int = 65
    pension_per_person: float = 0.02
    delta: float = 0.0005
    base_eff: float = 0.3
    investment_risk: float = 0.15
    failed_investment_loss: float = 0.1
    birth_prob_max: float = 0.03
    death_base_prob: float = 0.0002
    aging_risk_start: int = 50
    aging_risk_rate: float = 0.003
    mortality_doubling_years: float = 7.0
    healthcare_effectiveness: float = 10.0
    healthcare_response_rate: float = 0.1
    mortality_floor_fraction: float = 0.2
    healthcare_choice_mode: str = "Adaptive"
    private_healthcare_premium: float = 0.008
    private_healthcare_age_loading: float = 1.0
    private_healthcare_mortality_factor: float = 0.5
    private_healthcare_max_wealth_fraction: float = 0.2
    healthcare_choice_priority: float = 4.0
    initial_producer_money: float = 100.0
    initial_bank_capital: float = 20.0
    productivity: float = 2.0
    productivity_growth: float = 0.01
    technology_breakthrough_probability: float = 0.05
    technology_gain_min: float = 0.02
    technology_gain_max: float = 0.10
    firm_count: int = 5
    firm_productivity_dispersion: float = 0.15
    initial_demand_fraction: float = 0.65
    demand_adaptation: float = 0.4
    inventory_target: float = 0.15
    inventory_spoilage: float = 0.1
    price_competition: float = 2.0
    firm_markup: float = 0.1
    wage_inflation_indexation: float = 0.5
    wage_productivity_share: float = 0.5
    wage_bargaining_strength: float = 0.1
    target_unemployment: float = 0.06
    research_spending_fraction: float = 0.03
    research_effectiveness: float = 2.0
    technology_adoption_rate: float = 0.2
    research_adoption_effectiveness: float = 2.0
    firm_entry_fraction: float = 0.02
    firm_failure_years: int = 3
    business_lending: bool = False
    firm_credit_limit: float = 0.5
    firm_loan_term: int = 3
    consumption_fraction: float = 0.35
    wage_fraction: float = 0.5
    producer_dividend_fraction: float = 0.3
    private_investment_fraction: float = 0.05
    inflation_response: float = 0.1
    policy_rate: float = 0.02
    loan_spread: float = 0.03
    lending_enabled: bool = False
    loan_term: int = 10
    loan_demand: float = 0.1
    borrowing_limit: float = 1.0
    debt_service_limit: float = 0.35
    income_stress_fraction: float = 0.2
    loan_rate_stress: float = 0.02
    borrower_risk_spread: float = 0.03
    collateral_recovery_haircut: float = 0.25
    default_cooldown: int = 3
    capital_ratio: float = 0.1
    reserve_ratio: float = 0.1
    default_after: int = 3
    bank_dividend_fraction: float = 0.25
    government_borrowing: bool = False
    borrowing_target: float = 2.0
    debt_ceiling: float = 100.0
    bond_rate: float = 0.03
    bond_term: int = 10
    bond_purchase_fraction: float = 0.05
    bank_bond_fraction: float = 0.25
    sovereign_base_spread: float = 0.005
    sovereign_debt_sensitivity: float = 0.02
    sovereign_arrears_sensitivity: float = 0.1
    sovereign_default_penalty: float = 0.08
    sovereign_reputation_recovery: float = 0.1
    sovereign_risk_aversion: float = 5.0
    sovereign_exclusion_years: int = 3
    monetary_financing: bool = False
    issuance_per_step: float = 0.0
    money_cap: float = 0.0  # Zero means disabled, not a zero-money economy.
    money_cap_type: str = "Base money"
    index_pensions: bool = False


@dataclass
class Resident:
    person_id: int
    age: int
    assets: float
    parent_id: int | None = None
    healthcare_preference: float = 1.0
    healthcare_choice: str = "Public"
    healthcare_premium: float = 0.0
    ubi_received: float = 0.0
    pension_received: float = 0.0
    income: float = 0.0
    income_received: float = 0.0
    tax_paid: float = 0.0
    interest_paid: float = 0.0
    consumption_paid: float = 0.0
    consumption_units: float = 0.0
    last_disposable_income: float = 0.0
    last_repayment_income: float = 0.0
    bank_distribution_received: float = 0.0
    income_observed: bool = False
    default_count: int = 0
    last_default_year: int | None = None
    employer: int | None = None
    skill: float = 1.0
    work_experience: int = 0
    technology_skill: float = 1.0
    school_years: float = 0.0
    university_progress: float = 0.0
    university_enrolled: bool = False
    university_decided: bool = False
    university_completed: bool = False
    university_stalled: int = 0
    training_progress: float = 0.0
    education_teacher: bool = False
    fulltime_student: bool = False
    education_track: str = "None"

    @property
    def account(self):
        return f"Person {self.person_id}"


@dataclass
class Loan:
    borrower: int
    principal: float
    installment: float
    rate: float
    issued: int
    maturity: int
    missed: int = 0
    arrears: float = 0.0
    risk_score: float = 0.0


@dataclass
class Bond:
    holder: str
    principal: float
    rate: float
    issued: int
    maturity: int
    arrears: float = 0.0
    last_coupon_year: int = 0


def validate_config(config):
    defaults = MonetaryConfig()
    initial = {"pop_size", "loan_term", "bond_term", "default_after", "retirement_age", "aging_risk_start",
               "default_cooldown", "sovereign_exclusion_years", "firm_count", "firm_failure_years", "firm_loan_term",
               "university_duration", "retraining_duration", "energy_shock_duration"}
    fractions = {"consumption_fraction", "wage_fraction", "producer_dividend_fraction", "private_investment_fraction",
                 "inflation_response", "loan_demand", "capital_ratio", "reserve_ratio", "bank_dividend_fraction",
                 "bond_purchase_fraction", "bank_bond_fraction", "delta", "investment_risk",
                 "failed_investment_loss", "death_base_prob", "birth_prob_max", "healthcare_response_rate",
                 "mortality_floor_fraction", "private_healthcare_mortality_factor", "private_healthcare_max_wealth_fraction",
                 "tau_base", "tau_max", "debt_service_limit", "income_stress_fraction", "collateral_recovery_haircut",
                 "sovereign_reputation_recovery", "productivity_growth",
                 "technology_breakthrough_probability", "technology_gain_min", "technology_gain_max",
                 "firm_productivity_dispersion", "initial_demand_fraction", "demand_adaptation",
                 "inventory_target", "inventory_spoilage", "wage_inflation_indexation", "wage_productivity_share",
                 "wage_bargaining_strength", "target_unemployment", "research_spending_fraction",
                 "technology_adoption_rate", "firm_entry_fraction", "education_materials_fraction",
                 "school_skill_gain", "university_enrollment_fraction", "retraining_participation",
                 "skill_depreciation", "technology_skill_penalty", "work_technology_learning",
                 "energy_supply_growth", "energy_income_fraction", "energy_shock_probability", "energy_shock_severity"}
    for name, value in asdict(config).items():
        expected = getattr(defaults, name)
        if isinstance(expected, bool) and not isinstance(value, bool):
            raise ValueError(f"{name} must be true or false.")
        if not isinstance(expected, (bool, str)) and isinstance(value, (bool, str)):
            raise ValueError(f"{name} must be numeric.")
        if isinstance(value, (str, bool)):
            continue
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be a finite non-negative number.")
        if name in fractions and value > 1:
            raise ValueError(f"{name} must be between zero and one.")
        if name in initial and (not isinstance(value, int) or isinstance(value, bool)):
            raise ValueError(f"{name} must be a whole number.")
    for name in ("pop_size", "loan_term", "bond_term", "default_after", "initial_money_per_person", "mortality_doubling_years", "tau_gamma",
                 "firm_count", "firm_failure_years", "firm_loan_term", "university_duration", "retraining_duration",
                 "teacher_salary", "students_per_teacher", "education_cost_per_student", "energy_base_price", "energy_shock_duration"):
        if getattr(config, name) <= 0:
            raise ValueError(f"{name} must be positive.")
    if config.tau_base > config.tau_max:
        raise ValueError("The maximum tax rate must be at least the minimum tax rate.")
    if config.technology_gain_min > config.technology_gain_max:
        raise ValueError("The maximum technology gain must be at least the minimum gain.")
    if config.skill_ceiling < 1:
        raise ValueError("The skill ceiling must be at least the baseline skill of one.")
    if config.money_cap_type not in {"Base money", "Broad money"}:
        raise ValueError("Choose a valid money-cap regime.")
    if config.healthcare_choice_mode not in {"Adaptive", "Public only", "Private if affordable"}:
        raise ValueError("Choose a valid healthcare strategy.")
    validate_allocations([getattr(config, name) for name in ALLOCATION_FIELDS])


class MonetarySimulation:
    def __init__(self, config=None, seed=42, history_limit=10000):
        self.config = config or MonetaryConfig()
        validate_config(self.config)
        self.initial_config = self.config
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        # Technology has its own stream: enabling innovations must not shift
        # mortality, birth or investment-failure random draws.
        self.technology_rng = random.Random(seed + 2)
        self.technology_index = 1.0
        self.technology_breakthroughs = 0
        self.technology_events = deque(maxlen=history_limit)
        ages, preferences = random.Random(seed), random.Random(seed + 1)
        self.population = [Resident(i, ages.randint(1, 50), self.config.initial_capacity / self.config.pop_size,
                                    healthcare_preference=preferences.uniform(0.5, 1.5))
                           for i in range(self.config.pop_size)]
        for person in self.population:
            # Synthetic pre-simulation schooling, independent of wealth.
            person.school_years = min(12, max(0, person.age - 6))
        self.accounts = {p.account: self.config.initial_money_per_person for p in self.population}
        self.accounts.update({GOV: 0.0, PRODUCER: self.config.initial_producer_money, HEALTH: 0.0, EDUCATION: 0.0, ENERGY: 0.0})
        self.reserves = self.broad_money + self.config.initial_bank_capital
        if self.config.money_cap and self.capped_supply > self.config.money_cap + EPS:
            raise ValueError("Money cap is below starting supply. Increase the cap or lower initial money.")
        self.next_id = self.config.pop_size
        self.price = 1.0
        self.trade_price = 1.0
        self.reference_nominal_output = min(
            self.config.initial_capacity,
            sum(18 <= p.age < self.config.retirement_age for p in self.population) * self.effective_productivity)
        self.public_assets = 0.0
        self.producer_assets = 0.0
        self.loans: list[Loan] = []
        self.firm_loans: list[FirmLoan] = []
        self.bonds: list[Bond] = []
        self.step_count = 0
        self._in_step = False
        self.sovereign_default_pending = False
        self.sovereign_default_count = 0
        self.last_sovereign_default_year = None
        self.reputation_spread = 0.0
        self.sovereign_events = deque(maxlen=1000)
        self.mortality_multiplier = 1.0
        self.policy_changes = deque(maxlen=1000)
        self.transactions = deque(maxlen=10000)
        self.history = deque(maxlen=history_limit)
        self.market = FirmMarket(self)
        self.education = EducationSystem(self)
        self.energy = EnergySystem(self)
        self.reset_flows()
        self.flows.update(self.mortality_observations())
        self.flows["Observed mortality"] = None  # No exposure interval at year zero.
        self.flows.update(self.living_standards(observed=False))
        self.flows["Unemployment rate"] = self.flows["Average wage"] = None
        for key in ("Education quality", "Education funding coverage", "Education resources per learner",
                    "Mean worker skill", "Secondary attainment", "University attainment",
                    "Energy coverage", "Energy utilization"):
            self.flows[key] = None
        self.record()

    @property
    def broad_money(self):
        return sum(self.accounts.values())

    @property
    def effective_productivity(self):
        """Technology frontier; adopted firm productivity is reported separately."""
        return self.config.productivity * self.technology_index

    @property
    def goods_remaining(self):
        return self.market.inventory

    @goods_remaining.setter
    def goods_remaining(self, units):
        """Set a common opening stock, shared evenly among operating firms."""
        active = self.market.active
        for f in active:
            f.inventory = max(0, units) / len(active)

    @property
    def real_asset_value(self):
        return self.capacity * self.price + self.market.inventory_value

    @property
    def bank_loans(self):
        return [*self.loans, *self.firm_loans]

    def advance_technology(self):
        """Economy-wide gradual learning plus occasional permanent innovations."""
        opening_index = self.technology_index
        gain = 0.0
        if (self.config.technology_breakthrough_probability > 0
                and self.technology_rng.random() < self.config.technology_breakthrough_probability):
            gain = self.technology_rng.uniform(self.config.technology_gain_min, self.config.technology_gain_max)
            self.technology_breakthroughs += 1
            self.technology_events.append({"Year": self.step_count + 1, "Source": "Frontier",
                                           "Technology productivity gain": gain})
            self.flows["Technology breakthrough event"] = 1
        factor = (1 + self.config.productivity_growth) * (1 + gain)
        self.technology_index *= factor
        self.flows["Technology productivity gain"] = gain
        self.flows["Productivity growth realized"] = factor - 1
        self.market.innovate()
        self.flows["Productivity growth realized"] = self.technology_index / opening_index - 1
        if self.flows["Research breakthroughs"]:
            self.flows["Technology breakthrough event"] = 1

    @property
    def capped_supply(self):
        return self.reserves if self.config.money_cap_type == "Base money" else self.broad_money

    @property
    def bank_equity(self):
        required_yield = self.config.bond_rate + self.sovereign_spread()
        return self.reserves + sum(x.principal + x.arrears for x in self.bank_loans) + sum(
            sum(self.bond_values(x, required_yield=required_yield)) for x in self.bonds if x.holder == BANK) - self.broad_money

    @property
    def unpaid_interest(self):
        return sum(loan.arrears for loan in self.bank_loans)

    @property
    def prudential_equity(self):
        """Exclude uncollected interest and unrealized gains; retain bond losses."""
        required_yield = self.config.bond_rate + self.sovereign_spread()
        return (self.reserves + sum(loan.principal for loan in self.bank_loans)
                + sum(min(b.principal, self.bond_values(b, required_yield=required_yield)[0])
                      for b in self.bonds if b.holder == BANK)
                - self.broad_money)

    @property
    def bank_bond_valuation_reserve(self):
        required_yield = self.config.bond_rate + self.sovereign_spread()
        return sum(max(0, b.principal - self.bond_values(b, required_yield=required_yield)[0])
                   for b in self.bonds if b.holder == BANK)

    @property
    def current_year(self):
        return self.step_count + int(self._in_step)

    @property
    def government_debt(self):
        """Contractual principal plus accrued unpaid interest, not market value."""
        return sum(x.principal + x.arrears for x in self.bonds)

    @property
    def government_arrears(self):
        return self.bond_obligations(self.current_year)

    @property
    def government_market_debt(self):
        required_yield = self.config.bond_rate + self.sovereign_spread()
        return sum(sum(self.bond_values(b, required_yield=required_yield)) for b in self.bonds)

    @property
    def sovereign_market_access(self):
        return (self.last_sovereign_default_year is None
                or self.current_year - self.last_sovereign_default_year > self.config.sovereign_exclusion_years)

    def sovereign_spread(self, additional_debt=0.0):
        """Illustrative risk premium (capped at 50 percentage points), not a PD."""
        # Explicit state, not history[-1]: appending a zero-output observation
        # must not itself change bond prices after the accounts were closed.
        nominal_output = self.reference_nominal_output
        debt = self.government_debt + additional_debt
        ratio = min(10, debt / max(nominal_output, EPS))
        arrears_share = self.government_arrears / debt if debt > EPS else 0.0
        return min(.5, self.config.sovereign_base_spread + self.config.sovereign_debt_sensitivity * ratio
                   + self.config.sovereign_arrears_sensitivity * arrears_share + self.reputation_spread)

    def bond_values(self, bond, *, required_yield=None):
        """PV of remaining principal/coupons and separately carried coupon arrears."""
        rate = self.config.bond_rate + self.sovereign_spread() if required_yield is None else required_yield
        years = max(1, bond.maturity - max(self.current_year, bond.issued))
        discount = math.exp(-years * math.log1p(rate))
        if abs(bond.rate - rate) < 1e-12:
            principal_value = bond.principal
        elif rate > 0:
            principal_value = bond.principal * (bond.rate * (1 - discount) / rate + discount)
        else:
            principal_value = bond.principal * (1 + bond.rate * years)
        return principal_value, bond.arrears / (1 + rate)

    def bond_market_value(self, bond):
        return sum(self.bond_values(bond))

    def bond_obligations(self, year):
        return sum(b.arrears + (b.principal if b.maturity <= year else 0) for b in self.bonds)

    @property
    def capacity(self):
        return self.public_assets + self.producer_assets + sum(p.assets for p in self.population)

    @property
    def shares(self):
        return [getattr(self.config, name) for name in ALLOCATION_FIELDS]

    def debt(self, person):
        return sum(x.principal + x.arrears for x in self.loans if x.borrower == person.person_id)

    def bond_assets(self, person):
        required_yield = self.config.bond_rate + self.sovereign_spread()
        return sum(sum(self.bond_values(x, required_yield=required_yield))
                   for x in self.bonds if x.holder == person.account)

    def net_wealth(self, person):
        return self.accounts[person.account] + person.assets * self.price + self.bond_assets(person) - self.debt(person)

    def borrowing_room(self, person):
        """The same collateral rule applies to demand and actual origination."""
        collateral = max(0, person.assets * self.price + self.bond_assets(person))
        return max(0, collateral * self.config.borrowing_limit - self.debt(person))

    def verified_income(self, person):
        # At startup only wages already paid are observable; deposits, loans
        # and hoped-for returns are never treated as recurring income.
        return max(0, person.last_repayment_income if person.income_observed
                   else person.income - person.tax_paid)

    def scheduled_debt_service(self, person):
        next_year = self.step_count + 2
        return sum((loan.principal if loan.maturity <= next_year else min(loan.installment, loan.principal))
                   + loan.arrears + loan.principal * (loan.rate + self.config.loan_rate_stress)
                   for loan in self.loans if loan.borrower == person.person_id)

    def borrower_risk(self, person):
        """Transparent bounded heuristic, not a fitted probability of default."""
        collateral_limit = self.borrowing_room(person) + self.debt(person)
        leverage = self.debt(person) / collateral_limit if collateral_limit else 0.0
        income = self.verified_income(person)
        capacity = income * (1 - self.config.income_stress_fraction) * self.config.debt_service_limit
        commitments = self.scheduled_debt_service(person)
        burden = min(1, commitments / capacity) if capacity else float(commitments > 0)
        history = min(1, person.default_count / 3)
        return min(1.0, .5 * leverage + .3 * burden + .2 * history)

    def loan_quote(self, person):
        """Common income, collateral and rate quote used by demand and issuance."""
        score = self.borrower_risk(person)
        rate = self.config.policy_rate + self.config.loan_spread + self.config.borrower_risk_spread * score
        troubled = any(loan.missed or loan.arrears > EPS for loan in self.loans if loan.borrower == person.person_id)
        excluded = (person.last_default_year is not None
                    and self.step_count + 1 - person.last_default_year <= self.config.default_cooldown)
        eligible = (self.config.lending_enabled and 18 <= person.age < self.config.retirement_age
                    and not person.fulltime_student)
        capacity = max(0, self.verified_income(person) * (1 - self.config.income_stress_fraction)
                       * self.config.debt_service_limit - self.scheduled_debt_service(person))
        affordable = capacity / (1 / self.config.loan_term + rate + self.config.loan_rate_stress)
        room = min(self.borrowing_room(person), affordable) if eligible and not troubled and not excluded else 0.0
        return room, rate, score

    def log(self, payer, payee, amount, purpose):
        if amount > EPS:
            self.transactions.append({"Step": self.step_count + 1, "From": payer, "To": payee,
                                      "Amount": float(amount), "Purpose": purpose})

    def transfer(self, payer, payee, amount, purpose):
        if not math.isfinite(amount) or amount < -EPS:
            raise ValueError("Transfers must be finite and non-negative.")
        paid = min(max(amount, 0), self.accounts[payer])
        self.accounts[payer] -= paid
        self.accounts[payee] += paid
        self.log(payer, payee, paid, purpose)
        return paid

    def money_room(self):
        if not self.config.money_cap:
            return math.inf
        return max(0, self.config.money_cap - self.capped_supply)

    def credit_room(self):
        """All loans and bank-held bonds carry 100% risk weight in this model."""
        if self.prudential_equity <= EPS:
            return 0.0
        risk_assets = sum(x.principal + x.arrears for x in self.bank_loans) + sum(
            x.principal for x in self.bonds if x.holder == BANK)
        capital = self.prudential_equity / self.config.capital_ratio - risk_assets if self.config.capital_ratio else math.inf
        liquidity = self.reserves / self.config.reserve_ratio - self.broad_money if self.config.reserve_ratio else math.inf
        cap = self.money_room() if self.config.money_cap_type == "Broad money" else math.inf
        return max(0, min(capital, liquidity, cap))

    def issue_money(self, amount):
        if not math.isfinite(amount) or amount < 0:
            raise ValueError("Issuance must be finite and non-negative.")
        issued = min(amount, self.money_room())
        self.reserves += issued
        self.accounts[GOV] += issued
        self.flows["Money issued"] += issued
        self.log("Monetary authority", GOV, issued, "Fiat grant (not tax or bond revenue)")
        return issued

    def originate_loan(self, person, requested):
        if not math.isfinite(requested) or requested < 0:
            raise ValueError("Loan requests must be finite and non-negative.")
        room, rate, score = self.loan_quote(person)
        amount = min(requested, room, self.credit_room())
        if amount <= EPS:
            return 0.0
        term = self.config.loan_term
        self.accounts[person.account] += amount
        self.loans.append(Loan(person.person_id, amount, amount / term,
                               rate, self.step_count + 1, self.step_count + 1 + term, risk_score=score))
        self.flows["Loans originated"] += amount
        self.log(BANK, person.account, amount, "Loan creates deposit and matching debt")
        return amount

    def bank_payment(self, account, amount, purpose):
        paid = min(self.accounts[account], max(0, amount))
        self.accounts[account] -= paid
        self.log(account, BANK, paid, purpose)
        return paid

    def originate_firm_loan(self, firm, requested):
        """Working capital needs past sales and positive operating margin."""
        if not math.isfinite(requested) or requested < 0:
            raise ValueError("Business loan requests must be finite and non-negative.")
        loans = [x for x in self.firm_loans if x.borrower == firm.firm_id]
        if (not self.config.business_lending or not firm.active or firm.last_profit <= 0
                or any(x.missed or x.arrears > EPS for x in loans)):
            return 0.0
        outstanding = sum(x.principal + x.arrears for x in loans)
        room = max(0, firm.last_sales * self.config.firm_credit_limit - outstanding)
        rate = self.config.policy_rate + self.config.loan_spread
        affordable = firm.last_profit * (1 - self.config.income_stress_fraction) / (
            1 / self.config.firm_loan_term + rate + self.config.loan_rate_stress)
        amount = min(requested, room, max(0, affordable - outstanding), self.credit_room())
        if amount <= EPS:
            return 0.0
        term = self.config.firm_loan_term
        self.accounts[firm.account] += amount
        self.firm_loans.append(FirmLoan(firm.firm_id, amount, amount / term, rate,
                                       self.step_count + 1, self.step_count + 1 + term))
        self.flows["Business loans originated"] += amount
        self.log(BANK, firm.account, amount, "Business loan creates deposit and debt")
        return amount

    def service_firm_loans(self):
        year = self.step_count + 1
        for loan in list(self.firm_loans):
            if loan not in self.firm_loans:
                continue
            if loan.issued >= year:
                continue
            firm = self.market.firms[loan.borrower]
            interest = loan.principal * loan.rate
            loan.arrears += interest
            self.flows["Business loan interest accrued"] += interest
            paid = self.bank_payment(firm.account, loan.arrears, "Business loan interest")
            loan.arrears -= paid
            firm.interest += paid
            self.flows["Business loan interest paid"] += paid
            due = loan.principal if loan.maturity <= year else min(loan.installment, loan.principal)
            principal = self.bank_payment(firm.account, due, "Business principal destroys deposits")
            loan.principal -= principal
            self.flows["Business principal repaid"] += principal
            missed = loan.arrears > EPS or principal + EPS < due
            loan.missed = loan.missed + 1 if missed else 0
            if loan.principal + loan.arrears <= EPS:
                self.firm_loans.remove(loan)
            elif loan.missed >= self.config.default_after or loan.maturity <= year:
                self.market.fail(firm)
                # Failure resolves all this firm's loans in one operation.
        return

    def resolve_firm_debt(self, firm):
        for loan in [x for x in self.firm_loans if x.borrower == firm.firm_id]:
            paid = self.bank_payment(firm.account, loan.arrears, "Business liquidation interest")
            loan.arrears -= paid
            firm.interest += paid
            self.flows["Business loan interest paid"] += paid
            paid = self.bank_payment(firm.account, loan.principal, "Business liquidation principal")
            loan.principal -= paid
            self.flows["Business principal repaid"] += paid
            self.flows["Business principal losses"] += loan.principal
            self.flows["Business loan defaults"] += loan.principal + loan.arrears
            self.log(firm.account, BANK, loan.principal + loan.arrears, "Business residual debt write-off (non-cash)")
            self.firm_loans.remove(loan)

    def pay_loan(self, person, loan, principal_due):
        interest = self.bank_payment(person.account, loan.arrears, "Loan interest")
        loan.arrears -= interest
        person.interest_paid += interest
        principal = self.bank_payment(person.account, min(loan.principal, principal_due), "Loan principal repayment destroys deposits")
        loan.principal -= principal
        self.flows["Loan interest paid"] += interest
        self.flows["Loan principal repaid"] += principal
        return principal

    def liquidate_collateral(self, person, needed):
        """Liquidity-constrained sale, not destruction of capital or money."""
        proceeds = 0.0
        recovery = 1 - self.config.collateral_recovery_haircut
        if recovery <= 0:
            return proceeds
        for bond in [bond for bond in self.bonds if bond.holder == person.account]:
            if needed - proceeds <= EPS:
                break
            liquidation_value = self.bond_market_value(bond) * recovery
            paid = self.transfer(PRODUCER, person.account, min(needed - proceeds, liquidation_value),
                                 "Collateral bond liquidation")
            if paid:
                fraction = min(1, paid / liquidation_value)
                face, arrears = bond.principal * fraction, bond.arrears * fraction
                self.bonds.append(replace(bond, holder=PRODUCER, principal=face, arrears=arrears))
                bond.principal = max(0, bond.principal - face)
                bond.arrears = max(0, bond.arrears - arrears)
                if bond.principal + bond.arrears <= EPS:
                    self.bonds.remove(bond)
                proceeds += paid
        paid = self.transfer(PRODUCER, person.account,
                             min(max(0, needed - proceeds), person.assets * self.price * recovery),
                             "Collateral capital liquidation")
        units = min(person.assets, paid / (self.price * recovery))
        person.assets -= units
        self.producer_assets += units
        return proceeds + paid

    def resolve_loan(self, person, loan, *, borrower_default=True):
        """Collect available cash and collateral before writing off residual debt."""
        exposure = loan.principal + loan.arrears
        needed = max(0, exposure - self.accounts[person.account])
        self.liquidate_collateral(person, needed)
        before = self.accounts[person.account]
        self.pay_loan(person, loan, loan.principal)
        recovered = before - self.accounts[person.account]
        self.flows["Loan recoveries"] += recovered
        loss = loan.principal + loan.arrears
        self.flows["Loan defaults"] += loss
        self.flows["Loan principal losses"] += loan.principal
        self.log(person.account, BANK, loss, "Residual debt written off after recovery (non-cash)")
        self.loans.remove(loan)
        if borrower_default:
            person.default_count += 1
            person.last_default_year = self.step_count + 1
            self.flows["Defaulted loans"] += 1

    def service_loans(self):
        people = {p.person_id: p for p in self.population}
        for loan in list(self.loans):
            if loan.issued >= self.step_count + 1:
                continue
            person = people[loan.borrower]
            interest = loan.principal * loan.rate
            # Accrued unpaid interest is a bank asset and borrower liability.
            loan.arrears += interest
            self.flows["Loan interest accrued"] += interest
            matured = self.step_count + 1 >= loan.maturity
            due = loan.principal if matured else min(loan.principal, loan.installment)
            repaid = self.pay_loan(person, loan, due)
            missed = repaid + EPS < due or loan.arrears > EPS
            loan.missed = loan.missed + 1 if missed else 0
            if (matured and missed) or loan.missed >= self.config.default_after:
                self.resolve_loan(person, loan)
            elif loan.principal + loan.arrears <= EPS:
                self.loans.remove(loan)

    def sell_bond(self, holder, requested, *, refinance=False):
        if not math.isfinite(requested) or requested < 0:
            raise ValueError("Bond purchases must be finite and non-negative.")
        if not self.sovereign_market_access:
            return 0.0
        year = self.step_count + 1
        headroom = max(0, self.config.debt_ceiling - self.government_debt)
        rollover = sum(b.principal for b in self.bonds if b.maturity <= year) if refinance else 0.0
        room = headroom + rollover
        amount = min(requested, room, self.credit_room() if holder == BANK else self.accounts[holder])
        if amount <= EPS:
            return 0.0
        if holder == BANK:
            self.accounts[GOV] += amount
            self.flows["Bank bond credit"] += amount
            self.log(BANK, GOV, amount, "Bank bond purchase creates treasury deposit")
        else:
            self.transfer(holder, GOV, amount, "Government bond purchase")
        matched = max(0, amount - headroom)
        coupon = self.config.bond_rate + self.sovereign_spread(additional_debt=amount - matched)
        self.bonds.append(Bond(holder, amount, coupon, year, year + self.config.bond_term,
                               last_coupon_year=year))
        self.flows["Borrowing proceeds"] += amount
        # Above-ceiling funding is earmarked for matched redemption, never
        # available for coupons or discretionary spending.
        if matched:
            matured = [b for b in self.bonds if b.maturity <= year and b.issued < year]
            self._pay_bonds(matured, principal=True, limit=matched)
            self.flows["Refinanced principal"] += matched
        return amount

    def fund_government(self):
        if self.config.monetary_financing:
            self.issue_money(self.config.issuance_per_step)
        self.service_bonds()
        if not self.config.government_borrowing or not self.sovereign_market_access:
            return
        target = self.config.borrowing_target + self.bond_obligations(self.step_count + 1)
        bank_target = target * self.config.bank_bond_fraction
        household_target = target - bank_target
        confidence = 1 / (1 + self.config.sovereign_risk_aversion * self.sovereign_spread())
        offers = [(p, self.accounts[p.account] * self.config.bond_purchase_fraction * confidence)
                  for p in self.population if p.age >= 18]
        total = sum(amount for _, amount in offers)
        for person, offer in offers:
            raised = self.sell_bond(person.account, min(household_target, total) * offer / total if total else 0, refinance=True)
            if raised and self.flows["Debt service shortfall"] > EPS:
                self.service_bonds()
        self.sell_bond(BANK, bank_target * confidence, refinance=True)
        self.service_bonds()

    def _pay_bonds(self, bonds, *, principal, limit=math.inf):
        due = sum(b.principal if principal else b.arrears for b in bonds)
        available = min(limit, self.accounts[GOV], due)
        if available <= EPS:
            return
        category = "Bond principal repaid" if principal else "Bond interest paid"
        people = {p.account: p for p in self.population}
        for bond in bonds:
            obligation = bond.principal if principal else bond.arrears
            amount = available * obligation / due if due else 0.0
            if bond.holder == BANK:
                paid = self.bank_payment(GOV, amount, category)
                self.flows["Bank bond repayments"] += paid
                if not principal:
                    self.flows["Bank bond interest received"] += paid
            else:
                paid = self.transfer(GOV, bond.holder, amount, category)
                if not principal and bond.holder in people:
                    people[bond.holder].income_received += paid
            if principal:
                bond.principal = max(0, bond.principal - paid)
            else:
                bond.arrears = max(0, bond.arrears - paid)
            self.flows[category] += paid
            self.flows["Debt service spent"] += paid
        self.bonds = [b for b in self.bonds if b.principal + b.arrears > EPS]

    def service_bonds(self):
        """Mandatory debt service, repeated safely without double-accruing coupons."""
        year = self.step_count + 1
        existing = [b for b in self.bonds if b.issued < year]
        for bond in existing:
            elapsed = max(0, year - max(bond.issued, bond.last_coupon_year))
            interest = bond.principal * bond.rate * elapsed
            bond.arrears += interest
            bond.last_coupon_year = year
            self.flows["Bond interest accrued"] += interest
        due = self.bond_obligations(year)
        self.flows["Debt service due"] = max(self.flows["Debt service due"], due + self.flows["Debt service spent"])
        self._pay_bonds(existing, principal=False)
        matured = [b for b in self.bonds if b.issued < year and b.maturity <= year]
        self._pay_bonds(matured, principal=True)
        self.flows["Debt service shortfall"] = self.bond_obligations(year)

    def request_government_default(self):
        if not self.bonds:
            raise ValueError("There is no outstanding government bond debt to cancel.")
        self.sovereign_default_pending = True

    def _execute_government_default(self):
        self.sovereign_default_pending = False
        if not self.bonds:
            return
        principal = sum(b.principal for b in self.bonds)
        interest = sum(b.arrears for b in self.bonds)
        market_loss = self.government_market_debt
        bank_loss = sum(b.principal for b in self.bonds if b.holder == BANK)
        for bond in self.bonds:
            self.log(GOV, bond.holder, bond.principal + bond.arrears, "Sovereign debt repudiation (non-cash)")
        self.bonds.clear()
        self.flows["Sovereign debt written off"] += principal + interest
        self.flows["Sovereign market losses"] += market_loss
        self.flows["Bank bond principal losses"] += bank_loss
        self.flows["Sovereign default event"] = 1
        self.sovereign_default_count += 1
        self.last_sovereign_default_year = self.step_count + 1
        self.reputation_spread += self.config.sovereign_default_penalty
        self.sovereign_events.append({"Year": self.step_count + 1, "Principal cancelled": principal,
                                     "Interest cancelled": interest, "Creditor market loss": market_loss,
                                     "Bank principal loss": bank_loss})

    def collect_taxes(self):
        taxable = np.array([max(0, self.net_wealth(p)) for p in self.population])
        rates = wealth_tax_rates(taxable, self.config)
        self.flows["Minimum applied tax rate"] = float(rates.min()) if len(rates) else 0.0
        self.flows["Maximum applied tax rate"] = float(rates.max()) if len(rates) else 0.0
        due = sum(taxable * rates)
        for person, wealth, rate in zip(self.population, taxable, rates):
            paid = self.transfer(person.account, GOV, wealth * rate, "Net wealth tax")
            person.tax_paid += paid
            self.flows["Tax revenue"] += paid
        self.flows["Unpaid wealth tax"] = max(0, due - self.flows["Tax revenue"])
        self.flows["Effective wealth tax rate"] = self.flows["Tax revenue"] / float(taxable.sum()) if taxable.sum() else 0.0

    def prepare_budget(self):
        self.service_bonds()
        self.policy_budget = self.accounts[GOV]
        self.budget_allocations = allocate(self.policy_budget, self.shares)
        self.spent = {name: 0.0 for name in self.budget_allocations}

    def pay_policies(self):
        for p in self.population:
            p.ubi_received = self.transfer(GOV, p.account, self.budget_allocations["UBI"] / len(self.population), "UBI")
            p.income_received += p.ubi_received
            self.spent["UBI"] += p.ubi_received
        retirees = [p for p in self.population if p.age >= self.config.retirement_age]
        self.flows["Pension eligible"] = len(retirees)
        self.flows["UBI per person"] = self.spent["UBI"] / len(self.population) if self.population else 0.0
        target = self.config.pension_per_person * self.config.initial_money_per_person * (self.price if self.config.index_pensions else 1)
        pensions = min(self.budget_allocations["Pensions"], len(retirees) * target)
        for p in self.population:
            p.pension_received = 0
        for p in retirees:
            p.pension_received = self.transfer(GOV, p.account, pensions / len(retirees), "Pension")
            p.income_received += p.pension_received
        self.spent["Pensions"] = pensions
        self.flows["Pension shortfall"] = max(0, len(retirees) * target - pensions)
        self.spent["Healthcare"] = self.transfer(GOV, HEALTH, self.budget_allocations["Healthcare"], "Public healthcare")
        self.spent["Education"] = self.transfer(GOV, EDUCATION, self.budget_allocations["Education"], "Public education")

    def buy_capital(self, account, nominal):
        paid, units = self.market.buy({account: nominal}, "Capital goods purchase")[account]
        self.flows["Real investment"] += units
        return units, paid

    def invest(self):
        desired = self.budget_allocations["Public investment"]
        units, paid = self.buy_capital(GOV, desired)
        self.public_assets += units * self.config.base_eff
        self.flows["Public capital added"] += units * self.config.base_eff
        self.spent["Public investment"] = paid
        self.nominal_demand += desired
        # Pro-rata rationing of goods and credit avoids person-list order effects.
        adults = [p for p in self.population if 18 <= p.age < self.config.retirement_age]
        own = [self.accounts[p.account] * self.config.private_investment_fraction for p in adults]
        credit = [min(self.loan_quote(p)[0],
                      self.config.loan_demand * self.config.initial_money_per_person)
                  if self.config.lending_enabled else 0.0 for p in adults]
        total_credit = sum(credit)
        credit_scale = min(1, self.credit_room() / total_credit) if total_credit else 0
        desires = [cash + loan * credit_scale for cash, loan in zip(own, credit)]
        self.nominal_demand += sum(desires)
        total = sum(desires)
        supply_value = sum(f.inventory * f.price for f in self.market.active)
        scale = min(1, supply_value / total) if total else 0
        offers = {}
        for person, loan, desire in zip(adults, credit, desires):
            self.originate_loan(person, loan * credit_scale * scale)
            # Full funded cash offers reveal unmet demand, while loan creation
            # remains limited to the purchases that available goods can support.
            offers[person.account] = min(desire, self.accounts[person.account])
        purchases = self.market.buy(offers, "Private capital goods purchase")
        for person in adults:
            _, units = purchases[person.account]
            self.flows["Real investment"] += units
            efficiency = self.config.base_eff
            failed = self.rng.rand() < self.config.investment_risk
            if failed:
                efficiency *= 1 - self.config.failed_investment_loss
            if units > 0:
                self.flows["Failed private investments"] += int(failed)
                self.flows["Private capital shortfall"] += units * (self.config.base_eff - efficiency)
                self.flows["Private capital added"] += units * efficiency
            person.assets += units * efficiency

    def consume(self):
        # A higher policy rate discourages current consumption in this toy rule.
        fraction = self.config.consumption_fraction / (1 + self.config.policy_rate)
        offers = [self.accounts[p.account] * fraction for p in self.population]
        demand = sum(offers)
        self.nominal_demand += demand
        purchases = self.market.buy({p.account: offer for p, offer in zip(self.population, offers)}, "Consumption")
        units = 0.0
        for person in self.population:
            paid, bought = purchases[person.account]
            person.consumption_paid += paid
            person.consumption_units += bought
            self.flows["Consumption"] += paid
            units += bought
        self.flows["Real consumption"] = units

    def distribute_income(self):
        # Firm dividends are paid by the market after business debt service.
        # Healthcare salaries recycle a fraction of provider funds each year.
        health_pay = self.accounts[HEALTH] * self.config.wage_fraction
        for p in self.population:
            p.income_received += self.transfer(HEALTH, p.account, health_pay / len(self.population), "Healthcare income")
        excess = max(0, self.prudential_equity - self.config.initial_bank_capital)
        dividends = excess * self.config.bank_dividend_fraction
        # Distributions cannot leave the bank below capital or reserve constraints.
        risk = sum(x.principal + x.arrears for x in self.bank_loans) + sum(b.principal for b in self.bonds if b.holder == BANK)
        dividends = min(dividends, max(0, self.prudential_equity - risk * self.config.capital_ratio))
        if self.config.reserve_ratio:
            dividends = min(dividends, max(0, self.reserves / self.config.reserve_ratio - self.broad_money))
        if self.config.money_cap_type == "Broad money":
            dividends = min(dividends, self.money_room())
        for p in self.population:
            self.accounts[p.account] += dividends / len(self.population)
            p.income_received += dividends / len(self.population)
            p.bank_distribution_received += dividends / len(self.population)
            self.log(BANK, p.account, dividends / len(self.population), "Bank distribution creates deposits against bank equity")
        self.flows["Bank distributions"] = dividends

    def death_probability(self, age, *, funded=True, risk_factor=None):
        protection = (self.mortality_multiplier if funded else 1.0) if risk_factor is None else risk_factor
        return mortality_probability(age, self.config, protection)

    def private_death_probability(self, age):
        return mortality_probability(age, self.config, self.config.private_healthcare_mortality_factor)

    def private_premium(self, age):
        return self.config.initial_money_per_person * self.config.private_healthcare_premium * (
            1 + self.config.private_healthcare_age_loading * age / 100)

    def mortality_observations(self):
        """Mean age-specific risks for the same cohort, before mortality draws."""
        count = len(self.population)
        risks = {
            "Unfunded mortality": [self.death_probability(p.age, funded=False) for p in self.population],
            "Public care mortality": [self.death_probability(p.age) for p in self.population],
            "Expected mortality": [self.individual_death_probability(p) for p in self.population],
        }
        return {name: sum(values) / count if count else float("nan") for name, values in risks.items()}

    def update_health(self):
        self.flows["Public healthcare users"] = 0
        self.flows["Private healthcare users"] = 0
        real_funding = self.spent["Healthcare"] / self.trade_price / max(len(self.population), 1) / self.config.initial_money_per_person
        target = self.config.mortality_floor_fraction + (1 - self.config.mortality_floor_fraction) / (
            1 + self.config.healthcare_effectiveness * real_funding)
        self.mortality_multiplier += self.config.healthcare_response_rate * (target - self.mortality_multiplier)
        for p in self.population:
            p.healthcare_choice, p.healthcare_premium = "Public", 0.0
            # Private premium is indexed to prices; affordability uses liquid money.
            premium = self.private_premium(p.age) * self.price
            money = self.accounts[p.account]
            gain = self.death_probability(p.age) - self.private_death_probability(p.age)
            wants = self.config.healthcare_choice_mode == "Private if affordable" or (
                self.config.healthcare_choice_mode == "Adaptive" and
                gain * self.config.healthcare_choice_priority * p.healthcare_preference > premium / max(money, EPS))
            if wants and premium <= money * self.config.private_healthcare_max_wealth_fraction:
                p.healthcare_premium = self.transfer(p.account, HEALTH, premium, "Private healthcare premium")
                p.healthcare_choice = "Private"
                self.flows["Private premiums"] += p.healthcare_premium
                self.flows["Private healthcare users"] += 1
            else:
                self.flows["Public healthcare users"] += 1

    def individual_death_probability(self, person):
        return (self.private_death_probability(person.age) if person.healthcare_choice == "Private"
                else self.death_probability(person.age))

    def living_standards(self, *, observed=True):
        """Annual personal cash-flow proxies, frozen before deaths and births.

        Loans, principal repayments, asset sales, inheritances and revaluations
        are not income. There is no household pooling/equivalence scale.
        """
        names = ("Median disposable income", "Median real disposable income",
                 "Relative low-income share", "Low-income threshold", "Non-positive income share",
                 "Consumption per person", "Real consumption per person", "Pension replacement ratio")
        if not observed or not self.population:
            return {**dict.fromkeys(names, None), "Income observation population": 0}
        incomes = [p.income_received - p.tax_paid - p.interest_paid for p in self.population]
        median = float(np.median(incomes))
        threshold = RELATIVE_LOW_INCOME_FRACTION * median if median > 0 else None
        pension_cohort = [p.pension_received for p in self.population if 65 <= p.age <= 74]
        wage_cohort = [p.income for p in self.population if 50 <= p.age <= 59 and p.income > 0]
        replacement = float(np.median(pension_cohort) / np.median(wage_cohort)) if pension_cohort and wage_cohort else None
        count = len(self.population)
        consumption = sum(p.consumption_paid for p in self.population) / count
        return {
            "Median disposable income": median,
            "Median real disposable income": median / self.trade_price,
            "Relative low-income share": sum(income < threshold for income in incomes) / count if threshold is not None else None,
            "Low-income threshold": threshold,
            "Non-positive income share": sum(income <= 0 for income in incomes) / count,
            "Consumption per person": consumption,
            "Real consumption per person": sum(p.consumption_units for p in self.population) / count,
            "Pension replacement ratio": replacement,
            "Income observation population": count,
        }

    def settle_estates(self, dead_ids):
        survivors = [p for p in self.population if p.person_id not in dead_ids]
        for person in [p for p in self.population if p.person_id in dead_ids]:
            for loan in [x for x in self.loans if x.borrower == person.person_id]:
                self.resolve_loan(person, loan, borrower_default=False)
            heirs = [p for p in survivors if p.parent_id == person.person_id]
            if heirs:
                money = self.accounts[person.account]
                for heir in heirs:
                    self.transfer(person.account, heir.account, money / len(heirs), "Inheritance")
                    heir.assets += person.assets / len(heirs)
                for bond in [b for b in self.bonds if b.holder == person.account]:
                    for heir in heirs:
                        self.bonds.append(replace(bond, holder=heir.account, principal=bond.principal / len(heirs),
                                                  arrears=bond.arrears / len(heirs)))
                    self.bonds.remove(bond)
            else:
                self.flows["Estate revenue"] += self.transfer(person.account, GOV, self.accounts[person.account], "Unclaimed estate")
                self.public_assets += person.assets
                # Government-held own bonds are cancelled, not counted as revenue.
                for bond in [b for b in self.bonds if b.holder == person.account]:
                    self.flows["Estate debt cancellation"] += bond.principal + bond.arrears
                    self.bonds.remove(bond)
            del self.accounts[person.account]
        self.population = survivors

    def demographics(self):
        self.flows.update(self.mortality_observations())
        dead = {p.person_id for p in self.population if self.rng.rand() < self.individual_death_probability(p)}
        self.flows["Deaths"] = len(dead)
        self.flows["Observed mortality"] = len(dead) / len(self.population) if self.population else 0.0
        self.settle_estates(dead)
        newborns = []
        for p in self.population:
            p.age += 1
            if self.rng.rand() < age_dependent_birth_prob(p.age, self.config.birth_prob_max):
                child = Resident(self.next_id, 0, p.assets / 2, parent_id=p.person_id,
                                 healthcare_preference=float(self.rng.uniform(0.5, 1.5)))
                self.next_id += 1
                p.assets /= 2
                self.accounts[child.account] = 0.0
                self.transfer(p.account, child.account, self.accounts[p.account] / 2, "Birth endowment")
                newborns.append(child)
        self.population.extend(newborns)

    def reset_flows(self):
        names = ("Money issued", "Loans originated", "Loan interest accrued", "Loan interest paid", "Loan principal repaid",
                 "Loan defaults", "Bank bond credit", "Bank bond repayments", "Borrowing proceeds", "Bond interest paid",
                 "Bond principal repaid", "Debt service due", "Debt service shortfall", "Wages",
                 "Tax revenue", "Unpaid wealth tax", "Pension shortfall", "Real investment", "Consumption", "Real consumption",
                 "Bank distributions", "Private premiums", "Estate revenue", "Estate debt cancellation", "Deaths",
                 "Observed mortality", "Public healthcare users", "Private healthcare users", "Minimum applied tax rate",
                 "Maximum applied tax rate", "Effective wealth tax rate", "Pension eligible", "UBI per person",
                 "Failed private investments", "Private capital shortfall", "Private capital added",
                 "Opening government money", "Total government spending", "Money balance error",
                 "Base money balance error", "Government balance error", "Loan recoveries", "Loan principal losses",
                 "Defaulted loans", "Bank bond interest received", "Bank bond principal losses", "Bank realized profit",
                 "Debt service spent", "Bond interest accrued", "Refinanced principal", "Sovereign debt written off",
                 "Sovereign market losses", "Sovereign default event", "Opening government debt",
                 "Government debt balance error", "Bank bond valuation change",
                 "Technology breakthrough event", "Technology productivity gain", "Productivity growth realized")
        names += ("Opening inventories", "Inventory spoilage", "Inventory scrapped", "Inventory balance error",
                  "Labor force", "Employed", "Unemployed", "Unemployment rate", "Research spending",
                  "Research breakthroughs", "Firm entries", "Firm failures", "Firm profits",
                  "Business loans originated", "Business loan interest accrued", "Business loan interest paid",
                  "Business principal repaid", "Business principal losses", "Business loan defaults",
                  "Goods supply value", "Public capital added")
        names += ("Average wage",)
        names += ("Education salaries", "Education materials", "Real education goods",
                  "Teachers", "School students", "University students", "Full-time students", "Adult trainees",
                  "Education quality", "Education funding coverage", "Education resources per learner",
                  "School completions", "University graduates", "University dropouts", "Training completions",
                  "Mean worker skill", "Secondary attainment", "University attainment",
                  "Work skill gain", "Work experience added", "Mean work experience")
        names += ("Energy available", "Energy demand", "Energy used", "Energy unused", "Energy spending",
                  "Energy income", "Energy utilization", "Energy coverage", "Energy rationing",
                  "Energy shock active", "Energy-limited planned output", "Energy balance error", "Energy input balance error")
        self.flows = dict.fromkeys(names, 0.0)
        self.policy_budget = 0.0
        self.budget_allocations = allocate(0, self.shares)
        self.spent = dict.fromkeys(self.budget_allocations, 0.0)
        self.output = self.inflation = self.nominal_demand = 0.0

    def update_policy(self, **changes):
        known = {f.name for f in fields(MonetaryConfig)}
        initial = {"pop_size", "initial_money_per_person", "initial_capacity", "initial_producer_money", "initial_bank_capital",
                   "firm_count", "firm_productivity_dispersion"}
        if set(changes) - known or set(changes) & initial:
            raise ValueError("Unknown policy or initial condition; initial conditions require a new scenario.")
        candidate = replace(self.config, **changes)
        validate_config(candidate)
        old = self.config
        self.config = candidate
        if candidate.money_cap and self.capped_supply > candidate.money_cap + EPS:
            self.config = old
            raise ValueError("Cap is below existing supply. Existing money cannot be clipped; choose a higher cap.")
        if candidate.wage_fraction != old.wage_fraction:
            for f in self.market.active:
                f.wage = (f.wage * candidate.wage_fraction / old.wage_fraction if old.wage_fraction
                          else candidate.productivity * self.price * candidate.wage_fraction)
        changed = {k: v for k, v in changes.items() if getattr(old, k) != v}
        if changed:
            self.policy_changes.append({"Effective step": self.step_count + 1, "Changes": changed})
        return bool(changed)

    def step(self):
        if not self.population:
            return False
        opening_debt = self.government_debt
        opening_valuation_reserve = self.bank_bond_valuation_reserve
        self.reset_flows()
        self._in_step = True
        self.reputation_spread *= 1 - self.config.sovereign_reputation_recovery
        if self.sovereign_default_pending:
            self._execute_government_default()
        opening_money, opening_base = self.broad_money, self.reserves
        opening_gov = self.accounts[GOV]
        self.flows["Opening government money"] = opening_gov
        self.flows["Opening government debt"] = opening_debt
        self.trade_price = self.price
        self.advance_technology()
        for p in self.population:
            p.income_received = p.tax_paid = p.interest_paid = p.consumption_paid = p.consumption_units = p.bank_distribution_received = 0.0
            p.employer = None
            p.income = 0.0
            p.assets *= 1 - self.config.delta
        self.public_assets *= 1 - self.config.delta
        self.producer_assets *= 1 - self.config.delta
        self.education.prepare_year()
        self.market.begin_year()
        employed = self.flows["Employed"]
        self.flows["Average wage"] = self.flows["Wages"] / employed if employed else None
        self.reference_nominal_output = sum(f.output * f.price for f in self.market.active)
        self.flows["Goods supply value"] = self.market.inventory_value
        self.service_loans()
        self.collect_taxes()
        self.fund_government()
        self.prepare_budget()
        self.pay_policies()
        self.invest()
        self.consume()
        self.education.deliver()
        self.market.close_year()
        self.energy.close_year()
        self.distribute_income()
        self.update_health()
        self.flows.update(self.living_standards())
        for p in self.population:
            p.last_disposable_income = p.income_received - p.tax_paid - p.interest_paid
            # Affordability uses income before debt service to avoid counting
            # interest twice, and excludes discretionary bank-capital releases.
            p.last_repayment_income = p.income_received - p.tax_paid - p.bank_distribution_received
            p.income_observed = True
        self.demographics()
        self.flows["Bank realized profit"] = (self.flows["Loan interest paid"] + self.flows["Bank bond interest received"]
                                             + self.flows["Business loan interest paid"]
                                             - self.flows["Loan principal losses"] - self.flows["Bank bond principal losses"]
                                             - self.flows["Business principal losses"])
        self.flows["Bank bond valuation change"] = opening_valuation_reserve - self.bank_bond_valuation_reserve
        created = (self.flows["Money issued"] + self.flows["Loans originated"] + self.flows["Bank bond credit"]
                   + self.flows["Bank distributions"] + self.flows["Business loans originated"])
        destroyed = (self.flows["Loan principal repaid"] + self.flows["Loan interest paid"] + self.flows["Bank bond repayments"]
                     + self.flows["Business principal repaid"] + self.flows["Business loan interest paid"])
        self.flows["Money balance error"] = self.broad_money - opening_money - created + destroyed
        self.flows["Base money balance error"] = self.reserves - opening_base - self.flows["Money issued"]
        self.flows["Total government spending"] = sum(self.spent.values()) + self.flows["Debt service spent"]
        self.flows["Government balance error"] = self.accounts[GOV] - (opening_gov + self.flows["Tax revenue"] +
            self.flows["Borrowing proceeds"] + self.flows["Money issued"] + self.flows["Estate revenue"]
            - self.flows["Total government spending"])
        self.flows["Government debt balance error"] = self.government_debt - (
            opening_debt + self.flows["Borrowing proceeds"] + self.flows["Bond interest accrued"]
            - self.flows["Debt service spent"] - self.flows["Estate debt cancellation"]
            - self.flows["Sovereign debt written off"])
        self.step_count += 1
        self._in_step = False
        self.record()
        return True

    def advance(self, steps=1):
        for _ in range(steps):
            if not self.step():
                break

    def balance_sheets(self):
        household_assets = sum(self.accounts[p.account] + p.assets * self.price + self.bond_assets(p) for p in self.population)
        household_debt = sum(self.debt(p) for p in self.population)
        required_yield = self.config.bond_rate + self.sovereign_spread()
        producer_bonds = sum(sum(self.bond_values(b, required_yield=required_yield))
                             for b in self.bonds if b.holder == PRODUCER)
        bank_assets = self.reserves + sum(x.principal + x.arrears for x in self.bank_loans) + sum(
            sum(self.bond_values(b, required_yield=required_yield)) for b in self.bonds if b.holder == BANK)
        rows = [("Households", household_assets, household_debt),
                 (GOV, self.accounts[GOV] + self.public_assets * self.price, self.government_market_debt),
                 (PRODUCER, self.accounts[PRODUCER] + producer_bonds + self.producer_assets * self.price, 0), (HEALTH, self.accounts[HEALTH], 0),
                 (EDUCATION, self.accounts[EDUCATION], 0),
                 (ENERGY, self.accounts[ENERGY], 0),
                 (BANK, bank_assets, self.broad_money), ("Monetary authority", 0, self.reserves)]
        rows.extend((f.account, self.accounts[f.account] + f.inventory * f.price,
                     sum(x.principal + x.arrears for x in self.firm_loans if x.borrower == f.firm_id))
                    for f in self.market.firms)
        return [{"Sector": name, "Assets": assets, "Liabilities": liabilities, "Net worth": assets - liabilities}
                for name, assets, liabilities in rows]

    def person_rows(self):
        return [{"Person": p.person_id, "Age": p.age, "Parent": p.parent_id,
                  "Employer": p.employer, "Employed": p.employer is not None,
                  "Goods consumed": p.consumption_units,
                  "Skill": p.skill, "Technology familiarity": p.technology_skill, "School years": p.school_years,
                  "Work experience": p.work_experience,
                  "Education track": p.education_track, "University progress": p.university_progress,
                  "University completed": p.university_completed, "Training progress": p.training_progress,
                  "Employment sector": "Education" if p.education_teacher else ("Goods" if p.employer is not None else "None"),
                 "Money": self.accounts[p.account], "Real productive assets": p.assets,
                  "Bonds": self.bond_assets(p), "Debt": self.debt(p), "Net wealth": self.net_wealth(p),
                  "Bond face value": sum(b.principal for b in self.bonds if b.holder == p.account),
                  "Bond interest arrears": sum(b.arrears for b in self.bonds if b.holder == p.account),
                 "Real net wealth": self.net_wealth(p) / self.price,
                 "UBI": p.ubi_received, "Pension": p.pension_received, "Healthcare": p.healthcare_choice,
                  "Wages": p.income, "Health preference": p.healthcare_preference,
                  "Disposable income": p.last_disposable_income if p.income_observed else None,
                  "Income received": p.income_received, "Wealth tax paid": p.tax_paid, "Loan interest paid": p.interest_paid,
                  "Consumption": p.consumption_paid, "Verified repayment income": self.verified_income(p),
                  "Borrower risk score": self.borrower_risk(p), "Default count": p.default_count,
                  "Private premium": p.healthcare_premium, "Death probability": self.individual_death_probability(p)}
                for p in self.population]

    def record(self):
        wealth = [self.net_wealth(p) for p in self.population]
        output_value = self.reference_nominal_output if self.step_count else 0.0
        supply_value = self.flows["Goods supply value"]
        total_sales = sum(f.sales for f in self.market.active)
        concentration = sum((f.sales / total_sales) ** 2 for f in self.market.active) if total_sales > EPS else None
        # Conventional Gini is not bounded with negative net wealth; report it
        # only for non-negative distributions rather than silently clipping debt.
        gini = gini_coefficient(np.array(wealth)) if all(x >= 0 for x in wealth) else None
        self.history.append({"Step": self.step_count, "Population": len(self.population), "Net wealth": sum(wealth),
            "Real net wealth": sum(wealth) / self.price, "Productive capacity": self.capacity, "Output": self.output,
            "Worker productivity": self.effective_productivity, "Technology index": self.technology_index,
            "Technology breakthroughs": self.technology_breakthroughs,
            "Active firms": len(self.market.active), "Inventory value": self.market.inventory_value,
            "Market concentration": concentration,
            "Adopted worker productivity": (sum(self.config.productivity * f.productivity_factor * f.technology
                                               for f in self.market.active) / len(self.market.active)
                                            if self.market.active else 0.0),
            "Price level": self.price, "Inflation": self.inflation, "Base money": self.reserves, "Broad money": self.broad_money,
            "Desired goods spending": self.nominal_demand, "Output at trade prices": output_value,
            "Goods demand coverage": self.nominal_demand / supply_value if supply_value > EPS else None,
            "Unsold goods": self.goods_remaining,
            "Government money": self.accounts[GOV], "Government debt": self.government_debt,
            "Education sector money": self.accounts[EDUCATION],
            "Energy sector money": self.accounts[ENERGY], "Energy price": self.energy.price,
            "Government market debt": self.government_market_debt, "Government arrears": self.government_arrears,
            "Sovereign spread": self.sovereign_spread(), "New bond yield": self.config.bond_rate + self.sovereign_spread(),
            "Sovereign defaults": self.sovereign_default_count, "Sovereign market access": self.sovereign_market_access,
            "Sovereign reputation penalty": self.reputation_spread,
            "Average bond price": (self.government_market_debt / self.government_debt if self.government_debt > EPS else None),
            "Bank equity": self.bank_equity, "Prudential bank equity": self.prudential_equity,
            "Unpaid loan interest": self.unpaid_interest,
            "Outstanding loans": sum(x.principal + x.arrears for x in self.loans),
            "Business loans": sum(x.principal + x.arrears for x in self.firm_loans),
            "Gini": gini, "Policy budget": self.policy_budget, "Healthcare sector money": self.accounts[HEALTH],
            **{f"{k} spent": v for k, v in self.spent.items()},
            **{f"{name} allocation fraction": share for name, share in zip(self.budget_allocations, self.shares)},
            **{f"{k} allocated": v for k, v in self.budget_allocations.items()}, **self.flows})


def comparison_config(name):
    """Explicit, reproducible alternatives, not silent policy interventions."""
    presets: dict[str, dict[str, Any]] = {
        "No credit or printing": {},
        "Government bonds": {"government_borrowing": True, "bank_bond_fraction": 0.0},
        "Individual credit": {"lending_enabled": True},
        "Fixed broad money ceiling": {"lending_enabled": True, "money_cap_type": "Broad money", "money_cap": 200.0},
        "Expandable credit": {"lending_enabled": True, "government_borrowing": True},
        "Monetary financing": {"monetary_financing": True, "issuance_per_step": 2.0},
    }
    return MonetaryConfig(**presets[name])


COMPARISON_NAMES = ("No credit or printing", "Government bonds", "Individual credit", "Fixed broad money ceiling",
                    "Expandable credit", "Monetary financing")
