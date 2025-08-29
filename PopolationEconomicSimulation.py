import random
from itertools import count

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib.cm as cm

# --- Individual class ---
class Individual:
    def __init__(self, wealth, age=0, parent_id=None):
        self.wealth = wealth
        self.age = age
        self.parent_id = parent_id

# --- Simulation ---
def simulate(
        pop_size=500,
        init_wealth=1,
        base_growth=0.05,
        gain_prob=0.3,
        gain_fraction=0.25,
        gain_growth=0.15,
        loss_prob=0.3,
        loss_fraction=0.25,
        loss_rate=0.3,
        tick_count=10,
        logistic_capacity=1000,
        alpha=-0.001,
        tau_base=0.00,
        tau_max=0.52,
        tau_gamma:float=3,
        direct_redistribution_fraction=0.5,
        investment_probability=0.1,
        delta=0.001,
        beta=0.8,
        base_eff=0.3,
        shock_scale=0.2,
        max_neg_shock=0.3,
        psi=2.0,
        max_age=100,
        death_base_prob=0.05,
        birth_prob_max=0.15
):

    # --- Gini coefficient function ---
    def gini_coefficient(wealths):
        x = np.sort(wealths)
        n = len(x)
        cumx = np.cumsum(x)
        return (n + 1 - 2 * np.sum(cumx)/cumx[-1])/n

    # --- Age-dependent birth function ---
    def age_dependent_birth_prob(age, birth_prob_max=0.2):
        if age < 14 or age > 68:
            return 0.0
        # Gaussian centered at 30, std ~10
        peak_age = 30
        std_age = 20
        prob = birth_prob_max * np.exp(-0.5 * ((age - peak_age) / std_age) ** 2)
        return prob

    # --- Initialize population ---
    population = [Individual(wealth=init_wealth, age=random.randint(1,50)) for _ in range(pop_size)]
    government_budget = 0
    total_wealth_history = []
    government_budget_history = []
    gini_history = []
    population_history = []
    logistic_capacity_history = [logistic_capacity]

    # --- Plot setup (updated layout with age distribution) ---
    fig = plt.figure(figsize=(18, 12))  # taller figure
    gs = fig.add_gridspec(3, 3, height_ratios=[2, 1, 1])  # 3 rows: main, secondary, age distribution
    axes = [
        fig.add_subplot(gs[0, 0]),  # individual bars
        fig.add_subplot(gs[0, 1]),  # wealth distribution pie chart
        fig.add_subplot(gs[0, 2]),  # population history
        fig.add_subplot(gs[1, 1]),  # total wealth
        fig.add_subplot(gs[1, 2]),  # government budget
    ]
    axes_gini = fig.add_subplot(gs[1, 0])  # Gini coefficient
    axes_age = fig.add_subplot(gs[2, :])   # age distribution across bottom row

    tick_labels = [f"{int(100*t/tick_count)}-{int(100*(t+1)/tick_count)}%" for t in range(tick_count)]
    cmap = cm.get_cmap("viridis", tick_count)

    # --- Animation update ---
    def update(step):
        nonlocal population, government_budget, logistic_capacity

        # --- Aging ---
        for person in population:
            person.age += 1

        # --- Population array for calculations ---
        wealths = np.array([p.wealth for p in population])
        total_wealth = wealths.sum()

        # --- Growth ---
        individual_factor = 1 / (1 + alpha * wealths)
        global_factor = max(1 - total_wealth / logistic_capacity, 0)
        total_growth_factor = base_growth * individual_factor * global_factor
        for i, person in enumerate(population):
            person.wealth *= (1 + total_growth_factor[i])

        # --- Gains ---
        if np.random.rand() < gain_prob:
            probs = wealths / wealths.sum()
            lucky_idx = np.random.choice(len(population), size=int(gain_fraction*len(population)), replace=False, p=probs)
            for i in lucky_idx:
                population[i].wealth *= (1 + gain_growth * global_factor)

        # --- Losses ---
        if np.random.rand() < loss_prob:
            probs = 1 / (wealths + 1e-6)
            probs /= probs.sum()
            unlucky_idx = np.random.choice(len(population), size=int(loss_fraction*len(population)), replace=False, p=probs)
            loss_percent = np.random.uniform(0, loss_rate*global_factor, size=len(unlucky_idx))
            loss_percent = np.clip(loss_percent, 0, 0.99)
            for i, lp in zip(unlucky_idx, loss_percent):
                population[i].wealth *= (1 - lp)

        # --- Taxation ---
        wealths = np.array([p.wealth for p in population])
        w_min, w_max = wealths.min(), wealths.max()
        denom = max(w_max - w_min, 1e-3)
        tax_rates = tau_base + (tau_max - tau_base) * ((wealths - w_min)/denom)**tau_gamma
        taxes = tax_rates * wealths
        for i, person in enumerate(population):
            person.wealth -= taxes[i]
        government_budget += taxes.sum()

        # --- Direct redistribution ---
        wealths = np.array([p.wealth for p in population])
        epsilon = 0.1
        weights = 1 / (wealths + epsilon)
        weights /= weights.sum()
        redistribution_amount = government_budget * direct_redistribution_fraction
        for i, person in enumerate(population):
            person.wealth += redistribution_amount * weights[i]
        government_budget *= (1 - direct_redistribution_fraction)

        # --- Investment & logistic capacity ---
        if np.random.rand() < investment_probability and government_budget > 1:
            investment = np.random.rand() * government_budget
            invest_ratio = investment / (government_budget + 1e-9)
            p_success = 1 / (1 + np.exp(-psi*(invest_ratio-0.5)))
            eff_core = base_eff + 0.8 * invest_ratio
            shock = shock_scale*(2*np.random.rand()-1)
            efficiency = max(0.0, eff_core + shock)
            capacity_gain = efficiency * (investment**beta)
            if np.random.rand() < p_success:
                logistic_capacity += capacity_gain
            else:
                logistic_capacity = max(1.0, logistic_capacity - max_neg_shock*capacity_gain)
            government_budget -= investment
        logistic_capacity = max(1.0, (1-delta)*logistic_capacity)

        # --- Deaths with wealth-dependent inheritance ---
        new_population = []
        for idx, person in enumerate(population):
            age_factor = 0.002
            wealth_factor = 1 / (1 + person.wealth)
            death_prob_age = death_base_prob + age_factor * max(0, person.age - 50) * wealth_factor
            if np.random.rand() < death_prob_age or person.age >= max_age:
                children = [c for c in population if c.parent_id == idx]
                if children:
                    share = person.wealth / len(children)
                    for child in children:
                        child.wealth += share
                else:
                    government_budget += person.wealth
            else:
                new_population.append(person)
        population = new_population

        # --- Births with inheritance ---
        newborns = []
        for idx, person in enumerate(population):
            prob = age_dependent_birth_prob(person.age, birth_prob_max)
            if np.random.rand() < prob:
                inherited_wealth = person.wealth * 0.5
                person.wealth *= 0.5
                child = Individual(wealth=inherited_wealth, age=0, parent_id=idx)
                newborns.append(child)
        population.extend(newborns)

        # --- Record history ---
        wealths = np.array([p.wealth for p in population])
        total_wealth_history.append(wealths.sum())
        government_budget_history.append(government_budget)
        population_history.append(len(population))
        logistic_capacity_history.append(logistic_capacity)
        gini_history.append(gini_coefficient(wealths))

        # --- Individual wealth bars ---
        axes[0].clear()
        wealth_sorted = np.sort(wealths)
        colors_sorted = [cmap(int(i*tick_count/len(wealth_sorted))) for i in range(len(wealth_sorted))]
        axes[0].bar(range(len(wealth_sorted)), wealth_sorted, color=colors_sorted)
        axes[0].set_title("Wealth of each individual")
        axes[0].set_xlabel("Individual")
        axes[0].set_ylabel("Wealth")

        # --- Wealth distribution pie chart ---
        edges = np.percentile(wealth_sorted, np.linspace(0,100,tick_count+1))
        fractions = []
        for t in range(tick_count):
            if t == tick_count-1:
                tick_pop = ((wealth_sorted >= edges[t]) & (wealth_sorted <= edges[t+1]))
            else:
                tick_pop = ((wealth_sorted >= edges[t]) & (wealth_sorted < edges[t+1]))
            fractions.append(wealth_sorted[tick_pop].sum()/wealth_sorted.sum())
        fractions = np.nan_to_num(fractions)
        total_frac = fractions.sum()
        if total_frac > 0:
            fractions /= total_frac
        nonzero_idx = [i for i,f in enumerate(fractions) if f>0]
        axes[1].clear()
        axes[1].pie([fractions[i] for i in nonzero_idx],
                    labels=[tick_labels[i] for i in nonzero_idx],
                    autopct="%1.1f%%",
                    startangle=90,
                    colors=[cmap(i) for i in nonzero_idx])
        axes[1].set_title("Wealth distribution by percentile")

        # --- Population history ---
        axes[2].clear()
        axes[2].plot(range(len(population_history)), population_history, color="blue")
        axes[2].set_title("Population over time")
        axes[2].set_xlabel("Steps")
        axes[2].set_ylabel("Population")

        # --- Total wealth ---
        axes[3].clear()
        axes[3].plot(range(len(total_wealth_history)), total_wealth_history, color="green")
        axes[3].axhline(logistic_capacity, color='gray', linestyle='--')
        axes[3].set_title("Total wealth over time")
        axes[3].set_xlabel("Steps")
        axes[3].set_ylabel("Total wealth")

        # --- Government budget ---
        axes[4].clear()
        axes[4].plot(range(len(government_budget_history)), government_budget_history, color="purple")
        axes[4].set_title("Government budget")
        axes[4].set_xlabel("Steps")
        axes[4].set_ylabel("Budget")

        # --- Gini coefficient ---
        axes_gini.clear()
        axes_gini.plot(range(len(gini_history)), gini_history, color="orange")
        axes_gini.set_title("Gini coefficient over time")
        axes_gini.set_xlabel("Steps")
        axes_gini.set_ylabel("Gini")
        axes_gini.set_ylim(0,1)

        # --- Age distribution plot ---
        age_bins = np.arange(0, max_age + 10, 10)
        age_labels = [f"{age_bins[i]}-{age_bins[i+1]-1}" for i in range(len(age_bins)-1)]
        ages = np.array([p.age for p in population])
        age_counts, _ = np.histogram(ages, bins=age_bins)
        age_fractions = age_counts / age_counts.sum() if age_counts.sum() > 0 else age_counts

        axes_age.clear()
        axes_age.bar(age_labels, age_fractions, color=cm.viridis(np.linspace(0,1,len(age_labels))))
        axes_age.set_title("Population Age Distribution")
        axes_age.set_xlabel("Age Range")
        axes_age.set_ylabel("Fraction of Population")
        axes_age.set_ylim(0,1)

    ani = FuncAnimation(fig, update, frames=count(), interval=100, repeat=False)
    plt.tight_layout()
    plt.show()

# --- Run simulation ---
simulate(
    pop_size=50,
    tau_base=0.0,
    tau_max=0.60,
    tau_gamma=4,
    investment_probability=0.2,
    direct_redistribution_fraction=0.4
)
