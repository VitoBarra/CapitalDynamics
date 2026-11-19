"""Section-local controls and a live dashboard for the monetary model."""
from dataclasses import asdict, replace
import json
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from budget import LEGACY_FIELDS, POLICIES
from budget_ui import allocation_view
from monetary import COMPARISON_NAMES, MonetarySimulation, comparison_config

# Names are deliberately separate from the legacy widgets and model state.
SPECS: dict[str, list[tuple[Any, ...]]] = {
    "production": [
        ("productivity", "Output per worker", 0.0, 100.0, 0.1),
        ("consumption_fraction", "Consumption propensity (%)", 0.0, 100.0, 1.0),
        ("wage_fraction", "Wage funding fraction (%)", 0.0, 100.0, 1.0),
        ("producer_dividend_fraction", "Producer profit distributed (%)", 0.0, 100.0, 1.0),
        ("private_investment_fraction", "Money invested by working adults (%)", 0.0, 100.0, 1.0),
        ("base_eff", "Capital units per investment unit", 0.0, 2.0, 0.05),
        ("investment_risk", "Private investment failure chance (%)", 0.0, 100.0, 1.0),
        ("failed_investment_loss", "Capital lost on investment failure (%)", 0.0, 100.0, 1.0),
        ("delta", "Annual capital depreciation (%)", 0.0, 100.0, 0.05)],
    "taxes": [("tau_base", "Minimum net wealth tax (%)", 0.0, 100.0, 0.1),
              ("tau_max", "Maximum net wealth tax (%)", 0.0, 100.0, 0.1),
              ("tau_gamma", "Tax progressivity", 0.1, 20.0, 0.1)],
    "allocation": [(name, f"{policy} allocation (% of total budget)", 0.0, 100.0, 1.0)
                   for name, policy in zip((*LEGACY_FIELDS, "debt_service_fraction"), (*POLICIES, "Debt service"))],
    "bonds": [("government_borrowing", "Enable government borrowing"),
              ("borrowing_target", "New borrowing target per year", 0.0, 1000000.0, 1.0),
              ("debt_ceiling", "Government debt ceiling", 0.0, 1000000000.0, 10.0),
              ("bond_rate", "New bond coupon (%)", 0.0, 100.0, 0.1),
              ("bond_term", "New bond maturity (years)", 1, 100, 1),
              ("bond_purchase_fraction", "Adult money offered for bonds (%)", 0.0, 100.0, 1.0),
              ("bank_bond_fraction", "Borrowing target offered to bank (%)", 0.0, 100.0, 1.0),
              ("principal_first", "Pay principal before coupons within debt allocation")],
    "pensions": [("retirement_age", "Retirement age", 18, 150, 1),
                 ("pension_per_person", "Pension target (initial money multiple)", 0.0, 10.0, 0.01),
                 ("index_pensions", "Index pension target to prices")],
    "healthcare": [("healthcare_effectiveness", "Public care effectiveness", 0.0, 50.0, 0.5),
                   ("healthcare_response_rate", "Public care response speed (%)", 0.0, 100.0, 1.0),
                   ("mortality_floor_fraction", "Minimum mortality hazard fraction (%)", 0.0, 100.0, 1.0),
                   ("healthcare_choice_mode", "Care choice", ["Adaptive", "Public only", "Private if affordable"]),
                   ("private_healthcare_premium", "Private premium (initial money multiple)", 0.0, 10.0, 0.001),
                   ("private_healthcare_age_loading", "Private premium age surcharge", 0.0, 10.0, 0.1),
                   ("private_healthcare_mortality_factor", "Private mortality hazard fraction (%)", 0.0, 100.0, 1.0),
                   ("private_healthcare_max_wealth_fraction", "Maximum liquid money spent on private care (%)", 0.0, 100.0, 1.0),
                   ("healthcare_choice_priority", "Health preference weight", 0.0, 20.0, 0.5)],
    "banking": [("lending_enabled", "Enable individual investment loans"),
                ("loan_spread", "New loan spread over policy rate (%)", 0.0, 100.0, 0.1),
                ("loan_term", "New loan repayment term (years)", 1, 100, 1),
                ("loan_demand", "Annual loan demand (initial money fraction, %)", 0.0, 100.0, 1.0),
                ("borrowing_limit", "Debt limit / productive assets and bonds", 0.0, 10.0, 0.1),
                ("capital_ratio", "Minimum bank equity / risk assets (%)", 0.0, 100.0, 1.0),
                ("reserve_ratio", "Minimum reserves / deposits (%)", 0.0, 100.0, 1.0),
                ("default_after", "Default after consecutive missed payments", 1, 20, 1),
                ("bank_dividend_fraction", "Distribute excess bank equity (%)", 0.0, 100.0, 1.0)],
    "money": [("policy_rate", "Policy interest rate (%)", 0.0, 100.0, 0.1),
              ("inflation_response", "Price adjustment speed (%)", 0.0, 100.0, 1.0),
              ("monetary_financing", "Allow fiat grants to government"),
              ("issuance_per_step", "Money issuance per year", 0.0, 1000000.0, 1.0),
              ("money_cap", "Maximum money supply (0 = no cap)", 0.0, 1000000000.0, 10.0),
              ("money_cap_type", "Supply constrained by cap", ["Base money", "Broad money"])],
    "demographics": [("birth_prob_max", "Peak annual birth probability (%)", 0.0, 100.0, 0.1),
                     ("death_base_prob", "Background annual death probability (%)", 0.0, 100.0, 0.01),
                     ("aging_risk_start", "Adult mortality reference age", 0, 100, 1),
                     ("aging_risk_rate", "Adult hazard at reference age", 0.0, 0.1, 0.001),
                     ("mortality_doubling_years", "Mortality doubling time (years)", 1.0, 20.0, 0.5)],
}
PERCENT = {spec[0] for specs in SPECS.values() for spec in specs if "%" in spec[1]}


