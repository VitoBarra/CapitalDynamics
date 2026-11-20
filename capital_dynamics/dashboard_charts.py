"""Shared chart/data components, with consistent percentile and policy colors."""
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from capital_dynamics.budget import COLORS, POLICIES
from capital_dynamics.help_text import SERIES_HELP
from capital_dynamics.currency import column_unit
from capital_dynamics.economics import relative_wealth, tax_rates_at_relative_wealth, wealth_tax_rates

PALETTE = ["#2563EB", "#0D9488", "#D97706", "#7C3AED", "#E11D48", "#64748B"]
SERIES_COLORS = {**dict(zip(POLICIES, COLORS)),
    "UBI spent": COLORS[0], "Pensions spent": COLORS[1], "Healthcare spent": COLORS[2],
    "Public investment spent": COLORS[3], "Education spent": COLORS[4], "Debt service spent": COLORS[5],
    "Net wealth": PALETTE[0], "Real net wealth": PALETTE[1], "Public": COLORS[2], "Private": COLORS[0],
    "Unfunded": COLORS[5], "Loan defaults": COLORS[5], "Deaths": COLORS[5]}


def series_scale(names):
    return alt.Scale(domain=names, range=[SERIES_COLORS.get(name, PALETTE[i % len(PALETTE)]) for i, name in enumerate(names)])


def trend_chart(history, names, title, domain=None, percentage=False, *, area=False):
    explanations = "\n\n".join(f"**{name}:** {SERIES_HELP[name]}" for name in names if name in SERIES_HELP)
    st.subheader(title, help="Recorded results over the selected trend window. Hover for exact values; scroll to zoom and drag to pan."
                 + ("\n\nStacked areas show each series' contribution to the total." if area else "")
                 + (f"\n\n{explanations}" if explanations else ""))
    data = history[["Step", *names]].melt("Step", var_name="Series", value_name="Value")
    data["Unit"] = data["Series"].map(lambda name: column_unit(name) or ("share" if percentage else "count / index"))
    units = set(data["Unit"])
    axis_title = next(iter(units)) if len(units) == 1 else "Series units (see hover)"
    money_axis = all(unit.startswith("EUR") for unit in units)
    mark = alt.MarkDef(type="area") if area else alt.MarkDef(type="line", point=len(history) == 1)
    chart = alt.Chart(data, mark=mark).encode(
        x=alt.X("Step:Q", title="Year", axis=alt.Axis(tickMinStep=1, format="d")),
        y=alt.Y("Value:Q", title=axis_title, scale=alt.Scale(domain=domain) if domain else alt.Scale(zero=area),
                axis=alt.Axis(format=".1%") if percentage else
                alt.Axis(labelExpr="'€' + datum.label") if money_axis else alt.Axis(),
                stack="zero" if area else None),
        color=alt.Color("Series:N", title=None, scale=series_scale(names), sort=names),
        tooltip=[alt.Tooltip("Step:Q", title="Year"), "Series:N", "Unit:N",
                 alt.Tooltip("Value:Q", format=".3%" if percentage else ",.4f")],
    ).properties(height=240).interactive()
    st.altair_chart(chart, width="stretch", alt=title)


