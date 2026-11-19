"""Spacious section-local policy forms, stable during live chart refreshes."""
from typing import Any
import streamlit as st
from budget import LEGACY_FIELDS, POLICIES

POLICY_FIELDS: dict[str, list[tuple[Any, ...]]] = {'private_investments': [('gain_prob', 'Private opportunity event probability', 0.0, 1.0, 0.05),
                         ('gain_fraction',
                          'Population fraction offered an opportunity',
                          0.0,
                          1.0,
                          0.05),
                         ('gain_growth', 'Successful opportunity gain rate', 0.0, 2.0, 0.05),
                         ('investment_risk',
                          'Investment failure probability',
                          0.0,
                          1.0,
                          0.05,
                          'Each selected person independently faces this chance of losing wealth '
                          'instead of gaining. Set to 0 for the original gain-only opportunities.'),
                         ('failed_investment_loss',
                          'Wealth fraction lost on failure',
                          0.0,
                          1.0,
                          0.05,
                          "A failed opportunity loses this fraction of the person's current "
                          'wealth. A value of 1 loses all their wealth.'),
                         ('loss_prob', 'Loss event probability', 0.0, 1.0, 0.05),
                         ('loss_fraction', 'Population fraction receiving losses', 0.0, 1.0, 0.05),
                         ('loss_rate', 'Maximum loss rate', 0.0, 1.0, 0.05)],
 'investment': [('base_growth', 'Base growth rate', 0.0, 1.0, 0.01),
                ('alpha',
                 'Wealth effect on growth (alpha)',
                 -1.0,
                 1.0,
                 0.0001,
                 'Growth multiplier: 1 / max(1 + alpha × wealth, 0.01). Negative alpha favors '
                 'wealthier people.'),
                ('investment_probability', 'Investment probability', 0.0, 1.0, 0.05),
                ('delta', 'Capacity depreciation per step', 0.0, 1.0, 0.0001),
                ('beta', 'Investment return exponent (beta)', 0.0, 2.0, 0.05),
                ('base_eff', 'Base investment efficiency', 0.0, 2.0, 0.05),
                ('shock_scale', 'Investment shock magnitude', 0.0, 2.0, 0.05),
                ('max_neg_shock', 'Failed investment damage multiplier', 0.0, 2.0, 0.05),
                ('psi', 'Investment success sensitivity (psi)', 0.0, 20.0, 0.1)],
 'taxes': [('tau_base', 'Minimum wealth tax rate', 0.0, 1.0, 0.001),
           ('tau_max', 'Maximum wealth tax rate', 0.0, 1.0, 0.005),
           ('tau_gamma',
            'Tax progressivity (gamma)',
            0.1,
            20.0,
            0.1,
             'Higher values concentrate higher tax rates toward the wealthiest individuals.')],
 'ubi': [('direct_redistribution_fraction',
            'Government budget allocated to UBI per step',
            0.0,
            1.0,
            0.05,
            'Equal payment to every resident, funded from this share of available government '
            'funds. Paid before pensions and public healthcare.')],
 'pensions': [('retirement_age', 'Pension eligibility age', 0, 500, 1),
              ('pension_budget_fraction',
               'Remaining budget available for pensions',
               0.0,
               1.0,
               0.05,
               'Pensions are paid after UBI and before public healthcare. Unused pension funds '
               'stay in the government budget.'),
              ('pension_per_person',
               'Pension per retiree (initial wealth multiple)',
               0.0,
               10.0,
               0.05,
               'Desired payment each step. If funding is insufficient, all eligible people receive '
               'the same reduced payment.')],
 'healthcare': [('healthcare_spending_fraction',
                 'Remaining budget spent on healthcare',
                 0.0,
                 1.0,
                 0.05,
                 'Spent after UBI and pensions, before capacity investment. Zero stops new public '
                 'healthcare funding.'),
                ('healthcare_effectiveness',
                 'Healthcare effectiveness',
                 0.0,
                 50.0,
                 0.5,
                 'How strongly per-person spending reduces death risk, relative to initial wealth '
                 'per person.'),
                ('healthcare_response_rate',
                 'Mortality adjustment speed',
                 0.01,
                 1.0,
                 0.05,
                 'Fraction of the gap toward the spending-dependent mortality target closed each '
                 'step. Lower values make effects more gradual.'),
                ('mortality_floor_fraction',
                 'Minimum mortality risk fraction',
                 0.0,
                 1.0,
                 0.05,
                 'Lowest attainable fraction of unfunded mortality risk. For example 0.2 allows up '
                 'to an 80% reduction, except at maximum age.')],
 'private_healthcare': [('private_healthcare_premium',
                         'Private premium (initial wealth multiple)',
                         0.0,
                         10.0,
                         0.001),
                        ('private_healthcare_age_loading',
                         'Private premium age surcharge',
                         0.0,
                         10.0,
                         0.1,
                         'Premium = base premium × (1 + surcharge × age / maximum age).'),
                        ('private_healthcare_mortality_factor',
                         'Private care mortality risk fraction',
                         0.0,
                         1.0,
                         0.05,
                         'Private care multiplies unfunded death risk by this factor. Lower means '
                         'better care; maximum age remains a hard limit.'),
                        ('private_healthcare_max_wealth_fraction',
                         'Maximum wealth share spent on private care',
                         0.0,
                         1.0,
                         0.05),
                        ('healthcare_choice_priority',
                         'Value of health relative to preserving wealth',
                         0.0,
                         20.0,
                         0.5,
                         'Higher values make adaptive agents more willing to pay for health '
                         'improvements. Individual preferences vary around this value.')],
 'demographics': [('birth_prob_max', 'Maximum birth probability', 0.0, 1.0, 0.005),
                  ('death_base_prob', 'Base death probability', 0.0, 1.0, 0.0001),
                  ('aging_risk_start', 'Adult mortality reference age', 0, 100, 1,
                   'Reference age for the adult hazard, not an aging threshold or lifespan limit.'),
                  ('aging_risk_rate',
                   'Adult hazard at reference age',
                   0.0,
                   0.1,
                   0.001,
                   'Annual adult hazard at the reference age. Risk rises exponentially with age; '
                   'also scales infant and young-adult excess risks. Healthcare reduces the full hazard.'),
                  ('mortality_doubling_years', 'Mortality doubling time (years)', 1.0, 20.0, 0.5,
                   'Years for adult mortality hazard to double. Default 7 approximates modern human aging; '
                   'there is no maximum age.')]}


