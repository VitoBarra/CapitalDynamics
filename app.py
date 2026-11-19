"""Capital Dynamics: configurable batch and continuous economy simulation."""
from dataclasses import asdict, replace
from typing import Any
import json
import importlib
import simulation as simulation_model

# A running Streamlit process may still hold the pre-upgrade model module.
if not hasattr(simulation_model, "wealth_tax_rates"):
    importlib.reload(simulation_model)

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from simulation import Simulation, SimulationConfig, relative_wealth, tax_rates_at_relative_wealth, wealth_tax_rates
from policy_controls import policy_controls, sync_policy_controls, current_simulation

# Every person remains available even in scenarios larger than Altair's default limit.
alt.data_transformers.disable_max_rows()

st.set_page_config(page_title="Capital Dynamics", page_icon=":material/monitoring:", layout="wide")
st.title("Capital Dynamics")
st.caption("Economy sandbox")
st.write("Explore how investment, public policy and demographics shape wealth over time.")

DEFAULT_CONFIG = SimulationConfig()
if "simulation" not in st.session_state:
    st.session_state.simulation = Simulation(DEFAULT_CONFIG)
    st.session_state.running = False

# Upgrade saved state without discarding the running economy.
current_simulation()

if st.session_state.pop("reload_initial_controls", False):
    for name in ("pop_size", "init_wealth", "logistic_capacity"):
        st.session_state[f"config_{name}"] = getattr(DEFAULT_CONFIG, name)
    st.session_state.seed = 42

with st.sidebar:
    st.header("Workspace", anchor=False)
    scenario_tab, display_tab = st.tabs(["Scenario", "Display"])
    config = {**asdict(SimulationConfig()), **asdict(st.session_state.simulation.config)}
    fields: dict[str, Any] = {}

    def number(name, label, minimum, maximum, step, help_text=None):
        value = config[name]
        # Float inputs also accept integral defaults from the original model.
        value = float(value) if isinstance(minimum, float) else int(value)
        st.session_state.setdefault(f"config_{name}", value)
        fields[name] = st.number_input(label, min_value=minimum, max_value=maximum,
                                      step=step, help=help_text, key=f"config_{name}")

    with scenario_tab, st.form("scenario", enter_to_submit=False):
        st.subheader("Initial conditions", anchor=False)
        st.caption("Create a fresh economy using the active policies.")
        st.session_state.setdefault("seed", 42)
        seed = st.number_input("Random seed", 0, 1000000, key="seed")
        number("pop_size", "Starting population", 1, 10000, 10)
        number("init_wealth", "Initial wealth per person", 0.01, 1000000.0, 0.1)
        number("logistic_capacity", "Initial wealth capacity", 1.0, 1000000000.0, 100.0)
        apply = st.form_submit_button("Create new scenario", type="primary", width="stretch", key="new_scenario")
    if apply:
        settings = replace(st.session_state.simulation.config, **fields)
        st.session_state.simulation = Simulation(settings, seed=int(seed))
        st.session_state.running = False
        sync_policy_controls()

    if scenario_tab.button("Load default scenario", icon=":material/restore:", key="load_defaults", width="stretch"):
        st.session_state.simulation = Simulation(DEFAULT_CONFIG, seed=42)
        st.session_state.running = False
        sync_policy_controls()
        # Initial-condition widgets were already rendered in this run.
        st.session_state.reload_initial_controls = True
        st.rerun()

    with display_tab:
        st.subheader("Charts & display", anchor=False)
        st.caption("Adjust the charts for the current economy.")
        history_window = st.number_input("Steps shown in trends", 10, 10000, 500, 50, key="history_window")
        st.divider()
        st.markdown("**Wealth distribution**")
        groups = st.slider("Percentile groups", 2, 20, 10, key="groups")
        show_individuals = st.toggle("Show individual wealth", True, key="show_individuals")
        log_wealth = st.toggle("Logarithmic wealth scale", False, key="log_wealth",
                               help="Applies to the individual wealth chart. Zero wealth is omitted on a logarithmic scale.")
        st.divider()
        st.markdown("**Age distribution**")
        age_bin = st.select_slider("Age bin width", [1, 5, 10, 20], value=10, key="age_bin")
        age_unit = st.segmented_control("Distribution units", ["Share", "People"], default="Share", key="age_unit") or "Share"
    st.divider()
    st.caption("Open a policy panel in the dashboard to change the current economy. Apply changes to use them from the next step.")

