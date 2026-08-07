"""DataFrame table rendering with an optional CSV download button.

Displays exactly the DataFrame a query returned -- no reordering,
filtering, or recomputation happens here.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st


def render_table(
    df: pd.DataFrame,
    key: str,
    allow_download: bool = True,
    truncate_columns: dict[str, int] | None = None,
) -> None:
    """Render df as a sortable Streamlit table. truncate_columns maps a
    column name to a max display width (for very long text columns
    like a concatenated classification sequence) -- the underlying
    DataFrame, and the CSV download, are never truncated, only the
    on-screen display."""
    display_df = df.copy()
    if truncate_columns:
        for column, max_len in truncate_columns.items():
            if column in display_df.columns:
                display_df[column] = display_df[column].astype(str).apply(
                    lambda text, m=max_len: text if len(text) <= m else text[:m] + "…"
                )

    st.dataframe(display_df, width="stretch", hide_index=True)

    if allow_download and not df.empty:
        st.download_button(
            "Download full result as CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"{key}.csv",
            mime="text/csv",
            key=f"download_{key}",
        )
