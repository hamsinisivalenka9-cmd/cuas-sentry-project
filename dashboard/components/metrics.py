"""KPI card rendering.

Thin wrapper over st.metric for consistent styling -- displays a
value already computed by SQL, never computes one itself.
"""

from __future__ import annotations

import streamlit as st


def kpi_row(cards: list[tuple[str, str, str | None]]) -> None:
    """Render a row of KPI cards. Each card is (label, value, help_text)."""
    columns = st.columns(len(cards))
    for column, (label, value, help_text) in zip(columns, cards):
        with column:
            st.metric(label, value, help=help_text)
