"""The dashboard's query catalog: maps each approved query to the
small set of *presentation* facts (recommended visualization, which
page(s) show it, a documentation anchor) that do not exist anywhere in
the SQL files themselves and are not analytical content.

Business-meaning metadata (business question, audience, tables
involved, join path, grain, assumptions/limitations) is NOT
duplicated here -- it is read live from each query's own header
comment via dashboard.sql_loader (which itself reuses
scripts/run_analytics.py's QueryFile parser). This module only adds
what genuinely cannot come from the SQL file: how to visualize it and
where it belongs in the UI.

queries/fused_track_duration_by_type.sql predates the "-- Audience:"/
"-- Question:" header convention (it was written in Stage 6B, before
that convention existed), so its audience/question are asked once,
explicitly, right here -- the smallest possible dashboard-specific
override, not a rewrite of the SQL file.

Page structure (Stage 9): pages are organized by data domain rather
than by audience, so each page's purpose is unambiguous from its name.
A query may appear on more than one page where that's genuinely useful
(e.g. the Drone/Airplane result is a headline KPI on Overview and the
full detail on Fused Tracks) -- this never re-runs different SQL, only
the same query rendered in more than one place. No "Radar" page is
defined: no query in the current library performs radar-specific
analysis (radar_detections' own row count already appears in the
Data Quality page's row-count reconciliation), so a standalone Radar
tab would have no real functionality behind it.
"""

from __future__ import annotations

from dataclasses import dataclass

from dashboard.sql_loader import QueryFile, discover_queries

VisualizationKind = str  # one of the constants below, kept as plain str for simplicity

KPI_CARD = "kpi_card"
BAR_CHART = "bar_chart"
COMPARISON_CHART = "comparison_chart"
FUNNEL_CHART = "funnel_chart"
SCATTER_CHART = "scatter_chart"
LINE_CHART = "line_chart"
TABLE = "table"
STATUS_INDICATOR = "status_indicator"
DRILL_DOWN = "drill_down"

OVERVIEW = "overview"
CV_DETECTIONS = "cv_detections"
CV_TRACKS = "cv_tracks"
FUSED_TRACKS = "fused_tracks"
DATA_QUALITY = "data_quality"
SQL_QUERIES = "sql_queries"  # every query is always available here, in addition to its home page(s)

