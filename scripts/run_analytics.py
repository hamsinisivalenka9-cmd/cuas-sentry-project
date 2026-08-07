#!/usr/bin/env python3
"""Run reusable analytical SQL queries (queries/**/*.sql) against
data/output/sentry.db.

Read-only by construction: the database is opened via SQLite's
mode=ro URI and PRAGMA query_only is set, so no query executed through
this script can modify sentry.db, even by accident -- a query that
attempts a write fails at the SQLite layer, not merely by convention.

Discovers every .sql file under queries/ (recursively). A file's
category is its immediate parent directory name (executive/operational/
technical); files directly under queries/ itself (for example the
existing queries/fused_track_duration_by_type.sql) are grouped under
the category "general".

Usage:
    python scripts/run_analytics.py --list
    python scripts/run_analytics.py --category executive
    python scripts/run_analytics.py --query cv_incorporation_summary
    python scripts/run_analytics.py --all
    python scripts/run_analytics.py --query cv_track_history --param track_id=81754
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
QUERIES_DIR = REPO_ROOT / "queries"
DEFAULT_DB_PATH = REPO_ROOT / "data" / "output" / "sentry.db"

# Matches SQLite named parameters (":name") without matching plain
# colons elsewhere in a comment. This is a simple heuristic, not a full
# SQL parser -- a comment that happens to mention ":something" that
# isn't an actual bind parameter would be treated as one. All query
# files in this project only ever mention the parameter(s) they
# actually use in their header comments, so this holds in practice; a
# future query author should keep that convention.
PARAM_PATTERN = re.compile(r":([A-Za-z_][A-Za-z0-9_]*)")


class QueryFile:
    """One discovered .sql file under queries/, with its metadata
    parsed from its header comment block."""

    def __init__(self, path: Path):
        self.path = path
        self.name = path.stem
        self.category = path.parent.name if path.parent.resolve() != QUERIES_DIR.resolve() else "general"
        self.sql = path.read_text()

    def _labeled_field(self, label: str) -> str | None:
        """Pull a "-- Label: text" header field, concatenating any
        wrapped continuation lines (plain "-- more text" lines with no
        new "-- OtherLabel:" prefix) until a blank "--" line or the
        next labeled field."""
        lines = self.sql.splitlines()
        prefix = f"-- {label}:"
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped.startswith(prefix):
                continue
            parts = [stripped.split(prefix, 1)[1].strip()]
            for cont in lines[i + 1 :]:
                cont_stripped = cont.strip()
                if cont_stripped in ("--", "") or re.match(r"^-- [A-Za-z][A-Za-z ]*:", cont_stripped):
                    break
                if cont_stripped.startswith("--"):
                    parts.append(cont_stripped[2:].strip())
                else:
                    break
            return " ".join(parts)
        return None

    @property
    def question(self) -> str:
        return self._labeled_field("Question") or "(no 'Question:' line found in header comment)"

    @property
    def audience(self) -> str:
        return self._labeled_field("Audience") or "(unspecified)"

    @property
    def required_params(self) -> set[str]:
        return set(PARAM_PATTERN.findall(self.sql))


def discover_queries() -> list[QueryFile]:
    """Every .sql file under queries/, sorted by (category, name) for
    stable --list output."""
    return sorted(
        (QueryFile(p) for p in QUERIES_DIR.rglob("*.sql")),
        key=lambda q: (q.category, q.name),
    )


def connect_read_only(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise SystemExit(f"No database found at {db_path}. Run scripts/build_database.py first.")
    uri = f"file:{db_path.resolve()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.execute("PRAGMA query_only = ON")
    return connection


def parse_params(raw_params: list[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for item in raw_params:
        if "=" not in item:
            raise SystemExit(f"Invalid --param {item!r}, expected name=value")
        key, value = item.split("=", 1)
        params[key] = value
    return params


def _format_table(columns: list[str], rows: list[tuple]) -> str:
    widths = [
        max(len(str(col)), *(len(str(row[i])) for row in rows)) if rows else len(str(col))
        for i, col in enumerate(columns)
    ]
    lines = [
        "  ".join(col.ljust(w) for col, w in zip(columns, widths)),
        "  ".join("-" * w for w in widths),
    ]
    for row in rows:
        lines.append("  ".join(str(value).ljust(w) for value, w in zip(row, widths)))
    return "\n".join(lines)


def run_query(connection: sqlite3.Connection, query: QueryFile, params: dict[str, str]) -> int:
    """Execute one query and print its results. Returns a process exit
    code (0 on success, 1 on any SQL error or missing parameter)."""
    missing = query.required_params - set(params)
    if missing:
        print(
            f"ERROR: {query.category}/{query.name} requires parameter(s) "
            f"{sorted(missing)} -- pass with --param name=value",
            file=sys.stderr,
        )
        return 1

    bind_params = {name: params[name] for name in query.required_params}
    print(f"\n=== {query.category}/{query.name} ===")
    print(query.question)
    try:
        cursor = connection.execute(query.sql, bind_params)
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description] if cursor.description else []
    except sqlite3.Error as exc:
        print(f"ERROR running {query.path}: {exc}", file=sys.stderr)
        return 1

    if not columns:
        print("(query returned no result columns)")
        return 0
    print(_format_table(columns, rows))
    print(f"({len(rows)} row{'s' if len(rows) != 1 else ''})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--list", action="store_true", help="List all discovered queries and exit")
    parser.add_argument("--query", help="Run a single query by filename stem")
    parser.add_argument(
        "--category", help="Run every query in one category (executive/operational/technical/general)"
    )
    parser.add_argument("--all", action="store_true", help="Run every discovered query")
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        help="Bind a named query parameter, e.g. --param track_id=81754 (repeatable)",
    )
    args = parser.parse_args()

    queries = discover_queries()
    if not queries:
        print(f"No .sql files found under {QUERIES_DIR}", file=sys.stderr)
        return 1

    if args.list:
        current_category: str | None = None
        for q in queries:
            if q.category != current_category:
                current_category = q.category
                print(f"\n[{current_category}]")
            print(f"  {q.name:45s} ({q.audience}) -- {q.question}")
        return 0

    if args.query:
        selected = [q for q in queries if q.name == args.query]
        if not selected:
            print(f"No query named {args.query!r} found. Use --list to see available queries.", file=sys.stderr)
            return 1
    elif args.category:
        selected = [q for q in queries if q.category == args.category]
        if not selected:
            print(f"No queries found in category {args.category!r}.", file=sys.stderr)
            return 1
    elif args.all:
        selected = queries
    else:
        parser.print_help()
        return 1

    params = parse_params(args.param)
    connection = connect_read_only(args.db_path)
    exit_code = 0
    try:
        for q in selected:
            exit_code = run_query(connection, q, params) or exit_code
    finally:
        connection.close()
    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        # Expected when output is piped to something like `head` that
        # closes its input early -- not a real error.
        sys.exit(0)
