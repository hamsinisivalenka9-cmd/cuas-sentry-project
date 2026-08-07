"""Tests for the Stage 6 SQLite schema (src/cuas_etl/database.py and the
sql/*.sql files it runs).

These tests only exercise structure: table/view existence, primary keys,
foreign keys, UNIQUE constraints, indexes, and SQLite's own integrity
checks. No analytical data is inserted beyond the minimal rows needed to
prove a constraint works -- this project's ETL does not exist yet (Stage
6 is schema-only), so there is nothing to load and nothing to test at the
data-transformation level here.

Every test uses a fresh, temporary SQLite file (via the ``db_path``
fixture) so tests cannot interfere with each other or with any real
database a developer might have at data/output/sentry.db.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cuas_etl import database


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """A path to a SQLite file that does not exist yet, inside pytest's
    per-test temporary directory."""
    return tmp_path / "test_sentry.db"


@pytest.fixture
def conn(db_path: Path) -> sqlite3.Connection:
    """An initialized, empty database (schema + indexes + views, no
    data), with foreign-key enforcement turned on."""
    connection = database.initialize_database(db_path)
    yield connection
    connection.close()


def _insert_valid_source_message(connection: sqlite3.Connection, source_message_id: int = 1) -> None:
    """Insert one minimal, valid source_messages row -- the common
    starting point most other tables' rows must FK against."""
    connection.execute(
        "INSERT INTO source_messages "
        "(source_message_id, channel_id, topic, schema_id, sequence, log_time_ns, publish_time_ns) "
        "VALUES (?, 1, 'cv_detections', 1, 0, 1000, 1000)",
        (source_message_id,),
    )
    connection.commit()


# ---------------------------------------------------------------------------
# 1. Tables exist
# ---------------------------------------------------------------------------


def test_all_eleven_reviewed_tables_exist(conn: sqlite3.Connection) -> None:
    tables = database.list_tables(conn)
    for table_name in database.REVIEWED_TABLES:
        assert table_name in tables, f"reviewed table {table_name!r} was not created"
    assert len(database.REVIEWED_TABLES) == 11


def test_schema_version_table_exists_but_is_not_a_reviewed_table(conn: sqlite3.Connection) -> None:
    # schema_version is implementation-layer metadata added in Stage 6,
    # not one of the 11 reviewed analytical tables.
    tables = database.list_tables(conn)
    assert "schema_version" in tables
    assert "schema_version" not in database.REVIEWED_TABLES


def test_no_unexpected_tables_created(conn: sqlite3.Connection) -> None:
    tables = set(database.list_tables(conn))
    expected = set(database.REVIEWED_TABLES) | {"schema_version"}
    assert tables == expected


# ---------------------------------------------------------------------------
# 2. Views exist
# ---------------------------------------------------------------------------


def test_all_reviewed_views_exist(conn: sqlite3.Connection) -> None:
    views = database.list_views(conn)
    for view_name in database.REVIEWED_VIEWS:
        assert view_name in views, f"reviewed view {view_name!r} was not created"


def test_only_the_reviewed_views_exist(conn: sqlite3.Connection) -> None:
    # Requirement: create only the reviewed analytical views -- no extras.
    views = set(database.list_views(conn))
    assert views == set(database.REVIEWED_VIEWS)


def test_views_are_queryable_on_an_empty_database(conn: sqlite3.Connection) -> None:
    # A view over an append-only history table with no rows yet should
    # simply return no rows, not error.
    assert conn.execute("SELECT * FROM v_cv_track_summary").fetchall() == []
    assert conn.execute("SELECT * FROM v_fused_track_summary").fetchall() == []
    assert conn.execute("SELECT * FROM v_fused_track_type_basis").fetchall() == []


# ---------------------------------------------------------------------------
# 3. Schema version
# ---------------------------------------------------------------------------


def test_schema_version_is_recorded(conn: sqlite3.Connection) -> None:
    version = database.get_current_schema_version(conn)
    assert version == database.SCHEMA_VERSION


