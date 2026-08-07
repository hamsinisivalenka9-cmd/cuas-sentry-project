"""Discovers and executes the approved analytical SQL files under
queries/ -- the dashboard's only path to analytical data.

This module deliberately does NOT reimplement query discovery or
parameter-name extraction: it imports scripts/run_analytics.py
directly (via importlib, since scripts/ is a collection of standalone
entry points with no __init__.py -- the same technique
tests/test_analytics_runner.py already uses) and reuses its
QueryFile/discover_queries/connect_read_only exactly. This keeps the
SQL files as the single source of analytical truth: nothing here
duplicates a SELECT statement, a JOIN, an aggregation, or a
percentage/average calculation. The only thing added on top of
run_analytics.py is a pandas.DataFrame return type (for Streamlit
display) and stricter reject-unknown-input error handling suited to a
UI instead of a CLI.

Two small, non-analytical, hardcoded lookup queries are defined here
(_TRACK_ID_LIST_SQL / _FUSED_TRACK_ID_LIST_SQL) solely to populate the
Operations page's track-selector dropdowns with real values -- they
contain no joins, no aggregation, and no business logic (they list one
identity table's own primary key), so they are UI plumbing, not a
duplicate analytical query. This was flagged explicitly in the Stage 8
implementation plan.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pandas as pd

from dashboard.constants import DEFAULT_DB_PATH, QUERIES_DIR, RUN_ANALYTICS_PATH
from dashboard.database import connect_read_only


class QueryNotFoundError(KeyError):
    """Raised when a requested query name does not match any
    discovered .sql file."""


class UnexpectedParameterError(ValueError):
    """Raised when a caller supplies a parameter a query does not
    declare (via its own ':name' placeholders) -- this dashboard never
    silently ignores or forwards unexpected input into a query."""


class MissingParameterError(ValueError):
    """Raised when a query requires a parameter the caller did not
    supply."""


def _load_run_analytics_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_analytics", RUN_ANALYTICS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Imported once at module load -- scripts/run_analytics.py is a stable,
# already-tested module (tests/test_analytics_runner.py), not
# per-request work.
_run_analytics = _load_run_analytics_module()

QueryFile = _run_analytics.QueryFile  # re-exported for type hints elsewhere


def discover_queries() -> list[QueryFile]:
    """Every approved .sql file under queries/, including the
    preserved legacy queries/fused_track_duration_by_type.sql (which
    run_analytics.py already classifies under the "general" category).
    """
    return _run_analytics.discover_queries()


def get_query(name: str) -> QueryFile:
    for query in discover_queries():
        if query.name == name:
            return query
    raise QueryNotFoundError(f"No approved query named {name!r}. See discover_queries() for valid names.")


def list_categories() -> list[str]:
    seen: list[str] = []
    for query in discover_queries():
        if query.category not in seen:
            seen.append(query.category)
    return seen


def run_query(
    name: str,
    params: dict[str, object] | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> pd.DataFrame:
    """Execute one approved query by name and return its result as a
    DataFrame. Rejects an unknown query name, a missing required
    parameter, or an unexpected parameter the query does not declare.
    Never concatenates any input into the SQL text -- every parameter
    is passed through sqlite3's native parameter binding."""
    query = get_query(name)
    params = dict(params or {})

    missing = query.required_params - set(params)
    if missing:
        raise MissingParameterError(
            f"{query.category}/{query.name} requires parameter(s) {sorted(missing)}"
        )

    unexpected = set(params) - query.required_params
    if unexpected:
        raise UnexpectedParameterError(
            f"{query.category}/{query.name} does not accept parameter(s) {sorted(unexpected)} "
            f"-- it only declares {sorted(query.required_params) or '(none)'}"
        )

    connection = connect_read_only(db_path)
    try:
        cursor = connection.execute(query.sql, params)
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description] if cursor.description else []
    finally:
        connection.close()

    return pd.DataFrame(rows, columns=columns)


# ---------------------------------------------------------------------
# Non-analytical selector-population lookups (see module docstring).
# ---------------------------------------------------------------------

_TRACK_ID_LIST_SQL = "SELECT track_id FROM cv_tracks ORDER BY track_id"
_FUSED_TRACK_ID_LIST_SQL = "SELECT fused_track_id FROM fused_tracks ORDER BY fused_track_id"


def list_cv_track_ids(db_path: Path = DEFAULT_DB_PATH) -> list[int]:
    connection = connect_read_only(db_path)
    try:
        return [row[0] for row in connection.execute(_TRACK_ID_LIST_SQL)]
    finally:
        connection.close()


def list_fused_track_ids(db_path: Path = DEFAULT_DB_PATH) -> list[str]:
    connection = connect_read_only(db_path)
    try:
        return [row[0] for row in connection.execute(_FUSED_TRACK_ID_LIST_SQL)]
    finally:
        connection.close()
