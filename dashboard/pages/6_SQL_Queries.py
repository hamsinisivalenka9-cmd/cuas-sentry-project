"""SQL Queries page.

Two ways to run SQL against the database, both strictly read-only:

1. Approved queries -- browse, inspect, run, and download results from
   any of the approved .sql files under queries/ (discovered via
   dashboard.sql_loader, which reuses scripts/run_analytics.py's
   QueryFile parser). Only executes .sql files already present on
   disk -- never accepts a filesystem path from the user.

2. Query editor -- a free-text SQL box for read-only ad-hoc queries.
   Every submission is checked by dashboard.sql_validator before
   execution: it must be a single statement beginning with SELECT,
   WITH, EXPLAIN, or PRAGMA, and must not contain a write keyword
   anywhere in the statement (including inside a comment, since
   comments are stripped before both checks). The underlying
   connection is also opened read-only at the SQLite layer (mode=ro +
   PRAGMA query_only = ON, dashboard/database.py) -- the validator is
   defense-in-depth on top of that, not a substitute for it. Results
   are capped at DEFAULT_QUERY_ROW_LIMIT rows.
"""

from __future__ import annotations

import logging
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
import streamlit as st

logger = logging.getLogger("cuas_dashboard.sql_queries")

from dashboard import sql_loader
from dashboard.components.sidebar import render_sidebar
from dashboard.components.tables import render_table
from dashboard.constants import CATEGORY_LABELS, DEFAULT_DB_PATH, DEFAULT_QUERY_ROW_LIMIT, LAYOUT, PAGE_ICON
from dashboard.database import DatabaseNotFoundError, connect_read_only
from dashboard.query_catalog import build_catalog
from dashboard.sql_validator import validate_read_only_sql

st.set_page_config(page_title="SQL Queries", page_icon=PAGE_ICON, layout=LAYOUT)
render_sidebar()

st.title("SQL Queries")
st.markdown(
    "Run any approved analytical query, or write and run your own read-only SQL against "
    "`data/output/sentry.db`. The connection is opened read-only at the SQLite layer "
    f"(`mode=ro` + `PRAGMA query_only = ON`); the ad-hoc editor is additionally restricted to "
    f"a single SELECT/WITH/EXPLAIN/PRAGMA statement and returns at most "
    f"{DEFAULT_QUERY_ROW_LIMIT:,} rows."
)

# ---------------------------------------------------------------------
# Section 1: approved queries
# ---------------------------------------------------------------------
st.header("Approved queries")
st.caption(
    "Every query below is one of the .sql files under queries/. Nothing here is written "
    "or modified from the UI -- this only discovers, executes, and displays the file's own SQL."
)

catalog = build_catalog()
categories = sorted({entry.query.category for entry in catalog})

selected_category = st.selectbox(
    "Category",
    options=["(all)"] + categories,
    format_func=lambda c: c if c == "(all)" else CATEGORY_LABELS.get(c, c),
)

filtered = catalog if selected_category == "(all)" else [e for e in catalog if e.query.category == selected_category]
filtered = sorted(filtered, key=lambda e: (e.query.category, e.query.name))

selected_name = st.selectbox(
    "Query",
    options=[e.query.name for e in filtered],
    format_func=lambda name: f"{next(e.query.category for e in filtered if e.query.name == name)}/{name}",
)

entry = next(e for e in filtered if e.query.name == selected_name)
query = entry.query

st.subheader(f"{query.category}/{query.name}")
st.markdown(f"**Business question:** {entry.question}")
st.markdown(f"**Audience:** {entry.audience}")
st.markdown("**Documentation:** `docs/ANALYTICAL_INSIGHTS.md`")

with st.expander("SQL source", expanded=False):
    st.code(query.sql, language="sql")

params: dict[str, object] = {}
if query.required_params:
    st.markdown("**Parameters:**")
    for param_name in sorted(query.required_params):
        if param_name == "track_id":
            options = sql_loader.list_cv_track_ids()
            params[param_name] = st.selectbox(f"{param_name} (cv_tracks.track_id)", options=options, key=f"catalog_{param_name}")
        elif param_name == "fused_track_id":
            options = sql_loader.list_fused_track_ids()
            params[param_name] = st.selectbox(f"{param_name} (fused_tracks.fused_track_id)", options=options, key=f"catalog_{param_name}")
        else:
            params[param_name] = st.text_input(param_name, key=f"catalog_{param_name}")