def current_simulation():
    """Fragments and callbacks can run without the app's page-load migration."""
    import importlib
    import simulation as model
    if not hasattr(model.SimulationConfig, "budget_mode"):
        model = importlib.reload(model)
    restored = model.restore_simulation(st.session_state.simulation)
    st.session_state.simulation = restored
    return restored


def sync_policy_controls():
    """Discard drafts only when the user starts or resets a scenario."""
    config = current_simulation().config
    for specs in POLICY_FIELDS.values():
        for spec in specs:
            st.session_state[f"config_{spec[0]}"] = getattr(config, spec[0])
    st.session_state.config_healthcare_choice_mode = config.healthcare_choice_mode
    st.session_state.policy_notices = {}
    st.session_state.budget_notice = None
    for name in LEGACY_FIELDS:
        st.session_state[f"budget_percent_{name}"] = float(getattr(config, name) * 100)


def apply_policy(group):
    config = current_simulation().config
    changes = {spec[0]: st.session_state[f"config_{spec[0]}"] for spec in POLICY_FIELDS[group]
               if config.budget_mode != "Total budget" or spec[0] not in LEGACY_FIELDS}
    if group == "private_healthcare":
        changes["healthcare_choice_mode"] = st.session_state.config_healthcare_choice_mode
    notices = st.session_state.setdefault("policy_notices", {})
    try:
        changed = current_simulation().update_policy(**changes)
    except (ValueError, TypeError) as error:
        notices[group] = (False, str(error))
    else:
        step = st.session_state.simulation.step_count + 1
        notices[group] = (True, f"Policy applies from step {step:,}." if changed else "These settings are already active.")


COMPACT_LABELS = {
    "Private opportunity event probability": "Opportunity chance",
    "Population fraction offered an opportunity": "People offered",
    "Successful opportunity gain rate": "Gain rate",
    "Investment failure probability": "Failure chance",
    "Wealth fraction lost on failure": "Loss on failure",
    "Loss event probability": "Loss event chance",
    "Population fraction receiving losses": "People affected",
    "Maximum loss rate": "Maximum loss",
    "Base growth rate": "Base growth",
    "Wealth effect on growth (alpha)": "Wealth effect (α)",
    "Investment probability": "Investment chance",
    "Capacity depreciation per step": "Capacity depreciation",
    "Investment return exponent (beta)": "Return exponent (β)",
    "Base investment efficiency": "Base efficiency",
    "Investment shock magnitude": "Investment shock",
    "Failed investment damage multiplier": "Failure damage",
    "Investment success sensitivity (psi)": "Success sensitivity (ψ)",
    "Minimum wealth tax rate": "Minimum tax rate",
    "Maximum wealth tax rate": "Maximum tax rate",
    "Tax progressivity (gamma)": "Tax progressivity (γ)",
    "Government budget allocated to UBI per step": "Budget share for UBI",
    "Pension eligibility age": "Retirement age",
    "Remaining budget available for pensions": "Budget share for pensions",
    "Pension per retiree (initial wealth multiple)": "Pension per retiree",
    "Remaining budget spent on healthcare": "Budget share for healthcare",
    "Healthcare effectiveness": "Care effectiveness",
    "Mortality adjustment speed": "Mortality response speed",
    "Minimum mortality risk fraction": "Minimum risk fraction",
    "Private premium (initial wealth multiple)": "Private premium",
    "Private premium age surcharge": "Age surcharge",
    "Private care mortality risk fraction": "Private mortality risk",
    "Maximum wealth share spent on private care": "Maximum affordable share",
    "Value of health relative to preserving wealth": "Health priority",
    "Maximum birth probability": "Peak birth chance",
    "Base death probability": "Base mortality",
    "Age when extra mortality begins": "Aging risk starts at",
    "Additional annual-age risk": "Extra risk per year",
}


