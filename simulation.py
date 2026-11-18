"""Stateful economy model shared by batch and live simulations."""
from collections import deque
from dataclasses import dataclass, replace, fields
import random
import math
import numpy as np

@dataclass
class Individual:
    wealth: float
    age: int = 0
    parent_id: int | None = None
    person_id: int = 0
    healthcare_preference: float = 1.0
    healthcare_choice: str = "Public"
    healthcare_premium: float = 0.0
    pension_received: float = 0.0
    ubi_received: float = 0.0

@dataclass(frozen=True)
class SimulationConfig:
    pop_size: int = 300
    init_wealth: float = 1.0
    base_growth: float = 0.04
    gain_prob: float = 0.25
    gain_fraction: float = 0.15
    gain_growth: float = 0.1
    investment_risk: float = 0.15
    failed_investment_loss: float = 0.1
    loss_prob: float = 0.15
    loss_fraction: float = 0.1
    loss_rate: float = 0.1
    tick_count: int = 10
    logistic_capacity: float = 1000.0
    alpha: float = 0.0
    tau_base: float = 0.005
    tau_max: float = 0.04
    tau_gamma: float = 2.0
    direct_redistribution_fraction: float = 0.25
    investment_probability: float = 0.2
    delta: float = 0.0005
    beta: float = 0.8
    base_eff: float = 0.3
    shock_scale: float = 0.2
    max_neg_shock: float = 0.2
    psi: float = 2.0
    max_age: int = 100
    death_base_prob: float = 0.006
    birth_prob_max: float = 0.03
    healthcare_spending_fraction: float = 0.25
    healthcare_effectiveness: float = 10.0
    healthcare_response_rate: float = 0.1
    mortality_floor_fraction: float = 0.2
    aging_risk_start: int = 50
    aging_risk_rate: float = 0.001
    retirement_age: int = 65
    pension_budget_fraction: float = 0.2
    pension_per_person: float = 0.02
    healthcare_choice_mode: str = "Adaptive"
    private_healthcare_premium: float = 0.008
    private_healthcare_age_loading: float = 1.0
    private_healthcare_mortality_factor: float = 0.5
    private_healthcare_max_wealth_fraction: float = 0.2
    healthcare_choice_priority: float = 4.0


def gini_coefficient(wealths):
    x = np.sort(wealths)
    if not len(x) or x.sum() <= 0:
        return 0.0
    return float((len(x) + 1 - 2 * np.cumsum(x).sum() / x.sum()) / len(x))


def age_dependent_birth_prob(age, birth_prob_max):
    if age < 14 or age > 68:
        return 0.0
    return birth_prob_max * np.exp(-0.5 * ((age - 30) / 20) ** 2)


def relative_wealth(wealths):
    values = np.asarray(wealths, dtype=float)
    if not len(values):
        return values
    return np.clip((values - values.min()) / max(float(values.max() - values.min()), 0.001), 0, 1)


def tax_rates_at_relative_wealth(positions, config):
    positions = np.clip(np.asarray(positions, dtype=float), 0, 1)
    return config.tau_base + (config.tau_max - config.tau_base) * positions ** config.tau_gamma


def wealth_tax_rates(wealths, config):
    return tax_rates_at_relative_wealth(relative_wealth(wealths), config)


