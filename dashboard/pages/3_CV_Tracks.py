"""CV Tracks page.

Audience: anyone investigating persistent camera (CV) tracked objects
-- how long they last, their state history over time, and how
detection quality relates to how long a track persists. Queries
cv_tracks and cv_track_states via cv_track_history.sql,
longest_lived_tracks.sql (filtered to track_type = 'cv_track'), and
cv_detection_quality_vs_track_persistence.sql.

Note: CV tracks and fused tracks are independent tracking systems with
zero identifier overlap (docs/KEY_ANALYSIS.md) -- this page never joins
or compares them by ID.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st

from dashboard import charts, sql_loader
from dashboard.components.query_details import query_source_expander
from dashboard.components.sidebar import render_sidebar
from dashboard.components.tables import render_table
from dashboard.constants import DEFAULT_DB_PATH, LAYOUT, PAGE_ICON
from dashboard.query_catalog import entry_for_name

st.set_page_config(page_title="CV Tracks", page_icon=PAGE_ICON, layout=LAYOUT)
render_sidebar()


@st.cache_data(show_spinner=False)
def _run(name: str, params_tuple: tuple = (), db_mtime: float = 0.0):
    return sql_loader.run_query(name, dict(params_tuple))


@st.cache_data(show_spinner=False)
def _track_ids(db_mtime: float = 0.0) -> list[int]:
    return sql_loader.list_cv_track_ids()


_db_mtime = DEFAULT_DB_PATH.stat().st_mtime if DEFAULT_DB_PATH.exists() else 0.0

st.title("CV Tracks")
st.markdown(
    "Persistent camera (CV) tracked objects: how long they last and how their state "
    "changes over time. Queries `cv_tracks` and `cv_track_states` via `cv_track_history.sql`, "
    "`longest_lived_tracks.sql`, and `cv_detection_quality_vs_track_persistence.sql`."
)

st.markdown("---")

# ---------------------------------------------------------------------
# Longest-lived CV tracks
# ---------------------------------------------------------------------
st.subheader("Longest-lived CV tracks")
st.caption("The 10 CV tracks with the longest duration (last state time minus first state time).")
longest = _run("longest_lived_tracks", db_mtime=_db_mtime)
cv_subset = longest[longest["track_type"] == "cv_track"]
fig = charts.bar_chart(
    cv_subset, "track_id", "duration_seconds",
    title="Top 10 longest-lived CV tracks",
    x_label="CV track ID", y_label="Duration (seconds)",
)
st.plotly_chart(fig, width="stretch")
render_table(cv_subset, key="cvtrk_longest_lived")
query_source_expander(entry_for_name("longest_lived_tracks"))

st.markdown("---")

# ---------------------------------------------------------------------
# CV track history (drill-down, parameterized)
# ---------------------------------------------------------------------
st.subheader("CV track history")
st.caption("Classification confidence over time for one selected CV track, from cv_track_states.")
cv_ids = _track_ids(db_mtime=_db_mtime)
selected_track_id = st.selectbox("Select a CV track ID", options=cv_ids, key="cv_track_selector")
if selected_track_id is not None:
    cv_history = _run("cv_track_history", params_tuple=(("track_id", selected_track_id),), db_mtime=_db_mtime)
    if cv_history.empty:
        st.warning("No state history found for this track.")
    else:
        fig = charts.line_chart(
            cv_history, "log_time_ns", "top_predicted_class_probability",
            title=f"Classification confidence over time -- CV track {selected_track_id}",
            x_label="log_time_ns", y_label="Top predicted class probability",
        )
        st.plotly_chart(fig, width="stretch")
        render_table(cv_history, key=f"cv_history_{selected_track_id}")
    query_source_expander(entry_for_name("cv_track_history"))

st.markdown("---")

# ---------------------------------------------------------------------
# CV detection quality vs track persistence
# ---------------------------------------------------------------------
st.subheader("Detection quality vs. track persistence")
st.caption(
    "One point per CV track: average detection score vs. track duration. Point size reflects "
    "the percentage of sharp-or-better focus detections in that track. Descriptive correlation, "
    "not a controlled experiment."
)
quality_persistence = _run("cv_detection_quality_vs_track_persistence", db_mtime=_db_mtime)
fig = charts.scatter_chart(
    quality_persistence, "avg_detection_score", "track_duration_seconds",
    title="Avg. detection score vs. track duration (one point per CV track)",
    x_label="Avg. detection score", y_label="Track duration (seconds)",
    hover_col="track_id", size_col="pct_sharp_or_better_focus",
)
st.plotly_chart(fig, width="stretch")
render_table(quality_persistence, key="cvtrk_quality_persistence")
query_source_expander(entry_for_name("cv_detection_quality_vs_track_persistence"))