def distribution_data(population, groups):
    value = "Net wealth"
    wealth = population.sort_values(value).reset_index(drop=True).copy()
    wealth["Rank"] = np.arange(1, len(wealth) + 1)
    wealth["Group index"] = np.minimum(np.arange(len(wealth)) * groups // max(len(wealth), 1), groups - 1)
    labels = [f"{100*i/groups:g}–{100*(i+1)/groups:g}%" for i in range(groups)]
    wealth["Percentile group"] = wealth["Group index"].map(dict(enumerate(labels)))
    totals = wealth.groupby("Group index")[value].sum().reindex(range(groups), fill_value=0)
    total = float(totals.sum())
    shares = pd.DataFrame({"Percentile group": labels, "Group index": range(groups), value: totals.to_numpy(),
                           "Wealth share": totals.to_numpy() / total if total else np.zeros(groups)})
    return wealth, shares, labels


def wealth_distribution(population, groups, show_individuals, logarithmic):
    value = "Net wealth"
    wealth, shares, labels = distribution_data(population, groups)
    palette = alt.Scale(domain=labels, scheme="viridis")
    left, right = st.columns([2, 1] if show_individuals else [1, 1])
    with left:
        st.subheader("Net wealth of each individual",
                     help="One bar per living resident, sorted poorest to richest. Colors identify equal-sized population percentile groups. Hover for age, rank and wealth; Display settings control visibility and scale.")
        if show_individuals and len(wealth):
            plotted = wealth[wealth[value] > 0] if logarithmic else wealth
            bars = alt.Chart(plotted, mark=alt.MarkDef(type="bar")).encode(
                x=alt.X("Rank:Q", title="Individual rank · poorest to richest"),
                y=alt.Y(f"{value}:Q", title="Net wealth (EUR)", axis=alt.Axis(labelExpr="'€' + datum.label"),
                        scale=alt.Scale(type="log" if logarithmic else "linear")),
                color=alt.Color("Percentile group:N", scale=palette, sort=labels, legend=None),
                tooltip=["Person:Q", "Rank:Q", "Age:Q", alt.Tooltip(f"{value}:Q", format=",.6f", title="Net wealth (EUR)"), "Percentile group:N"],
            ).properties(height=300).interactive()
            st.altair_chart(bars, width="stretch", alt=f"Each individual's {value.lower()}, sorted from poorest to richest")
            if logarithmic:
                st.caption("Non-positive wealth is omitted only from this log chart; it remains in the data and percentile groups.")
        elif not len(wealth):
            st.info("No individuals remain.")
        else:
            st.caption("Enable individual wealth in Display settings to see every person.")
        st.caption("Percentile colors match across charts. Hover for details; scroll to zoom.")
    with right:
        st.subheader("Wealth by population percentile",
                     help="Residents are sorted by wealth and divided into equal-sized groups. Slices show each group's share of total wealth, not its share of people. If any resident has negative wealth, signed group totals replace the pie.")
        if (wealth[value] < 0).any():
            signed = alt.Chart(shares, mark=alt.MarkDef(type="bar")).encode(
                x=alt.X("Percentile group:N", sort=labels),
                y=alt.Y(f"{value}:Q", title="Net wealth (EUR)", axis=alt.Axis(labelExpr="'€' + datum.label")),
                color=alt.Color("Percentile group:N", scale=palette, legend=None),
                tooltip=["Percentile group:N", alt.Tooltip(f"{value}:Q", title="Net wealth (EUR)", format=",.4f")])
            st.altair_chart(signed, width="stretch", alt="Signed net wealth totals by population percentile")
            st.caption("Negative net wealth cannot be a pie slice; signed group totals are shown instead.")
        elif shares[value].sum() > 0:
            pie = alt.Chart(shares, mark=alt.MarkDef(type="arc")).encode(
                theta=f"{value}:Q", color=alt.Color("Percentile group:N", sort=labels, scale=palette),
                order=alt.Order("Group index:Q", sort="ascending"),
                tooltip=["Percentile group:N", alt.Tooltip("Wealth share:Q", format=".2%"), alt.Tooltip(f"{value}:Q", format=",.4f", title="Net wealth (EUR)")],
            ).properties(height=300)
            text = alt.Chart(shares, mark=alt.MarkDef(type="text", radius=100, color="white")).encode(
                theta=alt.Theta(f"{value}:Q", stack=True), order=alt.Order("Group index:Q", sort="ascending"),
                text=alt.Text("Wealth share:Q", format=".0%"))
            st.altair_chart(pie + text, width="stretch", alt="Share of private wealth held by each population percentile group")
        else:
            st.info("No positive wealth to distribute.")
        st.caption("Equal-sized groups run from poorest to richest; small populations can leave groups empty.")
    return shares


def tax_curve(values, config):
    st.subheader("Current net wealth tax curve",
                 help="The line shows active tax policy; dots project rates for current residents. Relative wealth measures distance from the poorest to the richest wealth value, not population percentile. Actual collections may differ from these projected rates.")
    positions = np.linspace(0, 1, 201)
    curve = pd.DataFrame({"Relative wealth": positions, "Tax rate": tax_rates_at_relative_wealth(positions, config)})
    line = alt.Chart(curve, mark=alt.MarkDef(type="line", color=PALETTE[0])).encode(
        x=alt.X("Relative wealth:Q", title="Relative wealth · poorest 0, richest 1"),
        y=alt.Y("Tax rate:Q", axis=alt.Axis(format=".0%"), scale=alt.Scale(zero=True)),
        tooltip=[alt.Tooltip("Relative wealth:Q", format=".2f"), alt.Tooltip("Tax rate:Q", format=".2%")])
    projected = pd.DataFrame({"Relative wealth": relative_wealth(values), "Tax rate": wealth_tax_rates(values, config), "Taxable wealth": values})
    points = alt.Chart(projected, mark=alt.MarkDef(type="circle", color=PALETTE[1], opacity=0.5, size=25)).encode(
        x="Relative wealth:Q", y="Tax rate:Q", tooltip=[alt.Tooltip("Taxable wealth:Q", title="Taxable wealth (EUR)", format=",.4f"), alt.Tooltip("Tax rate:Q", format=".2%")])
    st.altair_chart((line + points).properties(height=240), width="stretch", alt="Current progressive wealth tax curve and projected rates for the population")
    st.caption("Active policy; dots project current wealth. Relative wealth is distance from poorest to richest, not population rank. "
               "Only positive net wealth is taxable; collections are limited by liquid money. Equal wealth pays the minimum rate.")


def age_distribution(population, bin_width, unit):
    max_age = int(population.Age.max()) if len(population) else 0
    edges = np.arange(0, max(max_age, 100) + bin_width + 1, bin_width)
    counts, _ = np.histogram(population.Age.to_numpy(), bins=edges)
    ages = pd.DataFrame({"Age range": [f"{lo}–{hi-1}" for lo, hi in zip(edges[:-1], edges[1:])],
                         "People": counts, "Share": counts / max(len(population), 1)})
    chart = alt.Chart(ages, mark=alt.MarkDef(type="bar")).encode(
        x=alt.X("Age range:N", sort=ages["Age range"].tolist()),
        y=alt.Y(f"{unit}:Q", axis=alt.Axis(format=".0%") if unit == "Share" else alt.Axis(),
                scale=alt.Scale(domain=[0, 1]) if unit == "Share" else alt.Scale(zero=True)),
        color=alt.Color("Age range:N", scale=alt.Scale(scheme="viridis"), legend=None),
        tooltip=["Age range:N", "People:Q", alt.Tooltip("Share:Q", format=".2%")])
    st.altair_chart(chart.properties(height=240), width="stretch", alt="Population age distribution in configurable age bins")
