"""Generic Plotly chart builders.

Every function here takes an already-computed pandas.DataFrame (the
direct output of dashboard.sql_loader.run_query -- never re-aggregated
or re-filtered in Python beyond what's needed to hand data to Plotly)
and returns a plotly.graph_objects.Figure. No function in this module
knows about any specific query -- callers in dashboard/pages/*.py
supply the column names. This keeps every analytical number exactly as
SQL computed it; this module only decides how to draw it.

Design constraints (per the Stage 8 visualization requirements):
no 3D charts, no decorative animation, minimal color palette, every
chart gets a title/axis labels/caption from its caller, pie charts are
not used anywhere in this dashboard (bar/comparison charts communicate
the same proportions more clearly for this data).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from dashboard.constants import COLOR_NEUTRAL, COLOR_PRIMARY, COLOR_SECONDARY

_PALETTE = [COLOR_PRIMARY, COLOR_SECONDARY, COLOR_NEUTRAL, "#2ca02c", "#9467bd", "#8c564b"]


def bar_chart(
    df: pd.DataFrame,
    category_col: str,
    value_col: str,
    title: str,
    x_label: str,
    y_label: str,
    horizontal: bool = False,
) -> go.Figure:
    if horizontal:
        fig = go.Figure(go.Bar(y=df[category_col], x=df[value_col], orientation="h", marker_color=COLOR_PRIMARY))
        fig.update_layout(xaxis_title=y_label, yaxis_title=x_label)
    else:
        fig = go.Figure(go.Bar(x=df[category_col], y=df[value_col], marker_color=COLOR_PRIMARY))
        fig.update_layout(xaxis_title=x_label, yaxis_title=y_label)
    fig.update_layout(title=title, margin=dict(t=50, b=40, l=40, r=20))
    return fig


def comparison_bar_chart(
    df: pd.DataFrame,
    category_col: str,
    value_col: str,
    title: str,
    x_label: str,
    y_label: str,
    min_col: str | None = None,
    max_col: str | None = None,
) -> go.Figure:
    """A grouped comparison bar chart, optionally with min/max error
    bars when the source query returns them (several of this
    project's comparison queries do)."""
    error_y = None
    if min_col and max_col and min_col in df.columns and max_col in df.columns:
        error_y = dict(
            type="data",
            symmetric=False,
            array=df[max_col] - df[value_col],
            arrayminus=df[value_col] - df[min_col],
        )
    fig = go.Figure(
        go.Bar(
            x=df[category_col],
            y=df[value_col],
            marker_color=_PALETTE[: len(df)],
            error_y=error_y,
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        margin=dict(t=50, b=40, l=40, r=20),
    )
    return fig


def funnel_chart(labels: list[str], values: list[float], title: str) -> go.Figure:
    fig = go.Figure(go.Funnel(y=labels, x=values, marker=dict(color=COLOR_PRIMARY)))
    fig.update_layout(title=title, margin=dict(t=50, b=40, l=40, r=20))
    return fig


def scatter_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    x_label: str,
    y_label: str,
    hover_col: str | None = None,
    size_col: str | None = None,
) -> go.Figure:
    fig = go.Figure(
        go.Scatter(
            x=df[x_col],
            y=df[y_col],
            mode="markers",
            marker=dict(
                color=COLOR_PRIMARY,
                size=(12 + 0.3 * df[size_col]) if size_col and size_col in df.columns else 10,
            ),
            text=df[hover_col] if hover_col and hover_col in df.columns else None,
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        margin=dict(t=50, b=40, l=40, r=20),
    )
    return fig


def line_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    x_label: str,
    y_label: str,
) -> go.Figure:
    fig = go.Figure(go.Scatter(x=df[x_col], y=df[y_col], mode="lines+markers", line=dict(color=COLOR_PRIMARY)))
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        margin=dict(t=50, b=40, l=40, r=20),
    )
    return fig
