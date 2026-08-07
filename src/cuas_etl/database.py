"""SQLite database layer for the CUAS Sentry project (Stage 6).

This module creates and validates the database structure described in
``docs/DATABASE_DESIGN.md`` (reviewed in ``docs/SCHEMA_REVIEW.md``): the
11 reviewed analytical tables, their indexes, and their analytical
views. It reads and runs the SQL files in ``sql/`` -- it does not embed
any table definitions of its own, so the SQL files remain the single
source of truth for the schema.

This module does NOT load any data and does NOT implement ETL. Its job
ends once the empty, structurally-correct database exists.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SQL_DIR = REPO_ROOT / "sql"
DEFAULT_DB_PATH = REPO_ROOT / "data" / "output" / "sentry.db"

# Bump this, and add a short description, whenever sql/schema.sql changes
# in a way future readers should be able to see recorded in the database
# itself (see the schema_version table created in sql/schema.sql).
SCHEMA_VERSION = 2
SCHEMA_VERSION_DESCRIPTION = (
    "Stage 6 source-fidelity correction: 11-table analytical schema; "
    "CV detection quality fields and complete CV track class distributions. "
    "(docs/SCHEMA_REVIEW.md); indexes and the reviewed views included "
    "(v_fused_track_type_basis added in Stage 6B without changing the "
    "table structure -- see docs/CHECKSUM_RESOLUTION.md)."
)

# The 11 tables docs/TABLE_GRAIN.md and docs/DATABASE_DESIGN.md describe
# and approved. `schema_version` is deliberately excluded: it is
# implementation-layer metadata added in Stage 6, not one of the 10
# reviewed analytical tables.
REVIEWED_TABLES: tuple[str, ...] = (
    "source_messages",
    "cv_detections",
    "cv_tracks",
    "cv_track_states",
    "cv_track_class_distribution",
    "cv_detection_track_links",
    "radar_detections",
    "fused_tracks",
    "fused_track_states",
    "fused_track_measurements",
    "data_quality_issues",
)

# v_cv_track_summary and v_fused_track_summary are the two views
# docs/DATABASE_DESIGN.md Section 5.11 originally recommended.
# v_fused_track_type_basis was added in Stage 6B
# (docs/CHECKSUM_RESOLUTION.md) to resolve the Drone/Airplane checksum
# using a sensor-provenance signal already loaded by the existing ETL
# -- no schema or ETL change was required, only this view.
REVIEWED_VIEWS: tuple[str, ...] = (
    "v_cv_track_summary",
    "v_fused_track_summary",
    "v_fused_track_type_basis",
)


def get_connection(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with foreign-key enforcement turned on.

    Foreign-key enforcement (CLAUDE.md rule 8) is a per-connection SQLite
    setting, not a property stored in the database file -- it must be
    enabled every time a new connection is opened, not just once when the
    file is first created. Any code elsewhere in this project that opens
    its own connection instead of using this function must remember to
    set this PRAGMA itself.
    """
    connection = sqlite3.connect(str(db_path))
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _read_sql_file(file_name: str) -> str:
    """Read one of the SQL files in sql/ as plain text."""
    sql_path = SQL_DIR / file_name
    return sql_path.read_text()


