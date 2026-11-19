"""Shared budget visualizations; all percentages have an explicit denominator."""
import altair as alt
import pandas as pd
import streamlit as st
from capital_dynamics.budget import COLORS, allocation_rows
from capital_dynamics.currency import euro


def allocation_view(total, shares, spent, *, title="Policy allocation", key="budget"):
    st.subheader(title, help="Compare reserved shares of the common policy budget with shares of actual expenditure. Hover over a segment for its amount and percentage; unused allocations stay with government.")
    st.caption(f"Policy budget after mandatory debt service: {euro(total)} · Allocations use this total; spending shares use actual policy payments. Unused funds are retained.")
    data = pd.DataFrame(allocation_rows(total, shares, spent))
    data["Budget"] = "100% of policy budget"
    data["Order"] = range(len(data))
    names = data.Policy.tolist()
    colors = alt.Scale(domain=names, range=[*COLORS[:4], COLORS[-1]])
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
                                   alt.Tooltip("Amount:Q", format=",.2f", title="Amount (EUR)")],
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
                     column_config={
                         "Policy": st.column_config.TextColumn(help="Spending purpose. Unallocated is the share of the common budget not reserved for any policy."),
                         "Allocation (% of total budget)": st.column_config.NumberColumn(
                             format="%.1f%%", help="Reserved percentage of the entire common policy budget; all rows use the same denominator."),
                         "Actual (% of expenditure)": st.column_config.NumberColumn(
                             format="%.1f%%", help="This policy's actual payment divided by total actual expenditure, not by the common budget. Zero when nothing has been spent."),
                         "Allocated": st.column_config.NumberColumn("Allocated (EUR)", format="€%.2f", help="Euros reserved for this policy from the common budget."),
                         "Spent": st.column_config.NumberColumn("Spent (EUR)", format="€%.2f", help="Euros actually paid for this policy in the last recorded period."),
                         "Unused": st.column_config.NumberColumn("Unused (EUR)", format="€%.2f", help="Allocated minus spent, retained by government rather than automatically reassigned."),
                     },
                     alt="Policy allocation percentages, allocated amounts, actual spending, unused funds and shares of expenditure")
    if not sum(spent.values()):
        st.caption("No expenditure yet; actual expenditure percentages are zero, not a forecast.")