if st.button("Run query", type="primary", key="run_catalog_query"):
    try:
        result_df = sql_loader.run_query(query.name, params, db_path=DEFAULT_DB_PATH)
    except sql_loader.MissingParameterError as exc:
        st.error(f"Missing parameter: {exc}")
    except sql_loader.UnexpectedParameterError as exc:
        st.error(f"Unexpected parameter: {exc}")
    except Exception as exc:  # noqa: BLE001 - deliberately broad: never show a raw traceback to the user
        logger.exception("SQL Queries page failed running %s/%s with params=%r", query.category, query.name, params)
        st.error(
            f"This query failed to execute ({type(exc).__name__}: {exc}). "
            "Full details have been logged for debugging."
        )
    else:
        st.caption(f"{len(result_df)} row(s) returned.")
        render_table(result_df, key=f"catalog_{query.name}")

st.markdown("---")

# ---------------------------------------------------------------------
# Section 2: named examples + free-text query editor
# ---------------------------------------------------------------------
st.header("Query editor")
st.caption(
    "Write and run your own read-only SQL. Only a single statement beginning with SELECT, "
    "WITH, EXPLAIN, or PRAGMA is accepted; INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, "
    "REPLACE, ATTACH, DETACH, and VACUUM are rejected, including when hidden inside a comment "
    "or after a semicolon."
)

_EXAMPLE_QUERIES: dict[str, str] = {
    "Row counts by major table": (
        "SELECT 'source_messages' AS table_name, COUNT(*) AS row_count FROM source_messages\n"
        "UNION ALL SELECT 'cv_detections', COUNT(*) FROM cv_detections\n"
        "UNION ALL SELECT 'cv_tracks', COUNT(*) FROM cv_tracks\n"
        "UNION ALL SELECT 'cv_track_states', COUNT(*) FROM cv_track_states\n"
        "UNION ALL SELECT 'radar_detections', COUNT(*) FROM radar_detections\n"
        "UNION ALL SELECT 'fused_tracks', COUNT(*) FROM fused_tracks\n"
        "UNION ALL SELECT 'fused_track_states', COUNT(*) FROM fused_track_states\n"
        "UNION ALL SELECT 'data_quality_issues', COUNT(*) FROM data_quality_issues;"
    ),
    "CV detection incorporation": (
        "SELECT\n"
        "    (SELECT COUNT(*) FROM cv_detections) AS total_cv_detections,\n"
        "    (SELECT COUNT(DISTINCT detection_id) FROM cv_detection_track_links) AS incorporated_cv_detections,\n"
        "    ROUND(\n"
        "        100.0 * (SELECT COUNT(DISTINCT detection_id) FROM cv_detection_track_links)\n"
        "        / (SELECT COUNT(*) FROM cv_detections),\n"
        "        2\n"
        "    ) AS incorporation_percentage;"
    ),
    "CV track summaries": (
        "SELECT * FROM v_cv_track_summary ORDER BY duration_seconds DESC LIMIT 20;"
    ),
    "Fused track duration by class": (
        "WITH classified AS (\n"
        "    SELECT\n"
        "        fused_track_id,\n"
        "        CASE\n"
        "            WHEN has_transponder_measurement = 1 THEN 'Airplane'\n"
        "            WHEN dominant_object_class_name = 'OBJECT_CLASS_BIRD' THEN 'Excluded (BIRD)'\n"
        "            ELSE 'Drone'\n"
        "        END AS inferred_class,\n"
        "        duration_seconds\n"
        "    FROM v_fused_track_type_basis\n"
        ")\n"
        "SELECT inferred_class, COUNT(*) AS track_count,\n"
        "       ROUND(AVG(duration_seconds), 2) AS avg_duration_seconds\n"
        "FROM classified\n"
        "GROUP BY inferred_class\n"
        "ORDER BY inferred_class;"
    ),
    "Drone and Airplane comparison": (
        "WITH classified AS (\n"
        "    SELECT\n"
        "        fused_track_id,\n"
        "        CASE\n"
        "            WHEN has_transponder_measurement = 1 THEN 'Airplane'\n"
        "            WHEN dominant_object_class_name = 'OBJECT_CLASS_BIRD' THEN 'Excluded (BIRD)'\n"
        "            ELSE 'Drone'\n"
        "        END AS inferred_class,\n"
        "        duration_seconds\n"
        "    FROM v_fused_track_type_basis\n"
        ")\n"
        "SELECT inferred_class, COUNT(*) AS track_count,\n"
        "       ROUND(MIN(duration_seconds), 2) AS min_duration_seconds,\n"
        "       ROUND(MAX(duration_seconds), 2) AS max_duration_seconds\n"
        "FROM classified\n"
        "WHERE inferred_class IN ('Drone', 'Airplane')\n"
        "GROUP BY inferred_class\n"
        "ORDER BY inferred_class;"
    ),
    "Classification counts": (
        "SELECT object_class_name, COUNT(*) AS detection_count\n"
        "FROM cv_detections\n"
        "GROUP BY object_class_name\n"
        "ORDER BY detection_count DESC;"
    ),
    "Radar observations": (
        "SELECT\n"
        "    COUNT(*) AS radar_detection_count,\n"
        "    ROUND(AVG(azimuth_rad), 3) AS avg_azimuth_rad,\n"
        "    ROUND(AVG(elevation_rad), 3) AS avg_elevation_rad,\n"
        "    COUNT(DISTINCT track_id) AS distinct_radar_track_ids\n"
        "FROM radar_detections;"
    ),
    "Data-quality checks": (
        "SELECT\n"
        "    issue_type,\n"
        "    severity,\n"
        "    COUNT(*) AS issue_count\n"
        "FROM data_quality_issues\n"
        "GROUP BY issue_type, severity\n"
        "ORDER BY issue_count DESC;"
    ),
}

