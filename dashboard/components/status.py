"""Pass/fail/warning status indicators.

Interprets an already-computed boolean/count from SQL (e.g. "0 rows
returned" or "PRAGMA integrity_check said ok") -- it never decides
what counts as healthy on its own; that threshold (usually "zero rows
means healthy") is documented in each source query's own header
comment.
"""

from __future__ import annotations

import streamlit as st


def status_banner(is_healthy: bool, healthy_message: str, unhealthy_message: str) -> None:
    if is_healthy:
        st.success(f"PASS: {healthy_message}")
    else:
        st.warning(f"ATTENTION: {unhealthy_message}")


def zero_rows_is_healthy(row_count: int, healthy_message: str, unhealthy_message: str) -> None:
    """The recurring pattern across this project's technical queries:
    a query is documented as 'healthy result is zero rows' -- this
    renders that convention consistently."""
    status_banner(row_count == 0, healthy_message, f"{unhealthy_message} ({row_count} row(s) found)")
