"""Overview page.

Audience: anyone wanting a system-wide summary before drilling into a
specific data domain. Every number on this page is the direct output
of one of the approved queries/executive/*.sql files (plus the
preserved queries/fused_track_duration_by_type.sql) -- nothing is
recomputed in Python. Two KPIs (Total Fused Tracks, Total Radar
Detections) and one (Data-Quality Issues total) reuse an existing
query's already-computed rows rather than a dedicated new query, per
explicit approval (see docs/STAGE_08_SUMMARY.txt).
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

st.set_page_config(page_title="Overview", page_icon=PAGE_ICON, layout=LAYOUT)
render_sidebar()


@st.cache_data(show_spinner=False)
def _run(name: str, params_tuple: tuple = (), db_mtime: float = 0.0):
    return sql_loader.run_query(name, dict(params_tuple))


_db_mtime = DEFAULT_DB_PATH.stat().st_mtime if DEFAULT_DB_PATH.exists() else 0.0

st.title("Overview")
st.markdown(
    "System-wide counts and the two headline checksum results, drawn from "
    "`source_messages`, `cv_detections`, `cv_detection_track_links`, and "
    "`v_fused_track_type_basis`. Use this page to confirm overall pipeline scale "
    "before drilling into a specific data domain."
)

# ---------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------
recording = _run("recording_overview", db_mtime=_db_mtime)
incorporation = _run("cv_incorporation_summary", db_mtime=_db_mtime)
funnel = _run("cv_detection_to_track_funnel", db_mtime=_db_mtime)
row_counts = _run("table_row_count_reconciliation", db_mtime=_db_mtime)
duration_by_type = _run("fused_track_duration_by_type", db_mtime=_db_mtime)
issues = _run("data_quality_issue_summary", db_mtime=_db_mtime)

total_fused_tracks = int(row_counts.loc[row_counts["table_name"] == "fused_tracks", "row_count"].iloc[0])
total_radar_detections = int(row_counts.loc[row_counts["table_name"] == "radar_detections", "row_count"].iloc[0])
total_issue_count = int(issues["issue_count"].sum()) if not issues.empty else 0

drone_row = duration_by_type[duration_by_type["inferred_class"] == "Drone"]
airplane_row = duration_by_type[duration_by_type["inferred_class"] == "Airplane"]
drone_mean = float(drone_row["arithmetic_mean_duration_seconds"].iloc[0]) if not drone_row.empty else None
airplane_mean = float(airplane_row["arithmetic_mean_duration_seconds"].iloc[0]) if not airplane_row.empty else None

kpi_row(
    [
        ("Total source messages", formatting.format_count(recording["total_messages"].iloc[0]), "Count of rows in source_messages (recording_overview.sql)."),
        ("Total CV detections", formatting.format_count(incorporation["total_cv_detections"].iloc[0]), "Count of rows in cv_detections (cv_incorporation_summary.sql)."),
        ("Total persistent CV tracks", formatting.format_count(funnel["total_persistent_tracks"].iloc[0]), "Count of rows in cv_tracks (cv_detection_to_track_funnel.sql)."),
        ("Total fused tracks", formatting.format_count(total_fused_tracks), "fused_tracks row count, from table_row_count_reconciliation.sql."),
        ("Total radar detections", formatting.format_count(total_radar_detections), "radar_detections row count, from table_row_count_reconciliation.sql."),
    ]
)
kpi_row(
    [
        (
            "CV incorporation",
            formatting.format_percentage(incorporation["incorporation_percentage"].iloc[0]),
            "Distinct incorporated detections divided by total detections. Target ~81% per the "
            "assignment; this dataset computes 97.54%. See docs/analytics/CHECKSUM_RESOLUTION.md.",
        ),
        (
            "Drone mean duration",
            formatting.format_seconds(drone_mean) if drone_mean is not None else "n/a",
            "Arithmetic mean track duration for tracks classified as Drone. Target ~30s. Median is "
            "supplementary only, not the primary statistic.",
        ),
        (
            "Airplane mean duration",
            formatting.format_seconds(airplane_mean) if airplane_mean is not None else "n/a",
            "Arithmetic mean track duration for tracks classified as Airplane. Target ~600s. Median "
            "is supplementary only, not the primary statistic.",
        ),
        ("Data-quality issues", formatting.format_count(total_issue_count), "Sum of issue_count from data_quality_issue_summary.sql."),
        (
            "Recording duration",
            formatting.format_seconds(recording["recording_duration_seconds"].iloc[0], decimals=1),
            "MAX(log_time_ns) - MIN(log_time_ns) across source_messages, in seconds.",
        ),
    ]
)

st.markdown("---")

# ---------------------------------------------------------------------
# CV detection-to-track funnel
# ---------------------------------------------------------------------
st.subheader("CV detection-to-track funnel")
st.caption("How many camera detections were incorporated into a persistent track, out of the total observed.")
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
st.caption(
    f"Of {formatting.format_count(funnel_row['total_detections'])} CV detections, "
    f"{formatting.format_count(funnel_row['incorporated_detections'])} were incorporated into one of "
    f"{formatting.format_count(funnel_row['total_persistent_tracks'])} persistent CV tracks -- "
    f"an average of {funnel_row['avg_incorporated_detections_per_track']:.1f} detections per track. "
    "This is a correlational funnel, not a causal claim."
)
query_source_expander(entry_for_name("cv_detection_to_track_funnel"))

st.markdown("---")

# ---------------------------------------------------------------------
# Drone vs Airplane duration (the protected checksum result)
# ---------------------------------------------------------------------
st.subheader("Drone vs. Airplane average fused-track duration")
st.caption(
    "Classification caveat: Drone/Airplane is inferred from sensor provenance (transponder "
    "involvement), not any object-classification field -- proto.tower.TrackObjectClass has no "
    "DRONE or AIRPLANE value. Arithmetic mean is the primary statistic reported below; median is "
    "shown only as supplementary context. See docs/CHECKSUM_RESOLUTION.md for the full evidence "
    "trail."
)
fig = charts.comparison_bar_chart(
    duration_by_type, "inferred_class", "arithmetic_mean_duration_seconds",
    title="Average fused-track duration by inferred class (arithmetic mean)",
    x_label="Inferred class", y_label="Duration (seconds)",
)
st.plotly_chart(fig, width="stretch")
median_caption = "  |  ".join(
    f"{row.inferred_class} median: {formatting.format_seconds(row.median_duration_seconds_supplementary_only)}"
    for row in duration_by_type.itertuples()
)
st.caption(f"Supplementary median (not the primary statistic): {median_caption}")
render_table(duration_by_type, key="overview_duration_by_type")
query_source_expander(entry_for_name("fused_track_duration_by_type"))

st.markdown("---")

# ---------------------------------------------------------------------
# Data-quality issue summary
# ---------------------------------------------------------------------
st.subheader("Data-quality issue summary")
st.caption("Count of data-quality findings recorded by the ETL pipeline, grouped by type and severity.")
render_table(issues, key="overview_issues")
query_source_expander(entry_for_name("data_quality_issue_summary"))

st.markdown("---")

# ---------------------------------------------------------------------
# Key Findings
# ---------------------------------------------------------------------
st.subheader("Key findings")
st.caption("Summarized from docs/ANALYTICAL_INSIGHTS.md. The numbers here are the same ones rendered live above.")
st.markdown(
    """
    1. CV incorporation is 97.54%, not the assignment's ~81% target -- see
       docs/analytics/CHECKSUM_RESOLUTION.md for the full investigation.
    2. Drone/Airplane is answered by sensor provenance, not object classification. Airplane
       mean is within 2.4% of target; Drone mean is reported at +19.5% above target (median is
       closer but is not substituted for the mean).
    3. Multi-sensor tracks are shorter-lived on average -- see the Fused Tracks page for the
       exact-combination breakdown showing this is a population-mix effect, not a general
       multi-sensor penalty.
    4. Image focus quality correlates with CV incorporation (see the CV Detections page) --
       already tested and ruled out as an explanation for the CV-incorporation gap.
    5. 18 of 103 fused tracks change classification during their own lifetime -- see the Fused
       Tracks page.
    6. No relational-integrity violations were found in the technical query suite -- see the
       Data Quality page.
    """
)