class Simulation:
    def __init__(self, config=None, seed=42, history_limit=10000):
        self.config = config or SimulationConfig()
        self.initial_config = self.config
        self.policy_changes = deque(maxlen=1000)
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        ages = random.Random(seed)
        self.population = [Individual(self.config.init_wealth, ages.randint(1, 50), person_id=i)
                           for i in range(self.config.pop_size)]
        preferences = random.Random(seed + 1)
        for person in self.population:
            person.healthcare_preference = preferences.uniform(0.5, 1.5)
        self.next_id = self.config.pop_size
        self.government_budget = 0.0
        self.logistic_capacity = self.config.logistic_capacity
        self.step_count = 0
        self.failed_investments = 0
        self.investment_losses = 0.0
        self.investment_gains = 0.0
        self.healthcare_spending = 0.0
        self.mortality_multiplier = 1.0
        self.mortality_rate = self.config.death_base_prob
        self.deaths = 0
        self.observed_mortality = 0.0
        self.private_healthcare_balance = 0.0
        self.reset_accounts()
        self.history = deque(maxlen=history_limit)
        self.record()

    def record(self):
        wealths = np.array([p.wealth for p in self.population])
        self.history.append({
            "Step": self.step_count,
            "Population": len(self.population),
            "Total wealth": float(wealths.sum()),
            "Government budget": float(self.government_budget),
            "Gini coefficient": gini_coefficient(wealths),
            "Wealth capacity": float(self.logistic_capacity),
            "Failed private investments": self.failed_investments,
            "Private investment losses": self.investment_losses,
            "Private investment gains": self.investment_gains,
            "Baseline mortality": self.config.death_base_prob,
            "Mortality rate": self.mortality_rate,
            "Healthcare spending": self.healthcare_spending,
            "Deaths": self.deaths,
            "Observed mortality": self.observed_mortality,
            "UBI per person": self.ubi_payment_per_person,
            "UBI recipients": self.ubi_recipients,
            "Minimum applied tax rate": self.minimum_applied_tax_rate,
            "Maximum applied tax rate": self.maximum_applied_tax_rate,
            "Effective wealth tax rate": self.effective_tax_rate,
            **self.government_accounts(),
            "Pension eligible": self.pension_eligible,
            "Pension shortfall": self.pension_shortfall,
            "Public healthcare users": self.public_healthcare_users,
            "Private healthcare users": self.private_healthcare_users,
            "Private healthcare premiums": self.private_healthcare_revenue,
            "Private healthcare sector balance": self.private_healthcare_balance,
            "Total private sector wealth": float(wealths.sum()) + self.private_healthcare_balance,
        })

    def update_policy(self, **changes):
        """Apply a policy atomically from the next step without altering economy state."""
        initial_only = {"pop_size", "init_wealth", "logistic_capacity"}
        known = {field.name for field in fields(SimulationConfig)}
        if set(changes) - known:
            raise ValueError("Unknown policy parameter.")
        if set(changes) & initial_only:
            raise ValueError("Starting population, initial wealth and initial capacity require a new scenario.")
        candidate = replace(self.config, **changes)
        fraction_fields = {
            "gain_prob", "gain_fraction", "investment_risk", "failed_investment_loss",
            "loss_prob", "loss_fraction", "loss_rate", "tau_base", "tau_max",
            "direct_redistribution_fraction", "investment_probability", "delta",
            "death_base_prob", "birth_prob_max", "healthcare_spending_fraction",
            "healthcare_response_rate", "mortality_floor_fraction", "pension_budget_fraction",
            "private_healthcare_mortality_factor", "private_healthcare_max_wealth_fraction",
        }
        for name, value in changes.items():
            if name == "healthcare_choice_mode":
                if value not in {"Adaptive", "Public only", "Private if affordable"}:
                    raise ValueError("Choose a valid healthcare strategy.")
                continue
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("Policy values must be finite numbers.")
            if name in fraction_fields and not 0 <= value <= 1:
                raise ValueError("Rates and budget fractions must be between zero and one.")
            if name != "alpha" and value < 0:
                raise ValueError("Policy values must be non-negative.")
            if name in {"max_age", "retirement_age", "aging_risk_start", "tick_count"} and not isinstance(value, int):
                raise ValueError("Age and group settings must be whole numbers.")
        if candidate.tau_base > candidate.tau_max:
            raise ValueError("The maximum tax rate must be at least the minimum tax rate.")
        if candidate.max_age < 1 or candidate.tau_gamma <= 0:
            raise ValueError("Maximum age and tax progressivity must be positive.")
        changed = {name: value for name, value in changes.items() if value != getattr(self.config, name)}
        if not changed:
            return False
        self.policy_changes.append({"Effective step": self.step_count + 1, "Changes": changed})
        self.config = candidate
        return True

    def reset_accounts(self):
        """Reset flows for one step; retained balances carry over."""
        self.opening_government_budget = self.government_budget
        self.tax_revenue = 0.0
        self.estate_revenue = 0.0
        self.ubi_spending = 0.0
        self.ubi_payment_per_person = 0.0
        self.ubi_recipients = 0
        self.minimum_applied_tax_rate = 0.0
        self.maximum_applied_tax_rate = 0.0
        self.effective_tax_rate = 0.0
        self.pension_spending = 0.0
        self.pension_eligible = 0
        self.pension_shortfall = 0.0
        self.capacity_investment = 0.0
        self.private_healthcare_revenue = 0.0
        self.private_healthcare_users = 0
        self.public_healthcare_users = len(self.population)

    def government_accounts(self):
        spending = self.ubi_spending + self.pension_spending + self.healthcare_spending + self.capacity_investment
        expected = self.opening_government_budget + self.tax_revenue + self.estate_revenue - spending
        return {
            "Opening government budget": self.opening_government_budget,
            "Tax revenue": self.tax_revenue,
            "Estate revenue": self.estate_revenue,
            "UBI transfers": self.ubi_spending,
            "Pension spending": self.pension_spending,
            "Capacity investment": self.capacity_investment,
            "Total government spending": spending,
            "Government balance error": float(self.government_budget - expected),
        }

    def pay_ubi(self):
        """Pay every current resident the same amount from existing government funds."""
        self.ubi_recipients = len(self.population)
        self.ubi_spending = self.government_budget * self.config.direct_redistribution_fraction if self.population else 0.0
        self.ubi_payment_per_person = self.ubi_spending / self.ubi_recipients if self.ubi_recipients else 0.0
        self.government_budget -= self.ubi_spending
        for person in self.population:
            person.ubi_received = self.ubi_payment_per_person
            person.wealth += person.ubi_received

    def pay_pensions(self):
        retirees = [p for p in self.population if p.age >= self.config.retirement_age]
        self.pension_eligible = len(retirees)
        requested = len(retirees) * self.config.pension_per_person * self.config.init_wealth
        self.pension_spending = min(requested, self.government_budget * self.config.pension_budget_fraction)
        self.pension_shortfall = requested - self.pension_spending
        self.government_budget -= self.pension_spending
        payment = self.pension_spending / len(retirees) if retirees else 0.0
        for person in self.population:
            person.pension_received = payment if person.age >= self.config.retirement_age else 0.0
            person.wealth += person.pension_received

    def private_premium(self, age):
        return self.config.init_wealth * self.config.private_healthcare_premium * (
            1 + self.config.private_healthcare_age_loading * age / max(self.config.max_age, 1)
        )

    def private_death_probability(self, age, wealth):
        return self.death_probability(age, wealth, funded=False,
                                      risk_factor=self.config.private_healthcare_mortality_factor)

    def choose_healthcare(self):
        """People compare health gains with affordability and the cost to their wealth."""
        self.private_healthcare_users = 0
        self.public_healthcare_users = 0
        self.private_healthcare_revenue = 0.0
        for person in self.population:
            person.healthcare_choice = "Public"
            person.healthcare_premium = 0.0
            premium = self.private_premium(person.age)
            affordable = premium <= person.wealth * self.config.private_healthcare_max_wealth_fraction
            public_risk = self.death_probability(person.age, person.wealth)
            private_risk = self.private_death_probability(person.age, max(person.wealth - premium, 0))
            cost_share = premium / max(person.wealth, 1e-9)
            health_value = (public_risk - private_risk) * self.config.healthcare_choice_priority * person.healthcare_preference
            wants_private = self.config.healthcare_choice_mode == "Private if affordable" or (
                self.config.healthcare_choice_mode == "Adaptive" and health_value > cost_share
            )
            if affordable and wants_private:
                person.wealth -= premium
                person.healthcare_choice = "Private"
                person.healthcare_premium = premium
                self.private_healthcare_revenue += premium
                self.private_healthcare_users += 1
            else:
                self.public_healthcare_users += 1
        # Fees remain in the private economy as provider assets, rather than disappearing.
        self.private_healthcare_balance += self.private_healthcare_revenue

    def individual_death_probability(self, person):
        if person.healthcare_choice == "Private":
            return self.private_death_probability(person.age, person.wealth)
        return self.death_probability(person.age, person.wealth)

    def update_healthcare(self):
        """Spend remaining public funds and gradually adjust mortality protection."""
        self.healthcare_spending = self.government_budget * self.config.healthcare_spending_fraction
        self.government_budget -= self.healthcare_spending
        per_person = self.healthcare_spending / max(len(self.population), 1)
        # Scale spending relative to the scenario's initial wealth units.
        funding = per_person / max(self.config.init_wealth, 1e-9)
        target = self.config.mortality_floor_fraction + (1 - self.config.mortality_floor_fraction) / (
            1 + self.config.healthcare_effectiveness * funding
        )
        self.mortality_multiplier += self.config.healthcare_response_rate * (target - self.mortality_multiplier)
        self.mortality_rate = self.config.death_base_prob * self.mortality_multiplier

    def death_probability(self, age, wealth, funded=True, risk_factor=None):
        """Age raises risk; healthcare reduces baseline and age-related risks."""
        if age >= self.config.max_age:
            return 1.0
        aging = self.config.aging_risk_rate * max(0, age - self.config.aging_risk_start) / (1 + wealth)
        protection = (self.mortality_multiplier if funded else 1.0) if risk_factor is None else risk_factor
        return float(np.clip((self.config.death_base_prob + aging) * protection, 0, 1))

    def step(self):
        if not self.population:
            return False
        self.reset_accounts()
        self.failed_investments = 0
        self.investment_losses = 0.0
        self.investment_gains = 0.0
        for person in self.population:
            person.age += 1
        wealths = np.array([p.wealth for p in self.population])
        total_wealth = wealths.sum()
        individual_factor = 1 / np.maximum(1 + self.config.alpha * wealths, 0.01)
        global_factor = max(1 - total_wealth / self.logistic_capacity, 0)
        total_growth_factor = self.config.base_growth * individual_factor * global_factor
        for i, person in enumerate(self.population):
            person.wealth *= 1 + total_growth_factor[i]
        if self.rng.rand() < self.config.gain_prob:
            probs = (wealths + 1e-12) / (wealths + 1e-12).sum()
            lucky_idx = self.rng.choice(len(self.population), size=int(self.config.gain_fraction * len(self.population)), replace=False, p=probs)
            for i in lucky_idx:
                person = self.population[i]
                # Each selected opportunity independently succeeds or fails.
                # Failure can destroy wealth even when capacity limits growth.
                if self.config.investment_risk > 0 and self.rng.rand() < self.config.investment_risk:
                    loss = person.wealth * self.config.failed_investment_loss
                    person.wealth -= loss
                    self.failed_investments += 1
                    self.investment_losses += float(loss)
                else:
                    gain = person.wealth * self.config.gain_growth * global_factor
                    person.wealth += gain
                    self.investment_gains += float(gain)
        if self.rng.rand() < self.config.loss_prob:
            probs = 1 / (wealths + 1e-06)
            probs /= probs.sum()
            unlucky_idx = self.rng.choice(len(self.population), size=int(self.config.loss_fraction * len(self.population)), replace=False, p=probs)
            loss_percent = self.rng.uniform(0, self.config.loss_rate * global_factor, size=len(unlucky_idx))
            loss_percent = np.clip(loss_percent, 0, 0.99)
            for i, lp in zip(unlucky_idx, loss_percent):
                self.population[i].wealth *= 1 - float(lp)
        wealths = np.array([p.wealth for p in self.population])
        tax_rates = wealth_tax_rates(wealths, self.config)
        taxes = tax_rates * wealths
        for i, person in enumerate(self.population):
            person.wealth -= taxes[i]
        self.minimum_applied_tax_rate = float(tax_rates.min())
        self.maximum_applied_tax_rate = float(tax_rates.max())
        self.tax_revenue = float(taxes.sum())
        self.effective_tax_rate = self.tax_revenue / float(wealths.sum()) if wealths.sum() else 0.0
        self.government_budget += self.tax_revenue
        self.pay_ubi()
        self.pay_pensions()
        self.update_healthcare()
        self.choose_healthcare()
        if self.rng.rand() < self.config.investment_probability and self.government_budget > 1:
            investment = self.rng.rand() * self.government_budget
            invest_ratio = investment / (self.government_budget + 1e-09)
            p_success = 1 / (1 + np.exp(-self.config.psi * (invest_ratio - 0.5)))
            eff_core = self.config.base_eff + 0.8 * invest_ratio
            shock = self.config.shock_scale * (2 * self.rng.rand() - 1)
            efficiency = max(0.0, eff_core + shock)
            capacity_gain = efficiency * investment ** self.config.beta
            if self.rng.rand() < p_success:
                self.logistic_capacity += capacity_gain
            else:
                self.logistic_capacity = max(1.0, self.logistic_capacity - self.config.max_neg_shock * capacity_gain)
            self.government_budget -= investment
            self.capacity_investment = float(investment)
        self.logistic_capacity = max(1.0, (1 - self.config.delta) * self.logistic_capacity)
        new_population = []
        self.deaths = 0
        population_before_deaths = len(self.population)
        for idx, person in enumerate(self.population):
            death_prob_age = self.individual_death_probability(person)
            if self.rng.rand() < death_prob_age:
                self.deaths += 1
                children = [c for c in self.population if c.parent_id == person.person_id]
                if children:
                    share = person.wealth / len(children)
                    for child in children:
                        child.wealth += share
                else:
                    self.government_budget += person.wealth
                    self.estate_revenue += person.wealth
            else:
                new_population.append(person)
        self.observed_mortality = self.deaths / population_before_deaths
        self.population = new_population
        newborns = []
        for idx, person in enumerate(self.population):
            prob = age_dependent_birth_prob(person.age, self.config.birth_prob_max)
            if self.rng.rand() < prob:
                inherited_wealth = person.wealth * 0.5
                person.wealth *= 0.5
                child = Individual(wealth=inherited_wealth, age=0, parent_id=person.person_id, person_id=self.next_id,
                                   healthcare_preference=float(self.rng.uniform(0.5, 1.5)))
                self.next_id += 1
                newborns.append(child)
        self.population.extend(newborns)
        self.step_count += 1
        self.record()
        return True

    def advance(self, steps=1):
        for _ in range(steps):
            if not self.step():
                break

    def result(self):
        keys = [key for key in self.history[0] if key != "Step"]
        return {
            "history": {key: [row[key] for row in self.history] for key in keys},
            "wealth": [p.wealth for p in self.population],
            "ages": [p.age for p in self.population],
        }


