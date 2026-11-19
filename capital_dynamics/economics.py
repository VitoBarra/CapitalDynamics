"""Tax, inequality and demographic calculations for the monetary economy."""
import math

import numpy as np


def gini_coefficient(wealths):
    values = np.sort(np.asarray(wealths, dtype=float))
    if not len(values) or values.sum() <= 0:
        return 0.0
    return float((len(values) + 1 - 2 * np.cumsum(values).sum() / values.sum()) / len(values))


def relative_wealth(wealths):
    """Map the poorest to 0 and richest to 1 without a currency-unit threshold."""
    values = np.asarray(wealths, dtype=float)
    if not len(values):
        return values
    spread = float(values.max() - values.min())
    if spread == 0:
        return np.zeros_like(values)
    return np.clip((values - values.min()) / spread, 0, 1)


def tax_rates_at_relative_wealth(positions, config):
    positions = np.clip(np.asarray(positions, dtype=float), 0, 1)
    return config.tau_base + (config.tau_max - config.tau_base) * positions ** config.tau_gamma


def wealth_tax_rates(wealths, config):
    return tax_rates_at_relative_wealth(relative_wealth(wealths), config)


def age_dependent_birth_prob(age, birth_prob_max):
    if age < 14 or age > 68:
        return 0.0
    return birth_prob_max * np.exp(-0.5 * ((age - 30) / 20) ** 2)


def mortality_probability(age, config, protection=1.0):
    """Annual probability from background, infant, young-adult and adult hazards."""
    age = max(age, 0)
    if protection <= 0:
        return 0.0
    if config.death_base_prob >= 1:
        return 1.0
    background = -math.log1p(-config.death_base_prob)
    exponent = math.log(2) * (age - config.aging_risk_start) / config.mortality_doubling_years
    aging = config.aging_risk_rate * (
        math.exp(min(exponent, 700)) + 1.8 * math.exp(-2 * age)
        + 0.3 * math.exp(-0.5 * ((age - 25) / 10) ** 2)
    )
    hazard = (background + aging) * protection
    return min(-math.expm1(-hazard), math.nextafter(1.0, 0.0))
