"""Native controls for the monetary dashboard."""
from dataclasses import dataclass
from typing import Any

import streamlit as st


def sync_widget_value(key, value):
    """Queue a one-run programmatic reset, including the browser's value."""
    st.session_state[key] = value
    st.session_state.setdefault("_widget_sync_pending", set()).add(key)


def widget_default(key, value: Any, *, kind="number") -> Any:
    pending = st.session_state.get("_widget_sync_pending", set())
    if key not in pending:
        return value
    pending.discard(key)
    # Use only Session State on the reset run (Streamlit sends set_value), then
    # return to explicit defaults on normal runs. Merely deleting a widget key
    # changes Python state but can leave the browser showing the old value.
    return 0 if kind == "selection" else False if kind == "toggle" else "min"


@dataclass(frozen=True)
class Playback:
    mode: str
    interval: float = 0.5
    steps_per_refresh: int = 1


def toggle_running(state_key):
    st.session_state[state_key] = not st.session_state.get(state_key, False)


def playback_controls(simulation_key, running_key, *, reset_callback=None):
    """Keep widget identities stable across playback mode changes."""
    sim = st.session_state[simulation_key]
    keys = {"mode": "m_mode", "batch": "m_years", "advance": "m_advance", "interval": "m_interval",
            "refresh": "m_per_refresh", "toggle": "m_toggle_live", "single": "m_single_step", "reset": "m_reset"}
    with st.container(border=True):
        st.subheader("Simulation controls", anchor=False)
        mode = st.segmented_control("Simulation mode", ["Batch", "Live"], default="Batch", key=keys["mode"],
                                    help="Batch advances only when you click Advance. Live advances automatically while running; switching to Batch pauses playback.") or "Batch"
        if mode == "Batch":
            st.session_state[running_key] = False
            count, action = st.columns([2, 1], vertical_alignment="bottom")
            steps = count.number_input("Years to advance", 1, 10000, 10, key=keys["batch"],
                                        help="Number of simulation periods to run when you click Advance. In the monetary economy, one period is one year.")
            if action.button("Advance monetary economy", key=keys["advance"],
                             icon=":material/fast_forward:", type="primary", width="stretch", disabled=not sim.population,
                             help="Run the requested periods using active policies, preserving the current economy and history. Unavailable if no residents remain."):
                with st.spinner("Advancing simulation…"):
                    sim.advance(int(steps))
            playback = Playback(mode)
        else:
            rate, count = st.columns(2, vertical_alignment="bottom")
            interval = rate.select_slider("Refresh every (seconds)", [0.1, 0.25, 0.5, 1.0, 2.0], value=0.5, key=keys["interval"],
                                          help="Wall-clock interval between live dashboard updates. This changes playback speed, not the economic rules.")
            steps = count.number_input("Years per refresh", 1, 100, 1, key=keys["refresh"],
                                        help="Simulation periods advanced at each live update. Larger values run faster but skip more intermediate views; history is still recorded.")
            running = st.session_state.get(running_key, False)
            label = "Pause" if running else "Resume" if sim.step_count else "Start"
            start, single = st.columns(2)
            start.button(label, key=keys["toggle"], icon=":material/pause:" if running else ":material/play_arrow:",
                         type="primary", width="stretch", disabled=not sim.population,
                         on_click=toggle_running, args=(running_key,),
                         help="Pause automatic advancement to inspect results, or start/resume the same economy. Unavailable if no residents remain.")
            if single.button("Single year", key=keys["single"], icon=":material/skip_next:",
                             width="stretch", disabled=running or not sim.population,
                             help="Advance exactly one period without starting playback. Available only while paused and residents remain."):
                sim.advance()
            st.caption("Start / resume continues this economy. Pause to inspect it; single-step works while paused.")
            playback = Playback(mode, float(interval), int(steps))
        st.button("Reset monetary scenario", key=keys["reset"],
                  icon=":material/restart_alt:", on_click=reset_callback,
                  help="Replace the current economy and its history with year zero, using active policies, the scenario's initial conditions and original seed. Unapplied edits are discarded.")
    return playback


def policy_fields(specs, config, *, prefix, percentages=(), labels=None, columns=2, help_texts=None):
    """Use explicit native defaults so browser remounts retain active values.

    Session-state-only defaults can display widget minima when a closed popover
    mounts after a live fragment refresh. Explicit reset runs use the queued
    state assignment alone, avoiding competing defaults and warning messages.
    """
    labels = labels or {}
    help_texts = help_texts or {}
    for index in range(0, len(specs), columns):
        row = st.columns(columns, gap="small", vertical_alignment="bottom")
        for column, spec in zip(row, specs[index:index + columns]):
            name, original_label, *bounds = spec
            label = labels.get(name, original_label)
            value = getattr(config, name)
            key = f"{prefix}{name}"
            explanation = help_texts.get(name)
            if name in percentages:
                value = float(value * 100)
            elif bounds and isinstance(bounds[0], float):
                value = float(value)
            with column:
                if not bounds:
                    st.toggle(label, value=widget_default(key, bool(value), kind="toggle"), key=key,
                              help=explanation or original_label)
                elif isinstance(bounds[0], list):
                    st.selectbox(label, bounds[0], index=widget_default(key, bounds[0].index(value), kind="selection"), key=key,
                                 help=explanation or original_label)
                else:
                    minimum, maximum, step = bounds
                    help_value = explanation or original_label
                    st.number_input(label, min_value=minimum, max_value=maximum, value=widget_default(key, value),
                                    step=step, key=key, help=help_value)


def display_controls():
    prefix = "m_"
    window = st.number_input("Years shown in trends", 10, 10000, 500, 50,
                             key="m_window",
                             help="Show only the latest periods in trend charts. This does not advance the simulation, change current distributions or remove recorded history.")
    st.markdown("**Wealth distribution**")
    groups = st.slider("Percentile groups", 2, 20, 10, key=f"{prefix}groups",
                       help="Split residents from poorest to richest into equal-sized groups. For example, 10 gives deciles (10% each). Small populations may leave groups empty.")
    individuals = st.toggle("Show individual wealth", True, key=f"{prefix}show_individuals",
                            help="Show a bar for every resident, ordered from poorest to richest. Turning this off hides only that chart, not the grouped distribution or data.")
    logarithmic = st.toggle("Logarithmic wealth scale", False, key=f"{prefix}log_wealth",
                            help="Use a logarithmic axis to compare wealth across large ranges. Zero and negative values are omitted only from the individual chart, not from totals or percentile groups.")
    st.markdown("**Age distribution**")
    age_bin = st.select_slider("Age bin width", [1, 5, 10, 20], value=10, key=f"{prefix}age_bin",
                               help="Years of age combined in each histogram bar. For example, 10 groups ages 0–9, 10–19 and so on.")
    unit = st.segmented_control("Distribution units", ["Share", "People"], default="Share", key=f"{prefix}age_unit",
                                help="Share shows each age group's percentage of living residents. People shows the number of residents in each group.") or "Share"
    return {"window": window, "groups": groups, "individuals": individuals, "logarithmic": logarithmic,
            "age_bin": age_bin, "age_unit": unit}
