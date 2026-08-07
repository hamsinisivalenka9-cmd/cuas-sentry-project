"""Read-only database access and metadata for the dashboard.

Every connection opened here is read-only by construction (SQLite
mode=ro URI + PRAGMA query_only = ON) -- identical to
scripts/run_analytics.py's connect_read_only(), which this module
imports directly (see dashboard/sql_loader.py) rather than
re-implementing. No function in this module ever executes anything
other than SELECT/PRAGMA (query_only, integrity_check,
foreign_key_check) statements.

This module contains NO analytical business logic -- only structural
introspection (file size, table/view counts, schema version, source
checksum) and the two explicitly-approved read-only PRAGMA checks. Any
actual analytical result the dashboard displays comes from
dashboard/sql_loader.py running one of the approved .sql files.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from dashboard.constants import DEFAULT_DB_PATH, DEFAULT_MCAP_PATH


class DatabaseNotFoundError(RuntimeError):
    """Raised when data/output/sentry.db does not exist yet."""


def connect_read_only(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a genuinely read-only connection. Any write attempt through
    this connection fails at the SQLite layer (mode=ro + query_only),
    not merely by convention."""
    if not db_path.exists():
        raise DatabaseNotFoundError(
            f"No database found at {db_path}. Run: python scripts/build_database.py --rebuild"
        )
    uri = f"file:{db_path.resolve()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.execute("PRAGMA query_only = ON")
    return connection


@dataclass(frozen=True)
class DatabaseMetadata:
    """Pure structural facts about the database file -- no analytical
    content, only introspection."""

    db_path: Path
    exists: bool
    size_bytes: int | None
    sqlite_version: str
    schema_version: int | None
    table_count: int | None
    view_count: int | None


def get_database_metadata(db_path: Path = DEFAULT_DB_PATH) -> DatabaseMetadata:
    if not db_path.exists():
        return DatabaseMetadata(
            db_path=db_path,
            exists=False,
            size_bytes=None,
            sqlite_version=sqlite3.sqlite_version,
            schema_version=None,
            table_count=None,
            view_count=None,
        )

    size_bytes = db_path.stat().st_size
    connection = connect_read_only(db_path)
    try:
        schema_version_row = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()
        schema_version = schema_version_row[0] if schema_version_row else None

        table_count = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]
        view_count = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'view'"
        ).fetchone()[0]
    finally:
        connection.close()

    return DatabaseMetadata(
        db_path=db_path,
        exists=True,
        size_bytes=size_bytes,
        sqlite_version=sqlite3.sqlite_version,
        schema_version=schema_version,
        table_count=table_count,
        view_count=view_count,
    )


def compute_source_mcap_checksum(mcap_path: Path = DEFAULT_MCAP_PATH) -> str | None:
    """Live MD5 of the source MCAP file, computed by reading it
    read-only. Returns None if the file does not exist. This never
    opens the file for writing and never touches the database."""
    if not mcap_path.exists():
        return None
    digest = hashlib.md5()
    with open(mcap_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class IntegrityStatus:
    integrity_check_ok: bool
    integrity_check_detail: list[str]
    foreign_key_violations: list[tuple]


def run_integrity_checks(db_path: Path = DEFAULT_DB_PATH) -> IntegrityStatus:
    """Run SQLite's own built-in, read-only structural checks.
    PRAGMA integrity_check and PRAGMA foreign_key_check are both
    read-only diagnostics -- they inspect the database file, they do
    not modify it."""
    connection = connect_read_only(db_path)
    try:
        integrity_rows = [row[0] for row in connection.execute("PRAGMA integrity_check")]
        fk_violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        connection.close()

    return IntegrityStatus(
        integrity_check_ok=(integrity_rows == ["ok"]),
        integrity_check_detail=integrity_rows,
        foreign_key_violations=fk_violations,
    )