def policy_controls(group, title):
    config = current_simulation().config
    with st.expander(title, icon=":material/tune:", key=f"policy_menu_{group}"):
        if group == "ubi" and config.budget_mode == "Total budget":
            st.caption(f"UBI allocation: {config.direct_redistribution_fraction:.0%} of the total policy budget. "
                       "Edit all allocation percentages together under Government budget and taxes.")
            return
        st.caption("Adjust the settings, then apply this policy. Changes take effect next step and preserve the current economy.")
        with st.form(f"policy_{group}", border=False, enter_to_submit=False):
            if group == "private_healthcare":
                st.session_state.setdefault("config_healthcare_choice_mode", config.healthcare_choice_mode)
                st.selectbox("Care choice", ["Adaptive", "Public only", "Private if affordable"],
                             key="config_healthcare_choice_mode")
            specs = [spec for spec in POLICY_FIELDS[group]
                     if config.budget_mode != "Total budget" or spec[0] not in LEGACY_FIELDS]
            for name, policy in zip(LEGACY_FIELDS, POLICIES):
                if config.budget_mode == "Total budget" and any(spec[0] == name for spec in POLICY_FIELDS[group]):
                    st.caption(f"{policy} allocation: {getattr(config, name):.0%} of the total policy budget. "
                               "Edit all percentages together under Government budget and taxes.")
            for index in range(0, len(specs), 2):
                columns = st.columns(2, gap="medium", vertical_alignment="bottom")
                for column, spec in zip(columns, specs[index:index + 2]):
                    name, label, minimum, maximum, step, *help_text = spec
                    key = f"config_{name}"
                    value = getattr(config, name)
                    st.session_state.setdefault(key, float(value) if isinstance(minimum, float) else int(value))
                    with column:
                        st.number_input(COMPACT_LABELS.get(label, label), min_value=minimum, max_value=maximum,
                                        step=step, help=f"{label}. {help_text[0]}" if help_text else label, key=key)
            st.form_submit_button("Apply policy", icon=":material/check:", key=f"apply_{group}", type="primary", width="stretch",
                                  on_click=apply_policy, args=(group,))
        notice = st.session_state.get("policy_notices", {}).get(group)
        if notice:
            ok, message = notice
            (st.success if ok else st.error)(message)


def apply_budget():
    changes = {name: st.session_state[f"budget_percent_{name}"] / 100 for name in LEGACY_FIELDS}
    try:
        current_simulation().update_policy(budget_mode="Total budget", **changes)
    except (ValueError, TypeError) as error:
        st.session_state.budget_notice = (False, str(error))
    else:
        st.session_state.budget_notice = (True, "Budget allocations apply from the next step.")
        for name, value in changes.items():
            st.session_state[f"config_{name}"] = value


def budget_controls():
    config = current_simulation().config
    with st.expander("Budget allocation settings", icon=":material/tune:"):
        st.caption("All percentages use opening government funds plus taxes collected this step. "
                   "Estates received after spending are available next step. Unused allocations remain in the budget.")
        if config.budget_mode != "Total budget":
            st.warning("This scenario still uses sequential legacy spending. Applying this form explicitly switches "
                       "future steps to total-budget percentages; existing history is unchanged.")
        with st.form("budget_allocation", enter_to_submit=False):
            for name, policy in zip(LEGACY_FIELDS, POLICIES):
                key = f"budget_percent_{name}"
                st.session_state.setdefault(key, float(getattr(config, name) * 100))
                st.number_input(f"{policy} allocation (% of total budget)", 0.0, 100.0, step=1.0, key=key)
            st.form_submit_button("Apply budget allocation", key="apply_budget", on_click=apply_budget, width="stretch")
        notice = st.session_state.get("budget_notice")
        if notice:
            (st.success if notice[0] else st.error)(notice[1])
