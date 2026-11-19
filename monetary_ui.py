"""Section-local controls and a live dashboard for the monetary model."""
from dataclasses import asdict, replace
import json
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from budget import LEGACY_FIELDS, POLICIES
from budget_ui import allocation_view
from monetary import COMPARISON_NAMES, MonetarySimulation, comparison_config, restore_monetary_simulation
from ui_components import display_controls, playback_controls, policy_fields, sync_widget_value, widget_default
from dashboard_charts import trend_chart, wealth_distribution, tax_curve, age_distribution, series_scale

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
SHORT_LABELS = {**{name: f"{policy} (%)" for name, policy in zip(
    (*LEGACY_FIELDS, "debt_service_fraction"), (*POLICIES, "Debt service"))},
    "private_investment_fraction": "Private investment (%)", "producer_dividend_fraction": "Profit distributed (%)",
    "failed_investment_loss": "Capital lost on failure (%)", "investment_risk": "Failure chance (%)",
    "private_healthcare_max_wealth_fraction": "Maximum affordable share (%)", "private_healthcare_mortality_factor": "Private risk fraction (%)",
    "private_healthcare_premium": "Private premium", "private_healthcare_age_loading": "Age surcharge",
    "loan_demand": "Annual loan demand (%)", "borrowing_limit": "Debt / collateral limit", "default_after": "Missed payments before default",
    "bond_purchase_fraction": "Money offered for bonds (%)", "bank_bond_fraction": "Bank share of new bonds (%)",
    "principal_first": "Principal before coupons", "capital_ratio": "Minimum capital ratio (%)", "reserve_ratio": "Minimum reserve ratio (%)"}


def sync_monetary_controls():
    config = st.session_state.monetary_simulation.config
    for specs in SPECS.values():
        for name, *_ in specs:
            value = getattr(config, name)
            sync_widget_value(f"m_{name}", float(value * 100) if name in PERCENT else value)
    st.session_state.monetary_notices = {}


def sync_monetary_initial_controls():
    sim = st.session_state.monetary_simulation
    for key, value in {"m_seed": sim.seed, "m_initial_population": sim.config.pop_size,
        "m_initial_money": float(sim.config.init_wealth), "m_initial_capacity": float(sim.config.logistic_capacity),
        "m_initial_producer": float(sim.config.initial_producer_money), "m_initial_bank": float(sim.config.initial_bank_capital)}.items():
        sync_widget_value(key, value)


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
    with st.popover(title, icon=":material/tune:", key=f"m_settings_{group}"):
        if group == "allocation":
            st.caption("Each % uses the same total treasury budget, including financing. "
                       "Total must be ≤100%; unused funds stay with government.")
        with st.form(f"m_policy_{group}", border=False, enter_to_submit=False):
            policy_fields(SPECS[group], config, prefix="m_", percentages=PERCENT, labels=SHORT_LABELS)
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


def monetary_trend(history, columns, title, percentage=False, *, domain=None, area=False):
    trend_chart(history, columns, title, percentage=percentage, domain=domain, area=area, x_title="Year")


def observed_value(value, pattern):
    return "Not recorded" if pd.isna(value) else format(value, pattern)


