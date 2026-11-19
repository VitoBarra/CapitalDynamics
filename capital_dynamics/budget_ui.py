"""Shared budget visualizations; all percentages have an explicit denominator."""
import altair as alt
import pandas as pd
import streamlit as st
from capital_dynamics.budget import COLORS, allocation_rows


def allocation_view(total, shares, spent, *, title="Policy allocation", key="budget"):
    st.subheader(title)
    st.caption(f"Common budget: {total:,.2f} · Allocations use this total; spending shares use actual payments. Unused funds are retained.")
    data = pd.DataFrame(allocation_rows(total, shares, spent))
    data["Budget"] = "100% of policy budget"
    data["Order"] = range(len(data))
    names = data.Policy.tolist()
    colors = alt.Scale(domain=names, range=COLORS if len(shares) == 5 else [*COLORS[:4], COLORS[-1]])
    configured = data.assign(Budget="Budget allocation", Percent=data["Allocation (% of total budget)"], Amount=data.Allocated)
    plotted = configured
    if sum(spent.values()):
        actual = data.assign(Budget="Actual spending", Percent=data["Actual (% of expenditure)"], Amount=data.Spent)
        plotted = pd.concat([configured, actual], ignore_index=True)
    plotted["Label position"] = plotted.groupby("Budget", sort=False).Percent.cumsum() - plotted.Percent / 2
    bars = alt.Chart(plotted, mark=alt.MarkDef(type="bar")).encode(
        x=alt.X("Percent:Q", stack="zero", scale=alt.Scale(domain=[0, 100]),
                axis=alt.Axis(labelExpr="datum.value + '%'"), title=None),
        y=alt.Y("Budget:N", title=None, sort=["Budget allocation", "Actual spending"]),
        color=alt.Color("Policy:N", scale=colors, sort=names),
        order="Order:Q", tooltip=["Budget:N", "Policy:N", alt.Tooltip("Percent:Q", format=".1f"),
                                   alt.Tooltip("Amount:Q", format=",.2f")],
    ).properties(height=110 if sum(spent.values()) else 70)
    # Labels use the full stack so zero/small slices do not shift the other labels.
    text = alt.Chart(plotted, mark=alt.MarkDef(type="text", color="white")).transform_calculate(
        Label="datum.Percent >= 5 ? format(datum.Percent, '.0f') + '%' : ''"
    ).encode(
        x=alt.X("Label position:Q"), y=alt.Y("Budget:N", sort=["Budget allocation", "Actual spending"], title=None),
        text="Label:N")
    st.altair_chart(bars + text, width="stretch", key=f"{key}_allocation_chart",
                    alt="Government policy allocations as percentages of the same total budget, including unallocated funds")
    with st.expander("Allocation amounts and unused funds"):
        st.dataframe(data.drop(columns=["Budget", "Order"]), hide_index=True,
                     column_config={name: st.column_config.NumberColumn(format="%.1f%%")
                                    for name in ("Allocation (% of total budget)", "Actual (% of expenditure)")},
                     alt="Policy allocation percentages, allocated amounts, actual spending, unused funds and shares of expenditure")
    if not sum(spent.values()):
        st.caption("No expenditure yet; actual expenditure percentages are zero, not a forecast.")