# ---------------------------------------------------------------------------
# 4. Idempotent initialization
# ---------------------------------------------------------------------------


def test_initialize_database_is_idempotent(db_path: Path) -> None:
    conn1 = database.initialize_database(db_path)
    tables_after_first = set(database.list_tables(conn1))
    conn1.close()

    # Re-running against the same file must not error and must not
    # change the set of tables, views, or the recorded schema version.
    conn2 = database.initialize_database(db_path)
    tables_after_second = set(database.list_tables(conn2))
    assert tables_after_first == tables_after_second

    version_rows = conn2.execute(
        "SELECT COUNT(*) FROM schema_version WHERE version = ?",
        (database.SCHEMA_VERSION,),
    ).fetchone()[0]
    assert version_rows == 1, "re-initializing must not insert a duplicate schema_version row"
    conn2.close()


# ---------------------------------------------------------------------------
# 5. PRAGMA foreign_keys = ON
# ---------------------------------------------------------------------------


def test_foreign_keys_pragma_is_enabled_on_new_connections(conn: sqlite3.Connection) -> None:
    value = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert value == 1


# ---------------------------------------------------------------------------
# 6. Foreign-key ENFORCEMENT works -- every real, declared FK rejects an
# orphan reference.
# ---------------------------------------------------------------------------


def test_cv_detections_rejects_unknown_source_message_id(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO cv_detections (detection_id, detection_uid, source_message_id) "
            "VALUES (1, 'u1', 9999)"
        )
        conn.commit()


def test_cv_track_states_rejects_unknown_track_id(conn: sqlite3.Connection) -> None:
    _insert_valid_source_message(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO cv_track_states (cv_track_state_id, source_message_id, track_id, log_time_ns) "
            "VALUES (1, 1, 9999, 100)"
        )
        conn.commit()


def test_cv_detection_track_links_rejects_unknown_detection_id(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO cv_tracks (track_id) VALUES (1)")
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO cv_detection_track_links (detection_id, track_id) VALUES (9999, 1)"
        )
        conn.commit()


def test_cv_detection_track_links_rejects_unknown_track_id(conn: sqlite3.Connection) -> None:
    _insert_valid_source_message(conn)
    conn.execute(
        "INSERT INTO cv_detections (detection_id, detection_uid, source_message_id) VALUES (1, 'u1', 1)"
    )
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO cv_detection_track_links (detection_id, track_id) VALUES (1, 9999)"
        )
        conn.commit()


def test_radar_detections_rejects_unknown_source_message_id(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO radar_detections (radar_detection_id, source_message_id) VALUES (1, 9999)"
        )
        conn.commit()


def test_fused_track_states_rejects_unknown_fused_track_id(conn: sqlite3.Connection) -> None:
    _insert_valid_source_message(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO fused_track_states "
            "(fused_track_state_id, source_message_id, fused_track_id, log_time_ns) "
            "VALUES (1, 1, 'no-such-track', 100)"
        )
        conn.commit()


def test_fused_track_measurements_rejects_unknown_fused_track_state_id(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO fused_track_measurements (fused_track_measurement_id, fused_track_state_id) "
            "VALUES (1, 9999)"
        )
        conn.commit()


def test_cv_track_class_distribution_rejects_unknown_state_id(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO cv_track_class_distribution "
            "(cv_track_class_distribution_id, cv_track_state_id, class_raw, probability_score, source_order) "
            "VALUES (1, 9999, 21, 0.5, 0)"
        )
        conn.commit()


def test_cv_track_class_distribution_source_order_is_unique_per_state(conn: sqlite3.Connection) -> None:
    _insert_valid_source_message(conn)
    conn.execute("INSERT INTO cv_tracks (track_id) VALUES (1)")
    conn.execute(
        "INSERT INTO cv_track_states (cv_track_state_id, source_message_id, track_id, log_time_ns) "
        "VALUES (1, 1, 1, 100)"
    )
    conn.execute(
        "INSERT INTO cv_track_class_distribution VALUES (1, 1, 21, 'AIR', 0.5, 0)"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO cv_track_class_distribution VALUES (2, 1, 11, 'BIRD', 0.4, 0)"
        )
        conn.commit()