def monetary_workspace():
    if "monetary_simulation" not in st.session_state:
        st.session_state.monetary_simulation = MonetarySimulation()
        st.session_state.monetary_running = False
    else:
        st.session_state.monetary_simulation = restore_monetary_simulation(st.session_state.monetary_simulation)
    sim = st.session_state.monetary_simulation
    st.caption("Monetary economy · experimental accounting model, not a forecast")
    with st.sidebar:
        st.header("Monetary workspace", anchor=False)
        scenario_tab, display_tab = st.tabs(["Scenario", "Display"])
        scenario_tab.selectbox("Comparison scenario", COMPARISON_NAMES, key="m_comparison")
        scenario_tab.button("Load comparison scenario", key="m_load_comparison", on_click=load_comparison, width="stretch")
        with scenario_tab, st.form("m_scenario", border=False, enter_to_submit=False):
            st.subheader("Initial conditions")
            seed = st.number_input("Random seed", 0, 1000000, value=widget_default("m_seed", sim.seed), key="m_seed")
            pop = st.number_input("Starting population", 1, 10000, value=widget_default("m_initial_population", sim.config.pop_size), key="m_initial_population")
            money = st.number_input("Initial money per person", 0.01, 1000000.0, value=widget_default("m_initial_money", float(sim.config.init_wealth)), key="m_initial_money")
            capacity = st.number_input("Initial productive capacity", 0.0, 1000000000.0,
                                        value=widget_default("m_initial_capacity", float(sim.config.logistic_capacity)), key="m_initial_capacity")
            producer = st.number_input("Initial producer money", 0.0, 1000000000.0,
                                        value=widget_default("m_initial_producer", float(sim.config.initial_producer_money)), key="m_initial_producer")
            bank = st.number_input("Initial bank capital / reserves", 0.0, 1000000000.0,
                                    value=widget_default("m_initial_bank", float(sim.config.initial_bank_capital)), key="m_initial_bank")
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
        with display_tab:
            display = display_controls(monetary=True)

    playback = playback_controls("monetary_simulation", "monetary_running", monetary=True, reset_callback=reset_monetary)
    mode, interval, per_refresh = playback.mode, playback.interval, playback.steps_per_refresh
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
            if controls:
                with st.container(horizontal=True):
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
        # Old sessions retain their history; unavailable new observations are
        # gaps, not invented zero tax/mortality readings.
        for column in ("Minimum applied tax rate", "Maximum applied tax rate", "Effective wealth tax rate", "Baseline mortality",
                       "Observed mortality", "Public healthcare users", "Private healthcare users", "Pension eligible", "UBI per person",
                       "Failed private investments", "Private capital shortfall", "Private capital added",
                       "Opening government money", "Total government spending", "Government balance error"):
            if column not in history:
                history[column] = float("nan")
        trends = history.tail(int(display["window"]))
        last = history.iloc[-1]
        people = pd.DataFrame(economy.person_rows())
        if not len(people):
            people = pd.DataFrame(columns=["Person", "Age", "Net wealth", "Money", "Debt"])
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
            shares = wealth_distribution(people, display["groups"], display["individuals"], display["logarithmic"], value="Net wealth")
            left, right = st.columns(2)
            with left:
                monetary_trend(trends, ["Net wealth", "Real net wealth"], "Nominal and real household net wealth")
            with right:
                monetary_trend(trends, ["Gini"], "Net wealth inequality over time", domain=[0, 1])
            st.caption("Net wealth = deposits + productive assets at current prices + bonds at face value − loans and accrued interest. "
                       "The bank and public/producer sectors are reported separately, not assigned fictitious household ownership.")
        with slots["production"].container():
            a, b, c = st.columns(3)
            a.metric("Productive capacity", f"{economy.capacity:,.2f}", border=True)
            b.metric("Real output", f"{economy.output:,.2f}", border=True)
            c.metric("Population", f"{len(economy.population):,}", border=True)
            monetary_trend(trends, ["Productive capacity", "Output", "Real consumption", "Real investment"], "Production and goods use")
            monetary_trend(trends, ["Real net wealth", "Productive capacity"], "Real household net wealth and productive capacity")
            st.caption("Both series use current-price-deflated units, but net financial claims and productive capital are different concepts. "
                       "Productive capacity is not a wealth ceiling; there is no legacy wealth-cap reference line.")
            monetary_trend(trends, ["Private capital added", "Private capital shortfall"], "Private investment outcomes")
            st.caption(f"Failed private investments last year: {observed_value(last['Failed private investments'], ',.0f')}. "
                       "Shortfall is capital not created relative to full efficiency, not destroyed money or losses on existing wealth.")
            st.caption("Output is limited by capital and working-age residents. Consumption uses goods; investment converts goods into capital. "
                       "Unsold goods expire each year. Money printing does not directly increase capacity; there is no wealth cap.")
        with slots["government"].container():
            a, b, c = st.columns(3)
            a.metric("Government money", f"{economy.accounts['Government']:,.2f}", border=True)
            b.metric("Government debt", f"{economy.government_debt:,.2f}", border=True)
            c.metric("Debt service shortfall", f"{last['Debt service shortfall']:,.2f}", border=True)
            a, b = st.columns(2)
            a.metric("Tax revenue last year", f"{last['Tax revenue']:,.2f}", border=True)
            b.metric("Government cash outflows last year", observed_value(last['Total government spending'], ',.2f'), border=True)
            allocation_view(economy.policy_budget,
                [last[f"{name} allocation fraction"] for name in economy.budget_allocations], economy.spent, key="monetary")
            st.caption("Last recorded year; active settings apply next year. Debt principal is included as a cash outflow, not an operating expense.")
            left, right = st.columns(2)
            with left:
                tax_curve(people["Net wealth"].clip(lower=0).to_numpy(), economy.config, net=True)
            with right:
                effective = last['Effective wealth tax rate']
                st.metric("Effective net wealth tax last year", observed_value(effective, ".2%"), border=True)
                monetary_trend(trends, ["Minimum applied tax rate", "Effective wealth tax rate", "Maximum applied tax rate"],
                               "Applied net wealth tax rates", percentage=True)
            left, right = st.columns(2)
            with left:
                monetary_trend(trends, ["Government money", "Government debt"], "Government money and debt")
            with right:
                monetary_trend(trends, ["Tax revenue", "Borrowing proceeds", "Money issued", "Estate revenue"], "Government funding sources")
            monetary_trend(trends, [f"{p} spent" for p in (*POLICIES, "Debt service")], "Government expenditure by policy", area=True)
            finance_columns = ["Step", "Opening government money", "Tax revenue", "Borrowing proceeds", "Money issued",
                               "Estate revenue", *[f"{p} spent" for p in (*POLICIES, "Debt service")],
                               "Total government spending", "Government money", "Government balance error"]
            with st.expander("Government accounts"):
                st.dataframe(history[finance_columns].tail(1), hide_index=True, alt="Latest annual government cash reconciliation")
                st.caption("Closing money = opening money + taxes + borrowing + issuance + estates − policy payments − debt service. "
                           "Debt principal is a cash outflow, not an operating expense.")
            if last["Unpaid wealth tax"] > 0:
                st.caption(f"Uncollected wealth tax due to insufficient liquid money: {last['Unpaid wealth tax']:,.2f}. "
                           "This is reported but not carried as tax debt; there is no forced liquidation.")
        with slots["transfers"].container():
            a, b, c = st.columns(3)
            a.metric("UBI paid", f"{economy.spent['UBI']:,.2f}", border=True)
            b.metric("Pensions paid", f"{economy.spent['Pensions']:,.2f}", border=True)
            c.metric("Unfunded pension entitlement", f"{last['Pension shortfall']:,.2f}", border=True)
            if not pd.isna(last['UBI per person']):
                st.caption(f"UBI per recipient: {last['UBI per person']:,.4f} · Pension-eligible residents: {last['Pension eligible']:,.0f} (before deaths).")
            st.caption(f"Active UBI allocation: {economy.shares[0]:.0%}; pensions: {economy.shares[1]:.0%} of the same total budget. "
                       "UBI is equal for all residents. Pension payments are equal among eligible retirees and limited to their own allocation.")
            monetary_trend(trends, ["UBI spent", "Pensions spent", "Pension shortfall"], "Transfers and pension shortfall")
        with slots["health"].container():
            a, b, c = st.columns(3)
            a.metric("Public healthcare paid", f"{economy.spent['Healthcare']:,.2f}", border=True)
            b.metric("Private premiums paid", f"{last['Private premiums']:,.2f}", border=True)
            c.metric("Deaths this year", f"{int(last['Deaths']):,}", border=True)
            left, right = st.columns(2)
            with left:
                monetary_trend(trends, ["Baseline mortality", "Public mortality", "Observed mortality"], "Mortality over time", percentage=True)
            with right:
                monetary_trend(trends, ["Healthcare spent", "Private premiums"], "Healthcare funding")
            a, b, c = st.columns(3)
            a.metric("Public care users", observed_value(last['Public healthcare users'], ",.0f"), border=True)
            b.metric("Private care users", observed_value(last['Private healthcare users'], ",.0f"), border=True)
            c.metric("Healthcare sector money", f"{economy.accounts['Healthcare']:,.2f}", border=True)
            monetary_trend(trends, ["Public healthcare users", "Private healthcare users"], "Healthcare choices over time")
            risk = pd.DataFrame([{"Age": age, "Care": label, "Death probability": economy.death_probability(age, 0, funded=funded,
                    risk_factor=economy.config.private_healthcare_mortality_factor if label == "Private" else None)}
                    for age in range(max(120, max((p.age for p in economy.population), default=0)) + 1)
                    for label, funded in [("Public", True), ("Private", False), ("Unfunded", False)]])
            chart = alt.Chart(risk, mark=alt.MarkDef(type="line")).encode(x="Age:Q", y=alt.Y("Death probability:Q", axis=alt.Axis(format=".0%")),
                                                       color=alt.Color("Care:N", scale=series_scale(["Public", "Private", "Unfunded"])),
                                                        tooltip=["Age:Q", "Care:N", "Death probability:Q"])
            st.subheader("Death risk by age")
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
            age_distribution(people, display["age_bin"], display["age_unit"])
            monetary_trend(trends, ["Population", "Deaths"], "Population and deaths")
        with downloads.container():
            with st.expander("Accounts, contracts and downloads"):
                st.dataframe(pd.DataFrame(economy.balance_sheets()), hide_index=True, alt="Sector assets, liabilities and net worth")
                st.caption("The fiat issuer starts with negative equity equal to issued base money; additional grants reduce it further. "
                           "It is not subject to the commercial bank's solvency rule. Consolidated sector net worth equals real capital valued at current prices.")
                errors = {name: float(last.get(name, 0)) for name in ("Money balance error", "Base money balance error", "Government balance error")}
                st.dataframe(pd.DataFrame({"Reconciliation": errors.keys(), "Error": errors.values()}), hide_index=True,
                             alt="Money, base money and government account reconciliation errors")
                st.dataframe(people, hide_index=True, alt="Individual money, capital, bonds, loans, net wealth, pensions and healthcare")
                contracts = {"loans": [asdict(x) for x in economy.loans], "bonds": [asdict(x) for x in economy.bonds]}
                st.subheader("Percentile wealth shares")
                st.dataframe(shares, hide_index=True, alt="Net wealth amounts and shares by population percentile")
                st.subheader("Loan contracts")
                st.dataframe(pd.DataFrame(contracts["loans"]), hide_index=True, alt="Outstanding loans, terms and arrears")
                st.subheader("Government bond contracts")
                st.dataframe(pd.DataFrame(contracts["bonds"]), hide_index=True, alt="Bondholders, principal, coupon and maturity")
                if economy.policy_changes:
                    st.subheader("Policy changes")
                    st.dataframe(pd.DataFrame(economy.policy_changes), hide_index=True, alt="Policy changes and their effective years")
                for label, frame, filename in [
                    ("Download monetary history CSV", history, "monetary-history.csv"),
                     ("Download monetary population CSV", people, "monetary-population.csv"),
                     ("Download finance ledger CSV", history[finance_columns], "monetary-finances.csv"),
                    ("Download sector balance sheets CSV", pd.DataFrame(economy.balance_sheets()), "sector-balances.csv"),
                    ("Download transaction ledger CSV", pd.DataFrame(economy.transactions), "monetary-transactions.csv")]:
                    st.download_button(label, frame.to_csv(index=False), filename, "text/csv")
                settings = {"model": "monetary-v1", "seed": economy.seed, "initial_parameters": asdict(economy.initial_config),
                            "current_parameters": asdict(economy.config), "policy_changes": list(economy.policy_changes), **contracts}
                st.download_button("Download monetary scenario settings", json.dumps(settings, indent=2), "monetary-scenario.json", "application/json")
                st.caption("History retains 10,000 years; the transaction ledger retains the latest 10,000 entries, including labeled non-cash events. "
                           "Policy history retains 1,000 changes. Settings describe a reproducible run, not a full state checkpoint.")
    monetary_dashboard()