# One entry per query name -> (recommended visualization(s), home page(s)).
# The SQL Queries page is not listed per-entry since ALL queries are
# always available there; see dashboard/pages/6_SQL_Queries.py.
_DASHBOARD_METADATA: dict[str, dict] = {
    # --- overview ----------------------------------------------------------
    "recording_overview": {"visualizations": [KPI_CARD], "pages": [OVERVIEW]},
    "data_quality_issue_summary": {"visualizations": [TABLE, STATUS_INDICATOR], "pages": [OVERVIEW, DATA_QUALITY]},
    "fused_track_duration_by_type": {
        "visualizations": [COMPARISON_CHART, KPI_CARD],
        "pages": [OVERVIEW, FUSED_TRACKS],
        "audience_override": "Executive / Leadership",
        "question_override": "What is the average fused-track duration for Drone objects compared with Airplane objects?",
    },
    # --- cv detections -------------------------------------------------------
    "cv_incorporation_summary": {"visualizations": [KPI_CARD], "pages": [OVERVIEW, CV_DETECTIONS]},
    "cv_detection_to_track_funnel": {"visualizations": [FUNNEL_CHART, KPI_CARD], "pages": [OVERVIEW, CV_DETECTIONS]},
    "cv_focus_quality_vs_incorporation": {"visualizations": [BAR_CHART], "pages": [CV_DETECTIONS]},
    # --- cv tracks -------------------------------------------------------------
    "cv_track_history": {"visualizations": [TABLE, LINE_CHART, DRILL_DOWN], "pages": [CV_TRACKS]},
    "longest_lived_tracks": {"visualizations": [BAR_CHART, TABLE], "pages": [CV_TRACKS, FUSED_TRACKS]},
    "cv_detection_quality_vs_track_persistence": {"visualizations": [SCATTER_CHART, TABLE], "pages": [CV_TRACKS]},
    # --- fused tracks -------------------------------------------------------------
    "fused_track_history": {"visualizations": [TABLE, LINE_CHART, DRILL_DOWN], "pages": [FUSED_TRACKS]},
    "sensor_utilization_summary": {"visualizations": [BAR_CHART, TABLE], "pages": [FUSED_TRACKS]},
    "sensor_contributions_per_fused_track": {"visualizations": [TABLE], "pages": [FUSED_TRACKS]},
    "object_class_changes_over_time": {"visualizations": [TABLE], "pages": [FUSED_TRACKS]},
    "fused_track_classification_stability_vs_measurement_support": {
        "visualizations": [COMPARISON_CHART],
        "pages": [FUSED_TRACKS],
    },
    "multi_sensor_tracks_duration_comparison": {"visualizations": [COMPARISON_CHART], "pages": [FUSED_TRACKS]},
    "fused_track_duration_by_sensor_combination": {"visualizations": [BAR_CHART, TABLE], "pages": [FUSED_TRACKS]},
    # --- data quality -------------------------------------------------------
    "table_row_count_reconciliation": {"visualizations": [TABLE], "pages": [DATA_QUALITY, OVERVIEW]},
    "duplicate_relationship_check": {"visualizations": [STATUS_INDICATOR, TABLE], "pages": [DATA_QUALITY]},
    "class_distribution_completeness_and_ordering": {"visualizations": [STATUS_INDICATOR, TABLE], "pages": [DATA_QUALITY]},
    "enum_raw_name_consistency": {"visualizations": [STATUS_INDICATOR, TABLE], "pages": [DATA_QUALITY]},
    "source_message_child_reconciliation": {"visualizations": [STATUS_INDICATOR, TABLE], "pages": [DATA_QUALITY]},
    "zero_duration_or_single_state_tracks": {"visualizations": [TABLE], "pages": [DATA_QUALITY]},
}


@dataclass(frozen=True)
class CatalogEntry:
    query: QueryFile
    visualizations: list[str]
    pages: list[str]
    doc_anchor: str
    audience: str
    question: str


def _doc_anchor(query: QueryFile) -> str:
    """The docs/ANALYTICAL_INSIGHTS.md markdown anchor for this query's
    section header, e.g. queries/executive/recording_overview.sql ->
    #queriesexecutiverecording_overviewsql (GitHub-style anchor
    generation: lowercase, strip punctuation, spaces/slashes -> hyphens
    then stripped)."""
    label = f"queries/{query.category}/{query.name}.sql" if query.category != "general" else f"queries/{query.name}.sql"
    return "docs/ANALYTICAL_INSIGHTS.md#" + label.replace("/", "").replace(".", "").replace("_", "").lower()


def build_catalog() -> list[CatalogEntry]:
    entries: list[CatalogEntry] = []
    for query in discover_queries():
        meta = _DASHBOARD_METADATA.get(query.name)
        if meta is None:
            # Defensive default for a query the catalog hasn't been
            # told about yet -- surfaced on the SQL Queries page only,
            # never silently dropped from discovery.
            meta = {"visualizations": [TABLE], "pages": []}
        entries.append(
            CatalogEntry(
                query=query,
                visualizations=meta["visualizations"],
                pages=meta["pages"],
                doc_anchor=_doc_anchor(query),
                audience=meta.get("audience_override") or query.audience,
                question=meta.get("question_override") or query.question,
            )
        )
    return entries


def entries_for_page(page: str) -> list[CatalogEntry]:
    return [entry for entry in build_catalog() if page in entry.pages]


def entry_for_name(name: str) -> CatalogEntry | None:
    for entry in build_catalog():
        if entry.query.name == name:
            return entry
    return None
