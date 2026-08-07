"""CUAS Sentry analytics console -- Streamlit entry point.

Read-only presentation layer over the completed ETL pipeline and
analytical SQL library. This file (and every page under pages/) never
executes anything other than the approved .sql files under queries/
plus a handful of read-only PRAGMA/introspection calls documented in
dashboard/database.py. See docs/DASHBOARD_GUIDE.md for the full
architecture and read-only guarantees.

Launch with:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit adds this script's own directory (dashboard/) to sys.path,
# not the repo root -- insert the repo root explicitly so `dashboard.*`
# imports resolve the same way here as they do under pytest (see
# pyproject.toml's pythonpath = ["src", "."]).
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st

from dashboard.components.sidebar import render_sidebar
from dashboard.constants import LAYOUT, PAGE_ICON
from dashboard.database import DatabaseNotFoundError, get_database_metadata

st.set_page_config(
    page_title="CUAS Sentry Analytics",
    page_icon=PAGE_ICON,
    layout=LAYOUT,
)

render_sidebar()

st.title("CUAS Sentry Analytics")
st.caption(
    "Read-only reporting layer over the MCAP to ETL to SQLite to SQL "
    "analytics pipeline."
)

metadata = get_database_metadata()
if not metadata.exists:
    st.error(
        "No database found at data/output/sentry.db.\n\n"
        "Build it first:\n\n"
        "```\npython scripts/build_database.py --rebuild\n```"
    )
    st.stop()

st.markdown(
    """
    ### Architecture

    ```
    data/input/sanitized.mcap
        -> Python ETL (src/cuas_etl/)
        -> data/output/sentry.db (SQLite)
        -> SQL queries and views (sql/, queries/)
        -> this dashboard (Streamlit, read-only)
    ```

    Every percentage, average, join, and comparison shown anywhere in
    this dashboard comes from a SQL file under `queries/` or a view
    under `sql/views.sql`. This application only discovers those
    files, executes them read-only, and displays the results. Nothing
    here recomputes or overrides an analytical result.

    ### Pages

    - **Overview** -- system-wide counts, the CV incorporation and
      Drone/Airplane checksum results, and data-quality summary.
    - **CV Detections** -- individual camera detections and how many
      were incorporated into a track.
    - **CV Tracks** -- persistent camera-tracked objects and their
      state history.
    - **Fused Tracks** -- persistent fused (tower) tracked objects,
      sensor contributions, and classification stability.
    - **Data Quality** -- relational-integrity checks and pipeline
      health.
    - **SQL Queries** -- run the approved analytical queries or
      write and run your own read-only SQL.
    - **Documentation** -- links to the project's design and analysis
      documents.

    Use the sidebar for live database status.
    """
)

try:
    from dashboard import sql_loader

    st.caption(f"{len(sql_loader.discover_queries())} analytical queries available.")
except DatabaseNotFoundError as exc:  # pragma: no cover - defensive, metadata check above already guards this
    st.error(str(exc))
