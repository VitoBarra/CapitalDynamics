"""A domestic primary-energy flow, paid for by goods firms.

Supply is an exogenous annual resource flow, not duplicated productive capital.
Energy is neither stored nor part of goods inventories. Provider receipts stay
in deposits or are recycled as household resource income; none is new money.
"""
from collections import deque
import math
import random

ENERGY = "Energy"
EPS = 1e-9


class EnergySystem:
    def __init__(self, sim):
        self.sim = sim
        self.rng = random.Random(sim.seed + 5)
        self.events = deque(maxlen=1000)
        self.supply_index = 1.0
        self.price = sim.config.energy_base_price
        self.available = 0.0
        self.used = 0.0
        self.quotas = {}
        self.shock_remaining = 0
        self.shock_pending = False

    def allocate(self, plans):
        """Reserve supply pro rata before recruiting; unused quotas are curtailed."""
        sim, cfg = self.sim, self.sim.config
        if any(not math.isfinite(value) or value < 0 for value in plans.values()):
            raise ValueError("Energy production plans must be finite and non-negative.")
        self.supply_index *= 1 + cfg.energy_supply_growth
        source = None
        if self.shock_pending:
            source = "Queued scenario shock"
        elif self.shock_remaining == 0 and self.rng.random() < cfg.energy_shock_probability:
            source = "Random supply shock"
        if source:
            self.shock_remaining = max(self.shock_remaining, cfg.energy_shock_duration)
            self.events.append({"Year": sim.step_count + 1, "Source": source,
                                "Supply loss fraction": cfg.energy_shock_severity,
                                "Duration": cfg.energy_shock_duration})
        self.shock_pending = False
        active = self.shock_remaining > 0
        supply = cfg.energy_supply * self.supply_index
        self.available = supply * (1 - cfg.energy_shock_severity if active else 1)
        if active:
            self.shock_remaining -= 1
        demand = sum(plans.values()) * cfg.energy_intensity
        # A bounded scarcity rule, not an estimated wholesale market model.
        pressure = min(5, max(0, demand / self.available - .8)) if self.available > EPS else (5 if demand > EPS else 0)
        self.price = cfg.energy_base_price * (1 + cfg.energy_scarcity_response * pressure)
        scale = min(1, self.available / demand) if demand > EPS else 1.0
        self.quotas = {key: units * cfg.energy_intensity * scale for key, units in plans.items()}
        self.used = 0.0
        sim.flows["Energy available"] = self.available
        sim.flows["Energy demand"] = demand
        sim.flows["Energy rationing"] = max(0, demand - self.available)
        sim.flows["Energy coverage"] = min(1, self.available / demand) if demand > EPS else None
        sim.flows["Energy shock active"] = active
        sim.flows["Energy-limited planned output"] = sum(plans.values()) * (1 - scale) if cfg.energy_intensity > 0 else 0.0

    def output_limit(self, firm, planned):
        intensity = self.sim.config.energy_intensity
        return min(planned, self.quotas.get(firm.firm_id, 0) / intensity) if intensity > 0 else planned

    def purchase(self, firm, units):
        sim = self.sim
        if not math.isfinite(units) or units < 0:
            raise ValueError("Energy purchases must be finite and non-negative.")
        request = min(max(0, units), self.quotas.get(firm.firm_id, 0),
                      max(0, self.available - self.used))
        paid = sim.transfer(firm.account, ENERGY, request * self.price, "Production energy")
        delivered = paid / self.price
        self.quotas[firm.firm_id] = max(0, self.quotas.get(firm.firm_id, 0) - delivered)
        self.used += delivered
        firm.energy_used += delivered
        firm.energy_cost += paid
        sim.flows["Energy spending"] += paid
        return delivered

    def close_year(self):
        sim = self.sim
        sim.flows["Energy used"] = self.used
        sim.flows["Energy unused"] = max(0, self.available - self.used)
        sim.flows["Energy utilization"] = self.used / self.available if self.available > EPS else None
        sim.flows["Energy balance error"] = self.available - self.used - sim.flows["Energy unused"]
        sim.flows["Energy input balance error"] = self.used - sim.output * sim.config.energy_intensity
        # Payments occur after goods purchases, helping next year's demand.
        pool = sim.accounts[ENERGY] * sim.config.energy_income_fraction
        for person in sim.population:
            person.income_received += sim.transfer(ENERGY, person.account, pool / len(sim.population), "Energy income")
        sim.flows["Energy income"] = pool if sim.population else 0.0
