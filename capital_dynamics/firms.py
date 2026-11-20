"""Competing goods firms: cash-funded hiring, inventories and innovation.

Capital is operated under cost-free leases from existing capital owners: it is
not copied onto firm balance sheets. Firms own goods inventories and deposits.
All payments use the simulation ledger, including R&D wages and business credit.
"""
from dataclasses import asdict, dataclass
import math
import random

EPS = 1e-9
HOLDING = "Production"


@dataclass
class Firm:
    firm_id: int
    price: float = 1.0
    productivity_factor: float = 1.0
    technology: float = 1.0
    wage: float = 1.0
    inventory: float = 0.0
    expected_sales: float = 0.0
    last_sales: float = 0.0
    last_research: float = 0.0
    last_profit: float = 0.0
    distress: int = 0
    active: bool = True
    employees: int = 0
    output: float = 0.0
    sales: float = 0.0
    units_sold: float = 0.0
    demand: float = 0.0
    payroll: float = 0.0
    research: float = 0.0
    energy_used: float = 0.0
    energy_cost: float = 0.0
    interest: float = 0.0
    profit: float = 0.0
    last_productivity: float = 0.0

    @property
    def account(self):
        return f"Firm {self.firm_id}"


@dataclass
class FirmLoan:
    borrower: int
    principal: float
    installment: float
    rate: float
    issued: int
    maturity: int
    arrears: float = 0.0
    missed: int = 0