example_choice = st.selectbox(
    "Load a named example (optional)",
    options=["(none)"] + list(_EXAMPLE_QUERIES.keys()),
    key="sql_example_picker",
)

if "sql_editor_text" not in st.session_state:
    st.session_state["sql_editor_text"] = ""

if example_choice != "(none)" and st.session_state.get("sql_example_loaded") != example_choice:
    st.session_state["sql_editor_text"] = _EXAMPLE_QUERIES[example_choice]
    st.session_state["sql_example_loaded"] = example_choice

sql_text = st.text_area(
    "SQL statement",
    key="sql_editor_text",
    height=200,
    help="A single SELECT, WITH, EXPLAIN, or PRAGMA statement. Results are capped at "
    f"{DEFAULT_QUERY_ROW_LIMIT:,} rows.",
)

if st.button("Run Query", type="primary", key="run_editor_query"):
    validation = validate_read_only_sql(sql_text)
    if not validation.is_valid:
        st.error(validation.error)
    else:
        try:
            connection = connect_read_only(DEFAULT_DB_PATH)
        except DatabaseNotFoundError as exc:
            st.error(str(exc))
        else:
            try:
                # PRAGMA and EXPLAIN cannot be wrapped as a subquery -- only
                # SELECT/WITH statements are given an outer LIMIT; PRAGMA and
                # EXPLAIN results are already small and bounded by SQLite itself.
                statement = validation.cleaned_sql.rstrip(";")
                first_word = statement.split(None, 1)[0].upper()
                if first_word in ("SELECT", "WITH"):
                    statement_to_run = f"SELECT * FROM ({statement}) LIMIT {DEFAULT_QUERY_ROW_LIMIT}"
                else:
                    statement_to_run = statement
                cursor = connection.execute(statement_to_run)
                rows = cursor.fetchall()
                columns = [d[0] for d in cursor.description] if cursor.description else []
                result_df = pd.DataFrame(rows, columns=columns)
            except sqlite3.Error as exc:
                st.error(f"SQL error: {exc}")
            except Exception as exc:  # noqa: BLE001 - never show a raw traceback to the user
                logger.exception("SQL Queries page failed running ad-hoc SQL: %r", sql_text)
                st.error(f"This query failed to execute ({type(exc).__name__}: {exc}).")
            else:
                if result_df.empty:
                    st.caption("0 row(s) returned.")
                else:
                    st.caption(
                        f"{len(result_df)} row(s) returned"
                        + (f" (limited to {DEFAULT_QUERY_ROW_LIMIT:,})" if len(result_df) == DEFAULT_QUERY_ROW_LIMIT else "")
                        + "."
                    )
                render_table(result_df, key="editor_result")
            finally:
                connection.close()
