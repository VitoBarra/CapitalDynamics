"""Section-local controls and a live dashboard for the monetary model."""
from dataclasses import asdict, replace
import json
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from capital_dynamics.budget import ALLOCATION_FIELDS, POLICIES
from capital_dynamics.budget_ui import allocation_view
from capital_dynamics.calibration import REFERENCE_BENCHMARKS, RETRIEVED_ON
from capital_dynamics.currency import column_unit, euro, export_frame
from capital_dynamics.help_text import METRIC_HELP, POLICY_HELP, SECTION_HELP, TABLE_HELP
from capital_dynamics.monetary import COMPARISON_NAMES, MonetarySimulation, comparison_config
from capital_dynamics.ui_components import display_controls, playback_controls, policy_fields, sync_widget_value, widget_default
from capital_dynamics.dashboard_charts import trend_chart, wealth_distribution, tax_curve, age_distribution, series_scale

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
                   for name, policy in zip(ALLOCATION_FIELDS, POLICIES)],
    "bonds": [("government_borrowing", "Enable government borrowing"),
              ("borrowing_target", "Additional policy borrowing per year (€)", 0.0, 1000000.0, 1.0),
              ("debt_ceiling", "Government debt ceiling (€)", 0.0, 1000000000.0, 10.0),
              ("bond_rate", "Reference bond yield (%)", 0.0, 100.0, 0.1),
              ("bond_term", "New bond maturity (years)", 1, 100, 1),
              ("bond_purchase_fraction", "Adult money offered for bonds (%)", 0.0, 100.0, 1.0),
              ("bank_bond_fraction", "Borrowing target offered to bank (%)", 0.0, 100.0, 1.0),
              ("sovereign_base_spread", "Base sovereign spread (%)", 0.0, 50.0, 0.1),
              ("sovereign_debt_sensitivity", "Spread per debt / output unit (%)", 0.0, 50.0, 0.1),
              ("sovereign_arrears_sensitivity", "Spread at 100% overdue debt (%)", 0.0, 50.0, 0.5),
              ("sovereign_default_penalty", "Spread penalty per sovereign default (%)", 0.0, 50.0, 0.5),
              ("sovereign_reputation_recovery", "Annual reputation penalty recovery (%)", 0.0, 100.0, 1.0),
              ("sovereign_risk_aversion", "Investor sensitivity to sovereign spread", 0.0, 50.0, 0.5),
              ("sovereign_exclusion_years", "Full years excluded after sovereign default", 0, 20, 1)],
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
                 ("debt_service_limit", "Maximum debt service / income (%)", 0.0, 100.0, 1.0),
                 ("income_stress_fraction", "Underwriting income reduction (%)", 0.0, 100.0, 1.0),
                 ("loan_rate_stress", "Affordability interest-rate stress (%)", 0.0, 100.0, 0.1),
                 ("borrower_risk_spread", "Maximum borrower risk premium (%)", 0.0, 100.0, 0.1),
                 ("collateral_recovery_haircut", "Collateral liquidation discount (%)", 0.0, 100.0, 1.0),
                 ("default_cooldown", "Years without new credit after default", 0, 20, 1),
                ("capital_ratio", "Minimum bank equity / risk assets (%)", 0.0, 100.0, 1.0),
                ("reserve_ratio", "Minimum reserves / deposits (%)", 0.0, 100.0, 1.0),
                ("default_after", "Default after consecutive missed payments", 1, 20, 1),
                ("bank_dividend_fraction", "Distribute excess bank equity (%)", 0.0, 100.0, 1.0)],
    "money": [("policy_rate", "Policy interest rate (%)", 0.0, 100.0, 0.1),
              ("inflation_response", "Price adjustment speed (%)", 0.0, 100.0, 1.0),
              ("monetary_financing", "Allow fiat grants to government"),
              ("issuance_per_step", "Money issuance per year (€)", 0.0, 1000000.0, 1.0),
              ("money_cap", "Maximum money supply (€; 0 = no cap)", 0.0, 1000000000.0, 10.0),
              ("money_cap_type", "Supply constrained by cap", ["Base money", "Broad money"])],
    "demographics": [("birth_prob_max", "Peak annual birth probability (%)", 0.0, 100.0, 0.1),
                     ("death_base_prob", "Background annual death probability (%)", 0.0, 100.0, 0.01),
                     ("aging_risk_start", "Adult mortality reference age", 0, 100, 1),
                     ("aging_risk_rate", "Adult hazard at reference age", 0.0, 0.1, 0.001),
                     ("mortality_doubling_years", "Mortality doubling time (years)", 1.0, 20.0, 0.5)],
}
PERCENT = {spec[0] for specs in SPECS.values() for spec in specs if "%" in spec[1]}
SHORT_LABELS = {**{name: f"{policy} (%)" for name, policy in zip(
    ALLOCATION_FIELDS, POLICIES)},
    "private_investment_fraction": "Private investment (%)", "producer_dividend_fraction": "Profit distributed (%)",
    "failed_investment_loss": "Capital lost on failure (%)", "investment_risk": "Failure chance (%)",
    "private_healthcare_max_wealth_fraction": "Maximum affordable share (%)", "private_healthcare_mortality_factor": "Private risk fraction (%)",
    "private_healthcare_premium": "Private premium", "private_healthcare_age_loading": "Age surcharge",
    "loan_demand": "Annual loan demand (%)", "borrowing_limit": "Debt / collateral limit", "default_after": "Missed payments before default",
    "bond_purchase_fraction": "Money offered for bonds (%)", "bank_bond_fraction": "Bank share of new bonds (%)",
    "capital_ratio": "Minimum capital ratio (%)", "reserve_ratio": "Minimum reserve ratio (%)"}