# ---------------------------------------------------------------------------
# 7. Deliberately UNENFORCED relationships accept values a real foreign
# key would reject -- proving the reviewed design decisions (Stage 3 /
# docs/SCHEMA_REVIEW.md finding F1) are actually implemented as
# unenforced, not accidentally enforced or accidentally forgotten.
# ---------------------------------------------------------------------------


def test_cv_track_states_last_associated_detection_id_is_not_fk_enforced(conn: sqlite3.Connection) -> None:
    _insert_valid_source_message(conn)
    conn.execute("INSERT INTO cv_tracks (track_id) VALUES (1)")
    # A detection_id that does not exist anywhere -- this must be
    # ACCEPTED, per docs/SCHEMA_REVIEW.md finding F1 (4 confirmed
    # orphaned values in the real data must remain loadable here).
    conn.execute(
        "INSERT INTO cv_track_states "
        "(cv_track_state_id, source_message_id, track_id, log_time_ns, last_associated_detection_id) "
        "VALUES (1, 1, 1, 100, 424242)"
    )
    conn.commit()
    row = conn.execute(
        "SELECT last_associated_detection_id FROM cv_track_states WHERE cv_track_state_id = 1"
    ).fetchone()
    assert row[0] == 424242


def test_cv_track_states_parent_object_track_id_is_not_fk_enforced(conn: sqlite3.Connection) -> None:
    _insert_valid_source_message(conn)
    conn.execute("INSERT INTO cv_tracks (track_id) VALUES (1)")
    conn.execute(
        "INSERT INTO cv_track_states "
        "(cv_track_state_id, source_message_id, track_id, log_time_ns, parent_object_track_id) "
        "VALUES (1, 1, 1, 100, 555)"
    )
    conn.commit()  # must not raise


def test_cv_detections_parent_object_detection_id_is_not_fk_enforced(conn: sqlite3.Connection) -> None:
    _insert_valid_source_message(conn)
    conn.execute(
        "INSERT INTO cv_detections "
        "(detection_id, detection_uid, source_message_id, parent_object_detection_id) "
        "VALUES (1, 'u1', 1, 777)"
    )
    conn.commit()  # must not raise


def test_radar_detections_track_id_is_not_fk_enforced(conn: sqlite3.Connection) -> None:
    _insert_valid_source_message(conn)
    conn.execute(
        "INSERT INTO radar_detections (radar_detection_id, source_message_id, track_id) "
        "VALUES (1, 1, 'some-radar-track-id-with-no-match-anywhere')"
    )
    conn.commit()  # must not raise -- Stage 3 confirmed this is not a real relationship


# ---------------------------------------------------------------------------
# 8. UNIQUE constraints work
# ---------------------------------------------------------------------------


def test_cv_detections_detection_uid_unique_constraint(conn: sqlite3.Connection) -> None:
    _insert_valid_source_message(conn)
    conn.execute(
        "INSERT INTO cv_detections (detection_id, detection_uid, source_message_id) VALUES (1, 'dup', 1)"
    )
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO cv_detections (detection_id, detection_uid, source_message_id) VALUES (2, 'dup', 1)"
        )
        conn.commit()


