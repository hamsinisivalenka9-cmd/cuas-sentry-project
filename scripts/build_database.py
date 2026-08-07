#!/usr/bin/env python3
"""Build data/output/sentry.db from data/input/sanitized.mcap.

Coordinates schema creation, extraction, transformation, loading, and
validation, in that order. Never modifies the source MCAP file.

Usage:
    python scripts/build_database.py              # build if empty, else validate-and-exit
    python scripts/build_database.py --rebuild     # delete and rebuild from scratch

Idempotency is achieved primarily through deterministic surrogate keys,
this --rebuild workflow, and safe (IF NOT EXISTS) schema initialization
-- not through INSERT OR IGNORE. A non-rebuild run against an
already-populated database validates that the existing data is complete
and exits cleanly (0) if so, or fails with a clear message telling the
user to use --rebuild if not.

Exits with a nonzero status on any fatal failure. Never leaves a
partially-loaded database presented as successful.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cuas_etl import database, extract, load, transform, validation  # noqa: E402

DEFAULT_DB_PATH = REPO_ROOT / "data" / "output" / "sentry.db"
DEFAULT_MCAP_PATH = REPO_ROOT / "data" / "input" / "sanitized.mcap"


def _print_header(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def _print_validation_report(report: validation.ValidationReport) -> None:
    print(f"Checks run: {len(report.checks)}")
    print(f"Fatal failures: {len(report.fatal_failures)}")
    print(f"Warnings: {len(report.warnings)}")
    for check in report.checks:
        if not check.passed:
            print(f"  [{check.level.upper()}] {check.name}: {check.message}")
    if report.passed_overall:
        print("Result: PASSED (zero fatal failures)")
    else:
        print("Result: FAILED")


def _run_full_build(db_path: Path, mcap_path: Path) -> int:
    _print_header("Phase 1/2: Extract + Transform")
    t0 = time.time()
    extracted = extract.extract_mcap(mcap_path)
    extract.verify_expected_message_count(extracted)
    print(f"Extracted {extracted.total_message_count:,} messages: {extracted.topic_counts()}")

    tables = transform.transform_all(extracted)
    print(f"Transformed rows per table:")
    for name in (
        "source_messages", "cv_detections", "cv_tracks", "cv_track_states",
        "cv_track_class_distribution",
        "cv_detection_track_links", "radar_detections", "fused_tracks",
        "fused_track_states", "fused_track_measurements", "data_quality_issues",
    ):
        print(f"  {name:30s} {len(getattr(tables, name)):>7,}")
    print(f"Extract + transform took {time.time() - t0:.2f}s")

    _print_header("Phase 3: Load (two-phase, PRAGMA foreign_keys = ON)")
    connection = database.initialize_database(db_path)
    try:
        t0 = time.time()
        phase1_counts = load.load_phase1(connection, tables)
        print(f"Phase 1 committed: {phase1_counts}")
        phase2_counts = load.load_phase2(connection, tables)
        print(f"Phase 2 committed: {phase2_counts}")
        print(f"Load took {time.time() - t0:.2f}s")
    except load.LoadError as exc:
        print(f"\nFATAL LOAD ERROR:\n{exc}", file=sys.stderr)
        connection.close()
        return 1

    _print_header("Phase 4: Validation")
    report = validation.run_full_validation(connection, mcap_path=mcap_path)
    _print_validation_report(report)

    _print_final_summary(connection, db_path, tables, report)
    connection.close()
    return 0 if report.passed_overall else 1


def _validate_existing(db_path: Path, mcap_path: Path) -> int:
    _print_header(f"Database already populated at {db_path} -- validating instead of reloading")
    print("(pass --rebuild to force a clean rebuild)")
    connection = database.get_connection(db_path)
    report = validation.run_full_validation(connection, mcap_path=mcap_path)
    _print_validation_report(report)
    if report.passed_overall:
        print("\nExisting database is complete and valid. Exiting 0.")
        connection.close()
        return 0
    print(
        "\nExisting database FAILED validation. It may be partially loaded or "
        "stale. Re-run with --rebuild to load a fresh copy.",
        file=sys.stderr,
    )
    connection.close()
    return 1


def _print_final_summary(connection, db_path: Path, tables, report: validation.ValidationReport) -> None:
    _print_header("FINAL SUMMARY")
    print(f"Database path: {db_path}")
    print(f"Database size: {db_path.stat().st_size:,} bytes")
    print()
    print("Tables and row counts:")
    for table_name in database.REVIEWED_TABLES:
        count = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  {table_name:30s} {count:>7,}")
    print()
    print(f"Deduplicated detection<->track pairs: {len(tables.cv_detection_track_links):,}")
    print(f"Data-quality issues recorded: {len(tables.data_quality_issues):,}")
    integrity = next(c for c in report.checks if c.name == "integrity_check")
    fk_check = next(c for c in report.checks if c.name == "foreign_key_check")
    checksum = next((c for c in report.checks if c.name == "source_checksum"), None)
    print(f"integrity_check: {'ok' if integrity.passed else 'FAILED'}")
    print(f"foreign_key_check: {'ok (no violations)' if fk_check.passed else 'FAILED'}")
    if checksum is not None:
        print(f"source checksum: {'unchanged' if checksum.passed else 'CHANGED -- INVESTIGATE'}")
    print(f"Overall validation: {'PASSED' if report.passed_overall else 'FAILED'}")
    print()
    print(
        "NOTE: the ~81% CV-incorporation checksum remains unresolved "
        "(docs/CHECKSUM_RESOLUTION.md Part B/C) -- this build does not claim "
        "it passes. The Drone/Airplane duration checksum was resolved in "
        "Stage 6B via queries/fused_track_duration_by_type.sql -- run it "
        "directly for results; see docs/CHECKSUM_RESOLUTION.md for the "
        "honest mean-vs-target gap on the Drone group."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rebuild", action="store_true",
        help="Delete any existing database file first, then build fresh.",
    )
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--mcap-path", type=Path, default=DEFAULT_MCAP_PATH)
    args = parser.parse_args()

    db_path: Path = args.db_path
    mcap_path: Path = args.mcap_path

    if args.rebuild and db_path.exists():
        print(f"--rebuild: removing existing {db_path}")
        db_path.unlink()

    db_path.parent.mkdir(parents=True, exist_ok=True)

    # initialize_database is idempotent (IF NOT EXISTS everywhere), so
    # it is always safe to call here regardless of whether the file is
    # new or already populated.
    probe_connection = database.initialize_database(db_path)
    already_populated = load.database_already_populated(probe_connection)
    probe_connection.close()

    if already_populated and not args.rebuild:
        return _validate_existing(db_path, mcap_path)

    return _run_full_build(db_path, mcap_path)


if __name__ == "__main__":
    sys.exit(main())
