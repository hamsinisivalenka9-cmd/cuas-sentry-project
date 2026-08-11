"""Shared sidebar, rendered identically on every page.

Not in the originally proposed Stage 8 file list -- added because
Streamlit's multipage model runs each pages/*.py file as an
independent script, so the sidebar content (database status, compact
project overview, navigation) needs to live somewhere every page can
import without re-triggering dashboard/app.py's own
st.set_page_config() call. This is the smallest addition that makes
the sidebar consistent across all pages.

Shows only structural/introspection facts (path, size, table/view
counts, schema version, checksum) -- no analytical content, and no
control here ever writes to the database.
"""

from __future__ import annotations

import streamlit as st

from dashboard import database, formatting, sql_loader
from dashboard.constants import DEFAULT_DB_PATH


def render_sidebar() -> None:
    st.sidebar.title("CUAS Sentry")
    st.sidebar.caption("Read-only analytics console")

    metadata = database.get_database_metadata(DEFAULT_DB_PATH)

    if not metadata.exists:
        st.sidebar.error(
            "Database not found.\n\nRun:\n\n"
            "`python scripts/build_database.py --rebuild`"
        )
        return

    st.sidebar.success("Database connected")

    with st.sidebar.expander("Project overview", expanded=True):
        st.markdown(
            f"**Path:** `{metadata.db_path.relative_to(metadata.db_path.parent.parent.parent)}`  \n"
            f"**Size:** {formatting.format_bytes(metadata.size_bytes)}  \n"
            f"**Schema version:** {metadata.schema_version}  \n"
            f"**Tables:** {metadata.table_count} (11 analytical + `schema_version`)  \n"
            f"**Views:** {metadata.view_count}  \n"
            f"**Analytical queries:** {len(sql_loader.discover_queries())}  \n"
            f"**SQLite:** {metadata.sqlite_version}"
        )
        checksum = database.compute_source_mcap_checksum()
        if checksum:
            st.markdown(f"**Source MCAP MD5:** `{checksum[:12]}...`")
        else:
            st.caption("Source MCAP not found at data/input/sanitized.mcap (checksum unavailable).")

        st.caption(
            "Architecture: sanitized.mcap -> Python ETL -> SQLite -> "
            "reusable SQL queries/views -> this dashboard (read-only)."
        )

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Pages: Overview, CV Detections, CV Tracks, Fused Tracks, "
        "Data Quality, SQL Queries, Documentation.\n\n"
        "Use the page navigator above to switch pages."
    )

    st.sidebar.markdown("---")
    if st.sidebar.button("Refresh cached results"):
        st.cache_data.clear()
        st.sidebar.success("Cache cleared.")
    if st.sidebar.button("Reload SQL catalog"):
        st.cache_resource.clear()
        st.sidebar.success("Catalog reloaded.")