class FirmMarket:
    def __init__(self, sim):
        self.sim = sim
        self.rng = random.Random(sim.seed + 3)
        self.firms = []
        self.events = []
        self.started = False
        self.previous_unemployment = .06
        self.previous_inflation = 0.0
        self.price_weights = {}
        self.opening_prices = {}
        for _ in range(sim.config.firm_count):
            self.add_firm()

    @property
    def active(self):
        return [f for f in self.firms if f.active]

    @property
    def inventory(self):
        return sum(f.inventory for f in self.firms)

    @property
    def inventory_value(self):
        return sum(f.inventory * f.price for f in self.firms)

    def add_firm(self):
        sim, cfg = self.sim, self.sim.config
        spread = cfg.firm_productivity_dispersion
        factor = self.rng.uniform(1 - spread, 1 + spread)
        firm = Firm(len(self.firms), price=sim.price if hasattr(sim, "price") else 1.0,
                    productivity_factor=factor, technology=1.0,
                    wage=cfg.productivity * cfg.wage_fraction,
                    last_productivity=cfg.productivity * factor)
        self.firms.append(firm)
        sim.accounts[firm.account] = 0.0
        return firm

    def event(self, kind, firm, **details):
        self.events.append({"Year": self.sim.step_count + 1, "Event": kind,
                            "Firm": firm.firm_id, **details})
        if len(self.events) > 1000:
            del self.events[0]

    def innovate(self):
        """Last year's paid research affects this year's innovation/adoption."""
        sim, cfg = self.sim, self.sim.config
        for firm in self.active:
            intensity = firm.last_research / max(firm.last_sales, cfg.initial_money_per_person, EPS)
            probability = min(1, cfg.research_effectiveness * intensity)
            if intensity > 0 and self.rng.random() < probability:
                gain = self.rng.uniform(cfg.technology_gain_min, cfg.technology_gain_max)
                sim.technology_index *= 1 + gain
                firm.technology = sim.technology_index
                sim.technology_breakthroughs += 1
                sim.technology_events.append({"Year": sim.step_count + 1, "Firm": firm.firm_id,
                    "Source": "Firm research", "Technology productivity gain": gain})
                sim.flows["Research breakthroughs"] += 1
            else:
                # Trend learning does not require buying an innovation.
                firm.technology = min(sim.technology_index, firm.technology * (1 + cfg.productivity_growth))
            speed = min(1, cfg.technology_adoption_rate + cfg.research_adoption_effectiveness * intensity)
            firm.technology += speed * max(0, sim.technology_index - firm.technology)

    def begin_year(self):
        sim, cfg = self.sim, self.sim.config
        for f in self.firms:
            f.output = f.sales = f.units_sold = f.demand = f.payroll = f.research = f.interest = f.profit = 0.0
            f.energy_used = f.energy_cost = 0.0
            f.employees = 0
        self.price_weights = {}
        self.opening_prices = {}
        opening_inventory = self.inventory
        sim.flows["Opening inventories"] = opening_inventory
        spoiled = opening_inventory * cfg.inventory_spoilage
        for f in self.active:
            f.inventory *= 1 - cfg.inventory_spoilage
        sim.flows["Inventory spoilage"] = spoiled
        workers = [p for p in sim.population if 18 <= p.age < cfg.retirement_age and not p.fulltime_student]
        goods_workers = [p for p in workers if not p.education_teacher]
        for p in sim.population:
            if not p.education_teacher:
                p.employer = None
                p.income = 0.0
        if not self.started:
            self.started = True
            # Keep a dealer reserve for collateral trading; startup is a transfer,
            # never an extra endowment on top of initial producer money.
            capital = sim.accounts[HOLDING] * .8
            for f in self.active:
                sim.transfer(HOLDING, f.account, capital / len(self.active), "Firm startup capital")
                f.expected_sales = min(sim.capacity, len(goods_workers) * cfg.productivity) * cfg.initial_demand_fraction / len(self.active)
        self.enter(goods_workers)
        active = self.active
        sim.flows["Wages"] = sim.flows["Education salaries"]
        if not active:
            sim.energy.allocate({})
            sim.output = 0.0
            self.record_employment(workers)
            return
        # Capacity allocation responds to expected sales, with a small equal
        # access component. Leases confer use rights, not ownership of capital.
        total_expected = sum(f.expected_sales for f in active)
        self.price_weights = {f.firm_id: (.2 / len(active) + .8 * f.expected_sales / total_expected)
                              if total_expected > EPS else 1 / len(active) for f in active}
        self.opening_prices = {f.firm_id: f.price for f in active}
        plans = {f.firm_id: min(sim.capacity * self.price_weights[f.firm_id],
                               max(0, f.expected_sales * (1 + cfg.inventory_target) - f.inventory))
                 for f in active}
        sim.energy.allocate(plans)
        # Wages respond to lagged inflation, adopted productivity and labor scarcity.
        for f in active:
            productivity = cfg.productivity * f.productivity_factor * f.technology
            productivity_growth = productivity / f.last_productivity - 1 if f.last_productivity > EPS else 0.0
            growth = (cfg.wage_inflation_indexation * self.previous_inflation
                      + cfg.wage_productivity_share * productivity_growth
                      + cfg.wage_bargaining_strength * (cfg.target_unemployment - self.previous_unemployment))
            f.wage *= 1 + max(-.1, min(.2, growth))
            f.last_productivity = productivity
        # Random tie breaking, then higher wage bids hire first.
        self.rng.shuffle(workers)
        available = [p for p in workers if not p.education_teacher]
        # Skills improve selection/productivity but also command higher wages.
        available.sort(key=lambda p: p.skill, reverse=True)
        ordered = list(active)
        self.rng.shuffle(ordered)
        ordered.sort(key=lambda f: f.wage, reverse=True)
        for f in ordered:
            productivity = cfg.productivity * f.productivity_factor * f.technology
            planned = sim.energy.output_limit(f, plans[f.firm_id])
            energy_unit_cost = cfg.energy_intensity * sim.energy.price
            proposed = []
            potential = 0.0
            for person in available:
                if potential + EPS >= planned or productivity <= EPS:
                    break
                proposed.append(person)
                potential += productivity * sim.education.worker_multiplier(person, f)
            if not proposed:
                continue
            wage_for = lambda p: f.wage * (1 + cfg.skill_wage_premium * (p.skill - 1))
            need = max(0, sum(wage_for(p) for p in proposed) + min(planned, potential) * energy_unit_cost - sim.accounts[f.account])
            sim.originate_firm_loan(f, need)
            hired, potential = [], 0.0
            cash = sim.accounts[f.account]
            for p in available:
                if potential + EPS >= planned:
                    break
                wage = wage_for(p)
                extra_output = min(planned, potential + productivity * sim.education.worker_multiplier(p, f)) - min(planned, potential)
                required = wage + extra_output * energy_unit_cost
                if cash + EPS < required:
                    continue
                hired.append(p)
                cash = max(0, cash - required)
                potential += productivity * sim.education.worker_multiplier(p, f)
            hired_ids = {p.person_id for p in hired}
            available = [p for p in available if p.person_id not in hired_ids]
            f.employees = len(hired)
            for p in hired:
                p.employer = f.firm_id
                paid = sim.transfer(f.account, p.account, wage_for(p), "Firm wages")
                p.income += paid
                p.income_received += paid
                f.payroll += paid
            f.output = min(planned, potential)
            if cfg.energy_intensity > 0:
                delivered = sim.energy.purchase(f, f.output * cfg.energy_intensity)
                f.output = min(f.output, delivered / cfg.energy_intensity)
            f.inventory += f.output
            # R&D buys employee services rather than creating a fictitious asset.
            budget = sim.accounts[f.account] * cfg.research_spending_fraction if hired else 0.0
            for p in hired:
                paid = sim.transfer(f.account, p.account, budget / len(hired), "Research wages")
                p.income += paid
                p.income_received += paid
                f.research += paid
        sim.output = sum(f.output for f in active)
        sim.flows["Wages"] = sum(f.payroll + f.research for f in active) + sim.flows["Education salaries"]
        sim.flows["Research spending"] = sum(f.research for f in active)
        self.record_employment(workers)

    def enter(self, workers):
        sim, cfg = self.sim, self.sim.config
        if len(self.active) >= cfg.firm_count or not workers:
            return
        available = sum(sim.accounts[p.account] for p in workers) * cfg.firm_entry_fraction
        minimum = cfg.productivity * cfg.wage_fraction
        if available < minimum or available <= EPS:
            return
        f = self.add_firm()
        f.price = sim.price
        # Entrants start behind the frontier, catching up through adoption.
        f.technology = max(1, sim.technology_index * .8)
        for p in workers:
            sim.transfer(p.account, f.account, sim.accounts[p.account] * cfg.firm_entry_fraction, "New firm startup contribution")
        f.expected_sales = max(1, len(workers) / cfg.firm_count) * cfg.productivity * cfg.initial_demand_fraction
        sim.flows["Firm entries"] += 1
        self.event("Entry", f, Funding=sim.accounts[f.account])

    def record_employment(self, workers):
        sim = self.sim
        employed = sum(p.employer is not None for p in workers)
        sim.flows["Labor force"] = len(workers)
        sim.flows["Employed"] = employed
        sim.flows["Unemployed"] = len(workers) - employed
        sim.flows["Unemployment rate"] = (len(workers) - employed) / len(workers) if workers else None
        self.previous_unemployment = sim.flows["Unemployment rate"] if workers else 0.0

    def buy(self, offers, purpose):
        """Same basket for all buyers; cheap firms attract more nominal demand.

        Budgets are reallocated when a seller stocks out. Cash and actual units
        are booked separately; purchases at different prices cannot be divided
        by the aggregate price index to obtain physical goods.
        """
        sim, cfg = self.sim, self.sim.config
        offers = {account: min(max(0, amount), sim.accounts[account]) for account, amount in offers.items()}
        budget = sum(offers.values())
        if budget <= EPS:
            return {account: (0.0, 0.0) for account in offers}
        active = self.active
        # Log demand even for sellers that stocked out or did not produce.
        logs = {f.firm_id: -cfg.price_competition * math.log(max(f.price, 1e-6)) for f in active}
        largest = max(logs.values(), default=0.0)
        weights = {key: math.exp(max(-700, value - largest)) for key, value in logs.items()}
        total_weight = sum(weights.values())
        for f in active:
            f.demand += budget * weights[f.firm_id] / total_weight / f.price
        remaining = budget
        spending = {f.firm_id: 0.0 for f in active}
        sellers = [f for f in active if f.inventory > EPS]
        while sellers and remaining > EPS:
            total_weight = sum(weights[f.firm_id] for f in sellers)
            allocated = 0.0
            for f in sellers:
                amount = min(remaining * weights[f.firm_id] / total_weight,
                             f.inventory * f.price - spending[f.firm_id])
                spending[f.firm_id] += max(0, amount)
                allocated += max(0, amount)
            remaining = max(0, remaining - allocated)
            sellers = [f for f in sellers if f.inventory * f.price - spending[f.firm_id] > EPS]
            if allocated <= EPS:
                break
        units = sum(spending[f.firm_id] / f.price for f in active)
        paid_total = sum(spending.values())
        for f in active:
            amount = spending[f.firm_id]
            for account, offer in offers.items():
                sim.transfer(account, f.account, amount * offer / budget, purpose)
            sold = amount / f.price
            f.inventory = max(0, f.inventory - sold)
            f.sales += amount
            f.units_sold += sold
        return {account: (paid_total * offer / budget, units * offer / budget) for account, offer in offers.items()}

    def close_year(self):
        sim, cfg = self.sim, self.sim.config
        sim.service_firm_loans()
        for f in self.firms:
            f.profit = f.sales - f.payroll - f.research - f.interest - f.energy_cost
        for f in list(self.active):
            f.expected_sales += cfg.demand_adaptation * (f.demand - f.expected_sales)
            f.last_sales, f.last_research = f.sales, f.research
            f.last_profit = f.profit
            f.distress = f.distress + 1 if f.profit < -EPS and sim.accounts[f.account] < max(f.wage, EPS) else 0
            if f.distress >= cfg.firm_failure_years:
                self.fail(f)
        # Prices reflect both excess supply and wage costs, bounded each year.
        for f in self.active:
            supply = f.output + max(0, f.inventory + f.units_sold - f.output)
            gap = f.demand / supply - 1 if supply > EPS else (1 if f.demand > EPS else 0)
            demand_price = f.price * (1 + max(-.1, min(.25, cfg.inflation_response * gap)))
            unit_cost = (f.payroll + f.research + f.energy_cost) / f.output if f.output > EPS else 0
            target = max(demand_price, unit_cost * (1 + cfg.firm_markup))
            f.price = max(1e-6, min(f.price * 1.25, max(f.price * .9, target)))
        # Fixed opening-year weights avoid spurious inflation when firms'
        # sales shares change. Failed firms retain their final quote this year.
        price_ratio = sum(self.price_weights.get(f.firm_id, 0) * f.price / self.opening_prices[f.firm_id]
                          for f in self.firms if f.firm_id in self.opening_prices)
        if self.price_weights:
            sim.price = max(1e-6, sim.trade_price * price_ratio)
        sim.inflation = sim.price / sim.trade_price - 1
        self.previous_inflation = sim.inflation
        assets = sum(p.assets for p in sim.population)
        for f in self.active:
            dividend = min(sim.accounts[f.account], max(0, f.profit) * cfg.producer_dividend_fraction)
            if any(x.borrower == f.firm_id and (x.missed or x.arrears > EPS) for x in sim.firm_loans):
                dividend = 0.0
            for p in sim.population:
                if assets:
                    p.income_received += sim.transfer(f.account, p.account, dividend * p.assets / assets, "Firm dividends")
        sim.flows["Firm profits"] = sum(f.profit for f in self.firms)
        sim.flows["Inventory balance error"] = (self.inventory - (sim.flows["Opening inventories"]
            + sim.output - sim.flows["Real consumption"] - sim.flows["Real investment"]
            - sim.flows["Real education goods"]
            - sim.flows["Inventory spoilage"] - sim.flows["Inventory scrapped"]))

    def fail(self, firm):
        """Liquidate inventory to solvent rivals, resolve debt, then close.

        Unpurchased inventory is explicitly scrapped; leased capital survives.
        Residual cash goes to the production holding sector, not into thin air.
        """
        sim = self.sim
        if not firm.active:
            return
        for rival in self.active:
            if rival is firm or firm.inventory <= EPS:
                continue
            price = firm.price * (1 - sim.config.collateral_recovery_haircut)
            if price <= EPS:
                break
            bought = min(firm.inventory, sim.accounts[rival.account] * .25 / price)
            paid = sim.transfer(rival.account, firm.account, bought * price, "Failed firm inventory liquidation")
            rival.inventory += paid / price
            firm.inventory -= paid / price
        sim.resolve_firm_debt(firm)
        sim.flows["Inventory scrapped"] += firm.inventory
        firm.inventory = 0.0
        sim.transfer(firm.account, HOLDING, sim.accounts[firm.account], "Failed firm residual cash")
        firm.active = False
        firm.employees = 0
        sim.flows["Firm failures"] += 1
        self.event("Failure", firm)

    def rows(self):
        sim = self.sim
        shares = sum(f.sales for f in self.active)
        return [{**asdict(f), "Money": sim.accounts[f.account],
                 "Debt": sum(x.principal + x.arrears for x in sim.firm_loans if x.borrower == f.firm_id),
                 "Worker productivity": sim.config.productivity * f.productivity_factor * f.technology,
                 "Market share": f.sales / shares if shares > EPS else None}
                for f in self.firms]
