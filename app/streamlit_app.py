"""CivicPulse dashboard — the ward officer's 'act first' view.

Run locally:   streamlit run app/streamlit_app.py
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# allow `from src...` when run via `streamlit run app/streamlit_app.py`
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline import (  # noqa: E402
    load_grievances, amplify, rank_hotspots, ward_rollup, kpis,
)
from src.gemini_brief import generate_brief  # noqa: E402

st.set_page_config(page_title="CivicPulse — BBMP Grievance Intelligence",
                   page_icon="🛠️", layout="wide")


@st.cache_data(show_spinner="Loading grievance data…")
def get_data(scale_to: int) -> pd.DataFrame:
    base = load_grievances()
    if scale_to and scale_to > len(base):
        return amplify(base, scale_to)
    return base


# ------------------------------------------------------------------ sidebar
st.sidebar.title("🛠️ CivicPulse")
st.sidebar.caption("BBMP Grievance Intelligence · Bengaluru")

scale = st.sidebar.select_slider(
    "Dataset scale (rows)",
    options=[0, 50_000, 250_000, 1_000_000],
    value=50_000,
    help="0 = raw data as-is. Larger = city-scale demo / benchmark volume.",
)
df = get_data(scale)

all_cats = sorted(df["category"].dropna().unique().tolist())
cats = st.sidebar.multiselect("Categories", all_cats, default=all_cats)
min_sev = st.sidebar.slider("Minimum severity", 1, 5, 1)

dmin, dmax = df["grievance_date"].min().date(), df["grievance_date"].max().date()
since, until = st.sidebar.slider(
    "Date range", min_value=dmin, max_value=dmax, value=(dmin, dmax),
)

# ------------------------------------------------------------------ compute
hot = rank_hotspots(df, categories=cats, min_severity=min_sev,
                    since=since, until=until)
view = df[(df["grievance_date"].dt.date >= since) &
          (df["grievance_date"].dt.date <= until)]
if cats:
    view = view[view["category"].isin(cats)]
if min_sev > 1:
    view = view[view["severity"] >= min_sev]
k = kpis(view)

# ------------------------------------------------------------------ header
st.title("Where should we fix things first this week?")
st.caption(f"{k['date_min']} → {k['date_max']} · real BBMP grievance data "
           f"(OpenCity, Public Domain)")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Complaints", f"{k['total_complaints']:,}")
c2.metric("Unresolved", f"{k['unresolved_pct']}%")
c3.metric("Wards", k["wards"])
c4.metric("Public-safety", f"{k['public_safety_pct']}%")

st.divider()
left, right = st.columns([3, 2])

with left:
    st.subheader("🔥 Priority hotspots — act on these first")
    if len(hot):
        show = hot.copy()
        show["unresolved"] = (show["unresolved_rate"] * 100).round(0).astype(int).astype(str) + "%"
        show["priority"] = show["priority"].round(1)
        st.dataframe(
            show[["rank", "ward", "category", "complaints",
                  "unresolved", "severity", "last_seen", "priority"]],
            use_container_width=True, hide_index=True, height=430,
        )
        st.download_button("⬇️ Download worklist (CSV)",
                           hot.to_csv(index=False), "civicpulse_worklist.csv")
    else:
        st.info("No complaints match the current filters.")

with right:
    st.subheader("🗺️ Ward priority")
    wr = ward_rollup(hot)
    if len(wr):
        top = wr.head(12)
        fig = px.bar(top, x="total_priority", y="ward", orientation="h",
                     color="worst_severity", color_continuous_scale="Reds",
                     labels={"total_priority": "priority", "ward": ""})
        fig.update_layout(yaxis={"categoryorder": "total ascending"},
                          height=430, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("🧭 AI intervention roadmap")
if st.button("Generate roadmap for current view", type="primary"):
    with st.spinner("Writing the roadmap…"):
        st.markdown(generate_brief(hot, k))
else:
    st.caption("Click to generate a written action plan for the filtered hotspots.")

# ------------------------------------------------------------------ mix chart
st.divider()
st.subheader("📊 Complaint mix")
mix = (view.groupby("category").size().reset_index(name="complaints")
       .sort_values("complaints", ascending=False).head(12))
if len(mix):
    st.plotly_chart(
        px.bar(mix, x="complaints", y="category", orientation="h",
               labels={"category": ""}).update_layout(
            yaxis={"categoryorder": "total ascending"}, height=380,
            margin=dict(l=0, r=0, t=10, b=0)),
        use_container_width=True,
    )