def test_cv_track_states_unique_source_message_and_track(conn: sqlite3.Connection) -> None:
    _insert_valid_source_message(conn)
    conn.execute("INSERT INTO cv_tracks (track_id) VALUES (1)")
    conn.execute(
        "INSERT INTO cv_track_states (cv_track_state_id, source_message_id, track_id, log_time_ns) "
        "VALUES (1, 1, 1, 100)"
    )
    conn.execute(
        "INSERT INTO cv_track_class_distribution "
        "(cv_track_class_distribution_id, cv_track_state_id, class_raw, class_name, probability_score, source_order) "
        "VALUES (1, 1, 21, 'OBJECT_CLASSIFICATION_AIR_VEHICLE', 0.75, 0)"
    )
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        # Same (source_message_id, track_id) pair again, different surrogate id.
        conn.execute(
            "INSERT INTO cv_track_states (cv_track_state_id, source_message_id, track_id, log_time_ns) "
            "VALUES (2, 1, 1, 200)"
        )
        conn.commit()


def test_fused_track_states_unique_fused_track_and_log_time(conn: sqlite3.Connection) -> None:
    _insert_valid_source_message(conn)
    conn.execute("INSERT INTO fused_tracks (fused_track_id) VALUES ('t1')")
    conn.execute(
        "INSERT INTO fused_track_states (fused_track_state_id, source_message_id, fused_track_id, log_time_ns) "
        "VALUES (1, 1, 't1', 100)"
    )
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO fused_track_states (fused_track_state_id, source_message_id, fused_track_id, log_time_ns) "
            "VALUES (2, 1, 't1', 100)"
        )
        conn.commit()