with st.container(border=True):
    st.subheader("Simulation controls", anchor=False)
    mode = st.segmented_control("Simulation mode", ["Batch", "Live"], default="Batch", key="mode") or "Batch"
    if mode != "Live":
        st.session_state.running = False
    if mode == "Batch":
        a, b = st.columns([2, 1], vertical_alignment="bottom")
        steps = a.number_input("Steps to advance", 1, 10000, 100, 10, key="batch_steps")
        if b.button("Advance simulation", icon=":material/fast_forward:", type="primary", width="stretch", key="advance"):
            with st.spinner("Advancing simulation…"):
                st.session_state.simulation.advance(int(steps))
    else:
        a, b = st.columns(2, vertical_alignment="bottom")
        interval = a.select_slider("Refresh every (seconds)", [0.1, 0.25, 0.5, 1.0, 2.0], value=0.5, key="interval")
        steps_per_refresh = b.number_input("Steps per refresh", 1, 100, 1, key="steps_per_refresh")
        def toggle_live():
            st.session_state.running = not st.session_state.running

        a, b = st.columns(2)
        live_label = "Pause" if st.session_state.running else "Resume" if st.session_state.simulation.step_count else "Start"
        a.button(live_label, icon=":material/pause:" if st.session_state.running else ":material/play_arrow:",
                 type="primary", width="stretch", key="toggle_live", on_click=toggle_live)
        if b.button("Single step", icon=":material/skip_next:", disabled=st.session_state.running, width="stretch", key="single_step"):
            st.session_state.simulation.advance()
        st.caption("Live mode continues without a step limit while this session is open. Pause to inspect the charts; resume continues the same economy.")
    if st.button("Reset current scenario", icon=":material/restart_alt:", key="reset", help="Restart this economy with its current policies and original seed."):
        previous = st.session_state.simulation
        st.session_state.simulation = Simulation(previous.config, seed=previous.seed)
        st.session_state.running = False
        sync_policy_controls()


def line_chart(history, names, title, domain=None, reference_value=None, percentage=False):
    st.subheader(title)
    data = history[["Step", *names]].melt("Step", var_name="Series", value_name="Value")
    chart = alt.Chart(data, mark=alt.MarkDef(type="line")).encode(
        x=alt.X("Step:Q", title="Simulation step"),
        y=alt.Y("Value:Q", title=title, scale=alt.Scale(domain=domain) if domain else alt.Scale(zero=False),
                axis=alt.Axis(format=".1%") if percentage else alt.Axis()),
        color=alt.Color("Series:N", title=None),
        tooltip=["Step:Q", "Series:N", alt.Tooltip("Value:Q", format=".3%" if percentage else ",.4f")],
    ).properties(height=240).interactive()
    if reference_value is not None:
        reference = alt.Chart(
            pd.DataFrame({"Current capacity": [reference_value]}),
            mark=alt.MarkDef(type="rule", color="#888888", strokeDash=[6, 4], strokeWidth=2),
        ).encode(
            y=alt.Y("Current capacity:Q", title=title),
            tooltip=[alt.Tooltip("Current capacity:Q", format=",.4f")],
        )
        st.altair_chart(chart + reference, width="stretch", alt=f"{title}, with a dashed horizontal line at current capacity")
        st.caption(f"Dashed horizontal line: current wealth capacity ({reference_value:,.2f}).")
    else:
        st.altair_chart(chart, width="stretch", alt=title)


# Policy forms stay outside the timer so chart updates never redraw draft inputs.
summary_slot = st.container()
with st.container(border=True):
    st.header("Current wealth distribution")
    st.caption("Who holds the wealth, and how evenly is it shared?")
    policy_controls("private_investments", "Private investment settings")
    wealth_slot = st.container()

with st.container(border=True):
    st.header("Economy over time")
    st.caption("Track growth, productive capacity and population.")
    policy_controls("investment", "Growth and public investment settings")
    economy_slot = st.container()

with st.container(border=True):
    st.header("Government budget and taxes")
    st.caption("Track tax revenue, the government balance and expenditure by purpose.")
    policy_controls("taxes", "Tax settings")
    government_slot = st.container()

with st.container(border=True):
    st.header("UBI and pensions")
    st.caption("Budget priority: UBI → pensions → public healthcare → capacity investment.")
    policy_controls("ubi", "UBI settings")
    policy_controls("pensions", "Pension settings")
    transfers_slot = st.container()

