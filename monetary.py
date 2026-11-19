"""A small stock-flow-consistent monetary economy, separate from the legacy model.

One commercial bank, a fiat issuer and aggregate goods/healthcare producers.
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

from budget import LEGACY_FIELDS, allocate, validate_allocations
from simulation import Simulation, SimulationConfig, age_dependent_birth_prob, gini_coefficient, wealth_tax_rates

EPS = 1e-9
GOV, PRODUCER, HEALTH, BANK = "Government", "Production", "Healthcare", "Bank"


BASE = SimulationConfig()


@dataclass(frozen=True)
class MonetaryConfig:
    # Share calibration, not the legacy growth/wealth accounting machinery.
    pop_size: int = BASE.pop_size
    init_wealth: float = BASE.init_wealth  # Initial deposits per resident.
    logistic_capacity: float = BASE.logistic_capacity  # Initial real capital, not a cap.
    tau_base: float = 0.0
    tau_max: float = 0.6
    tau_gamma: float = BASE.tau_gamma
    direct_redistribution_fraction: float = BASE.direct_redistribution_fraction
    pension_budget_fraction: float = BASE.pension_budget_fraction
    healthcare_spending_fraction: float = BASE.healthcare_spending_fraction
    investment_budget_fraction: float = BASE.investment_budget_fraction
    retirement_age: int = BASE.retirement_age
    pension_per_person: float = BASE.pension_per_person
    delta: float = BASE.delta
    base_eff: float = BASE.base_eff
    investment_risk: float = BASE.investment_risk
    failed_investment_loss: float = BASE.failed_investment_loss
    birth_prob_max: float = BASE.birth_prob_max
    death_base_prob: float = BASE.death_base_prob
    aging_risk_start: int = BASE.aging_risk_start
    aging_risk_rate: float = BASE.aging_risk_rate
    mortality_doubling_years: float = BASE.mortality_doubling_years
    healthcare_effectiveness: float = BASE.healthcare_effectiveness
    healthcare_response_rate: float = BASE.healthcare_response_rate
    mortality_floor_fraction: float = BASE.mortality_floor_fraction
    healthcare_choice_mode: str = BASE.healthcare_choice_mode
    private_healthcare_premium: float = BASE.private_healthcare_premium
    private_healthcare_age_loading: float = BASE.private_healthcare_age_loading
    private_healthcare_mortality_factor: float = BASE.private_healthcare_mortality_factor
    private_healthcare_max_wealth_fraction: float = BASE.private_healthcare_max_wealth_fraction
    healthcare_choice_priority: float = BASE.healthcare_choice_priority
    budget_mode: str = "Total budget"
    initial_producer_money: float = 100.0
    initial_bank_capital: float = 20.0
    productivity: float = 2.0
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
    debt_service_fraction: float = 0.05
    principal_first: bool = False
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


@dataclass
class Bond:
    holder: str
    principal: float
    rate: float
    issued: int
    maturity: int


def validate_config(config):
    defaults = MonetaryConfig()
    initial = {"pop_size", "loan_term", "bond_term", "default_after", "retirement_age", "aging_risk_start"}
    fractions = {"consumption_fraction", "wage_fraction", "producer_dividend_fraction", "private_investment_fraction",
                 "inflation_response", "loan_demand", "capital_ratio", "reserve_ratio", "bank_dividend_fraction",
                 "bond_purchase_fraction", "bank_bond_fraction", "debt_service_fraction", "delta", "investment_risk",
                 "failed_investment_loss", "death_base_prob", "birth_prob_max", "healthcare_response_rate",
                 "mortality_floor_fraction", "private_healthcare_mortality_factor", "private_healthcare_max_wealth_fraction",
                 "tau_base", "tau_max"}
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
    for name in ("pop_size", "loan_term", "bond_term", "default_after", "init_wealth", "mortality_doubling_years", "tau_gamma"):
        if getattr(config, name) <= 0:
            raise ValueError(f"{name} must be positive.")
    if config.tau_base > config.tau_max:
        raise ValueError("The maximum tax rate must be at least the minimum tax rate.")
    if config.budget_mode != "Total budget" or config.money_cap_type not in {"Base money", "Broad money"}:
        raise ValueError("Choose a valid budget and money-cap regime.")
    if config.healthcare_choice_mode not in {"Adaptive", "Public only", "Private if affordable"}:
        raise ValueError("Choose a valid healthcare strategy.")
    validate_allocations([getattr(config, name) for name in LEGACY_FIELDS] + [config.debt_service_fraction])


class MonetarySimulation:
    def __init__(self, config=None, seed=42, history_limit=10000):
        self.config = config or MonetaryConfig()
        validate_config(self.config)
        self.initial_config = self.config
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        ages, preferences = random.Random(seed), random.Random(seed + 1)
        self.population = [Resident(i, ages.randint(1, 50), self.config.logistic_capacity / self.config.pop_size,
                                    healthcare_preference=preferences.uniform(0.5, 1.5))
                           for i in range(self.config.pop_size)]
        self.accounts = {p.account: self.config.init_wealth for p in self.population}
        self.accounts.update({GOV: 0.0, PRODUCER: self.config.initial_producer_money, HEALTH: 0.0})
        self.reserves = self.broad_money + self.config.initial_bank_capital
        if self.config.money_cap and self.capped_supply > self.config.money_cap + EPS:
            raise ValueError("Money cap is below starting supply. Increase the cap or lower initial money.")
        self.initial_base = self.reserves
        self.next_id = self.config.pop_size
        self.price = 1.0
        self.public_assets = 0.0
        self.producer_assets = 0.0
        self.loans: list[Loan] = []
        self.bonds: list[Bond] = []
        self.step_count = 0
        self.mortality_multiplier = 1.0
        self.mortality_rate = self.config.death_base_prob
        self.policy_changes = deque(maxlen=1000)
        self.transactions = deque(maxlen=10000)
        self.history = deque(maxlen=history_limit)
        self.reset_flows()
        self.record()

    @property
    def broad_money(self):
        return sum(self.accounts.values())

    @property
    def capped_supply(self):
        return self.reserves if self.config.money_cap_type == "Base money" else self.broad_money

    @property
    def bank_equity(self):
        return self.reserves + sum(x.principal + x.arrears for x in self.loans) + sum(
            x.principal for x in self.bonds if x.holder == BANK) - self.broad_money

    @property
    def government_debt(self):
        return sum(x.principal for x in self.bonds)

    @property
    def capacity(self):
        return self.public_assets + self.producer_assets + sum(p.assets for p in self.population)

    @property
    def shares(self):
        return [getattr(self.config, name) for name in LEGACY_FIELDS] + [self.config.debt_service_fraction]

    def debt(self, person):
        return sum(x.principal + x.arrears for x in self.loans if x.borrower == person.person_id)

    def bond_assets(self, person):
        return sum(x.principal for x in self.bonds if x.holder == person.account)

    def net_wealth(self, person):
        return self.accounts[person.account] + person.assets * self.price + self.bond_assets(person) - self.debt(person)

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
        if self.bank_equity <= EPS:
            return 0.0
        risk_assets = sum(x.principal + x.arrears for x in self.loans) + sum(
            x.principal for x in self.bonds if x.holder == BANK)
        capital = self.bank_equity / self.config.capital_ratio - risk_assets if self.config.capital_ratio else math.inf
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
        if not self.config.lending_enabled or person.age < 18 or person.age >= self.config.retirement_age:
            return 0.0
        collateral = max(0, person.assets * self.price + self.bond_assets(person))
        room = max(0, collateral * self.config.borrowing_limit - self.debt(person))
        amount = min(requested, room, self.credit_room())
        if amount <= EPS:
            return 0.0
        term = self.config.loan_term
        self.accounts[person.account] += amount
        self.loans.append(Loan(person.person_id, amount, amount / term,
                               self.config.policy_rate + self.config.loan_spread,
                               self.step_count + 1, self.step_count + 1 + term))
        self.flows["Loans originated"] += amount
        self.log(BANK, person.account, amount, "Loan creates deposit and matching debt")
        return amount

    def bank_payment(self, account, amount, purpose):
        paid = min(self.accounts[account], max(0, amount))
        self.accounts[account] -= paid
        self.log(account, BANK, paid, purpose)
        return paid

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
            paid_interest = self.bank_payment(person.account, loan.arrears, "Loan interest")
            loan.arrears -= paid_interest
            self.flows["Loan interest paid"] += paid_interest
            matured = self.step_count + 1 >= loan.maturity
            due = loan.principal if matured else min(loan.principal, loan.installment)
            repaid = self.bank_payment(person.account, due, "Loan principal repayment destroys deposits")
            loan.principal -= repaid
            self.flows["Loan principal repaid"] += repaid
            missed = repaid + EPS < due or loan.arrears > EPS
            loan.missed = loan.missed + 1 if missed else 0
            if (matured and missed) or loan.missed >= self.config.default_after:
                self.flows["Loan defaults"] += loan.principal + loan.arrears
                self.log(person.account, BANK, loan.principal + loan.arrears, "Debt written off; bank bears loss (non-cash)")
                self.loans.remove(loan)
            elif loan.principal + loan.arrears <= EPS:
                self.loans.remove(loan)

    def sell_bond(self, holder, requested):
        if not math.isfinite(requested) or requested < 0:
            raise ValueError("Bond purchases must be finite and non-negative.")
        room = max(0, self.config.debt_ceiling - self.government_debt)
        amount = min(requested, room, self.credit_room() if holder == BANK else self.accounts[holder])
        if amount <= EPS:
            return 0.0
        if holder == BANK:
            self.accounts[GOV] += amount
            self.flows["Bank bond credit"] += amount
            self.log(BANK, GOV, amount, "Bank bond purchase creates treasury deposit")
        else:
            self.transfer(holder, GOV, amount, "Government bond purchase")
        self.bonds.append(Bond(holder, amount, self.config.bond_rate, self.step_count + 1,
                               self.step_count + 1 + self.config.bond_term))
        self.flows["Borrowing proceeds"] += amount
        return amount

    def fund_government(self):
        if self.config.monetary_financing:
            self.issue_money(self.config.issuance_per_step)
        if not self.config.government_borrowing:
            return
        target = min(self.config.borrowing_target, max(0, self.config.debt_ceiling - self.government_debt))
        bank_target = target * self.config.bank_bond_fraction
        household_target = target - bank_target
        offers = [(p, self.accounts[p.account] * self.config.bond_purchase_fraction) for p in self.population if p.age >= 18]
        total = sum(amount for _, amount in offers)
        for person, offer in offers:
            self.sell_bond(person.account, min(household_target, total) * offer / total if total else 0)
        self.sell_bond(BANK, bank_target)

    def service_bonds(self, allowance):
        existing = [bond for bond in self.bonds if bond.issued < self.step_count + 1]
        interests = {id(b): b.principal * b.rate for b in existing}
        principals = {id(b): b.principal if b.maturity <= self.step_count + 1 else 0 for b in existing}
        self.flows["Debt service due"] = sum(interests.values()) + sum(principals.values())
        categories = [(principals, "Bond principal repaid"), (interests, "Bond interest paid")]
        if not self.config.principal_first:
            categories.reverse()
        principal_paid = {}
        for amounts, category in categories:
            due = sum(amounts.values())
            available = min(allowance, self.accounts[GOV], due)
            for bond in existing:
                amount = available * amounts[id(bond)] / due if due else 0
                if bond.holder == BANK:
                    paid = self.bank_payment(GOV, amount, category)
                    self.flows["Bank bond repayments"] += paid
                else:
                    paid = self.transfer(GOV, bond.holder, amount, category)
                self.flows[category] += paid
                if category == "Bond principal repaid":
                    principal_paid[id(bond)] = paid
            allowance -= available
        for bond in existing:
            if bond.maturity <= self.step_count + 1:
                loss = max(0, bond.principal - principal_paid.get(id(bond), 0))
                self.flows["Bond principal defaults"] += loss
                if loss:
                    self.log(GOV, bond.holder, loss, "Matured bond haircut (non-cash)")
                self.bonds.remove(bond)
        self.flows["Debt service shortfall"] = max(0, self.flows["Debt service due"] -
            self.flows["Bond interest paid"] - self.flows["Bond principal repaid"])

    def pay_wages(self, potential):
        workers = [p for p in self.population if 18 <= p.age < self.config.retirement_age]
        wages = min(self.accounts[PRODUCER], potential * self.price * self.config.wage_fraction)
        for person in self.population:
            person.income = 0.0
        for person in workers:
            person.income = self.transfer(PRODUCER, person.account, wages / len(workers), "Wages")
        self.flows["Wages"] = sum(p.income for p in self.population)

    def collect_taxes(self):
        taxable = np.array([max(0, self.net_wealth(p)) for p in self.population])
        rates = wealth_tax_rates(taxable, self.config)
        self.flows["Minimum applied tax rate"] = float(rates.min()) if len(rates) else 0.0
        self.flows["Maximum applied tax rate"] = float(rates.max()) if len(rates) else 0.0
        due = sum(taxable * rates)
        for person, wealth, rate in zip(self.population, taxable, rates):
            self.flows["Tax revenue"] += self.transfer(person.account, GOV, wealth * rate, "Net wealth tax")
        self.flows["Unpaid wealth tax"] = max(0, due - self.flows["Tax revenue"])
        self.flows["Effective wealth tax rate"] = self.flows["Tax revenue"] / float(taxable.sum()) if taxable.sum() else 0.0

    def prepare_budget(self):
        self.policy_budget = self.accounts[GOV]
        self.budget_allocations = allocate(self.policy_budget, self.shares)
        self.spent = {name: 0.0 for name in self.budget_allocations}

    def pay_policies(self):
        for p in self.population:
            p.ubi_received = self.transfer(GOV, p.account, self.budget_allocations["UBI"] / len(self.population), "UBI")
            self.spent["UBI"] += p.ubi_received
        retirees = [p for p in self.population if p.age >= self.config.retirement_age]
        self.flows["Pension eligible"] = len(retirees)
        self.flows["UBI per person"] = self.spent["UBI"] / len(self.population) if self.population else 0.0
        target = self.config.pension_per_person * self.config.init_wealth * (self.price if self.config.index_pensions else 1)
        pensions = min(self.budget_allocations["Pensions"], len(retirees) * target)
        for p in self.population:
            p.pension_received = 0
        for p in retirees:
            p.pension_received = self.transfer(GOV, p.account, pensions / len(retirees), "Pension")
        self.spent["Pensions"] = pensions
        self.flows["Pension shortfall"] = max(0, len(retirees) * target - pensions)
        self.spent["Healthcare"] = self.transfer(GOV, HEALTH, self.budget_allocations["Healthcare"], "Public healthcare")
        self.service_bonds(self.budget_allocations["Debt service"])
        self.spent["Debt service"] = self.flows["Bond interest paid"] + self.flows["Bond principal repaid"]

    def buy_capital(self, account, nominal):
        spending = min(nominal, self.accounts[account], self.goods_remaining * self.price)
        paid = self.transfer(account, PRODUCER, max(0, spending), "Capital goods purchase")
        units = paid / self.price
        self.goods_remaining = max(0, self.goods_remaining - units)
        self.flows["Real investment"] += units
        return units, paid

    def invest(self):
        desired = self.budget_allocations["Public investment"]
        units, paid = self.buy_capital(GOV, desired)
        self.public_assets += units * self.config.base_eff
        self.spent["Public investment"] = paid
        self.nominal_demand += desired
        # Pro-rata rationing of goods and credit avoids person-list order effects.
        adults = [p for p in self.population if 18 <= p.age < self.config.retirement_age]
        own = [self.accounts[p.account] * self.config.private_investment_fraction for p in adults]
        credit = [min(max(0, p.assets * self.price * self.config.borrowing_limit - self.debt(p)),
                      self.config.loan_demand * self.config.init_wealth)
                  if self.config.lending_enabled else 0.0 for p in adults]
        total_credit = sum(credit)
        credit_scale = min(1, self.credit_room() / total_credit) if total_credit else 0
        desires = [cash + loan * credit_scale for cash, loan in zip(own, credit)]
        self.nominal_demand += sum(desires)
        total = sum(desires)
        scale = min(1, self.goods_remaining * self.price / total) if total else 0
        for person, loan, desire in zip(adults, credit, desires):
            self.originate_loan(person, loan * credit_scale * scale)
            units, _ = self.buy_capital(person.account, desire * scale)
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
        scale = min(1, self.goods_remaining * self.price / demand) if demand else 0
        for person, offer in zip(self.population, offers):
            paid = self.transfer(person.account, PRODUCER, offer * scale, "Consumption")
            self.flows["Consumption"] += paid
        units = self.flows["Consumption"] / self.price
        self.goods_remaining = max(0, self.goods_remaining - units)
        self.flows["Real consumption"] = units

    def distribute_income(self):
        # Dividends use current receipts, not unlimited creation of deposits.
        sales = self.flows["Consumption"] + self.flows["Real investment"] * self.trade_price
        pool = min(self.accounts[PRODUCER], max(0, sales - self.flows["Wages"]) * self.config.producer_dividend_fraction)
        assets = sum(p.assets for p in self.population)
        for p in self.population:
            if assets:
                self.transfer(PRODUCER, p.account, pool * p.assets / assets, "Producer dividends")
        # Healthcare salaries recycle a fraction of provider funds each year.
        health_pay = self.accounts[HEALTH] * self.config.wage_fraction
        for p in self.population:
            self.transfer(HEALTH, p.account, health_pay / len(self.population), "Healthcare income")
        excess = max(0, self.bank_equity - self.config.initial_bank_capital)
        dividends = excess * self.config.bank_dividend_fraction
        # Distributions cannot leave the bank below capital or reserve constraints.
        risk = sum(x.principal + x.arrears for x in self.loans) + sum(b.principal for b in self.bonds if b.holder == BANK)
        dividends = min(dividends, max(0, self.bank_equity - risk * self.config.capital_ratio))
        if self.config.reserve_ratio:
            dividends = min(dividends, max(0, self.reserves / self.config.reserve_ratio - self.broad_money))
        if self.config.money_cap_type == "Broad money":
            dividends = min(dividends, self.money_room())
        for p in self.population:
            self.accounts[p.account] += dividends / len(self.population)
            self.log(BANK, p.account, dividends / len(self.population), "Bank distribution creates deposits against bank equity")
        self.flows["Bank distributions"] = dividends

    # Reuse the existing human-shaped mortality profile, not its money/wealth flows.
    death_probability = Simulation.death_probability
    private_death_probability = Simulation.private_death_probability
    private_premium = Simulation.private_premium

    def update_health(self):
        self.flows["Public healthcare users"] = 0
        self.flows["Private healthcare users"] = 0
        real_funding = self.spent["Healthcare"] / self.trade_price / max(len(self.population), 1) / self.config.init_wealth
        target = self.config.mortality_floor_fraction + (1 - self.config.mortality_floor_fraction) / (
            1 + self.config.healthcare_effectiveness * real_funding)
        self.mortality_multiplier += self.config.healthcare_response_rate * (target - self.mortality_multiplier)
        base = self.config.death_base_prob
        self.mortality_rate = 1.0 if base >= 1 else -math.expm1(math.log1p(-base) * self.mortality_multiplier)
        for p in self.population:
            p.healthcare_choice, p.healthcare_premium = "Public", 0.0
            # Private premium is indexed to prices; affordability uses liquid money.
            premium = self.private_premium(p.age) * self.price
            money = self.accounts[p.account]
            gain = self.death_probability(p.age, 0) - self.private_death_probability(p.age, 0)
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
        return (self.private_death_probability(person.age, 0) if person.healthcare_choice == "Private"
                else self.death_probability(person.age, 0))

    def settle_estates(self, dead_ids):
        survivors = [p for p in self.population if p.person_id not in dead_ids]
        for person in [p for p in self.population if p.person_id in dead_ids]:
            # Bonds and real assets are sold to the producer at face/current price,
            # subject to producer liquidity. Unsold assets go to heirs/the state.
            debt = self.debt(person)
            need = max(0, debt - self.accounts[person.account])
            bonds = [b for b in self.bonds if b.holder == person.account]
            for bond in bonds:
                if need <= EPS:
                    break
                sold = self.transfer(PRODUCER, person.account, min(need, bond.principal), "Estate bond liquidation")
                if sold:
                    self.bonds.append(replace(bond, holder=PRODUCER, principal=sold))
                    bond.principal -= sold
                    need -= sold
            sold = self.transfer(PRODUCER, person.account, min(need, person.assets * self.price), "Estate asset liquidation")
            person.assets -= sold / self.price
            self.producer_assets += sold / self.price
            for loan in [x for x in self.loans if x.borrower == person.person_id]:
                interest = self.bank_payment(person.account, loan.arrears, "Estate loan interest")
                loan.arrears -= interest
                principal = self.bank_payment(person.account, loan.principal, "Estate loan principal")
                loan.principal -= principal
                self.flows["Loan interest paid"] += interest
                self.flows["Loan principal repaid"] += principal
                self.flows["Loan defaults"] += loan.principal + loan.arrears
                self.loans.remove(loan)
            heirs = [p for p in survivors if p.parent_id == person.person_id]
            if heirs:
                money = self.accounts[person.account]
                for heir in heirs:
                    self.transfer(person.account, heir.account, money / len(heirs), "Inheritance")
                    heir.assets += person.assets / len(heirs)
                for bond in [b for b in self.bonds if b.holder == person.account]:
                    for heir in heirs:
                        self.bonds.append(replace(bond, holder=heir.account, principal=bond.principal / len(heirs)))
                    self.bonds.remove(bond)
            else:
                self.flows["Estate revenue"] += self.transfer(person.account, GOV, self.accounts[person.account], "Unclaimed estate")
                self.public_assets += person.assets
                # Government-held own bonds are cancelled, not counted as revenue.
                for bond in [b for b in self.bonds if b.holder == person.account]:
                    self.flows["Estate debt cancellation"] += bond.principal
                    self.bonds.remove(bond)
            del self.accounts[person.account]
        self.population = survivors

    def demographics(self):
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
                 "Bond principal repaid", "Bond principal defaults", "Debt service due", "Debt service shortfall", "Wages",
                 "Tax revenue", "Unpaid wealth tax", "Pension shortfall", "Real investment", "Consumption", "Real consumption",
                 "Bank distributions", "Private premiums", "Estate revenue", "Estate debt cancellation", "Deaths",
                 "Observed mortality", "Public healthcare users", "Private healthcare users", "Minimum applied tax rate",
                 "Maximum applied tax rate", "Effective wealth tax rate", "Pension eligible", "UBI per person",
                 "Failed private investments", "Private capital shortfall", "Private capital added",
                 "Opening government money", "Total government spending", "Money balance error",
                 "Base money balance error", "Government balance error")
        self.flows = dict.fromkeys(names, 0.0)
        self.policy_budget = 0.0
        self.budget_allocations = allocate(0, self.shares)
        self.spent = dict.fromkeys(self.budget_allocations, 0.0)
        self.output = self.inflation = self.nominal_demand = self.goods_remaining = 0.0

    def update_policy(self, **changes):
        known = {f.name for f in fields(MonetaryConfig)}
        initial = {"pop_size", "init_wealth", "logistic_capacity", "initial_producer_money", "initial_bank_capital", "budget_mode"}
        if set(changes) - known or set(changes) & initial:
            raise ValueError("Unknown policy or initial condition; initial conditions require a new scenario.")
        candidate = replace(self.config, **changes)
        validate_config(candidate)
        old = self.config
        self.config = candidate
        if candidate.money_cap and self.capped_supply > candidate.money_cap + EPS:
            self.config = old
            raise ValueError("Cap is below existing supply. Existing money cannot be clipped; choose a higher cap.")
        changed = {k: v for k, v in changes.items() if getattr(old, k) != v}
        if changed:
            self.policy_changes.append({"Effective step": self.step_count + 1, "Changes": changed})
        return bool(changed)

    def step(self):
        if not self.population:
            return False
        self.reset_flows()
        opening_money, opening_base = self.broad_money, self.reserves
        opening_gov = self.accounts[GOV]
        self.flows["Opening government money"] = opening_gov
        self.trade_price = self.price
        for p in self.population:
            p.assets *= 1 - self.config.delta
        self.public_assets *= 1 - self.config.delta
        self.producer_assets *= 1 - self.config.delta
        workers = sum(18 <= p.age < self.config.retirement_age for p in self.population)
        self.output = min(self.capacity, workers * self.config.productivity)
        self.goods_remaining = self.output
        self.pay_wages(self.output)
        self.service_loans()
        self.collect_taxes()
        self.fund_government()
        self.prepare_budget()
        self.pay_policies()
        self.invest()
        self.consume()
        value = self.output * self.price
        gap = self.nominal_demand / value - 1 if value > EPS else (1 if self.nominal_demand > EPS else 0)
        self.inflation = float(np.clip(self.config.inflation_response * gap, -0.1, 0.25))
        self.price = max(1e-6, self.price * (1 + self.inflation))
        self.inflation = self.price / self.trade_price - 1
        self.distribute_income()
        self.update_health()
        self.demographics()
        created = self.flows["Money issued"] + self.flows["Loans originated"] + self.flows["Bank bond credit"] + self.flows["Bank distributions"]
        destroyed = self.flows["Loan principal repaid"] + self.flows["Loan interest paid"] + self.flows["Bank bond repayments"]
        self.flows["Money balance error"] = self.broad_money - opening_money - created + destroyed
        self.flows["Base money balance error"] = self.reserves - opening_base - self.flows["Money issued"]
        self.flows["Government balance error"] = self.accounts[GOV] - (opening_gov + self.flows["Tax revenue"] +
            self.flows["Borrowing proceeds"] + self.flows["Money issued"] + self.flows["Estate revenue"] - sum(self.spent.values()))
        self.flows["Total government spending"] = sum(self.spent.values())
        self.step_count += 1
        self.record()
        return True

    def advance(self, steps=1):
        for _ in range(steps):
            if not self.step():
                break

    def balance_sheets(self):
        household_assets = sum(self.accounts[p.account] + p.assets * self.price + self.bond_assets(p) for p in self.population)
        household_debt = sum(self.debt(p) for p in self.population)
        producer_bonds = sum(b.principal for b in self.bonds if b.holder == PRODUCER)
        bank_assets = self.reserves + sum(x.principal + x.arrears for x in self.loans) + sum(b.principal for b in self.bonds if b.holder == BANK)
        rows = [("Households", household_assets, household_debt),
                (GOV, self.accounts[GOV] + self.public_assets * self.price, self.government_debt),
                (PRODUCER, self.accounts[PRODUCER] + producer_bonds + self.producer_assets * self.price, 0), (HEALTH, self.accounts[HEALTH], 0),
                (BANK, bank_assets, self.broad_money), ("Monetary authority", 0, self.reserves)]
        return [{"Sector": name, "Assets": assets, "Liabilities": liabilities, "Net worth": assets - liabilities}
                for name, assets, liabilities in rows]

    def person_rows(self):
        return [{"Person": p.person_id, "Age": p.age, "Parent": p.parent_id,
                 "Money": self.accounts[p.account], "Real productive assets": p.assets,
                 "Bonds": self.bond_assets(p), "Debt": self.debt(p), "Net wealth": self.net_wealth(p),
                 "Real net wealth": self.net_wealth(p) / self.price,
                 "UBI": p.ubi_received, "Pension": p.pension_received, "Healthcare": p.healthcare_choice,
                 "Wages": p.income, "Health preference": p.healthcare_preference,
                 "Private premium": p.healthcare_premium, "Death probability": self.individual_death_probability(p)}
                for p in self.population]

    def record(self):
        wealth = [self.net_wealth(p) for p in self.population]
        # Conventional Gini is not bounded with negative net wealth; report it
        # only for non-negative distributions rather than silently clipping debt.
        gini = gini_coefficient(np.array(wealth)) if all(x >= 0 for x in wealth) else None
        self.history.append({"Step": self.step_count, "Population": len(self.population), "Net wealth": sum(wealth),
            "Real net wealth": sum(wealth) / self.price, "Productive capacity": self.capacity, "Output": self.output,
            "Price level": self.price, "Inflation": self.inflation, "Base money": self.reserves, "Broad money": self.broad_money,
            "Government money": self.accounts[GOV], "Government debt": self.government_debt,
            "Bank equity": self.bank_equity, "Outstanding loans": sum(x.principal + x.arrears for x in self.loans),
            "Gini": gini, "Policy budget": self.policy_budget, "Public mortality": self.mortality_rate,
            "Baseline mortality": self.config.death_base_prob, "Healthcare sector money": self.accounts[HEALTH],
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


def restore_monetary_simulation(previous):
    """Rebind hot-reloaded sessions to current code without resetting their economy.

    Existing tax rates, contracts, random state and history are retained. New
    observations start on the next step, never backfilled into old history.
    """
    if isinstance(previous, MonetarySimulation):
        return previous
    restored = object.__new__(MonetarySimulation)
    restored.__dict__.update(previous.__dict__)
    known = {field.name for field in fields(MonetaryConfig)}
    restored.config = MonetaryConfig(**{k: v for k, v in asdict(previous.config).items() if k in known})
    restored.initial_config = MonetaryConfig(**{k: v for k, v in asdict(previous.initial_config).items() if k in known})
    return restored


COMPARISON_NAMES = ("No credit or printing", "Government bonds", "Individual credit", "Fixed broad money ceiling",
                    "Expandable credit", "Monetary financing")
