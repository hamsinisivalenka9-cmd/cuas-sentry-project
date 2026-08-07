"""The "query source" expander -- shown beneath every visualization so
a user can trace any chart, table, or KPI back to the exact .sql file
and query text that produced it.

This is the dashboard's core traceability guarantee: nothing is ever
shown without a path back to queries/<category>/<name>.sql.
"""

from __future__ import annotations

import streamlit as st

from dashboard.query_catalog import CatalogEntry


def query_source_expander(entry: CatalogEntry, expanded: bool = False) -> None:
    relative_path = entry.query.path.relative_to(entry.query.path.parent.parent.parent)
    with st.expander(f"Source query: {relative_path}", expanded=expanded):
        st.caption(entry.question)
        st.markdown(
            f"**Audience:** {entry.audience}  \n"
            f"**Category:** {entry.query.category}  \n"
            f"**Required parameters:** {', '.join(sorted(entry.query.required_params)) or 'none'}  \n"
            f"**Documentation:** see `docs/ANALYTICAL_INSIGHTS.md`"
        )
        st.code(entry.query.sql, language="sql")
