"""Tests for src/cuas_etl/validation.py.

UNIT TESTS (below the first marker) build tiny, fully synthetic
databases (via database.initialize_database against a temp file, then
hand-inserted rows) with no dependency on the real MCAP file.

INTEGRATION TESTS (function names prefixed test_real_mcap_) build a real
database from the actual source file and validate it -- the only place
in this file that touches real data.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cuas_etl import database, validation


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    connection = database.initialize_database(tmp_path / "test.db")
    yield connection
    connection.close()


# ===========================================================================
# UNIT TESTS -- synthetic databases only (mcap_path=None everywhere, so
# no re-derivation or checksum check runs)
# ===========================================================================


def test_integrity_check_passes_on_empty_database(conn):
    check = validation.check_integrity(conn)
    assert check.passed and check.level == "fatal"


def test_foreign_key_check_passes_on_empty_database(conn):
    check = validation.check_foreign_keys(conn)
    assert check.passed


def test_tables_and_views_exist_on_freshly_initialized_database(conn):
    checks = validation.check_tables_and_views_exist(conn)
    assert all(c.passed for c in checks)
    assert len(checks) == len(database.REVIEWED_TABLES) + len(database.REVIEWED_VIEWS)


def test_structural_row_count_check_fails_fatally_on_empty_database(conn):
    # An empty database has 0 rows everywhere, which does not match the
    # expected structural counts -- these checks should fail (fatal),
    # not silently pass just because the query ran without error.
    checks = validation.check_structural_row_counts(conn)
    assert any(not c.passed for c in checks)
    assert all(c.level == "fatal" for c in checks)


def test_pk_unique_duplicate_check_passes_when_no_duplicates(conn):
    checks = validation.check_pk_unique_duplicates(conn)
    assert all(c.passed for c in checks)  # nothing inserted, nothing duplicated


def test_required_not_null_check_passes_on_empty_database(conn):
    # Vacuously true: zero rows means zero NULL violations.
    checks = validation.check_required_not_null_columns(conn)
    assert all(c.passed for c in checks)


def test_json_validity_check_detects_invalid_json(conn):
    conn.execute(
        "INSERT INTO source_messages VALUES (1,1,'radar_detections',1,0,100,100)"
    )
    conn.execute(
        "INSERT INTO radar_detections "
        "(radar_detection_id, source_message_id, cluster_json) VALUES (1, 1, 'not valid json')"
    )
    conn.commit()
    checks = validation.check_json_validity(conn)
    cluster_check = next(c for c in checks if "cluster_json" in c.name)
    assert cluster_check.passed is False
    assert cluster_check.actual == 1


def test_json_validity_check_accepts_valid_empty_array(conn):
    conn.execute("INSERT INTO source_messages VALUES (1,1,'radar_detections',1,0,100,100)")
    conn.execute(
        "INSERT INTO radar_detections (radar_detection_id, source_message_id, cluster_json) "
        "VALUES (1, 1, '[]')"
    )
    conn.commit()
    checks = validation.check_json_validity(conn)
    cluster_check = next(c for c in checks if "cluster_json" in c.name)
    assert cluster_check.passed is True


def test_enum_consistency_flags_name_without_raw_as_fatal(conn):
    conn.execute("INSERT INTO source_messages VALUES (1,1,'cv_detections',1,0,100,100)")
    conn.execute(
        "INSERT INTO cv_detections (detection_id, detection_uid, source_message_id, "
        "object_class_raw, object_class_name) VALUES (1, 'u1', 1, NULL, 'SOMETHING')"
    )
    conn.commit()
    checks = validation.check_enum_raw_name_consistency(conn)
    inverted_check = next(c for c in checks if c.name == "enum_inverted_null:cv_detections.object_class_raw")
    assert inverted_check.passed is False
    assert inverted_check.level == "fatal"


def test_enum_consistency_unrecognized_raw_is_only_a_warning(conn):
    conn.execute("INSERT INTO source_messages VALUES (1,1,'cv_detections',1,0,100,100)")
    conn.execute(
        "INSERT INTO cv_detections (detection_id, detection_uid, source_message_id, "
        "object_class_raw, object_class_name) VALUES (1, 'u1', 1, 999999, NULL)"
    )
    conn.commit()
    checks = validation.check_enum_raw_name_consistency(conn)
    unrecognized_check = next(c for c in checks if c.name == "enum_unrecognized:cv_detections.object_class_raw")
    assert unrecognized_check.passed is False
    assert unrecognized_check.level == "warning"  # not fatal


def test_parent_child_reconciliation_detects_dangling_reference(conn):
    # Insert directly with foreign_keys effectively bypassed at the SQL
    # level to construct an inconsistent state deliberately, proving the
    # independent LEFT JOIN check catches it even without relying on
    # PRAGMA foreign_key_check.
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("INSERT INTO cv_tracks (track_id) VALUES (1)")
    conn.execute(
        "INSERT INTO cv_track_states (cv_track_state_id, source_message_id, track_id, log_time_ns) "
        "VALUES (1, 9999, 1, 100)"
    )
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")
    checks = validation.check_parent_child_reconciliation(conn)
    check = next(c for c in checks if "cv_track_states.source_message_id" in c.name)
    assert check.passed is False
    assert check.actual == 1


def test_orphan_reference_reconciliation_matches_when_consistent(conn):
    conn.execute("INSERT INTO source_messages VALUES (1,1,'cv_detections',1,0,100,100)")
    conn.execute("INSERT INTO cv_tracks (track_id) VALUES (1)")
    conn.execute(
        "INSERT INTO cv_track_states (cv_track_state_id, source_message_id, track_id, log_time_ns, "
        "last_associated_detection_id) VALUES (1, 1, 1, 100, 999)"
    )
    conn.execute(
        "INSERT INTO data_quality_issues (issue_id, issue_type, severity, description, detected_at_utc) "
        "VALUES (1, 'orphaned_detection_reference', 'warning', 'x', '2026-01-01T00:00:00Z')"
    )
    conn.commit()
    check = validation.check_orphan_reference_reconciliation(conn)
    assert check.expected == 1
    assert check.actual == 1
    assert check.passed is True


def test_bridge_table_rederivation_skipped_gracefully_without_fresh_tables(conn):
    check = validation.check_bridge_table_rederivation(conn, tables=None)
    assert check.level == "info"
    assert check.passed is True


def test_source_fidelity_rederivation_skips_without_fresh_tables(conn):
    checks = validation.check_source_fidelity_rederivation(conn, tables=None)
    assert len(checks) == 1
    assert checks[0].level == "info"
    assert checks[0].passed is True


def test_id_contiguity_check_detects_a_gap(conn):
    conn.execute("INSERT INTO source_messages VALUES (1,1,'cv_detections',1,0,100,100)")
    conn.execute("INSERT INTO source_messages VALUES (3,1,'cv_detections',1,0,100,100)")  # gap at 2
    conn.commit()
    checks = validation.check_deterministic_id_contiguity(conn)
    check = next(c for c in checks if "source_messages" in c.name)
    assert check.passed is False
    assert check.level == "warning"


def test_validation_report_passed_overall_ignores_warnings():
    report = validation.ValidationReport()
    report.add(validation.ValidationCheck("a", "warning", False, 1, 2, "a warning"))
    report.add(validation.ValidationCheck("b", "fatal", True, 1, 1, "an ok fatal check"))
    assert report.passed_overall is True  # only fatal failures block success


def test_validation_report_passed_overall_false_on_fatal_failure():
    report = validation.ValidationReport()
    report.add(validation.ValidationCheck("a", "fatal", False, 1, 2, "a fatal failure"))
    assert report.passed_overall is False


# ===========================================================================
# INTEGRATION TESTS -- a real, fully-loaded database from the real file
# ===========================================================================


def test_real_mcap_full_validation_passes_on_freshly_built_database(tmp_path):
    from cuas_etl import extract, load, transform

    db_path = tmp_path / "real.db"
    connection = database.initialize_database(db_path)
    extracted = extract.extract_mcap()
    tables = transform.transform_all(extracted)
    load.load_phase1(connection, tables)
    load.load_phase2(connection, tables)

    report = validation.run_full_validation(connection)
    assert report.passed_overall is True, [
        f"{c.level}:{c.name}: {c.message}" for c in report.checks if not c.passed
    ]
    assert len(report.fatal_failures) == 0
    connection.close()
