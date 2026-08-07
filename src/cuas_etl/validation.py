"""Validation phase: check a populated SQLite database for structural
and referential correctness, and cross-check it against independently
re-derivable facts about the source file.

This module is read-only -- it never modifies the database. Every check
produces a ValidationCheck with an explicit level (fatal / warning /
info), so a caller (scripts/run_validation.py, scripts/build_database.py)
can distinguish "the build is broken" from "a known, documented
limitation" from "just FYI" without guessing.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from cuas_etl import database
from cuas_etl.transform import TransformedTables

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MCAP_PATH = REPO_ROOT / "data" / "input" / "sanitized.mcap"

# Recorded once, Stage 1, and re-verified unchanged at the end of every
# stage since -- see docs/STAGE_01_SUMMARY.txt.
EXPECTED_MCAP_MD5 = "e32b641c93b84861d855b01a79ea09d0"

# Exact, CONFIRMED structural counts (Stage 2/3, docs/TABLE_GRAIN.md).
# cv_detection_track_links and data_quality_issues are deliberately
# excluded here -- their counts are outcomes of the orphan/dedup logic,
# not fixed facts about the file, and are checked separately via
# independent re-derivation (check_bridge_table_rederivation), never
# hardcoded as "the" expected analytical answer.
EXPECTED_STRUCTURAL_ROW_COUNTS: dict[str, int] = {
    "source_messages": 57_266,
    "cv_detections": 1_911,
    "cv_tracks": 17,
    "cv_track_states": 9_496,
    "cv_track_class_distribution": 37_984,
    "radar_detections": 2_929,
    "fused_tracks": 103,
    "fused_track_states": 11_630,
    "fused_track_measurements": 11_992,
}


@dataclass
class ValidationCheck:
    """One validation result."""

    name: str
    level: str  # "fatal" | "warning" | "info"
    passed: bool
    expected: object
    actual: object
    message: str


@dataclass
class ValidationReport:
    checks: list[ValidationCheck] = field(default_factory=list)

    def add(self, check: ValidationCheck) -> None:
        self.checks.append(check)

    @property
    def fatal_failures(self) -> list[ValidationCheck]:
        return [c for c in self.checks if c.level == "fatal" and not c.passed]

    @property
    def warnings(self) -> list[ValidationCheck]:
        return [c for c in self.checks if c.level == "warning" and not c.passed]

    @property
    def passed_overall(self) -> bool:
        """True iff there are zero fatal failures. Warnings and info
        checks never block a successful build -- they are documented
        limitations, not defects."""
        return len(self.fatal_failures) == 0


# ---------------------------------------------------------------------------
# Individual check functions -- each is independently callable/testable.
# ---------------------------------------------------------------------------


def check_integrity(connection: sqlite3.Connection) -> ValidationCheck:
    issues = database.run_integrity_check(connection)
    passed = issues == ["ok"]
    return ValidationCheck(
        "integrity_check", "fatal", passed, expected=["ok"], actual=issues,
        message="PRAGMA integrity_check" + (" passed." if passed else f" FAILED: {issues}"),
    )


def check_foreign_keys(connection: sqlite3.Connection) -> ValidationCheck:
    violations = database.run_foreign_key_check(connection)
    passed = len(violations) == 0
    return ValidationCheck(
        "foreign_key_check", "fatal", passed, expected=[], actual=violations,
        message="PRAGMA foreign_key_check" + (" passed." if passed else f" FAILED: {violations}"),
    )


def check_tables_and_views_exist(connection: sqlite3.Connection) -> list[ValidationCheck]:
    checks = []
    tables = set(database.list_tables(connection))
    views = set(database.list_views(connection))
    for table_name in database.REVIEWED_TABLES:
        checks.append(ValidationCheck(
            f"table_exists:{table_name}", "fatal", table_name in tables,
            expected=True, actual=table_name in tables,
            message=f"table {table_name!r} " + ("exists." if table_name in tables else "is MISSING."),
        ))
    for view_name in database.REVIEWED_VIEWS:
        checks.append(ValidationCheck(
            f"view_exists:{view_name}", "fatal", view_name in views,
            expected=True, actual=view_name in views,
            message=f"view {view_name!r} " + ("exists." if view_name in views else "is MISSING."),
        ))
    return checks


def check_structural_row_counts(connection: sqlite3.Connection) -> list[ValidationCheck]:
    checks = []
    for table_name, expected_count in EXPECTED_STRUCTURAL_ROW_COUNTS.items():
        actual_count = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        passed = actual_count == expected_count
        checks.append(ValidationCheck(
            f"row_count:{table_name}", "fatal", passed,
            expected=expected_count, actual=actual_count,
            message=(
                f"{table_name}: expected {expected_count:,} rows (confirmed structural "
                f"fact, Stage 2/3), found {actual_count:,}."
            ),
        ))
    return checks


def check_pk_unique_duplicates(connection: sqlite3.Connection) -> list[ValidationCheck]:
    """Independently re-verify every PK/UNIQUE constraint by querying for
    duplicates directly -- redundant with SQLite's own enforcement at
    insert time, but a genuinely independent check, as requested."""
    duplicate_queries = {
        "cv_detections.detection_uid": (
            "SELECT detection_uid, COUNT(*) c FROM cv_detections "
            "GROUP BY detection_uid HAVING c > 1"
        ),
        "cv_track_states.(source_message_id,track_id)": (
            "SELECT source_message_id, track_id, COUNT(*) c FROM cv_track_states "
            "GROUP BY source_message_id, track_id HAVING c > 1"
        ),
        "cv_track_class_distribution.(cv_track_state_id,source_order)": (
            "SELECT cv_track_state_id, source_order, COUNT(*) c "
            "FROM cv_track_class_distribution "
            "GROUP BY cv_track_state_id, source_order HAVING c > 1"
        ),
        "fused_track_states.(fused_track_id,log_time_ns)": (
            "SELECT fused_track_id, log_time_ns, COUNT(*) c FROM fused_track_states "
            "GROUP BY fused_track_id, log_time_ns HAVING c > 1"
        ),
        "cv_detection_track_links.(detection_id,track_id)": (
            "SELECT detection_id, track_id, COUNT(*) c FROM cv_detection_track_links "
            "GROUP BY detection_id, track_id HAVING c > 1"
        ),
    }
    checks = []
    for constraint_name, query in duplicate_queries.items():
        duplicates = connection.execute(query).fetchall()
        passed = len(duplicates) == 0
        checks.append(ValidationCheck(
            f"unique_duplicates:{constraint_name}", "fatal", passed,
            expected=0, actual=len(duplicates),
            message=(
                f"{constraint_name}: {len(duplicates)} duplicate key group(s) found "
                f"(expected 0)."
            ),
        ))
    return checks


def check_required_not_null_columns(connection: sqlite3.Connection) -> list[ValidationCheck]:
    required_columns = {
        "source_messages": ["channel_id", "topic", "schema_id", "sequence", "log_time_ns", "publish_time_ns"],
        "cv_detections": ["detection_uid", "source_message_id"],
        "cv_track_states": ["source_message_id", "track_id", "log_time_ns"],
        "cv_track_class_distribution": [
            "cv_track_state_id", "class_raw", "probability_score", "source_order"
        ],
        "cv_detection_track_links": ["detection_id", "track_id"],
        "radar_detections": ["source_message_id"],
        "fused_tracks": ["fused_track_id"],
        "fused_track_states": ["source_message_id", "fused_track_id", "log_time_ns"],
        "fused_track_measurements": ["fused_track_state_id"],
        "data_quality_issues": ["issue_type", "severity", "description", "detected_at_utc"],
    }
    checks = []
    for table_name, columns in required_columns.items():
        for column in columns:
            null_count = connection.execute(
                f"SELECT COUNT(*) FROM {table_name} WHERE {column} IS NULL"
            ).fetchone()[0]
            passed = null_count == 0
            checks.append(ValidationCheck(
                f"not_null:{table_name}.{column}", "fatal", passed,
                expected=0, actual=null_count,
                message=f"{table_name}.{column}: {null_count} unexpected NULL value(s).",
            ))
    return checks


def check_json_validity(connection: sqlite3.Connection) -> list[ValidationCheck]:
    json_columns = [
        ("radar_detections", "cluster_json"),
        ("fused_track_measurements", "detection_ids_json"),
    ]
    checks = []
    for table_name, column in json_columns:
        rows = connection.execute(
            f"SELECT rowid, {column} FROM {table_name} WHERE {column} IS NOT NULL"
        ).fetchall()
        invalid = []
        for rowid, raw_json in rows:
            try:
                parsed = json.loads(raw_json)
            except (json.JSONDecodeError, TypeError):
                invalid.append(rowid)
                continue
            if not isinstance(parsed, list):
                invalid.append(rowid)
        passed = len(invalid) == 0
        checks.append(ValidationCheck(
            f"json_validity:{table_name}.{column}", "fatal", passed,
            expected=0, actual=len(invalid),
            message=(
                f"{table_name}.{column}: {len(invalid)} row(s) with invalid or non-array "
                f"JSON out of {len(rows)} checked."
            ),
        ))
    return checks


def check_enum_raw_name_consistency(connection: sqlite3.Connection) -> list[ValidationCheck]:
    """For every *_raw/*_name enum pair, confirm raw and name are always
    both NULL or both non-NULL together (they are always computed from
    the same row's raw value in transform.py, so this should hold with
    zero exceptions). A NULL name alongside a non-NULL raw would mean an
    unrecognized enum integer -- informational, not fatal, since it is a
    legitimate outcome of "preserve unknown numeric values with a NULL
    name," but still worth surfacing if it ever happens."""
    enum_pairs = [
        ("cv_detections", "object_class_raw", "object_class_name"),
        ("cv_detections", "semantic_confidence_raw", "semantic_confidence_name"),
        ("cv_detections", "focus_quality_raw", "focus_quality_name"),
        ("cv_detections", "disposition_raw", "disposition_name"),
        ("cv_detections", "motion_state_raw", "motion_state_name"),
        ("cv_track_states", "status_raw", "status_name"),
        ("cv_track_states", "status_code_raw", "status_code_name"),
        ("cv_track_states", "object_class_raw", "object_class_name"),
        ("cv_track_states", "disposition_raw", "disposition_name"),
        ("cv_track_states", "motion_state_raw", "motion_state_name"),
        ("cv_track_class_distribution", "class_raw", "class_name"),
        ("radar_detections", "object_type_class_raw", "object_type_class_name"),
        ("radar_detections", "object_class_raw", "object_class_name"),
        ("radar_detections", "filter_type_raw", "filter_type_name"),
        ("fused_track_states", "object_class_raw", "object_class_name"),
        ("fused_track_states", "disposition_raw", "disposition_name"),
        ("fused_track_states", "track_status_raw", "track_status_name"),
        ("fused_track_measurements", "sensor_id_raw", "sensor_id_name"),
    ]
    checks = []
    for table_name, raw_col, name_col in enum_pairs:
        unrecognized = connection.execute(
            f"SELECT COUNT(*) FROM {table_name} WHERE {raw_col} IS NOT NULL AND {name_col} IS NULL"
        ).fetchone()[0]
        inverted = connection.execute(
            f"SELECT COUNT(*) FROM {table_name} WHERE {raw_col} IS NULL AND {name_col} IS NOT NULL"
        ).fetchone()[0]
        checks.append(ValidationCheck(
            f"enum_unrecognized:{table_name}.{raw_col}", "warning", unrecognized == 0,
            expected=0, actual=unrecognized,
            message=(
                f"{table_name}.{raw_col}: {unrecognized} row(s) with a raw enum value not "
                "recognized by the protobuf descriptor (name is NULL for these -- expected "
                "behavior for an unknown value, not fatal, but worth reviewing)."
            ),
        ))
        checks.append(ValidationCheck(
            f"enum_inverted_null:{table_name}.{raw_col}", "fatal", inverted == 0,
            expected=0, actual=inverted,
            message=(
                f"{table_name}.{name_col}: {inverted} row(s) have a name but no raw value -- "
                "should never happen, since name is always derived from raw in the same row."
            ),
        ))
    return checks


def check_parent_child_reconciliation(connection: sqlite3.Connection) -> list[ValidationCheck]:
    """Independent LEFT JOIN-based re-verification that every foreign key
    actually resolves -- redundant with PRAGMA foreign_key_check, but an
    independently-written check, as requested."""
    relationships = [
        ("cv_detections.source_message_id", "cv_detections", "source_message_id", "source_messages", "source_message_id"),
        ("cv_track_states.source_message_id", "cv_track_states", "source_message_id", "source_messages", "source_message_id"),
        ("cv_track_states.track_id", "cv_track_states", "track_id", "cv_tracks", "track_id"),
        ("cv_track_class_distribution.cv_track_state_id", "cv_track_class_distribution", "cv_track_state_id", "cv_track_states", "cv_track_state_id"),
        ("cv_detection_track_links.detection_id", "cv_detection_track_links", "detection_id", "cv_detections", "detection_id"),
        ("cv_detection_track_links.track_id", "cv_detection_track_links", "track_id", "cv_tracks", "track_id"),
        ("radar_detections.source_message_id", "radar_detections", "source_message_id", "source_messages", "source_message_id"),
        ("fused_track_states.source_message_id", "fused_track_states", "source_message_id", "source_messages", "source_message_id"),
        ("fused_track_states.fused_track_id", "fused_track_states", "fused_track_id", "fused_tracks", "fused_track_id"),
        ("fused_track_measurements.fused_track_state_id", "fused_track_measurements", "fused_track_state_id", "fused_track_states", "fused_track_state_id"),
    ]
    checks = []
    for name, child_table, child_col, parent_table, parent_col in relationships:
        orphan_count = connection.execute(
            f"SELECT COUNT(*) FROM {child_table} c "
            f"LEFT JOIN {parent_table} p ON c.{child_col} = p.{parent_col} "
            f"WHERE p.{parent_col} IS NULL"
        ).fetchone()[0]
        passed = orphan_count == 0
        checks.append(ValidationCheck(
            f"parent_child:{name}", "fatal", passed,
            expected=0, actual=orphan_count,
            message=f"{name}: {orphan_count} row(s) reference a non-existent {parent_table} row.",
        ))
    return checks


def check_orphan_reference_reconciliation(connection: sqlite3.Connection) -> ValidationCheck:
    """Compare the recorded orphaned_detection_reference issue count
    against an independent re-count: the number of DISTINCT
    (last_associated_detection_id, track_id) pairs in cv_track_states
    whose detection_id is not present in cv_detections."""
    expected = connection.execute(
        "SELECT COUNT(*) FROM ("
        "  SELECT DISTINCT last_associated_detection_id, track_id FROM cv_track_states "
        "  WHERE last_associated_detection_id IS NOT NULL "
        "  AND last_associated_detection_id NOT IN (SELECT detection_id FROM cv_detections)"
        ")"
    ).fetchone()[0]
    actual = connection.execute(
        "SELECT COUNT(*) FROM data_quality_issues WHERE issue_type = 'orphaned_detection_reference'"
    ).fetchone()[0]
    passed = expected == actual
    return ValidationCheck(
        "orphan_reference_reconciliation", "fatal", passed,
        expected=expected, actual=actual,
        message=(
            f"Independently recomputed {expected} orphaned detection reference(s) from raw "
            f"cv_track_states data; data_quality_issues records {actual}."
        ),
    )


def check_bridge_table_rederivation(
    connection: sqlite3.Connection, tables: TransformedTables | None
) -> ValidationCheck:
    """Compare cv_detection_track_links' loaded row count against an
    independently re-derived count -- NOT a hardcoded target. If
    `tables` is provided (a fresh transform.transform_all() result), its
    cv_detection_track_links length is used as the independent
    re-derivation; otherwise this check is skipped (info-level) rather
    than silently assumed to pass."""
    if tables is None:
        return ValidationCheck(
            "bridge_table_rederivation", "info", True, expected="n/a", actual="skipped",
            message="Skipped: no fresh TransformedTables provided for re-derivation.",
        )
    expected = len(tables.cv_detection_track_links)
    actual = connection.execute("SELECT COUNT(*) FROM cv_detection_track_links").fetchone()[0]
    passed = expected == actual
    return ValidationCheck(
        "bridge_table_rederivation", "fatal", passed,
        expected=expected, actual=actual,
        message=(
            f"Re-running extraction and transformation independently derived "
            f"{expected} cv_detection_track_links rows; the database has {actual}."
        ),
    )


def check_deterministic_id_contiguity(connection: sqlite3.Connection) -> list[ValidationCheck]:
    """Sanity check that every deterministically-assigned surrogate key
    column is a contiguous 1..N sequence with no gaps or duplicates --
    the expected shape for the traversal-order assignment scheme
    documented in transform.py. (This does not by itself prove two
    separate rebuilds agree -- that is proven by the determinism test in
    tests/test_transform.py, which runs the pipeline twice and diffs the
    results directly.)"""
    surrogate_columns = [
        ("source_messages", "source_message_id"),
        ("cv_track_states", "cv_track_state_id"),
        ("cv_track_class_distribution", "cv_track_class_distribution_id"),
        ("radar_detections", "radar_detection_id"),
        ("fused_track_states", "fused_track_state_id"),
        ("fused_track_measurements", "fused_track_measurement_id"),
        ("data_quality_issues", "issue_id"),
    ]
    checks = []
    for table_name, column in surrogate_columns:
        row = connection.execute(
            f"SELECT COUNT(*), MIN({column}), MAX({column}) FROM {table_name}"
        ).fetchone()
        count, min_id, max_id = row
        if count == 0:
            passed = True
            detail = "table is empty"
        else:
            passed = (min_id == 1) and (max_id == count)
            detail = f"count={count}, min={min_id}, max={max_id}"
        checks.append(ValidationCheck(
            f"id_contiguity:{table_name}.{column}", "warning", passed,
            expected="contiguous 1..N", actual=detail,
            message=f"{table_name}.{column}: {detail} ({'contiguous' if passed else 'GAP OR OFFSET DETECTED'}).",
        ))
    return checks


def check_timestamp_magnitude(connection: sqlite3.Connection) -> list[ValidationCheck]:
    """Sanity-check that TrackState's plain int64 timestamp fields
    (create_timestamp_ns, last_measurement_timestamp_ns,
    measurement_timestamp_ns) are the same rough order of magnitude as
    the CONFIRMED-nanosecond log_time_ns range -- flags, rather than
    assumes, if they turn out to be a different unit (docs/DATA_CLEANING.md).
    """
    log_time_min, log_time_max = connection.execute(
        "SELECT MIN(log_time_ns), MAX(log_time_ns) FROM source_messages"
    ).fetchone()

    checks = []
    magnitude_fields = [
        ("fused_track_states", "create_timestamp_ns"),
        ("fused_track_states", "last_measurement_timestamp_ns"),
        ("fused_track_measurements", "measurement_timestamp_ns"),
    ]
    for table_name, column in magnitude_fields:
        row = connection.execute(
            f"SELECT MIN({column}), MAX({column}) FROM {table_name} WHERE {column} IS NOT NULL AND {column} != 0"
        ).fetchone()
        field_min, field_max = row
        if field_min is None:
            checks.append(ValidationCheck(
                f"timestamp_magnitude:{table_name}.{column}", "info", True,
                expected="comparable to log_time_ns", actual="no non-zero values",
                message=f"{table_name}.{column}: no non-zero values to check.",
            ))
            continue
        # "Comparable magnitude" = within the same order of magnitude as
        # the known log_time_ns range (loosely: at least 10% of it, and
        # not more than 100x it) -- a deliberately loose bound, since
        # this is a sanity flag, not a precise unit-conversion assertion.
        plausible = (log_time_min * 0.1) <= field_min <= (log_time_max * 10)
        checks.append(ValidationCheck(
            f"timestamp_magnitude:{table_name}.{column}", "warning", plausible,
            expected=f"~[{log_time_min}, {log_time_max}]", actual=f"[{field_min}, {field_max}]",
            message=(
                f"{table_name}.{column} range [{field_min}, {field_max}] "
                f"{'is' if plausible else 'is NOT'} plausibly the same nanosecond-epoch unit "
                f"as source_messages.log_time_ns range [{log_time_min}, {log_time_max}]."
            ),
        ))
    return checks


def check_source_checksum(mcap_path: Path | str = DEFAULT_MCAP_PATH, expected_md5: str = EXPECTED_MCAP_MD5) -> ValidationCheck:
    """Confirm the source MCAP file's MD5 checksum is unchanged from the
    Stage 1 baseline -- direct, repeatable proof rule 1 ("never modify
    the source file") was honored throughout the ETL run."""
    mcap_path = Path(mcap_path)
    digest = hashlib.md5()
    with open(mcap_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    actual_md5 = digest.hexdigest()
    passed = actual_md5 == expected_md5
    return ValidationCheck(
        "source_checksum", "fatal", passed, expected=expected_md5, actual=actual_md5,
        message=(
            f"data/input/sanitized.mcap MD5: {actual_md5} "
            f"({'matches' if passed else 'DOES NOT MATCH'} baseline {expected_md5})."
        ),
    )


def check_source_fidelity_rederivation(
    connection: sqlite3.Connection, tables: TransformedTables | None
) -> list[ValidationCheck]:
    """Compare all newly preserved values with a fresh raw-source transform."""
    if tables is None:
        return [ValidationCheck(
            "source_fidelity_rederivation", "info", True, "n/a", "skipped",
            "Skipped: no fresh TransformedTables provided for source comparison.",
        )]

    expected_scalars = [
        (
            row["detection_id"], row["focus_quality_raw"], row["focus_quality_name"],
            row["focus_score"], row["sharpness"],
        )
        for row in tables.cv_detections
    ]
    actual_scalars = connection.execute(
        "SELECT detection_id, focus_quality_raw, focus_quality_name, focus_score, sharpness "
        "FROM cv_detections ORDER BY detection_id"
    ).fetchall()
    expected_scalars.sort(key=lambda row: row[0])

    expected_distribution = [
        (
            row["cv_track_class_distribution_id"], row["cv_track_state_id"],
            row["class_raw"], row["class_name"], row["probability_score"],
            row["source_order"],
        )
        for row in tables.cv_track_class_distribution
    ]
    actual_distribution = connection.execute(
        "SELECT cv_track_class_distribution_id, cv_track_state_id, class_raw, class_name, "
        "probability_score, source_order FROM cv_track_class_distribution "
        "ORDER BY cv_track_class_distribution_id"
    ).fetchall()

    order_violations = connection.execute(
        "SELECT COUNT(*) FROM ("
        " SELECT cv_track_state_id FROM cv_track_class_distribution"
        " GROUP BY cv_track_state_id"
        " HAVING COUNT(*) != 4 OR MIN(source_order) != 0 OR MAX(source_order) != 3"
        ")"
    ).fetchone()[0]

    return [
        ValidationCheck(
            "source_fidelity:cv_detection_quality", "fatal",
            expected_scalars == actual_scalars, len(expected_scalars), len(actual_scalars),
            "Fresh raw-source transform matches every stored CV detection quality value.",
        ),
        ValidationCheck(
            "source_fidelity:cv_track_class_distribution", "fatal",
            expected_distribution == actual_distribution,
            len(expected_distribution), len(actual_distribution),
            "Fresh raw-source transform matches every ordered class-distribution entry.",
        ),
        ValidationCheck(
            "source_fidelity:class_distribution_source_order", "fatal",
            order_violations == 0, 0, order_violations,
            f"{order_violations} CV track state(s) lack the complete ordered source positions 0..3.",
        ),
    ]


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------


def run_full_validation(
    connection: sqlite3.Connection,
    mcap_path: Path | str | None = DEFAULT_MCAP_PATH,
    rederive_for_comparison: bool = True,
) -> ValidationReport:
    """Run every validation check and return a single ValidationReport.

    If `mcap_path` is given and `rederive_for_comparison` is True, this
    also re-runs extraction and transformation fresh (a few seconds) to
    independently re-derive the bridge-table row count for comparison,
    and checks the source file's checksum. Set `rederive_for_comparison`
    to False (or `mcap_path` to None) to skip both and run only the
    pure-SQL checks -- useful for unit tests against a small synthetic
    database that has no real source file behind it.
    """
    report = ValidationReport()

    report.add(check_integrity(connection))
    report.add(check_foreign_keys(connection))
    for check in check_tables_and_views_exist(connection):
        report.add(check)
    for check in check_structural_row_counts(connection):
        report.add(check)
    for check in check_pk_unique_duplicates(connection):
        report.add(check)
    for check in check_required_not_null_columns(connection):
        report.add(check)
    for check in check_json_validity(connection):
        report.add(check)
    for check in check_enum_raw_name_consistency(connection):
        report.add(check)
    for check in check_parent_child_reconciliation(connection):
        report.add(check)
    report.add(check_orphan_reference_reconciliation(connection))
    for check in check_deterministic_id_contiguity(connection):
        report.add(check)
    for check in check_timestamp_magnitude(connection):
        report.add(check)

    fresh_tables = None
    if mcap_path is not None and rederive_for_comparison:
        # Imported locally to avoid a hard import-time dependency on the
        # extract/transform modules for callers that only want the pure
        # SQL checks against a synthetic database.
        from cuas_etl.extract import extract_mcap
        from cuas_etl.transform import transform_all

        report.add(check_source_checksum(mcap_path))
        fresh_extracted = extract_mcap(mcap_path)
        fresh_tables = transform_all(fresh_extracted)

    report.add(check_bridge_table_rederivation(connection, fresh_tables))
    for check in check_source_fidelity_rederivation(connection, fresh_tables):
        report.add(check)

    return report