def sync_monetary_controls():
    config = st.session_state.monetary_simulation.config
    for specs in SPECS.values():
        for name, *_ in specs:
            value = getattr(config, name)
            st.session_state[f"m_{name}"] = float(value * 100) if name in PERCENT else value
    st.session_state.monetary_notices = {}


def sync_monetary_initial_controls():
    sim = st.session_state.monetary_simulation
    for key, value in {"m_seed": sim.seed, "m_initial_population": sim.config.pop_size,
        "m_initial_money": float(sim.config.init_wealth), "m_initial_capacity": float(sim.config.logistic_capacity),
        "m_initial_producer": float(sim.config.initial_producer_money),
        "m_initial_bank": float(sim.config.initial_bank_capital)}.items():
        st.session_state[key] = value


def apply_monetary_policy(group):
    changes = {spec[0]: st.session_state[f"m_{spec[0]}"] / (100 if spec[0] in PERCENT else 1)
               if len(spec) == 5 and isinstance(spec[2], float)
               else st.session_state[f"m_{spec[0]}"] for spec in SPECS[group]}
    notices = st.session_state.setdefault("monetary_notices", {})
    try:
        changed = st.session_state.monetary_simulation.update_policy(**changes)
    except (ValueError, TypeError) as error:
        notices[group] = (False, str(error))
    else:
        notices[group] = (True, "Changes apply next year; existing loan and bond contracts keep their original terms."
                          if changed else "These settings are already active.")


def monetary_controls(group, title):
    config = st.session_state.monetary_simulation.config
    with st.expander(title, icon=":material/tune:"):
        if group == "allocation":
            st.caption("One common total: treasury opening money + collected taxes + borrowing proceeds + fiat grants. "
                       "Debt service has its own allocation. All allocations are fixed before payments and must total at most 100%. "
                       "Unused amounts are retained, never passed to the next policy.")
        with st.form(f"m_policy_{group}", enter_to_submit=False):
            for spec in SPECS[group]:
                name, label, *bounds = spec
                key = f"m_{name}"
                value = getattr(config, name)
                st.session_state.setdefault(key, float(value * 100) if name in PERCENT else value)
                if not bounds:
                    st.toggle(label, key=key)
                elif isinstance(bounds[0], list):
                    st.selectbox(label, bounds[0], key=key)
                else:
                    minimum, maximum, step = bounds
                    st.number_input(label, min_value=minimum, max_value=maximum, step=step, key=key)
            st.form_submit_button("Apply budget allocation" if group == "allocation" else "Apply policy",
                                  key=f"m_apply_{group}", on_click=apply_monetary_policy, args=(group,), width="stretch")
        notice = st.session_state.get("monetary_notices", {}).get(group)
        if notice:
            (st.success if notice[0] else st.error)(notice[1])


