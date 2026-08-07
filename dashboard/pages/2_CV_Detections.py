"""CV Detections page.

Audience: anyone investigating individual camera (CV) detections and
how many of them were incorporated into a persistent CV track. Data
comes from cv_detections and cv_detection_track_links via the
cv_incorporation_summary, cv_detection_to_track_funnel, and
cv_focus_quality_vs_incorporation queries -- nothing here is
recomputed in Python.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st

from dashboard import charts, formatting, sql_loader
from dashboard.components.metrics import kpi_row
from dashboard.components.query_details import query_source_expander
from dashboard.components.sidebar import render_sidebar
from dashboard.components.tables import render_table
from dashboard.constants import DEFAULT_DB_PATH, LAYOUT, PAGE_ICON
from dashboard.query_catalog import entry_for_name

st.set_page_config(page_title="CV Detections", page_icon=PAGE_ICON, layout=LAYOUT)
render_sidebar()


@st.cache_data(show_spinner=False)
def _run(name: str, params_tuple: tuple = (), db_mtime: float = 0.0):
    return sql_loader.run_query(name, dict(params_tuple))


_db_mtime = DEFAULT_DB_PATH.stat().st_mtime if DEFAULT_DB_PATH.exists() else 0.0

st.title("CV Detections")
st.markdown(
    "Individual camera (CV) detections and how many of them were incorporated into a "
    "persistent CV track. Queries `cv_detections` and `cv_detection_track_links` via "
    "`cv_incorporation_summary.sql`, `cv_detection_to_track_funnel.sql`, and "
    "`cv_focus_quality_vs_incorporation.sql`."
)

st.markdown("---")

# ---------------------------------------------------------------------
# Incorporation summary
# ---------------------------------------------------------------------
st.subheader("CV incorporation summary")
st.caption(
    "Percentage of CV detections that were linked to at least one CV track, computed as "
    "distinct incorporated detections divided by total detections."
)
incorporation = _run("cv_incorporation_summary", db_mtime=_db_mtime)
row = incorporation.iloc[0]
kpi_row(
    [
        ("Total CV detections", formatting.format_count(row["total_cv_detections"]), "COUNT(*) from cv_detections."),
        ("Incorporated detections", formatting.format_count(row["incorporated_cv_detections"]), "Distinct cv_detections rows with a matching row in cv_detection_track_links."),
        ("Incorporation rate", formatting.format_percentage(row["incorporation_percentage"]), "Incorporated detections / total detections."),
    ]
)
render_table(incorporation, key="cvdet_incorporation")
query_source_expander(entry_for_name("cv_incorporation_summary"))

st.markdown("---")

# ---------------------------------------------------------------------
# Detection-to-track funnel
# ---------------------------------------------------------------------
st.subheader("Detection-to-track funnel")
st.caption("How total detections narrow down to incorporated detections and the persistent tracks that received them.")
funnel = _run("cv_detection_to_track_funnel", db_mtime=_db_mtime)
funnel_row = funnel.iloc[0]
fig = charts.funnel_chart(
    labels=["Total detections", "Incorporated detections", "Tracks receiving detections"],
    values=[
        funnel_row["total_detections"],
        funnel_row["incorporated_detections"],
        funnel_row["tracks_receiving_detections"],
    ],
    title="CV detection to track funnel",
)
st.plotly_chart(fig, width="stretch")
render_table(funnel, key="cvdet_funnel")
query_source_expander(entry_for_name("cv_detection_to_track_funnel"))

st.markdown("---")

# ---------------------------------------------------------------------
# Focus quality vs incorporation
# ---------------------------------------------------------------------
st.subheader("Focus quality vs. incorporation")
st.caption(
    "CV incorporation rate grouped by the detection's focus-quality classification. "
    "Correlational only -- already tested and ruled out as an explanation for the "
    "CV-incorporation checksum gap."
)
focus_quality = _run("cv_focus_quality_vs_incorporation", db_mtime=_db_mtime)
fig = charts.bar_chart(
    focus_quality, "focus_quality_name", "incorporation_pct",
    title="CV incorporation rate by focus quality",
    x_label="Focus quality", y_label="Incorporation %",
)
st.plotly_chart(fig, width="stretch")
render_table(focus_quality, key="cvdet_focus_quality")
query_source_expander(entry_for_name("cv_focus_quality_vs_incorporation"))
