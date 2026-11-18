"""Section-local policy forms that remain stable during live chart refreshes."""
from typing import Any
import streamlit as st

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
            'Higher values concentrate higher tax rates toward the wealthiest individuals.'),
           ('direct_redistribution_fraction',
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
                  ('death_base_prob', 'Base death probability', 0.0, 1.0, 0.001),
                  ('max_age', 'Maximum age', 1, 500, 1),
                  ('aging_risk_start', 'Age when extra mortality begins', 0, 500, 1),
                  ('aging_risk_rate',
                   'Additional annual-age risk',
                   0.0,
                   0.1,
                   0.001,
                   'Extra risk per age unit above the threshold, divided by 1 + individual wealth. '
                   'Healthcare reduces this risk as well.')]}


def current_simulation():
    """Fragments and callbacks can run without the app's page-load migration."""
    import importlib
    import simulation as model
    if not hasattr(model, "wealth_tax_rates"):
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


def apply_policy(group):
    changes = {spec[0]: st.session_state[f"config_{spec[0]}"] for spec in POLICY_FIELDS[group]}
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
    "Maximum age": "Maximum age",
    "Age when extra mortality begins": "Aging risk starts at",
    "Additional annual-age risk": "Extra risk per year",
}


def policy_controls(group, title):
    config = current_simulation().config
    with st.popover(title, icon=":material/tune:", type="tertiary", key=f"policy_menu_{group}"):
        st.caption("Takes effect next step; the current run continues.")
        with st.form(f"policy_{group}", border=False):
            if group == "private_healthcare":
                st.session_state.setdefault("config_healthcare_choice_mode", config.healthcare_choice_mode)
                st.selectbox("Care choice", ["Adaptive", "Public only", "Private if affordable"],
                             key="config_healthcare_choice_mode")
            specs = POLICY_FIELDS[group]
            for index in range(0, len(specs), 2):
                columns = st.columns(2, gap="small")
                for column, spec in zip(columns, specs[index:index + 2]):
                    name, label, minimum, maximum, step, *help_text = spec
                    key = f"config_{name}"
                    value = getattr(config, name)
                    st.session_state.setdefault(key, float(value) if isinstance(minimum, float) else int(value))
                    with column:
                        st.number_input(COMPACT_LABELS.get(label, label), min_value=minimum, max_value=maximum,
                                        step=step, help=help_text[0] if help_text else None, key=key)
            st.form_submit_button("Apply", key=f"apply_{group}", type="primary", width="stretch",
                                  on_click=apply_policy, args=(group,))
        notice = st.session_state.get("policy_notices", {}).get(group)
        if notice:
            ok, message = notice
            (st.success if ok else st.error)(message)