def reset_monetary():
    previous = st.session_state.monetary_simulation
    st.session_state.monetary_running = False
    try:
        fresh = MonetarySimulation(previous.config, previous.seed)
    except ValueError as error:
        st.session_state.monetary_reset_error = str(error)
        return
    st.session_state.monetary_simulation = fresh
    st.session_state.monetary_running = False
    st.session_state.monetary_reset_error = None
    sync_monetary_controls()
    sync_monetary_initial_controls()


def load_comparison():
    st.session_state.monetary_simulation = MonetarySimulation(comparison_config(st.session_state.m_comparison))
    st.session_state.monetary_running = False
    st.session_state.monetary_reset_error = None
    sync_monetary_controls()
    sync_monetary_initial_controls()


def toggle_monetary():
    st.session_state.monetary_running = not st.session_state.monetary_running


def monetary_trend(history, columns, title, percentage=False):
    st.subheader(title)
    frame = history[["Step", *columns]].melt("Step", var_name="Series", value_name="Value")
    chart = alt.Chart(frame, mark=alt.MarkDef(type="line")).encode(
        x=alt.X("Step:Q", title="Year"),
        y=alt.Y("Value:Q", axis=alt.Axis(format=".1%") if percentage else alt.Axis(), scale=alt.Scale(zero=False)),
        color=alt.Color("Series:N", title=None),
        tooltip=["Step:Q", "Series:N", alt.Tooltip("Value:Q", format=".2%" if percentage else ",.3f")],
    ).properties(height=230).interactive()
    st.altair_chart(chart, width="stretch", alt=title)