def simulate(steps=100, seed=42, **parameters):
    simulation = Simulation(SimulationConfig(**parameters), seed=seed, history_limit=None)
    simulation.advance(steps)
    return simulation.result()


def restore_simulation(previous):
    """Upgrade a saved session without restarting its economy or random sequence."""
    required = ("policy_changes", "initial_config", "private_healthcare_balance", "ubi_payment_per_person")
    if isinstance(previous, Simulation) and all(hasattr(previous, name) for name in required):
        return previous
    from dataclasses import asdict
    config = SimulationConfig(**asdict(previous.config))
    restored = Simulation(config, seed=previous.seed)
    history_defaults = restored.history[0].copy()
    restored.__dict__.update(previous.__dict__)
    restored.config = config
    restored.initial_config = SimulationConfig(**asdict(getattr(previous, "initial_config", config)))
    if not hasattr(restored, "policy_changes"):
        restored.policy_changes = deque(maxlen=1000)
    if "udb_spending" in previous.__dict__ and "ubi_spending" not in previous.__dict__:
        restored.ubi_spending = previous.udb_spending
    elif "welfare_spending" in previous.__dict__ and "ubi_spending" not in previous.__dict__:
        restored.ubi_spending = previous.welfare_spending
    if "udb_payment_per_person" in previous.__dict__ and "ubi_payment_per_person" not in previous.__dict__:
        restored.ubi_payment_per_person = previous.udb_payment_per_person
    if "udb_recipients" in previous.__dict__ and "ubi_recipients" not in previous.__dict__:
        restored.ubi_recipients = previous.udb_recipients
    for row in restored.history:
        if "UBI transfers" not in row:
            if "UDB transfers" in row:
                row["UBI transfers"] = row.pop("UDB transfers")
            elif "Welfare transfers" in row:
                row["UBI transfers"] = row.pop("Welfare transfers")
        if "UBI per person" not in row and "UDB per person" in row:
            row["UBI per person"] = row.pop("UDB per person")
        if "UBI recipients" not in row and "UDB recipients" in row:
            row["UBI recipients"] = row.pop("UDB recipients")
        for key, value in history_defaults.items():
            row.setdefault(key, value)
    for person in restored.population:
        if hasattr(person, "udb_received") and not hasattr(person, "ubi_received"):
            person.ubi_received = person.udb_received
        for name, value in {"healthcare_preference": 1.0, "healthcare_choice": "Public",
                            "healthcare_premium": 0.0, "pension_received": 0.0, "ubi_received": 0.0}.items():
            if not hasattr(person, name):
                setattr(person, name, value)
    return restored
