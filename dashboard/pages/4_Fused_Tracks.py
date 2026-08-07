"""Fused Tracks page.

Audience: anyone investigating persistent fused (tower) tracked
objects -- sensor contributions, classification stability, and
duration by inferred class and sensor combination. Queries
fused_tracks, fused_track_states, and their supporting bridge tables
via fused_track_history.sql, longest_lived_tracks.sql (filtered to
track_type = 'fused_track'), sensor_contributions_per_fused_track.sql,
object_class_changes_over_time.sql,
fused_track_classification_stability_vs_measurement_support.sql,
multi_sensor_tracks_duration_comparison.sql,
fused_track_duration_by_sensor_combination.sql,
fused_track_duration_by_type.sql, and sensor_utilization_summary.sql.

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

from dashboard import charts, formatting, sql_loader
from dashboard.components.query_details import query_source_expander
from dashboard.components.sidebar import render_sidebar
from dashboard.components.tables import render_table
from dashboard.constants import DEFAULT_DB_PATH, LAYOUT, PAGE_ICON
from dashboard.query_catalog import entry_for_name

st.set_page_config(page_title="Fused Tracks", page_icon=PAGE_ICON, layout=LAYOUT)
render_sidebar()


@st.cache_data(show_spinner=False)
def _run(name: str, params_tuple: tuple = (), db_mtime: float = 0.0):
    return sql_loader.run_query(name, dict(params_tuple))


@st.cache_data(show_spinner=False)
def _fused_track_ids(db_mtime: float = 0.0) -> list[str]:
    return sql_loader.list_fused_track_ids()


_db_mtime = DEFAULT_DB_PATH.stat().st_mtime if DEFAULT_DB_PATH.exists() else 0.0

st.title("Fused Tracks")
st.markdown(
    "Persistent fused (tower) tracked objects: duration, sensor contributions, and "
    "classification stability. Queries `fused_tracks` and `fused_track_states` via the "
    "queries listed in each section below."
)

st.markdown("---")

# ---------------------------------------------------------------------
# Duration by inferred class (Drone vs Airplane detail)
# ---------------------------------------------------------------------
st.subheader("Duration by inferred class")
st.caption(
    "Drone/Airplane is inferred from sensor provenance (transponder involvement), not any "
    "object-classification field. Arithmetic mean is the primary statistic; median is "
    "supplementary only. See docs/CHECKSUM_RESOLUTION.md."
)
duration_by_type = _run("fused_track_duration_by_type", db_mtime=_db_mtime)
fig = charts.comparison_bar_chart(
    duration_by_type, "inferred_class", "arithmetic_mean_duration_seconds",
    title="Average fused-track duration by inferred class (arithmetic mean)",
    x_label="Inferred class", y_label="Duration (seconds)",
)
st.plotly_chart(fig, width="stretch")
render_table(duration_by_type, key="fused_duration_by_type")
query_source_expander(entry_for_name("fused_track_duration_by_type"))

st.markdown("---")

# ---------------------------------------------------------------------
# Longest-lived fused tracks
# ---------------------------------------------------------------------
st.subheader("Longest-lived fused tracks")
st.caption("The 10 fused tracks with the longest duration (last state time minus first state time).")
longest = _run("longest_lived_tracks", db_mtime=_db_mtime)
fused_subset = longest[longest["track_type"] == "fused_track"]
fig = charts.bar_chart(
    fused_subset, "track_id", "duration_seconds",
    title="Top 10 longest-lived fused tracks",
    x_label="Fused track ID", y_label="Duration (seconds)",
)
st.plotly_chart(fig, width="stretch")
render_table(fused_subset, key="fused_longest_lived")
query_source_expander(entry_for_name("longest_lived_tracks"))

st.markdown("---")

# ---------------------------------------------------------------------
# Fused track history (drill-down, parameterized)
# ---------------------------------------------------------------------
st.subheader("Fused track history")
st.caption("Classification confidence over time for one selected fused track, from fused_track_states.")
fused_ids = _fused_track_ids(db_mtime=_db_mtime)
selected_fused_id = st.selectbox("Select a fused track ID", options=fused_ids, key="fused_track_selector")
if selected_fused_id is not None:
    fused_history = _run(
        "fused_track_history", params_tuple=(("fused_track_id", selected_fused_id),), db_mtime=_db_mtime
    )
    if fused_history.empty:
        st.warning("No state history found for this track.")
    else:
        fig = charts.line_chart(
            fused_history, "log_time_ns", "object_class_confidence",
            title=f"Classification confidence over time -- fused track {selected_fused_id}",
            x_label="log_time_ns", y_label="object_class_confidence",
        )
        st.plotly_chart(fig, width="stretch")
        render_table(fused_history, key=f"fused_history_{selected_fused_id}")
    query_source_expander(entry_for_name("fused_track_history"))

st.markdown("---")

# ---------------------------------------------------------------------
# Sensor contributions per fused track
# ---------------------------------------------------------------------
st.subheader("Sensor contributions per fused track")
st.caption("Which sensors (CV, radar) contributed measurements to each fused track.")
sensor_contrib = _run("sensor_contributions_per_fused_track", db_mtime=_db_mtime)
render_table(sensor_contrib, key="fused_sensor_contrib")
query_source_expander(entry_for_name("sensor_contributions_per_fused_track"))

st.markdown("---")

# ---------------------------------------------------------------------
# Sensor utilization summary
# ---------------------------------------------------------------------
st.subheader("Sensor utilization summary")
st.caption("Aggregate counts of how often each sensor type contributed across all fused tracks.")
sensor_util = _run("sensor_utilization_summary", db_mtime=_db_mtime)
fig = charts.bar_chart(
    sensor_util, sensor_util.columns[0], sensor_util.columns[1],
    title="Sensor utilization across fused tracks",
    x_label=sensor_util.columns[0], y_label=sensor_util.columns[1],
)
st.plotly_chart(fig, width="stretch")
render_table(sensor_util, key="fused_sensor_util")
query_source_expander(entry_for_name("sensor_utilization_summary"))

st.markdown("---")

# ---------------------------------------------------------------------
# Classification changes over time
# ---------------------------------------------------------------------
st.subheader("Classification changes over time")
st.caption("The fused tracks whose classification changed during their own lifetime (docs/SCHEMA_REVIEW.md finding F6).")
class_changes = _run("object_class_changes_over_time", db_mtime=_db_mtime)
render_table(
    class_changes, key="fused_class_changes",
    truncate_columns={"class_sequence_in_time_order": 100},
)
query_source_expander(entry_for_name("object_class_changes_over_time"))

st.markdown("---")

# ---------------------------------------------------------------------
# Classification stability vs measurement support
# ---------------------------------------------------------------------
st.subheader("Classification stability vs. measurement support")
st.caption("Average measurement count for tracks with stable vs. unstable classification.")
stability = _run("fused_track_classification_stability_vs_measurement_support", db_mtime=_db_mtime)
fig = charts.comparison_bar_chart(
    stability, "classification_stability", "avg_measurement_count",
    title="Avg. measurement count: stable vs. unstable classification",
    x_label="Group", y_label="Avg. measurement count",
)
st.plotly_chart(fig, width="stretch")
render_table(stability, key="fused_stability")
query_source_expander(entry_for_name("fused_track_classification_stability_vs_measurement_support"))

st.markdown("---")

# ---------------------------------------------------------------------
# Multi-sensor tracks duration comparison
# ---------------------------------------------------------------------
st.subheader("Multi-sensor vs. single-sensor track duration")
st.caption("Average fused-track duration for tracks supported by multiple sensors vs. a single sensor.")
multi_sensor = _run("multi_sensor_tracks_duration_comparison", db_mtime=_db_mtime)
fig = charts.comparison_bar_chart(
    multi_sensor, multi_sensor.columns[0], multi_sensor.columns[1],
    title="Average duration: multi-sensor vs. single-sensor tracks",
    x_label=multi_sensor.columns[0], y_label=multi_sensor.columns[1],
)
st.plotly_chart(fig, width="stretch")
render_table(multi_sensor, key="fused_multi_sensor")
query_source_expander(entry_for_name("multi_sensor_tracks_duration_comparison"))

st.markdown("---")

# ---------------------------------------------------------------------
# Duration by sensor combination
# ---------------------------------------------------------------------
st.subheader("Duration by sensor combination")
st.caption("Average fused-track duration broken down by the exact combination of contributing sensors.")
by_combo = _run("fused_track_duration_by_sensor_combination", db_mtime=_db_mtime)
fig = charts.bar_chart(
    by_combo, by_combo.columns[0], by_combo.columns[1],
    title="Average duration by sensor combination",
    x_label=by_combo.columns[0], y_label=by_combo.columns[1],
)
st.plotly_chart(fig, width="stretch")
render_table(by_combo, key="fused_by_combo")
query_source_expander(entry_for_name("fused_track_duration_by_sensor_combination"))