with st.container(border=True):
    st.header("Healthcare, aging and mortality")
    st.caption("Compare public funding, private care and their effects on health.")
    policy_controls("healthcare", "Public healthcare settings")
    policy_controls("private_healthcare", "Private care and personal choice settings")
    healthcare_slot = st.container()

with st.container(border=True):
    st.header("Population age distribution")
    st.caption("Inspect the age profile and adjust births, aging and mortality.")
    policy_controls("demographics", "Demographics and aging settings")
    age_slot = st.container()
download_slot = st.container()


@st.fragment(run_every=interval if mode == "Live" and st.session_state.running else None, key="dashboard")
def dashboard():
    sim = current_simulation()
    if mode == "Live" and st.session_state.running:
        sim.advance(int(steps_per_refresh))
        if not sim.population:
            st.session_state.running = False
            st.rerun()
    history = pd.DataFrame(sim.history)
    trends = history.tail(int(history_window))
    last = history.iloc[-1]
    status = "Running" if st.session_state.running else "Paused" if mode == "Live" else "Batch"
    # Own each slot's child container so nested chart layouts remain inside
    # the fragment on timer reruns as well as full app runs.
    with summary_slot.container():
        st.caption(f"{status} · Step {sim.step_count:,} · Seed {sim.seed} · {len(sim.history):,} retained history rows")
        if not sim.population:
            st.warning("The population became extinct. Reset the scenario or adjust its demographic settings.")
    with wealth_slot.container():
        st.caption(
            f"Last step's private opportunities: {int(last.get('Failed private investments', 0)):,} failures · "
            f"{last.get('Private investment losses', 0):,.2f} wealth lost · "
            f"{last.get('Private investment gains', 0):,.2f} wealth gained."
        )
        population = pd.DataFrame([{"Person": p.person_id, "Age": p.age, "Wealth": p.wealth,
                                    "Parent": p.parent_id, "Healthcare": p.healthcare_choice,
                                    "Healthcare premium": p.healthcare_premium, "Pension received": p.pension_received,
                                    "Health preference": p.healthcare_preference, "UBI received": p.ubi_received,
                                    "Death probability": sim.individual_death_probability(p)} for p in sim.population],
                                  columns=["Person", "Age", "Wealth", "Parent", "Healthcare", "Healthcare premium",
                                           "Pension received", "Health preference", "UBI received", "Death probability"])
        wealth = population.sort_values("Wealth").reset_index(drop=True)
        wealth["Rank"] = np.arange(1, len(wealth) + 1)
        # Rank-based groups preserve equal-wealth populations and avoid overlapping percentile edges.
        wealth["Group index"] = np.minimum(np.arange(len(wealth)) * groups // max(len(wealth), 1), groups - 1)
        labels = [f"{100*i/groups:g}–{100*(i+1)/groups:g}%" for i in range(groups)]
        wealth["Percentile group"] = wealth["Group index"].map(dict(enumerate(labels)))
        palette = alt.Scale(domain=labels, scheme="viridis")
        left, right = st.columns([2, 1] if show_individuals else [1, 1])
        with left:
            if show_individuals:
                st.subheader("Wealth of each individual")
                if len(wealth):
                    plotted = wealth[wealth.Wealth > 0] if log_wealth else wealth
                    bars = alt.Chart(plotted, mark=alt.MarkDef(type="bar")).encode(
                        x=alt.X("Rank:Q", title="Individual rank · poorest to richest"),
                        y=alt.Y("Wealth:Q", scale=alt.Scale(type="log" if log_wealth else "linear")),
                        color=alt.Color("Percentile group:N", scale=palette, sort=labels, legend=None),
                        tooltip=["Person:Q", "Rank:Q", "Age:Q", alt.Tooltip("Wealth:Q", format=",.6f"), "Percentile group:N"],
                    ).properties(height=320).interactive()
                    st.altair_chart(bars, width="stretch", alt="Each individual's wealth, sorted from poorest to richest")
                    if log_wealth:
                        st.caption("Zero-wealth individuals are omitted on the logarithmic scale; they remain in the data table and percentile calculation.")
                else:
                    st.info("No individuals remain.")
            else:
                st.subheader("Wealth distribution details")
                st.caption("Enable the individual wealth chart in the sidebar to inspect every person.")
            st.caption("Colors match the percentile chart. Hover for individual wealth, age and rank; scroll to zoom.")
        totals = wealth.groupby("Group index").Wealth.sum().reindex(range(groups), fill_value=0)
        total = totals.sum()
        shares = pd.DataFrame({"Percentile group": labels, "Wealth": totals.to_numpy(),
                               "Wealth share": totals.to_numpy() / total if total else np.zeros(groups)})
        with right:
            st.subheader("Wealth by population percentile")
            if total > 0:
                pie = alt.Chart(shares, mark=alt.MarkDef(type="arc")).encode(
                    theta="Wealth:Q", color=alt.Color("Percentile group:N", sort=labels, scale=palette),
                    tooltip=["Percentile group:N", alt.Tooltip("Wealth share:Q", format=".2%"),
                             alt.Tooltip("Wealth:Q", format=",.4f")],
                ).properties(height=320)
                text = alt.Chart(shares, mark=alt.MarkDef(type="text", radius=100)).encode(
                    theta=alt.Theta("Wealth:Q", stack=True), order=alt.Order("Percentile group:N", sort="ascending"),
                    text=alt.Text("Wealth share:Q", format=".0%"), color=alt.value("white"))
                st.altair_chart(pie + text, width="stretch", alt="Share of private wealth held by each population percentile group")
            else:
                st.info("No private wealth to distribute.")
            st.caption("Groups run from poorest to richest. Small populations can leave groups empty.")

        st.metric("Gini coefficient", f'{last["Gini coefficient"]:.3f}', border=True)
        line_chart(trends, ["Gini coefficient"], "Gini coefficient", domain=[0, 1])

    with economy_slot.container():
        left, right = st.columns(2)
        with left:
            st.metric("Wealth capacity", f'{last["Wealth capacity"]:,.2f}', border=True)
            line_chart(trends, ["Total wealth", "Wealth capacity"], "Private wealth and capacity",
                       reference_value=float(last["Wealth capacity"]))
        with right:
            st.metric("Population", f'{int(last["Population"]):,}', border=True)
            line_chart(trends, ["Population"], "Population")
    with government_slot.container():
        a, b, c = st.columns(3)
        a.metric("Government budget", f'{last["Government budget"]:,.2f}', border=True)
        b.metric("Tax revenue this step", f'{last["Tax revenue"]:,.2f}', border=True)
        c.metric("Government spending this step", f'{last["Total government spending"]:,.2f}', border=True)
        line_chart(trends, ["Government budget"], "Government budget")
        left, right = st.columns(2)
        with left:
            st.subheader("Current wealth tax curve")
            positions = np.linspace(0, 1, 201)
            curve = pd.DataFrame({"Relative wealth": positions, "Tax rate": tax_rates_at_relative_wealth(positions, sim.config)})
            curve_chart = alt.Chart(curve, mark=alt.MarkDef(type="line")).encode(
                x=alt.X("Relative wealth:Q", title="Relative wealth · poorest 0, richest 1"),
                y=alt.Y("Tax rate:Q", axis=alt.Axis(format=".1%"), scale=alt.Scale(zero=True)),
                tooltip=[alt.Tooltip("Relative wealth:Q", format=".2f"), alt.Tooltip("Tax rate:Q", format=".2%")],
            ).properties(height=240)
            projected = pd.DataFrame({"Relative wealth": relative_wealth(population.Wealth.to_numpy()),
                                      "Tax rate": wealth_tax_rates(population.Wealth.to_numpy(), sim.config),
                                      "Personal wealth": population.Wealth})
            points = alt.Chart(projected, mark=alt.MarkDef(type="circle", size=25, opacity=0.4)).encode(
                x="Relative wealth:Q", y="Tax rate:Q", tooltip=[alt.Tooltip("Personal wealth:Q", format=",.4f"), alt.Tooltip("Tax rate:Q", format=".2%")])
            st.altair_chart(curve_chart + points, width="stretch", alt="Current progressive wealth tax curve and projected rates for the population")
            st.caption("Curve uses the active policy; dots project rates on current wealth. Relative wealth is distance between the poorest and richest, not a population percentile. Equal wealth pays the minimum. Taxes apply to wealth each step.")
        with right:
            st.metric("Effective tax rate last step", f'{last["Effective wealth tax rate"]:.2%}', border=True)
            line_chart(trends, ["Minimum applied tax rate", "Effective wealth tax rate", "Maximum applied tax rate"], "Applied wealth tax rates", percentage=True)
        spending_columns = ["UBI transfers", "Pension spending", "Healthcare spending", "Capacity investment"]
        spending = trends[["Step", *spending_columns]].melt("Step", var_name="Purpose", value_name="Spending")
        left, right = st.columns(2)
        with left:
            st.subheader("Government spending over time")
            spending_chart = alt.Chart(spending, mark=alt.MarkDef(type="area")).encode(
                x=alt.X("Step:Q", title="Simulation step"), y=alt.Y("Spending:Q", stack="zero"),
                color="Purpose:N", tooltip=["Step:Q", "Purpose:N", alt.Tooltip("Spending:Q", format=",.4f")],
            ).properties(height=240)
            st.altair_chart(spending_chart, width="stretch", alt="Government spending by UBI, pensions, public healthcare and capacity investment")
        with right:
            st.subheader("Latest spending breakdown")
            latest_spending = pd.DataFrame({"Purpose": spending_columns, "Spending": [last[name] for name in spending_columns]})
            spending_bars = alt.Chart(latest_spending, mark=alt.MarkDef(type="bar")).encode(
                x="Spending:Q", y=alt.Y("Purpose:N", sort=spending_columns), color=alt.Color("Purpose:N", legend=None),
                tooltip=["Purpose:N", alt.Tooltip("Spending:Q", format=",.4f")],
            ).properties(height=240)
            st.altair_chart(spending_bars, width="stretch", alt="Latest government expenditure by purpose")
        ledger_rows = ["Opening government budget", "Tax revenue", "Estate revenue", *spending_columns,
                       "Total government spending", "Government budget", "Government balance error"]
        ledger = pd.DataFrame({"Account": ledger_rows, "Amount": [last[name] for name in ledger_rows]})
        with st.expander("Government accounts"):
            st.dataframe(ledger, hide_index=True, alt="Government opening funds, revenue, expenditure and closing budget reconciliation")
        st.caption("Opening budget + taxes + estates − UBI − pensions − public healthcare − capacity investment = closing budget. Private premiums are paid by individuals and are outside government expenditure.")

    with transfers_slot.container():
        a, b = st.columns(2)
        a.metric("UBI spending this step", f'{last["UBI transfers"]:,.2f}', border=True)
        b.metric("UBI per person", f'{last["UBI per person"]:,.4f}', border=True)
        st.caption("Universal Basic Income (UBI) is the same payment for every resident, deducted from government funds before pensions, public healthcare and capacity investment.")
        a, b = st.columns(2)
        a.metric("Pension spending", f"{last['Pension spending']:,.2f}", border=True)
        b.metric("Unfunded pension entitlement", f"{last['Pension shortfall']:,.2f}", border=True)
        st.caption(f"Eligible for pensions before deaths: {int(last['Pension eligible']):,}. Payments are budget-limited and shared equally among retirees. UBI also reaches retirees.")

    with healthcare_slot.container():
        a, b, c = st.columns(3)
        a.metric("Public-care baseline mortality", f"{sim.mortality_rate:.2%}", border=True)
        b.metric("Healthcare spending this step", f"{sim.healthcare_spending:,.2f}", border=True)
        c.metric("Deaths this step", f"{sim.deaths:,}", border=True)
        left, right = st.columns(2)
        with left:
            line_chart(trends, ["Baseline mortality", "Mortality rate", "Observed mortality"],
                       "Mortality over time", percentage=True)
        with right:
            line_chart(trends, ["Healthcare spending"], "Healthcare spending per step")
        a, b, c = st.columns(3)
        a.metric("Private care purchases this step", f"{sim.private_healthcare_users:,}", border=True)
        b.metric("Private premiums this step", f"{sim.private_healthcare_revenue:,.2f}", border=True)
        c.metric("Private healthcare sector assets", f"{sim.private_healthcare_balance:,.2f}", border=True)
        line_chart(trends, ["Public healthcare users", "Private healthcare users"], "Healthcare choices over time")
        st.caption("Choices count patients before deaths and births in each step. Private premiums reduce personal wealth and become private provider assets. Provider assets are tracked separately from individual wealth.")
        st.caption("Each step represents one year of aging. Death is a random event at every age, not a maximum-age cutoff. Public funding gradually reduces the mortality hazard; protection fades when funding falls. Baseline mortality excludes age effects; observed mortality includes them and random variation.")
        representative_wealth = float(population.Wealth.median()) if len(population) else sim.config.init_wealth
        risk_ages = range(max(120, int(population.Age.max()) if len(population) else 0) + 1)
        risk_data = pd.DataFrame([
            {"Age": age, "Policy": policy, "Death probability": sim.death_probability(age, representative_wealth, funded)}
            for policy, funded in [("Public care", True), ("No healthcare", False)]
            for age in risk_ages
        ])
        private_curve = pd.DataFrame([
            {"Age": age, "Policy": "Private care", "Death probability": sim.private_death_probability(
                age, max(representative_wealth - sim.private_premium(age), 0))} for age in risk_ages
        ])
        risk_data = pd.concat([risk_data, private_curve], ignore_index=True)
        risk_chart = alt.Chart(risk_data, mark=alt.MarkDef(type="line")).encode(
            x=alt.X("Age:Q"), y=alt.Y("Death probability:Q", axis=alt.Axis(format=".0%"), scale=alt.Scale(domain=[0, 1])),
            color="Policy:N", tooltip=["Age:Q", "Policy:N", alt.Tooltip("Death probability:Q", format=".2%")],
        ).properties(height=240).interactive()
        st.subheader("Death risk by age")
        st.altair_chart(risk_chart, width="stretch", alt="Death probability by age for public care, private care and no healthcare")
        st.caption("The human-shaped profile includes infant risk, low childhood risk and exponentially rising adult risk. Wealth affects private-care affordability, not aging directly. Private care shows potential risk even when unaffordable. The chart's age range is not a lifespan limit.")
        st.caption("Calibration context: [SSA 2022 life table](https://www.ssa.gov/oact/STATS/table4c6_2022_TR2025.html); [mortality by age and over time](https://ourworldindata.org/how-do-the-risks-of-death-change-as-people-age). This is an approximate modern profile, not a fitted life table. Healthcare effects are illustrative, not causal estimates.")
    with age_slot.container():
        edges = np.arange(0, max(int(population.Age.max()) if len(population) else 0, 100) + age_bin + 1, age_bin)
        counts, _ = np.histogram(population.Age.to_numpy(), bins=edges)
        ages = pd.DataFrame({"Age range": [f"{lo}–{hi-1}" for lo, hi in zip(edges[:-1], edges[1:])],
                             "People": counts, "Share": counts / max(len(population), 1)})
        age_chart = alt.Chart(ages, mark=alt.MarkDef(type="bar")).encode(
            x=alt.X("Age range:N", sort=ages["Age range"].tolist()),
            y=alt.Y(f"{age_unit}:Q", axis=alt.Axis(format=".0%") if age_unit == "Share" else alt.Axis(),
                    scale=alt.Scale(domain=[0, 1]) if age_unit == "Share" else alt.Scale(zero=True)),
            color=alt.Color("Age range:N", scale=alt.Scale(scheme="viridis"), legend=None),
            tooltip=["Age range:N", "People:Q", alt.Tooltip("Share:Q", format=".2%")],
        ).properties(height=240)
        st.altair_chart(age_chart, width="stretch", alt="Population age distribution in configurable age bins")
    with download_slot.container():
        with st.expander("Detailed data and downloads"):
            st.subheader("Population snapshot")
            st.dataframe(population, hide_index=True, alt="Personal wealth, pension income, healthcare choice, premium and death probability for every person")
            st.subheader("Government and private sector accounts")
            finance_columns = ["Step", *ledger_rows, "Pension shortfall", "Private healthcare premiums", "Private healthcare sector balance", "Total private sector wealth"]
            st.download_button("Download finance ledger CSV", history[finance_columns].to_csv(index=False), "capital-dynamics-finances.csv", "text/csv")
            st.caption(f"Total private sector wealth (individuals + healthcare providers): {last['Total private sector wealth']:,.2f}.")
            if sim.policy_changes:
                st.subheader("Policy changes")
                changes = pd.DataFrame(list(sim.policy_changes))
                st.dataframe(changes, hide_index=True, alt="Policy changes and the simulation step where each takes effect")
            st.subheader("Percentile wealth shares")
            st.dataframe(shares, hide_index=True, alt="Wealth amount and share for each percentile group")
            st.download_button("Download population CSV", population.to_csv(index=False), "capital-dynamics-population.csv", "text/csv")
            st.download_button("Download history CSV", history.to_csv(index=False), "capital-dynamics-history.csv", "text/csv")
            settings = {"seed": sim.seed, "initial_parameters": asdict(sim.initial_config),
                        "current_parameters": asdict(sim.config), "policy_changes": list(sim.policy_changes)}
            st.download_button("Download scenario settings", json.dumps(settings, indent=2), "capital-dynamics-scenario.json", "application/json")
            st.caption("Live mode retains the latest 10,000 history rows to keep memory use bounded. Downloads include all retained rows; trend charts show the selected window.")


dashboard()