def test_cv_tracks_primary_key_uniqueness(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO cv_tracks (track_id) VALUES (1)")
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO cv_tracks (track_id) VALUES (1)")
        conn.commit()


def test_fused_tracks_primary_key_uniqueness(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO fused_tracks (fused_track_id) VALUES ('t1')")
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO fused_tracks (fused_track_id) VALUES ('t1')")
        conn.commit()


def test_cv_detection_track_links_composite_primary_key_uniqueness(conn: sqlite3.Connection) -> None:
    _insert_valid_source_message(conn)
    conn.execute(
        "INSERT INTO cv_detections (detection_id, detection_uid, source_message_id) VALUES (1, 'u1', 1)"
    )
    conn.execute("INSERT INTO cv_tracks (track_id) VALUES (1)")
    conn.execute("INSERT INTO cv_detection_track_links (detection_id, track_id) VALUES (1, 1)")
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO cv_detection_track_links (detection_id, track_id) VALUES (1, 1)")
        conn.commit()


# ---------------------------------------------------------------------------
# 9. CHECK constraint
# ---------------------------------------------------------------------------


def test_data_quality_issues_severity_check_constraint(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO data_quality_issues (issue_id, issue_type, severity, description, detected_at_utc) "
        "VALUES (1, 'orphaned_detection_reference', 'warning', 'test', '2026-01-01T00:00:00Z')"
    )
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO data_quality_issues (issue_id, issue_type, severity, description, detected_at_utc) "
            "VALUES (2, 'orphaned_detection_reference', 'not_a_real_severity', 'test', '2026-01-01T00:00:00Z')"
        )
        conn.commit()


# ---------------------------------------------------------------------------
# 10. NOT NULL columns are actually required
# ---------------------------------------------------------------------------


def test_source_messages_required_columns_reject_nulls(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO source_messages "
            "(source_message_id, channel_id, topic, schema_id, sequence, log_time_ns, publish_time_ns) "
            "VALUES (1, 1, NULL, 1, 0, 100, 100)"
        )
        conn.commit()


# ---------------------------------------------------------------------------
# 11. PRAGMA integrity_check and PRAGMA foreign_key_check
# ---------------------------------------------------------------------------


def test_integrity_check_passes_on_empty_database(conn: sqlite3.Connection) -> None:
    result = database.run_integrity_check(conn)
    assert result == ["ok"]


def test_integrity_check_passes_after_valid_inserts(conn: sqlite3.Connection) -> None:
    _insert_valid_source_message(conn)
    conn.execute("INSERT INTO cv_tracks (track_id) VALUES (1)")
    conn.execute(
        "INSERT INTO cv_track_states (cv_track_state_id, source_message_id, track_id, log_time_ns) "
        "VALUES (1, 1, 1, 100)"
    )
    conn.commit()
    assert database.run_integrity_check(conn) == ["ok"]


def test_foreign_key_check_passes_on_empty_database(conn: sqlite3.Connection) -> None:
    assert database.run_foreign_key_check(conn) == []


def test_foreign_key_check_passes_after_valid_inserts(conn: sqlite3.Connection) -> None:
    _insert_valid_source_message(conn)
    conn.execute("INSERT INTO cv_tracks (track_id) VALUES (1)")
    conn.execute(
        "INSERT INTO cv_track_states (cv_track_state_id, source_message_id, track_id, log_time_ns) "
        "VALUES (1, 1, 1, 100)"
    )
    conn.commit()
    assert database.run_foreign_key_check(conn) == []


def test_foreign_key_check_detects_violations_smuggled_in_with_enforcement_off(
    conn: sqlite3.Connection,
) -> None:
    # PRAGMA foreign_key_check inspects existing data regardless of
    # whether enforcement was on while it was written -- this proves
    # that by deliberately turning enforcement off, inserting a bad row,
    # turning it back on, and confirming the check still catches it.
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute(
        "INSERT INTO cv_detections (detection_id, detection_uid, source_message_id) VALUES (1, 'u1', 9999)"
    )
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")

    violations = database.run_foreign_key_check(conn)
    assert len(violations) == 1
    assert violations[0].table == "cv_detections"


# ---------------------------------------------------------------------------
# 12. validate_database() summary
# ---------------------------------------------------------------------------


def test_validate_database_reports_all_ok_on_fresh_database(conn: sqlite3.Connection) -> None:
    summary = database.validate_database(conn)
    assert summary["missing_reviewed_tables"] == []
    assert summary["missing_reviewed_views"] == []
    assert summary["integrity_check_ok"] is True
    assert summary["foreign_key_check_ok"] is True
    assert summary["foreign_keys_enforced"] is True
    assert summary["schema_version"] == database.SCHEMA_VERSION


# ---------------------------------------------------------------------------
# 13. Index redundancy (docs/SCHEMA_REVIEW.md finding F3): the two
# indexes identified as redundant with an existing UNIQUE constraint must
# NOT be created, while the explicit, non-redundant indexes must be.
# ---------------------------------------------------------------------------


def test_redundant_cv_track_states_source_message_index_was_removed(conn: sqlite3.Connection) -> None:
    indexes = database.list_indexes(conn, "cv_track_states")
    assert "idx_cv_track_states_source_message" not in indexes
    # The UNIQUE(source_message_id, track_id) constraint's automatic
    # index still exists and still covers lookups by source_message_id.
    assert any(name.startswith("sqlite_autoindex_cv_track_states") for name in indexes)


def test_redundant_fused_track_states_fused_track_id_index_was_removed(conn: sqlite3.Connection) -> None:
    indexes = database.list_indexes(conn, "fused_track_states")
    assert "idx_fused_track_states_fused_track_id" not in indexes
    assert any(name.startswith("sqlite_autoindex_fused_track_states") for name in indexes)


def test_expected_explicit_indexes_exist(conn: sqlite3.Connection) -> None:
    expected_by_table = {
        "source_messages": {"idx_source_messages_topic", "idx_source_messages_log_time"},
        "cv_detections": {"idx_cv_detections_source_message", "idx_cv_detections_object_class"},
        "cv_track_states": {
            "idx_cv_track_states_track_id",
            "idx_cv_track_states_last_assoc_det",
            "idx_cv_track_states_object_class",
        },
        "cv_detection_track_links": {"idx_cv_detection_track_links_track"},
        "radar_detections": {"idx_radar_detections_source_message", "idx_radar_detections_track_id"},
        "fused_track_states": {
            "idx_fused_track_states_log_time",
            "idx_fused_track_states_source_message",
            "idx_fused_track_states_object_class",
        },
        "fused_track_measurements": {
            "idx_fused_track_measurements_state",
            "idx_fused_track_measurements_sensor",
        },
        "data_quality_issues": {"idx_data_quality_issues_type", "idx_data_quality_issues_table"},
    }
    for table_name, expected_indexes in expected_by_table.items():
        actual_indexes = set(database.list_indexes(conn, table_name))
        assert expected_indexes.issubset(actual_indexes), (
            f"{table_name} is missing expected indexes: "
            f"{expected_indexes - actual_indexes}"
        )


def test_tiny_identity_tables_have_no_secondary_indexes(conn: sqlite3.Connection) -> None:
    # cv_tracks and fused_tracks are small identity tables that need no
    # index beyond enforcing their primary key.
    #
    # cv_tracks.track_id is a single-column INTEGER PRIMARY KEY, which
    # SQLite treats as an alias for the table's own rowid -- the table
    # itself serves as that index, so SQLite creates no separate
    # sqlite_autoindex entry for it at all.
    assert database.list_indexes(conn, "cv_tracks") == []
    # fused_tracks.fused_track_id is a TEXT PRIMARY KEY, which is NOT a
    # rowid alias, so SQLite does create one automatic index to enforce it.
    assert database.list_indexes(conn, "fused_tracks") == ["sqlite_autoindex_fused_tracks_1"]


# ---------------------------------------------------------------------------
# 14. End-to-end loading-order smoke test (docs/DATABASE_DESIGN.md
# Section 5.12 / docs/SCHEMA_REVIEW.md finding F2): one row per table,
# inserted in the documented two-phase order, must succeed with foreign
# keys fully enforced throughout.
# ---------------------------------------------------------------------------


def test_two_phase_loading_order_succeeds_with_foreign_keys_enforced(conn: sqlite3.Connection) -> None:
    # Phase 1: envelope, then identity tables (complete upfront scan).
    _insert_valid_source_message(conn, source_message_id=1)
    conn.execute("INSERT INTO cv_tracks (track_id) VALUES (1)")
    conn.execute("INSERT INTO fused_tracks (fused_track_id, legacy_track_id) VALUES ('ft1', 1)")
    conn.commit()

    # Phase 2: everything else, in FK-respecting order.
    conn.execute(
        "INSERT INTO cv_detections (detection_id, detection_uid, source_message_id) VALUES (1, 'u1', 1)"
    )
    conn.execute(
        "INSERT INTO cv_track_states (cv_track_state_id, source_message_id, track_id, log_time_ns) "
        "VALUES (1, 1, 1, 100)"
    )
    conn.execute(
        "INSERT INTO cv_track_class_distribution "
        "(cv_track_class_distribution_id, cv_track_state_id, class_raw, class_name, probability_score, source_order) "
        "VALUES (1, 1, 21, 'OBJECT_CLASSIFICATION_AIR_VEHICLE', 0.75, 0)"
    )
    conn.execute("INSERT INTO cv_detection_track_links (detection_id, track_id) VALUES (1, 1)")
    conn.execute(
        "INSERT INTO radar_detections (radar_detection_id, source_message_id) VALUES (1, 1)"
    )
    conn.execute(
        "INSERT INTO fused_track_states "
        "(fused_track_state_id, source_message_id, fused_track_id, log_time_ns) "
        "VALUES (1, 1, 'ft1', 100)"
    )
    conn.execute(
        "INSERT INTO fused_track_measurements (fused_track_measurement_id, fused_track_state_id) "
        "VALUES (1, 1)"
    )
    conn.execute(
        "INSERT INTO data_quality_issues (issue_id, issue_type, severity, description, detected_at_utc) "
        "VALUES (1, 'orphaned_detection_reference', 'info', 'example', '2026-01-01T00:00:00Z')"
    )
    conn.commit()

    for table_name in database.REVIEWED_TABLES:
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        assert count == 1, f"{table_name} should have exactly 1 row after the loading-order smoke test"

    assert database.run_integrity_check(conn) == ["ok"]
    assert database.run_foreign_key_check(conn) == []