def monetary_workspace():
    if "monetary_simulation" not in st.session_state:
        st.session_state.monetary_simulation = MonetarySimulation()
        st.session_state.monetary_running = False
        sync_monetary_initial_controls()
    sim = st.session_state.monetary_simulation
    st.caption("Monetary economy · experimental accounting model, not a forecast")
    with st.sidebar:
        st.header("Monetary workspace", anchor=False)
        st.selectbox("Comparison scenario", COMPARISON_NAMES, key="m_comparison")
        st.button("Load comparison scenario", key="m_load_comparison", on_click=load_comparison, width="stretch")
        st.caption("Loading a comparison creates a fresh monetary economy. Your legacy economy is kept separately.")
        with st.form("m_scenario", enter_to_submit=False):
            st.subheader("Initial conditions")
            for key, value in {"m_seed": sim.seed, "m_initial_population": sim.config.pop_size,
                "m_initial_money": float(sim.config.init_wealth), "m_initial_capacity": float(sim.config.logistic_capacity),
                "m_initial_producer": float(sim.config.initial_producer_money),
                "m_initial_bank": float(sim.config.initial_bank_capital)}.items():
                st.session_state.setdefault(key, value)
            seed = st.number_input("Random seed", 0, 1000000, key="m_seed")
            pop = st.number_input("Starting population", 1, 10000, key="m_initial_population")
            money = st.number_input("Initial money per person", 0.01, 1000000.0, key="m_initial_money")
            capacity = st.number_input("Initial productive capacity", 0.0, 1000000000.0,
                                        key="m_initial_capacity")
            producer = st.number_input("Initial producer money", 0.0, 1000000000.0,
                                        key="m_initial_producer")
            bank = st.number_input("Initial bank capital / reserves", 0.0, 1000000000.0,
                                    key="m_initial_bank")
            if st.form_submit_button("Create monetary scenario", key="m_new_scenario", width="stretch"):
                try:
                    new = MonetarySimulation(replace(sim.config, pop_size=int(pop), init_wealth=float(money),
                        logistic_capacity=float(capacity), initial_producer_money=float(producer), initial_bank_capital=float(bank)), int(seed))
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.session_state.monetary_simulation = new
                    st.session_state.monetary_running = False
                    st.session_state.monetary_reset_error = None
                    sync_monetary_controls()
                    sim = new
        window = st.number_input("Years shown in trends", 10, 10000, 500, key="m_window")

    with st.container(border=True):
        st.subheader("Simulation controls")
        mode = st.segmented_control("Simulation mode", ["Batch", "Live"], default="Batch", key="m_mode") or "Batch"
        interval, per_refresh = 0.5, 1
        if mode == "Batch":
            st.session_state.monetary_running = False
            years = st.number_input("Years to advance", 1, 10000, 10, key="m_years")
            if st.button("Advance monetary economy", key="m_advance", type="primary"):
                sim.advance(int(years))
        else:
            interval = st.select_slider("Refresh every (seconds)", [0.1, 0.25, 0.5, 1.0, 2.0], value=0.5, key="m_interval")
            per_refresh = st.number_input("Years per refresh", 1, 100, 1, key="m_per_refresh")
            st.button("Pause" if st.session_state.monetary_running else "Resume", key="m_toggle_live", on_click=toggle_monetary)
            if st.button("Single year", key="m_single_step", disabled=st.session_state.monetary_running):
                sim.advance()
        st.button("Reset monetary scenario", key="m_reset", on_click=reset_monetary)
        if st.session_state.get("monetary_reset_error"):
            st.error(st.session_state.monetary_reset_error + " Adjust the money cap before resetting.")

    slots = {}
    sections = [
        ("wealth", "Current wealth distribution", []),
        ("production", "Economy and production", [("production", "Production and investment settings")]),
        ("government", "Government budget and taxes", [("taxes", "Net wealth tax settings"),
            ("allocation", "Budget allocation settings"), ("bonds", "Government borrowing settings")]),
        ("transfers", "UBI and pensions", [("pensions", "Pension settings")]),
        ("health", "Healthcare, aging and mortality", [("healthcare", "Healthcare settings")]),
        ("bank", "Banking and credit", [("banking", "Banking settings")]),
        ("money", "Money and prices", [("money", "Monetary policy settings")]),
        ("age", "Population age distribution", [("demographics", "Demographic settings")]),
    ]
    status_slot = st.container()
    for name, title, controls in sections:
        with st.container(border=True):
            st.header(title)
            if name in {"transfers", "health", "production"}:
                st.caption("Funding percentages are configured together under Government budget and taxes; "
                           "all use the same total budget, regardless of section order.")
            for group, label in controls:
                monetary_controls(group, label)
            slots[name] = st.container()
    downloads = st.container()

    @st.fragment(run_every=interval if mode == "Live" and st.session_state.monetary_running else None, key="monetary_dashboard")
    def monetary_dashboard():
        economy = st.session_state.monetary_simulation
        if mode == "Live" and st.session_state.monetary_running:
            economy.advance(int(per_refresh))
            if not economy.population:
                st.session_state.monetary_running = False
                st.rerun()
        history = pd.DataFrame(economy.history)
        trends = history.tail(int(window))
        last = history.iloc[-1]
        people = pd.DataFrame(economy.person_rows())
        with status_slot.container():
            st.caption(f"Year {economy.step_count:,} · Seed {economy.seed} · "
                       f"{'Running' if st.session_state.monetary_running else 'Paused'}")
            if not economy.population:
                st.warning("The population is extinct. Reset or create a new scenario.")
            if economy.bank_equity <= 0:
                st.warning("The bank is insolvent: new credit is frozen. Deposits remain book claims; "
                           "there is no automatic bailout or deposit insurance in this model.")
        with slots["wealth"].container():
            a, b, c = st.columns(3)
            a.metric("Nominal net wealth", f"{last['Net wealth']:,.2f}", border=True)
            b.metric("Real net wealth", f"{last['Real net wealth']:,.2f}", border=True)
            c.metric("Net wealth Gini", "N/A (negative wealth)" if pd.isna(last['Gini']) else f"{last['Gini']:.3f}", border=True)
            if len(people):
                ordered = people.sort_values("Net wealth").reset_index(drop=True)
                ordered["Rank"] = range(1, len(ordered) + 1)
                bars = alt.Chart(ordered, mark=alt.MarkDef(type="bar")).encode(x="Rank:Q", y="Net wealth:Q",
                    tooltip=["Person:Q", "Age:Q", "Money:Q", "Bonds:Q", "Debt:Q", "Net wealth:Q"])
                st.altair_chart(bars, width="stretch", alt="Individual net wealth, including money, productive assets, bonds and debt")
            monetary_trend(trends, ["Net wealth", "Real net wealth"], "Nominal and real household net wealth")
            st.caption("Net wealth = deposits + productive assets at current prices + bonds at face value − loans and accrued interest. "
                       "The bank and public/producer sectors are reported separately, not assigned fictitious household ownership.")
        with slots["production"].container():
            a, b, c = st.columns(3)
            a.metric("Productive capacity", f"{economy.capacity:,.2f}", border=True)
            b.metric("Real output", f"{economy.output:,.2f}", border=True)
            c.metric("Population", f"{len(economy.population):,}", border=True)
            monetary_trend(trends, ["Productive capacity", "Output", "Real consumption", "Real investment"], "Production and goods use")
            st.caption("Output is limited by capital and working-age residents. Consumption uses goods; investment converts goods into capital. "
                       "Unsold goods expire each year. Money printing does not directly increase capacity; there is no wealth cap.")
        with slots["government"].container():
            a, b, c = st.columns(3)
            a.metric("Government money", f"{economy.accounts['Government']:,.2f}", border=True)
            b.metric("Government debt", f"{economy.government_debt:,.2f}", border=True)
            c.metric("Debt service shortfall", f"{last['Debt service shortfall']:,.2f}", border=True)
            allocation_view(economy.policy_budget,
                [last[f"{name} allocation fraction"] for name in economy.budget_allocations], economy.spent, key="monetary")
            st.caption("Allocation chart and amounts describe the last recorded year. Active settings above apply next year. "
                       "Debt principal repayment is included here as a cash outflow, not an operating expense.")
            st.caption("The policy budget includes all treasury money available before allocations, including financing. "
                       "Borrowing and fiat grants are not tax revenue. Current-year estates enter after spending, for next year.")
            monetary_trend(trends, ["Tax revenue", "Borrowing proceeds", "Money issued", "Estate revenue"], "Government funding sources")
            monetary_trend(trends, [f"{p} spent" for p in (*POLICIES, "Debt service")], "Government expenditure by policy")
            if last["Unpaid wealth tax"] > 0:
                st.caption(f"Uncollected wealth tax due to insufficient liquid money: {last['Unpaid wealth tax']:,.2f}. "
                           "This is reported but not carried as tax debt; there is no forced liquidation.")
        with slots["transfers"].container():
            a, b, c = st.columns(3)
            a.metric("UBI paid", f"{economy.spent['UBI']:,.2f}", border=True)
            b.metric("Pensions paid", f"{economy.spent['Pensions']:,.2f}", border=True)
            c.metric("Unfunded pension entitlement", f"{last['Pension shortfall']:,.2f}", border=True)
            st.caption(f"Active UBI allocation: {economy.shares[0]:.0%}; pensions: {economy.shares[1]:.0%} of the same total budget. "
                       "UBI is equal for all residents. Pension payments are equal among eligible retirees and limited to their own allocation.")
            monetary_trend(trends, ["UBI spent", "Pensions spent", "Pension shortfall"], "Transfers and pension shortfall")
        with slots["health"].container():
            a, b, c = st.columns(3)
            a.metric("Public healthcare paid", f"{economy.spent['Healthcare']:,.2f}", border=True)
            b.metric("Private premiums paid", f"{last['Private premiums']:,.2f}", border=True)
            c.metric("Deaths this year", f"{int(last['Deaths']):,}", border=True)
            monetary_trend(trends, ["Healthcare spent", "Private premiums"], "Healthcare funding")
            risk = pd.DataFrame([{"Age": age, "Care": label, "Death probability": economy.death_probability(age, 0, funded=funded,
                    risk_factor=economy.config.private_healthcare_mortality_factor if label == "Private" else None)}
                    for age in range(max(120, max((p.age for p in economy.population), default=0)) + 1)
                    for label, funded in [("Public", True), ("Private", False), ("Unfunded", False)]])
            chart = alt.Chart(risk, mark=alt.MarkDef(type="line")).encode(x="Age:Q", y=alt.Y("Death probability:Q", axis=alt.Axis(format=".0%")),
                                                       color="Care:N", tooltip=["Age:Q", "Care:N", "Death probability:Q"])
            st.altair_chart(chart, width="stretch", alt="Annual mortality risk by age for public, private and unfunded care")
            st.caption("Public funding is adjusted for prices; private premiums are price-indexed. Providers retain funds and pay income to households. "
                       "Healthcare quality is an illustrative rule, not a causal estimate. There is no maximum-age cutoff.")
        with slots["bank"].container():
            a, b, c = st.columns(3)
            a.metric("Bank equity", f"{economy.bank_equity:,.2f}", border=True)
            b.metric("Outstanding household loans", f"{last['Outstanding loans']:,.2f}", border=True)
            c.metric("Loan defaults this year", f"{last['Loan defaults']:,.2f}", border=True)
            monetary_trend(trends, ["Outstanding loans", "Bank equity", "Loan defaults"], "Credit and bank solvency")
            st.caption("Investment loans create deposits and matching liabilities. Repaying principal destroys deposits. "
                       "Interest moves value to bank equity; bank distributions return some to deposits. Defaults reduce bank assets and equity, "
                       "not existing deposits. New credit is constrained by bank capital, reserves and any broad-money ceiling.")
        with slots["money"].container():
            a, b, c = st.columns(3)
            a.metric("Base money", f"{economy.reserves:,.2f}", border=True)
            b.metric("Broad money", f"{economy.broad_money:,.2f}", border=True)
            c.metric("Inflation this year", f"{economy.inflation:.2%}", border=True)
            monetary_trend(trends, ["Base money", "Broad money"], "Money supplies")
            monetary_trend(trends, ["Inflation"], "Inflation", percentage=True)
            monetary_trend(trends, ["Price level"], "Price level (starting year = 1)")
            st.caption("Base money = bank reserves. Broad money = all non-bank deposits, including treasury, goods producers and healthcare providers. "
                       "A base-money cap does not cap bank deposits. A broad-money cap also constrains bank credit and distributions. "
                       "Prices adjust to desired goods spending relative to output; annual changes are bounded at −10% / +25% for numerical stability.")
        with slots["age"].container():
            if len(people):
                chart = alt.Chart(people, mark=alt.MarkDef(type="bar")).encode(x=alt.X("Age:Q", bin=alt.Bin(step=10)), y="count()")
                st.altair_chart(chart, width="stretch", alt="Population age distribution in ten-year bins")
            monetary_trend(trends, ["Population", "Deaths"], "Population and deaths")
        with downloads.container():
            with st.expander("Accounts, contracts and downloads"):
                st.dataframe(pd.DataFrame(economy.balance_sheets()), hide_index=True, alt="Sector assets, liabilities and net worth")
                st.caption("The fiat issuer starts with negative equity equal to issued base money; additional grants reduce it further. "
                           "It is not subject to the commercial bank's solvency rule. Consolidated sector net worth equals real capital valued at current prices.")
                errors = {name: float(last.get(name, 0)) for name in ("Money balance error", "Base money balance error", "Government balance error")}
                st.json(errors)
                st.dataframe(people, hide_index=True, alt="Individual money, capital, bonds, loans, net wealth, pensions and healthcare")
                contracts = {"loans": [asdict(x) for x in economy.loans], "bonds": [asdict(x) for x in economy.bonds]}
                st.json(contracts)
                for label, frame, filename in [
                    ("Download monetary history CSV", history, "monetary-history.csv"),
                    ("Download monetary population CSV", people, "monetary-population.csv"),
                    ("Download sector balance sheets CSV", pd.DataFrame(economy.balance_sheets()), "sector-balances.csv"),
                    ("Download transaction ledger CSV", pd.DataFrame(economy.transactions), "monetary-transactions.csv")]:
                    st.download_button(label, frame.to_csv(index=False), filename, "text/csv")
                settings = {"model": "monetary-v1", "seed": economy.seed, "initial_parameters": asdict(economy.initial_config),
                            "current_parameters": asdict(economy.config), "policy_changes": list(economy.policy_changes), **contracts}
                st.download_button("Download monetary scenario settings", json.dumps(settings, indent=2), "monetary-scenario.json", "application/json")
                st.caption("History retains 10,000 years; the transaction ledger retains the latest 10,000 entries, including labeled non-cash events. "
                           "Policy history retains 1,000 changes. Settings describe a reproducible run, not a full state checkpoint.")
    monetary_dashboard()
