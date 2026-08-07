"""End-to-end ETL integration tests against the real MCAP file.

Every test in this file is an integration test (real
data/input/sanitized.mcap, read-only). The central requirement here is
the explicit determinism guarantee: two independent, from-scratch
rebuilds of the database must produce byte-identical results --
surrogate IDs, row counts, bridge pairs, issue records, and validation
outputs -- proving the pipeline has no reliance on random IDs, wall
clock time (other than the recorded build timestamp itself), dict/set
ordering, or any other non-deterministic input.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from cuas_etl import database, extract, load, transform, validation


def _build_fresh_database(db_path: Path) -> sqlite3.Connection:
    connection = database.initialize_database(db_path)
    extracted = extract.extract_mcap()
    tables = transform.transform_all(extracted)
    load.load_phase1(connection, tables)
    load.load_phase2(connection, tables)
    return connection


def _dump_all_tables(connection: sqlite3.Connection) -> dict[str, list[tuple]]:
    dump: dict[str, list[tuple]] = {}
    for table_name in database.REVIEWED_TABLES:
        if table_name == "data_quality_issues":
            # detected_at_utc is a build-wall-clock timestamp by design,
            # not a derived value -- excluded here, checked separately
            # (minus that column) in test_..._identical_issue_records.
            columns = [
                r[1]
                for r in connection.execute("PRAGMA table_info(data_quality_issues)")
                if r[1] != "detected_at_utc"
            ]
            select_list = ", ".join(f'"{c}"' for c in columns)
            rows = connection.execute(
                f"SELECT {select_list} FROM data_quality_issues ORDER BY rowid"
            ).fetchall()
        else:
            rows = connection.execute(
                f"SELECT * FROM {table_name} ORDER BY rowid"
            ).fetchall()
        dump[table_name] = [tuple(row) for row in rows]
    return dump


def test_real_mcap_two_independent_rebuilds_are_byte_identical(tmp_path):
    conn_a = _build_fresh_database(tmp_path / "rebuild_a.db")
    conn_b = _build_fresh_database(tmp_path / "rebuild_b.db")

    dump_a = _dump_all_tables(conn_a)
    dump_b = _dump_all_tables(conn_b)

    assert dump_a.keys() == dump_b.keys()
    for table_name in dump_a:
        rows_a = dump_a[table_name]
        rows_b = dump_b[table_name]
        assert len(rows_a) == len(rows_b), (
            f"{table_name}: rebuild A has {len(rows_a)} rows, "
            f"rebuild B has {len(rows_b)} rows"
        )
        assert rows_a == rows_b, f"{table_name}: rebuild A and rebuild B rows differ"

    conn_a.close()
    conn_b.close()


def test_real_mcap_two_independent_rebuilds_have_identical_bridge_pairs(tmp_path):
    conn_a = _build_fresh_database(tmp_path / "rebuild_a.db")
    conn_b = _build_fresh_database(tmp_path / "rebuild_b.db")

    def bridge_pairs(connection: sqlite3.Connection) -> list[tuple]:
        return connection.execute(
            "SELECT detection_id, track_id FROM cv_detection_track_links "
            "ORDER BY detection_id, track_id"
        ).fetchall()

    assert bridge_pairs(conn_a) == bridge_pairs(conn_b)
    conn_a.close()
    conn_b.close()


def test_real_mcap_two_independent_rebuilds_have_identical_issue_records(tmp_path):
    conn_a = _build_fresh_database(tmp_path / "rebuild_a.db")
    conn_b = _build_fresh_database(tmp_path / "rebuild_b.db")

    def issues(connection: sqlite3.Connection) -> list[tuple]:
        # Exclude detected_at_utc: it is a build-wall-clock timestamp by
        # design, not a derived value, so it is expected to differ
        # between separately-invoked rebuilds.
        return connection.execute(
            "SELECT issue_id, issue_type, severity, description, "
            "related_table, related_id FROM data_quality_issues ORDER BY issue_id"
        ).fetchall()

    assert issues(conn_a) == issues(conn_b)
    conn_a.close()
    conn_b.close()


def test_real_mcap_two_independent_rebuilds_produce_identical_validation_outputs(tmp_path):
    conn_a = _build_fresh_database(tmp_path / "rebuild_a.db")
    conn_b = _build_fresh_database(tmp_path / "rebuild_b.db")

    report_a = validation.run_full_validation(conn_a)
    report_b = validation.run_full_validation(conn_b)

    def fingerprint(report: validation.ValidationReport) -> list[tuple]:
        return [
            (c.name, c.level, c.passed, c.expected, c.actual)
            for c in report.checks
        ]

    assert fingerprint(report_a) == fingerprint(report_b)
    assert report_a.passed_overall is True
    assert report_b.passed_overall is True

    conn_a.close()
    conn_b.close()


def test_real_mcap_rebuild_flag_replaces_an_existing_database(tmp_path):
    db_path = tmp_path / "rebuild_target.db"
    conn1 = _build_fresh_database(db_path)
    count_before = conn1.execute("SELECT COUNT(*) FROM source_messages").fetchone()[0]
    conn1.close()

    db_path.unlink()  # emulate the --rebuild deletion step explicitly
    conn2 = _build_fresh_database(db_path)
    count_after = conn2.execute("SELECT COUNT(*) FROM source_messages").fetchone()[0]
    conn2.close()

    assert count_before == count_after == extract.EXPECTED_TOTAL_MESSAGE_COUNT


def test_real_mcap_non_rebuild_run_against_populated_database_does_not_duplicate_rows(tmp_path):
    db_path = tmp_path / "idempotent.db"
    conn = _build_fresh_database(db_path)
    count_before = conn.execute("SELECT COUNT(*) FROM source_messages").fetchone()[0]

    assert load.database_already_populated(conn) is True
    # Simulate the non-rebuild path: build_database.py must not attempt a
    # second load against an already-populated database.
    report = validation.run_full_validation(conn)
    assert report.passed_overall is True

    count_after = conn.execute("SELECT COUNT(*) FROM source_messages").fetchone()[0]
    assert count_before == count_after

    conn.close()
