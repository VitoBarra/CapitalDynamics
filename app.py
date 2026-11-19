"""Capital Dynamics: monetary economy dashboard."""
import altair as alt
import streamlit as st

from monetary_ui import monetary_workspace


# Every resident remains available beyond Altair's default row limit.
alt.data_transformers.disable_max_rows()

st.set_page_config(page_title="Capital Dynamics", page_icon=":material/monitoring:", layout="wide")
st.title("Capital Dynamics")
st.caption("Economy sandbox")
st.write("Explore how production, money, public policy and demographics shape wealth over time.")

monetary_workspace()