def sync_monetary_controls():
    config = st.session_state.monetary_simulation.config
    for specs in SPECS.values():
        for name, *_ in specs:
            value = getattr(config, name)
            sync_widget_value(f"m_{name}", float(value * 100) if name in PERCENT else value)
    st.session_state.monetary_notices = {}
    st.session_state.sovereign_default_notice = None
    sync_widget_value("m_confirm_sovereign_default", False)


def sync_monetary_initial_controls():
    sim = st.session_state.monetary_simulation
    for key, value in {"m_seed": sim.seed, "m_initial_population": sim.config.pop_size,
        "m_initial_money": float(sim.config.initial_money_per_person), "m_initial_capacity": float(sim.config.initial_capacity),
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
    with st.popover(title, icon=":material/tune:", key=f"m_settings_{group}",
                    help=f"Open {title.lower()}. Edit values, then click Apply to change future years without restarting the economy."):
        if group == "allocation":
            st.caption("Each % uses the remaining treasury budget after mandatory debt service and any refinancing. "
                       "Total must be ≤100%; unused funds stay with government.")
        with st.form(f"m_policy_{group}", border=False, enter_to_submit=False):
            policy_fields(SPECS[group], config, prefix="m_", percentages=PERCENT, labels=SHORT_LABELS,
                          help_texts=POLICY_HELP)
            st.form_submit_button("Apply budget allocation" if group == "allocation" else "Apply policy",
                                  key=f"m_apply_{group}", on_click=apply_monetary_policy, args=(group,), width="stretch",
                                  help="Validate and save this section's edits for the next simulated year. Keeps residents and history; existing loan and bond contracts retain their terms.")
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

def queue_sovereign_default():
    sim = st.session_state.monetary_simulation
    if not st.session_state.get("m_confirm_sovereign_default", False):
        return
    try:
        sim.request_government_default()
    except ValueError as error:
        st.session_state.sovereign_default_notice = str(error)
        return
    st.session_state.sovereign_default_notice = None
    st.session_state.monetary_running = False


def cancel_sovereign_default():
    st.session_state.monetary_simulation.sovereign_default_pending = False


def sovereign_default_controls(sim):
    with st.popover("Sovereign default", icon=":material/warning:", key="m_default_menu",
                    help="Queue total cancellation of government bonds and coupon arrears for the next simulated year. This is not a reset and does not cancel private loans or deposits."):
        st.warning("Default wipes government bond claims held by residents, producers and the bank. "
                   "Creditors lose wealth; bank capital can fall below zero. New government borrowing is blocked temporarily "
                   "and a reputation spread raises future borrowing costs. Deposits are not automatically cancelled or bailed out.")
        confirmed = st.checkbox("I understand: cancel all government bond debt", key="m_confirm_sovereign_default",
                                value=widget_default("m_confirm_sovereign_default", False, kind="toggle"),
                                help="Confirmation is required. Cancellation takes effect when you next advance the simulation; existing wealth/history are not reset.")
        st.button("Queue sovereign default", key="m_queue_default", on_click=queue_sovereign_default,
                  disabled=not confirmed or not sim.bonds or sim.sovereign_default_pending,
                  help="Pause live playback and schedule default for the next simulated year. This action affects government bonds only.")
        if sim.sovereign_default_pending:
            st.button("Cancel queued default", key="m_cancel_default", on_click=cancel_sovereign_default,
                      help="Cancel the pending default before advancing. An already executed default cannot be undone except by resetting the scenario.")
        if st.session_state.get("sovereign_default_notice"):
            st.error(st.session_state.sovereign_default_notice)


def monetary_trend(history, columns, title, percentage=False, *, domain=None, area=False):
    trend_chart(history, columns, title, percentage=percentage, domain=domain, area=area)


def observed_value(value, pattern):
    return "Not recorded" if pd.isna(value) else format(value, pattern)


def table_columns(frame):
    """Currency and physical units are explicit without changing numeric data."""
    columns = {}
    for name in frame.columns:
        unit = column_unit(name)
        help_text = TABLE_HELP.get(name)
        if unit.startswith("EUR"):
            label = f"{name} ({unit})"
            columns[name] = st.column_config.NumberColumn(label, format="€%.2f", help=help_text)
        elif unit:
            columns[name] = st.column_config.NumberColumn(f"{name} ({unit})", help=help_text)
        elif help_text:
            columns[name] = st.column_config.Column(help=help_text)
    return columns


def monetary_workspace():
    if "monetary_simulation" not in st.session_state:
        st.session_state.monetary_simulation = MonetarySimulation()
        st.session_state.monetary_running = False
    sim = st.session_state.monetary_simulation
    st.caption("Monetary economy · experimental accounting model, not a forecast")
    st.caption("Currency: euro (€ / EUR). Real wealth is in year-0 euros; capital and goods use physical model units. "
               "This is not a calibrated model of the euro-area economy.")
    st.caption("Choose or create a scenario in the sidebar, then advance years or start Live mode. "
               "Hover over the help icons for explanations; settings take effect only after Apply.")
    with st.sidebar:
        st.header("Monetary workspace", anchor=False)
        scenario_tab, display_tab = st.tabs(["Scenario", "Display"])
        scenario_tab.selectbox("Comparison scenario", COMPARISON_NAMES, key="m_comparison",
                               help="Choose a preset illustrating borrowing, credit or money-creation rules. Selection alone does not change the economy; click Load to start it.")
        scenario_tab.button("Load comparison scenario", key="m_load_comparison", on_click=load_comparison, width="stretch",
                            help="Replace the current economy and history with the selected preset at year zero. Resets initial conditions and policies, discards unapplied edits and pauses playback.")
        with scenario_tab, st.form("m_scenario", border=False, enter_to_submit=False):
            st.subheader("Initial conditions", help="Starting values for a new economy. Editing these fields does not change the current run until you click Create monetary scenario.")
            seed = st.number_input("Random seed", 0, 1000000, value=widget_default("m_seed", sim.seed), key="m_seed",
                                   help="Controls random starting residents and events. The same seed, initial settings and sequence of policy changes reproduce the same run.")
            pop = st.number_input("Starting population", 1, 10000, value=widget_default("m_initial_population", sim.config.pop_size), key="m_initial_population",
                                  help="Number of residents created at year zero. Births and deaths change this later; larger populations require more computation.")
            money = st.number_input("Initial money per person (€)", 0.01, 1000000.0, value=widget_default("m_initial_money", float(sim.config.initial_money_per_person)), key="m_initial_money",
                                    help="Starting euro deposit for each resident. Also anchors pension targets, private premiums and annual loan demand.")
            capacity = st.number_input("Initial productive capacity", 0.0, 1000000000.0,
                                        value=widget_default("m_initial_capacity", float(sim.config.initial_capacity)), key="m_initial_capacity",
                                        help="Total productive capital at year zero, in real units. Limits goods output, not household wealth; investment and depreciation change it later.")
            producer = st.number_input("Initial producer money (€)", 0.0, 1000000000.0,
                                        value=widget_default("m_initial_producer", float(sim.config.initial_producer_money)), key="m_initial_producer",
                                        help="Starting deposits held by goods producers, separate from household money. These funds help pay wages before sales revenue arrives.")
            bank = st.number_input("Initial bank capital / reserves (€)", 0.0, 1000000000.0,
                                    value=widget_default("m_initial_bank", float(sim.config.initial_bank_capital)), key="m_initial_bank",
                                    help="Initial bank equity backed by additional reserves. Provides a cushion against loan losses and supports lending under capital and reserve constraints.")
            if st.form_submit_button("Create monetary scenario", key="m_new_scenario", width="stretch",
                                     help="Replace the current economy and history with these initial conditions and seed at year zero. Keeps active policies, discards unapplied policy edits and pauses playback."):
                try:
                    new = MonetarySimulation(replace(sim.config, pop_size=int(pop), initial_money_per_person=float(money),
                        initial_capacity=float(capacity), initial_producer_money=float(producer), initial_bank_capital=float(bank)), int(seed))
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.session_state.monetary_simulation = new
                    st.session_state.monetary_running = False
                    st.session_state.monetary_reset_error = None
                    sync_monetary_controls()
                    sim = new
        with display_tab:
            display = display_controls()

    playback = playback_controls("monetary_simulation", "monetary_running", reset_callback=reset_monetary)
    mode, interval, per_refresh = playback.mode, playback.interval, playback.steps_per_refresh
    if st.session_state.get("monetary_reset_error"):
        st.error(st.session_state.monetary_reset_error + " Adjust the money cap before resetting.")

    slots = {}
    sections = [
        ("wealth", "Current wealth distribution", []),
        ("living", "Living standards and income", []),
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
            st.header(title, help=SECTION_HELP[name])
            if controls:
                with st.container(horizontal=True):
                    for group, label in controls:
                        monetary_controls(group, label)
                    if name == "government":
                        sovereign_default_controls(sim)
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
            if economy.prudential_equity <= 0:
                st.warning("The bank has no positive prudential capital: new credit is frozen. Deposits remain book claims; "
                            "there is no automatic bailout or deposit insurance in this model.")
            if economy.sovereign_default_pending:
                st.warning("Sovereign default is queued. The next simulated year cancels government bonds and arrears, not household loans or deposits.")
            if not economy.sovereign_market_access:
                st.warning("Government bond market access is suspended after sovereign default. "
                           "Treasury spending must rely on remaining cash, taxes and any permitted fiat grants.")
        with slots["wealth"].container():
            a, b, c = st.columns(3)
            a.metric("Nominal net wealth", euro(last['Net wealth']), border=True, help=METRIC_HELP["Nominal net wealth"])
            b.metric("Real net wealth", euro(last['Real net wealth']), border=True, help=METRIC_HELP["Real net wealth"])
            c.metric("Net wealth Gini", "N/A (negative wealth)" if pd.isna(last['Gini']) else f"{last['Gini']:.3f}", border=True, help=METRIC_HELP["Net wealth Gini"])
            shares = wealth_distribution(people, display["groups"], display["individuals"], display["logarithmic"])
            left, right = st.columns(2)
            with left:
                monetary_trend(trends, ["Net wealth", "Real net wealth"], "Nominal and real household net wealth")
            with right:
                monetary_trend(trends, ["Gini"], "Net wealth inequality over time", domain=[0, 1])
            st.caption("Net wealth = deposits + productive assets at current prices + government bonds at market value − loans and accrued interest. "
                       "The bank and public/producer sectors are reported separately, not assigned fictitious household ownership.")
        with slots["living"].container():
            a, b, c = st.columns(3)
            a.metric("Median disposable income", euro(last["Median disposable income"]), border=True,
                     help=METRIC_HELP["Median disposable income"])
            b.metric("Relative low-income share", observed_value(last["Relative low-income share"], ".1%"), border=True,
                     help=METRIC_HELP["Relative low-income share"])
            c.metric("Consumption per person", euro(last["Consumption per person"]), border=True,
                     help=METRIC_HELP["Consumption per person"])
            a, b, c = st.columns(3)
            a.metric("Median real disposable income", euro(last["Median real disposable income"]), border=True,
                     help=METRIC_HELP["Median real disposable income"])
            b.metric("Pension replacement ratio", observed_value(last["Pension replacement ratio"], ".1%"), border=True,
                     help=METRIC_HELP["Pension replacement ratio"])
            c.metric("Non-positive income share", observed_value(last["Non-positive income share"], ".1%"), border=True,
                     help=METRIC_HELP["Non-positive income share"])
            monetary_trend(trends, ["Median disposable income", "Median real disposable income"], "Personal disposable income")
            monetary_trend(trends, ["Relative low-income share", "Non-positive income share"], "Low-income indicators (personal-income proxies)",
                           percentage=True)
            monetary_trend(trends, ["Consumption per person"], "Consumption spending per resident")
            monetary_trend(trends, ["Real consumption per person"], "Goods consumed per resident")
            monetary_trend(trends, ["Pension replacement ratio"], "Pension replacement ratio", percentage=True)
            st.caption("Annual measures use residents present before deaths, aging and births, not the closing population. "
                       "Income excludes loans, asset sales, principal repayments, inheritance and capital gains. "
                       "Private premiums and consumption are spending, not income deductions. Year zero has no annual observations.")
            st.caption("Low income means personal disposable income below 60% of its positive median. "
                       "There is no household pooling/equivalisation, so this is not the official EU poverty rate. "
                       "When the median is non-positive, the relative measure is undefined; non-positive income share remains available.")
            with st.expander("Official data references and calibration status"):
                st.caption(f"Source snapshot retrieved {RETRIEVED_ON}; definitions and periods differ. "
                           "These are reference targets, not fitted defaults. No data are fetched during simulation.")
                references = pd.DataFrame(REFERENCE_BENCHMARKS)
                st.dataframe(references, hide_index=True, column_config={
                    "Source": st.column_config.LinkColumn(help="Official source URL for the observation or methodology."),
                    "Use": st.column_config.TextColumn(help="How the observation can be used, and why direct substitution may be invalid."),
                })
                st.caption("Credit limits, recovery discounts and risk-score weights are transparent scenario assumptions—not EBA-prescribed thresholds or fitted default probabilities.")
        with slots["production"].container():
            a, b, c = st.columns(3)
            a.metric("Productive capacity", f"{economy.capacity:,.2f}", border=True, help=METRIC_HELP["Productive capacity"])
            b.metric("Real output", f"{economy.output:,.2f}", border=True, help=METRIC_HELP["Real output"])
            c.metric("Population", f"{len(economy.population):,}", border=True, help=METRIC_HELP["Population"])
            monetary_trend(trends, ["Productive capacity", "Output", "Real consumption", "Real investment"], "Production and goods use")
            monetary_trend(trends, ["Real net wealth", "Productive capacity"], "Real household net wealth and productive capacity")
            st.caption("Real net wealth is measured in year-0 euros; productive capacity is measured in capital units. "
                       "These are different quantities, and productive capacity is not a wealth ceiling.")
            monetary_trend(trends, ["Private capital added", "Private capital shortfall"], "Private investment outcomes")
            st.caption(f"Failed private investments last year: {observed_value(last['Failed private investments'], ',.0f')}. "
                       "Shortfall is capital not created relative to full efficiency, not destroyed money or losses on existing wealth.")
            st.caption("Output is limited by capital and working-age residents. Consumption uses goods; investment converts goods into capital. "
                       "Unsold goods expire each year. Money printing does not directly increase capacity; there is no wealth cap.")
        with slots["government"].container():
            a, b, c = st.columns(3)
            a.metric("Government money", euro(economy.accounts['Government']), border=True, help=METRIC_HELP["Government money"])
            b.metric("Government debt", euro(economy.government_debt), border=True, help=METRIC_HELP["Government debt"])
            c.metric("Debt service shortfall", euro(last['Debt service shortfall']), border=True, help=METRIC_HELP["Debt service shortfall"])
            a, b, c = st.columns(3)
            a.metric("Government arrears", euro(last["Government arrears"]), border=True, help=METRIC_HELP["Government arrears"])
            b.metric("Sovereign spread", f"{last['Sovereign spread']:.2%}", border=True, help=METRIC_HELP["Sovereign spread"])
            c.metric("New bond yield", f"{last['New bond yield']:.2%}", border=True, help=METRIC_HELP["New bond yield"])
            a, b, c = st.columns(3)
            a.metric("Mandatory debt service paid", euro(last["Debt service spent"]), border=True, help=METRIC_HELP["Mandatory debt service paid"])
            b.metric("Average bond price", observed_value(last["Average bond price"], ".3f"), border=True, help=METRIC_HELP["Average bond price"])
            c.metric("Sovereign defaults", f"{int(last['Sovereign defaults']):,}", border=True, help=METRIC_HELP["Sovereign defaults"])
            a, b = st.columns(2)
            a.metric("Tax revenue last year", euro(last['Tax revenue']), border=True, help=METRIC_HELP["Tax revenue last year"])
            b.metric("Government cash outflows last year", euro(last['Total government spending']), border=True, help=METRIC_HELP["Government cash outflows last year"])
            allocation_view(economy.policy_budget,
                [last[f"{name} allocation fraction"] for name in economy.budget_allocations], economy.spent, key="monetary")
            st.caption("Last recorded year; active settings apply next year. Debt principal is included as a cash outflow, not an operating expense.")
            st.caption("Debt service is mandatory and paid before the four policy allocations. "
                       "If cash is insufficient, refinancing is attempted when borrowing is enabled; otherwise principal and coupons remain owed. "
                       "The debt ceiling limits net borrowing, but matched redemptions can refinance matured principal without a net increase.")
            monetary_trend(trends, ["Government debt", "Government market debt", "Government arrears"], "Contractual debt, market value and arrears")
            monetary_trend(trends, ["Sovereign spread", "New bond yield"], "Sovereign borrowing costs", percentage=True)
            monetary_trend(trends, ["Average bond price"], "Government bond price per euro of claim")
            left, right = st.columns(2)
            with left:
                tax_curve(people["Net wealth"].clip(lower=0).to_numpy(), economy.config)
            with right:
                effective = last['Effective wealth tax rate']
                st.metric("Effective net wealth tax last year", observed_value(effective, ".2%"), border=True, help=METRIC_HELP["Effective net wealth tax last year"])
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
                st.dataframe(history[finance_columns].tail(1), hide_index=True,
                             column_config=table_columns(history[finance_columns]),
                             alt="Latest annual government cash reconciliation")
                st.caption("Closing money = opening money + taxes + borrowing + issuance + estates − policy payments − debt service. "
                            "Debt principal is a cash outflow, not an operating expense.")
                debt_columns = ["Step", "Opening government debt", "Borrowing proceeds", "Bond interest accrued",
                                "Debt service spent", "Estate debt cancellation", "Sovereign debt written off",
                                "Government debt", "Government debt balance error"]
                st.dataframe(history[debt_columns].tail(1), hide_index=True, column_config=table_columns(history[debt_columns]),
                             alt="Government nominal debt reconciliation, including carried interest and explicit write-offs")
            if last["Unpaid wealth tax"] > 0:
                st.caption(f"Uncollected wealth tax due to insufficient liquid money: {euro(last['Unpaid wealth tax'])}. "
                           "This is reported but not carried as tax debt; there is no forced liquidation.")
        with slots["transfers"].container():
            a, b, c = st.columns(3)
            a.metric("UBI paid", euro(economy.spent['UBI']), border=True, help=METRIC_HELP["UBI paid"])
            b.metric("Pensions paid", euro(economy.spent['Pensions']), border=True, help=METRIC_HELP["Pensions paid"])
            c.metric("Unfunded pension entitlement", euro(last['Pension shortfall']), border=True, help=METRIC_HELP["Unfunded pension entitlement"])
            if not pd.isna(last['UBI per person']):
                st.caption(f"UBI per recipient: {euro(last['UBI per person'], 4)} · Pension-eligible residents: {last['Pension eligible']:,.0f} (before deaths).")
            st.caption(f"Active UBI allocation: {economy.shares[0]:.0%}; pensions: {economy.shares[1]:.0%} of the same total budget. "
                       "UBI is equal for all residents. Pension payments are equal among eligible retirees and limited to their own allocation.")
            monetary_trend(trends, ["UBI spent", "Pensions spent", "Pension shortfall"], "Transfers and pension shortfall")
        with slots["health"].container():
            a, b, c = st.columns(3)
            a.metric("Public healthcare paid", euro(economy.spent['Healthcare']), border=True, help=METRIC_HELP["Public healthcare paid"])
            b.metric("Private premiums paid", euro(last['Private premiums']), border=True, help=METRIC_HELP["Private premiums paid"])
            c.metric("Deaths this year", f"{int(last['Deaths']):,}", border=True, help=METRIC_HELP["Deaths this year"])
            left, right = st.columns(2)
            with left:
                monetary_trend(trends, ["Unfunded mortality", "Public care mortality", "Expected mortality", "Observed mortality"],
                               "Mortality over time", percentage=True)
                st.caption("Expected risks include age and use the same residents before deaths and births. "
                           "Unfunded/public lines assume everyone in that cohort uses that care; expected mortality uses actual care choices.")
            with right:
                monetary_trend(trends, ["Healthcare spent", "Private premiums"], "Healthcare funding")
            a, b, c = st.columns(3)
            a.metric("Public care users", observed_value(last['Public healthcare users'], ",.0f"), border=True, help=METRIC_HELP["Public care users"])
            b.metric("Private care users", observed_value(last['Private healthcare users'], ",.0f"), border=True, help=METRIC_HELP["Private care users"])
            c.metric("Healthcare sector money", euro(economy.accounts['Healthcare']), border=True, help=METRIC_HELP["Healthcare sector money"])
            monetary_trend(trends, ["Public healthcare users", "Private healthcare users"], "Healthcare choices over time")
            risk = pd.DataFrame([{"Age": age, "Care": label, "Death probability": economy.death_probability(age, funded=funded,
                    risk_factor=economy.config.private_healthcare_mortality_factor if label == "Private" else None)}
                    for age in range(max(120, max((p.age for p in economy.population), default=0)) + 1)
                    for label, funded in [("Public", True), ("Private", False), ("Unfunded", False)]])
            chart = alt.Chart(risk, mark=alt.MarkDef(type="line")).encode(x="Age:Q", y=alt.Y("Death probability:Q", axis=alt.Axis(format=".0%")),
                                                       color=alt.Color("Care:N", scale=series_scale(["Public", "Private", "Unfunded"])),
                                                        tooltip=["Age:Q", "Care:N", alt.Tooltip("Death probability:Q", format=".2%")])
            st.subheader("Death risk by age", help="Annual probability of death at each age under current care settings. These are model risks, not observed death counts. Hover over a line for its values.")
            st.altair_chart(chart, width="stretch", alt="Annual mortality risk by age for public, private and unfunded care")
            st.caption("Public funding is adjusted for prices; private premiums are price-indexed. Providers retain funds and pay income to households. "
                       "Healthcare quality is an illustrative rule, not a causal estimate. There is no maximum-age cutoff.")
        with slots["bank"].container():
            a, b, c = st.columns(3)
            a.metric("Bank equity", euro(economy.bank_equity), border=True, help=METRIC_HELP["Bank equity"])
            b.metric("Outstanding household loans", euro(last['Outstanding loans']), border=True, help=METRIC_HELP["Outstanding household loans"])
            c.metric("Loan defaults this year", euro(last['Loan defaults']), border=True, help=METRIC_HELP["Loan defaults this year"])
            monetary_trend(trends, ["Outstanding loans", "Bank equity", "Loan defaults"], "Credit and bank solvency")
            a, b, c = st.columns(3)
            a.metric("Prudential bank equity", euro(last["Prudential bank equity"]), border=True,
                     help=METRIC_HELP["Prudential bank equity"])
            b.metric("Unpaid loan interest", euro(last["Unpaid loan interest"]), border=True,
                     help=METRIC_HELP["Unpaid loan interest"])
            c.metric("Bank realized profit", euro(last["Bank realized profit"]), border=True,
                     help=METRIC_HELP["Bank realized profit"])
            a, b, c = st.columns(3)
            a.metric("Loan recoveries", euro(last["Loan recoveries"]), border=True, help=METRIC_HELP["Loan recoveries"])
            b.metric("Defaulted loans", f"{int(last['Defaulted loans']):,}", border=True, help=METRIC_HELP["Defaulted loans"])
            c.metric("Loan principal losses", euro(last["Loan principal losses"]), border=True, help=METRIC_HELP["Loan principal losses"])
            monetary_trend(trends, ["Bank equity", "Prudential bank equity", "Unpaid loan interest"],
                           "Market equity, prudential capital and unpaid interest")
            monetary_trend(trends, ["Loan recoveries", "Loan defaults"], "Loan recoveries and residual losses")
            st.caption("Investment loans create deposits and matching liabilities. Repaying principal destroys deposits. "
                       "Interest moves value to bank equity; bank distributions return some to deposits. Defaults reduce bank assets and equity, "
                       "not existing deposits. New credit is constrained by bank capital, reserves and any broad-money ceiling.")
            st.caption("New loans also require verified repayment income under income/rate stress, net of existing commitments. "
                       "Risk premiums depend on existing leverage, debt service and default history—not a fitted probability. "
                       "Collateral is sold at a discount subject to producer liquidity before residual debt is written off. "
                       "Uncollected loan interest cannot support new credit or bank distributions.")
        with slots["money"].container():
            a, b, c = st.columns(3)
            a.metric("Base money", euro(economy.reserves), border=True, help=METRIC_HELP["Base money"])
            b.metric("Broad money", euro(economy.broad_money), border=True, help=METRIC_HELP["Broad money"])
            c.metric("Inflation this year", f"{economy.inflation:.2%}", border=True, help=METRIC_HELP["Inflation this year"])
            monetary_trend(trends, ["Base money", "Broad money"], "Money supplies")
            monetary_trend(trends, ["Inflation"], "Inflation", percentage=True)
            monetary_trend(trends, ["Price level"], "Price level (starting year = 1)")
            a, b = st.columns(2)
            a.metric("Goods demand coverage", observed_value(last["Goods demand coverage"], ".1%"),
                     border=True, help=METRIC_HELP["Goods demand coverage"])
            b.metric("Unsold goods", f"{last['Unsold goods']:,.2f}", border=True, help=METRIC_HELP["Unsold goods"])
            monetary_trend(trends, ["Desired goods spending", "Output at trade prices"],
                           "Goods spending versus supply value (before price adjustment)")
            st.caption("Base money = bank reserves. Broad money = all non-bank deposits, including treasury, goods producers and healthcare providers. "
                       "A base-money cap does not cap bank deposits. A broad-money cap also constrains bank credit and distributions. "
                        "Prices adjust to desired goods spending relative to output; annual changes are bounded at −10% / +25% for numerical stability.")
            st.caption("Demand coverage below 100% causes deflation in this model. Production follows available capacity and workers, "
                       "not expected sales; unsold goods expire. Saving, retained profits and treasury balances can keep demand below supply "
                       "even when broad money is unchanged. This is a simplified goods-price index, not a calibrated consumer price index.")
        with slots["age"].container():
            age_distribution(people, display["age_bin"], display["age_unit"])
            monetary_trend(trends, ["Population", "Deaths"], "Population and deaths")
        with downloads.container():
            with st.expander("Accounts, contracts and downloads"):
                balances = pd.DataFrame(economy.balance_sheets())
                st.dataframe(balances, hide_index=True, column_config=table_columns(balances),
                             alt="Sector assets, liabilities and net worth")
                st.caption("The fiat issuer starts with negative equity equal to issued base money; additional grants reduce it further. "
                           "It is not subject to the commercial bank's solvency rule. Consolidated sector net worth equals real capital valued at current prices.")
                errors = {name: float(last[name]) for name in ("Money balance error", "Base money balance error", "Government balance error")}
                reconciliation = pd.DataFrame({"Reconciliation": errors.keys(), "Error": errors.values()})
                st.dataframe(reconciliation, hide_index=True, column_config=table_columns(reconciliation),
                             alt="Money, base money and government account reconciliation errors")
                st.dataframe(people, hide_index=True, column_config=table_columns(people),
                             alt="Individual money, capital, bonds, loans, net wealth, pensions and healthcare")
                contracts = {"loans": [asdict(x) for x in economy.loans], "bonds": [asdict(x) for x in economy.bonds]}
                st.subheader("Percentile wealth shares", help="Current wealth totals and shares for equally sized groups, from poorest to richest. Shares refer to wealth, not the number of residents.")
                st.dataframe(shares, hide_index=True, column_config=table_columns(shares),
                             alt="Net wealth amounts and shares by population percentile")
                st.subheader("Loan contracts", help="Outstanding household loans and their original contract terms. Hover over column headers for units and definitions. An empty table means no loans are outstanding.")
                loans = pd.DataFrame(contracts["loans"])
                st.dataframe(loans, hide_index=True, column_config=table_columns(loans), alt="Outstanding loans, terms and arrears")
                st.subheader("Government bond contracts", help="Outstanding government bonds, their holders, annual coupons and repayment years. Existing contracts retain their original terms after policy edits.")
                bonds = pd.DataFrame([{**asdict(b), "Market value": economy.bond_market_value(b),
                                       "Price per euro face": economy.bond_values(b)[0] / b.principal if b.principal else None}
                                      for b in economy.bonds])
                st.dataframe(bonds, hide_index=True, column_config=table_columns(bonds), alt="Bondholders, principal, coupon and maturity")
                if economy.sovereign_events:
                    st.subheader("Sovereign default history", help="Executed debt repudiations and creditor losses. These are non-cash write-offs, not payments or income.")
                    events = pd.DataFrame(economy.sovereign_events)
                    st.dataframe(events, hide_index=True, column_config=table_columns(events),
                                 alt="Sovereign defaults with cancelled principal, interest and creditor losses")
                if economy.policy_changes:
                    st.subheader("Policy changes", help="Retained record of applied policy changes and the years they take effect. Draft edits are not recorded; at most 1,000 changes are kept.")
                    changes = pd.DataFrame(economy.policy_changes)
                    st.dataframe(changes, hide_index=True, column_config=table_columns(changes), alt="Policy changes and their effective years")
                for label, frame, filename in [
                    ("Download monetary history CSV", history, "monetary-history.csv"),
                     ("Download monetary population CSV", people, "monetary-population.csv"),
                     ("Download finance ledger CSV", history[finance_columns], "monetary-finances.csv"),
                    ("Download sector balance sheets CSV", pd.DataFrame(economy.balance_sheets()), "sector-balances.csv"),
                    ("Download transaction ledger CSV", pd.DataFrame(economy.transactions), "monetary-transactions.csv")]:
                    st.download_button(label, export_frame(frame).to_csv(index=False), filename, "text/csv",
                                       help={
                                           "monetary-history.csv": "Export all retained annual observations, not just the years visible in trend charts. History retains up to 10,000 years.",
                                           "monetary-population.csv": "Export a current snapshot of living residents, including age, deposits, capital, bonds, loans, net wealth and care choices.",
                                           "monetary-finances.csv": "Export retained annual treasury funding, policy payments, debt service and cash-balance reconciliation.",
                                           "sector-balances.csv": "Export current assets, liabilities and net worth for each sector, including the bank and fiat issuer.",
                                           "monetary-transactions.csv": "Export the latest 10,000 ledger entries, including labeled non-cash events such as write-offs. This may not cover the entire run.",
                                       }[filename])
                settings = {"model": "capital-dynamics", "currency": "EUR", "calibration_status": "Illustrative, not fitted",
                            "reference_snapshot": RETRIEVED_ON, "seed": economy.seed, "initial_parameters": asdict(economy.initial_config),
                             "current_parameters": asdict(economy.config), "policy_changes": list(economy.policy_changes),
                             "sovereign_events": list(economy.sovereign_events), "sovereign_default_pending": economy.sovereign_default_pending,
                             "sovereign_reputation_penalty": economy.reputation_spread, **contracts}
                st.download_button("Download monetary scenario settings", json.dumps(settings, indent=2), "monetary-scenario.json", "application/json",
                                   help="Export JSON with the seed, initial and active parameters, retained policy changes and current contracts. This documents the run but is not a full save-state checkpoint.")
                st.caption("History retains 10,000 years; the transaction ledger retains the latest 10,000 entries, including labeled non-cash events. "
                            "Policy history retains 1,000 changes. Settings document the run, not a full state checkpoint; "
                            "a complete replay also needs any older interventions.")
    monetary_dashboard()
