"""Native, reusable controls shared by both economy dashboards."""
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


def playback_controls(simulation_key, running_key, *, monetary=False, reset_callback=None):
    """Keep widget identities stable while sharing playback behavior and layout."""
    sim = st.session_state[simulation_key]
    keys = ({"mode": "m_mode", "batch": "m_years", "advance": "m_advance", "interval": "m_interval",
             "refresh": "m_per_refresh", "toggle": "m_toggle_live", "single": "m_single_step", "reset": "m_reset"}
            if monetary else {"mode": "mode", "batch": "batch_steps", "advance": "advance", "interval": "interval",
                              "refresh": "steps_per_refresh", "toggle": "toggle_live", "single": "single_step", "reset": "reset"})
    with st.container(border=True):
        st.subheader("Simulation controls", anchor=False)
        mode = st.segmented_control("Simulation mode", ["Batch", "Live"], default="Batch", key=keys["mode"]) or "Batch"
        if mode == "Batch":
            st.session_state[running_key] = False
            count, action = st.columns([2, 1], vertical_alignment="bottom")
            steps = count.number_input("Years to advance" if monetary else "Steps to advance", 1, 10000,
                                        10 if monetary else 100, key=keys["batch"])
            if action.button("Advance monetary economy" if monetary else "Advance simulation", key=keys["advance"],
                             icon=":material/fast_forward:", type="primary", width="stretch", disabled=not sim.population):
                with st.spinner("Advancing simulation…"):
                    sim.advance(int(steps))
            playback = Playback(mode)
        else:
            rate, count = st.columns(2, vertical_alignment="bottom")
            interval = rate.select_slider("Refresh every (seconds)", [0.1, 0.25, 0.5, 1.0, 2.0], value=0.5, key=keys["interval"])
            steps = count.number_input("Years per refresh" if monetary else "Steps per refresh", 1, 100, 1, key=keys["refresh"])
            running = st.session_state.get(running_key, False)
            label = "Pause" if running else "Resume" if sim.step_count else "Start"
            start, single = st.columns(2)
            start.button(label, key=keys["toggle"], icon=":material/pause:" if running else ":material/play_arrow:",
                         type="primary", width="stretch", disabled=not sim.population,
                         on_click=toggle_running, args=(running_key,))
            if single.button("Single year" if monetary else "Single step", key=keys["single"], icon=":material/skip_next:",
                             width="stretch", disabled=running or not sim.population):
                sim.advance()
            st.caption("Start / resume continues this economy. Pause to inspect it; single-step works while paused.")
            playback = Playback(mode, float(interval), int(steps))
        st.button("Reset monetary scenario" if monetary else "Reset current scenario", key=keys["reset"],
                  icon=":material/restart_alt:", on_click=reset_callback,
                  help="Restart with the active policies and original seed.")
    return playback


def policy_fields(specs, config, *, prefix, percentages=(), labels=None, columns=2):
    """Use explicit native defaults so browser remounts retain active values.

    Session-state-only defaults can display widget minima when a closed popover
    mounts after a live fragment refresh. Explicit reset runs use the queued
    state assignment alone, avoiding competing defaults and warning messages.
    """
    labels = labels or {}
    for index in range(0, len(specs), columns):
        row = st.columns(columns, gap="small", vertical_alignment="bottom")
        for column, spec in zip(row, specs[index:index + columns]):
            name, original_label, *bounds = spec
            label = labels.get(name, labels.get(original_label, original_label))
            value = getattr(config, name)
            key = f"{prefix}{name}"
            if name in percentages:
                value = float(value * 100)
            elif bounds and isinstance(bounds[0], float):
                value = float(value)
            with column:
                if not bounds:
                    st.toggle(label, value=widget_default(key, bool(value), kind="toggle"), key=key,
                              help=original_label if label != original_label else None)
                elif isinstance(bounds[0], list):
                    st.selectbox(label, bounds[0], index=widget_default(key, bounds[0].index(value), kind="selection"), key=key)
                else:
                    minimum, maximum, step, *help_text = bounds
                    help_value = f"{original_label}. {help_text[0]}" if help_text else original_label
                    st.number_input(label, min_value=minimum, max_value=maximum, value=widget_default(key, value),
                                    step=step, key=key, help=help_value)


def display_controls(*, monetary=False):
    prefix = "m_" if monetary else ""
    window = st.number_input("Years shown in trends" if monetary else "Steps shown in trends", 10, 10000, 500, 50,
                             key="m_window" if monetary else "history_window")
    st.markdown("**Wealth distribution**")
    groups = st.slider("Percentile groups", 2, 20, 10, key=f"{prefix}groups")
    individuals = st.toggle("Show individual wealth", True, key=f"{prefix}show_individuals")
    logarithmic = st.toggle("Logarithmic wealth scale", False, key=f"{prefix}log_wealth",
                            help="Non-positive values are omitted only from the logarithmic individual chart.")
    st.markdown("**Age distribution**")
    age_bin = st.select_slider("Age bin width", [1, 5, 10, 20], value=10, key=f"{prefix}age_bin")
    unit = st.segmented_control("Distribution units", ["Share", "People"], default="Share", key=f"{prefix}age_unit") or "Share"
    return {"window": window, "groups": groups, "individuals": individuals, "logarithmic": logarithmic,
            "age_bin": age_bin, "age_unit": unit}
