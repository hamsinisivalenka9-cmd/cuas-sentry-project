#!/usr/bin/env python3
"""Run every validation check against an existing data/output/sentry.db,
without building or modifying it.

Usage:
    python scripts/run_validation.py
    python scripts/run_validation.py --db-path some/other.db
    python scripts/run_validation.py --skip-rederivation   # pure-SQL checks only, faster

Exits 0 if every fatal check passes, 1 otherwise. Never writes to the
database or to the source MCAP file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cuas_etl import database, validation  # noqa: E402

DEFAULT_DB_PATH = REPO_ROOT / "data" / "output" / "sentry.db"
DEFAULT_MCAP_PATH = REPO_ROOT / "data" / "input" / "sanitized.mcap"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--mcap-path", type=Path, default=DEFAULT_MCAP_PATH)
    parser.add_argument(
        "--skip-rederivation", action="store_true",
        help="Skip re-extracting/re-transforming the source file for the bridge-table "
        "re-derivation and checksum checks -- runs only the pure-SQL checks, faster.",
    )
    args = parser.parse_args()

    if not args.db_path.exists():
        print(f"No database found at {args.db_path}. Run scripts/build_database.py first.", file=sys.stderr)
        return 1

    connection = database.get_connection(args.db_path)
    report = validation.run_full_validation(
        connection,
        mcap_path=None if args.skip_rederivation else args.mcap_path,
        rederive_for_comparison=not args.skip_rederivation,
    )
    connection.close()

    print(f"Database: {args.db_path}")
    print(f"Checks run: {len(report.checks)}")
    print(f"Fatal failures: {len(report.fatal_failures)}")
    print(f"Warnings: {len(report.warnings)}")
    print()
    for check in report.checks:
        marker = "PASS" if check.passed else check.level.upper()
        print(f"[{marker:7s}] {check.name}: {check.message}")

    print()
    if report.passed_overall:
        print("Overall: PASSED")
        return 0
    print("Overall: FAILED", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