def initialize_database(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Create every reviewed table, index, and view if they do not
    already exist, and record the current schema version.

    Idempotent: every statement in sql/schema.sql, sql/indexes.sql, and
    sql/views.sql uses IF NOT EXISTS, so calling this function again
    against an already-initialized database makes no changes and raises
    no error. Each of the three SQL files wraps its own statements in an
    explicit BEGIN TRANSACTION / COMMIT (requirement: wrap database
    creation in a transaction), so table creation, index creation, and
    view creation each either fully succeed or are fully rolled back.

    Does not insert any analytical data -- only structure.

    Returns an open connection to the initialized database, with
    foreign-key enforcement already turned on.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = get_connection(db_path)
    try:
        connection.executescript(_read_sql_file("schema.sql"))
        connection.executescript(_read_sql_file("indexes.sql"))
        connection.executescript(_read_sql_file("views.sql"))
        _record_schema_version(connection)
    except Exception:
        connection.close()
        raise
    return connection


def _record_schema_version(connection: sqlite3.Connection) -> None:
    """Insert a schema_version row for SCHEMA_VERSION if one is not
    already present. Idempotent: safe to call on every initialization.
    """
    already_recorded = connection.execute(
        "SELECT COUNT(*) FROM schema_version WHERE version = ?",
        (SCHEMA_VERSION,),
    ).fetchone()[0]
    if already_recorded == 0:
        connection.execute(
            "INSERT INTO schema_version (version, applied_at_utc, description) "
            "VALUES (?, datetime('now'), ?)",
            (SCHEMA_VERSION, SCHEMA_VERSION_DESCRIPTION),
        )
        connection.commit()


def get_current_schema_version(connection: sqlite3.Connection) -> int | None:
    """Return the highest schema version recorded in this database, or
    None if the schema_version table is empty (or does not exist yet)."""
    try:
        row = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()
    except sqlite3.OperationalError:
        return None
    return row[0] if row is not None else None


def list_tables(connection: sqlite3.Connection) -> list[str]:
    """Return every user-defined table name in the database, sorted."""
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [row[0] for row in rows]


def list_views(connection: sqlite3.Connection) -> list[str]:
    """Return every view name in the database, sorted."""
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'view' ORDER BY name"
    ).fetchall()
    return [row[0] for row in rows]


def list_indexes(connection: sqlite3.Connection, table_name: str) -> list[str]:
    """Return every index name defined on one table, sorted. Includes the
    automatic indexes SQLite creates for PRIMARY KEY and UNIQUE
    constraints, not only the ones explicitly created in
    sql/indexes.sql."""
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = ? "
        "ORDER BY name",
        (table_name,),
    ).fetchall()
    return [row[0] for row in rows]


def run_integrity_check(connection: sqlite3.Connection) -> list[str]:
    """Run SQLite's built-in structural integrity check.

    Returns a list of problem descriptions. A healthy database returns
    exactly one element, the string "ok".
    """
    rows = connection.execute("PRAGMA integrity_check").fetchall()
    return [row[0] for row in rows]


class ForeignKeyViolation(NamedTuple):
    """One row from PRAGMA foreign_key_check: a specific row in a
    specific table whose foreign key does not point at a valid row."""

    table: str
    rowid: int | None
    referenced_table: str
    foreign_key_index: int


def run_foreign_key_check(connection: sqlite3.Connection) -> list[ForeignKeyViolation]:
    """Run SQLite's foreign-key consistency check across all data
    currently in the database.

    Returns a list of violations; an empty list means every foreign key
    currently stored is valid. This check works regardless of whether
    PRAGMA foreign_keys was ON while the data was written, so it is a
    meaningful check even for data loaded through a misconfigured
    connection.
    """
    rows = connection.execute("PRAGMA foreign_key_check").fetchall()
    return [ForeignKeyViolation(*row) for row in rows]


def validate_database(connection: sqlite3.Connection) -> dict:
    """Run every structural/referential check this project cares about
    and return a single summary dictionary.

    This is a read-only diagnostic function -- it never modifies the
    database. See sql/validation.sql for the equivalent checks as plain
    SQL, runnable directly with the sqlite3 CLI.
    """
    tables = list_tables(connection)
    views = list_views(connection)
    missing_tables = [t for t in REVIEWED_TABLES if t not in tables]
    missing_views = [v for v in REVIEWED_VIEWS if v not in views]
    integrity_issues = run_integrity_check(connection)
    fk_violations = run_foreign_key_check(connection)
    foreign_keys_pragma_value = connection.execute("PRAGMA foreign_keys").fetchone()[0]

    return {
        "tables_found": tables,
        "views_found": views,
        "missing_reviewed_tables": missing_tables,
        "missing_reviewed_views": missing_views,
        "integrity_check_ok": integrity_issues == ["ok"],
        "integrity_check_issues": integrity_issues,
        "foreign_key_check_ok": len(fk_violations) == 0,
        "foreign_key_violations": fk_violations,
        "foreign_keys_enforced": bool(foreign_keys_pragma_value),
        "schema_version": get_current_schema_version(connection),
    }
