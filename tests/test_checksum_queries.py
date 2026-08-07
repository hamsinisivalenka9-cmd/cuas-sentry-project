"""Tests for queries/fused_track_duration_by_type.sql and its supporting
view, sql/views.sql::v_fused_track_type_basis.

UNIT TESTS (below the first marker) build a small, fully synthetic
database and verify the classification/median logic itself in
isolation -- no dependency on the real MCAP file.

INTEGRATION TESTS (function names prefixed test_real_mcap_) build a
real database from the actual source file and execute the actual
queries/fused_track_duration_by_type.sql file against it, asserting
the observed, evidence-supported results documented in
docs/CHECKSUM_RESOLUTION.md -- not the assignment's raw ~30s/~600s
targets. These are regression guards confirming the query keeps
producing what the investigation found, not assertions that the
checksum "passes" against the original targets.

CV incorporation is deliberately NOT tested here: docs/CHECKSUM_
RESOLUTION.md Part B/C concluded no evidence-supported definition
reproduces ~81%, and no production change was made for it, so there is
nothing new to assert beyond the existing cv_detection_track_links
tests already in tests/test_load.py and tests/test_transform.py.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cuas_etl import database, extract, load, transform

QUERY_PATH = Path(__file__).resolve().parent.parent / "queries" / "fused_track_duration_by_type.sql"


def _run_duration_query(connection: sqlite3.Connection) -> dict[str, dict]:
    sql = QUERY_PATH.read_text()
    rows = connection.execute(sql).fetchall()
    columns = [d[0] for d in connection.execute(sql).description]
    return {row[0]: dict(zip(columns, row)) for row in rows}


# ===========================================================================
# UNIT TESTS -- synthetic database only
# ===========================================================================


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    connection = database.initialize_database(tmp_path / "test.db")
    yield connection
    connection.close()


def _insert_source_message(conn, smid):
    conn.execute(
        "INSERT INTO source_messages VALUES (?,1,'track_states',2,0,?,?)",
        (smid, smid * 1_000_000_000, smid * 1_000_000_000),
    )


def _insert_fused_track(conn, fused_track_id):
    conn.execute("INSERT INTO fused_tracks (fused_track_id) VALUES (?)", (fused_track_id,))


def _insert_state(conn, state_id, fused_track_id, smid, log_time_s, object_class_name, object_class_raw=4):
    _insert_source_message(conn, smid)
    conn.execute(
        "INSERT INTO fused_track_states "
        "(fused_track_state_id, source_message_id, fused_track_id, log_time_ns, "
        "object_class_raw, object_class_name) VALUES (?,?,?,?,?,?)",
        (state_id, smid, fused_track_id, log_time_s * 1_000_000_000, object_class_raw, object_class_name),
    )


def _insert_measurement(conn, meas_id, state_id, sensor_id_name, sensor_id_raw):
    conn.execute(
        "INSERT INTO fused_track_measurements "
        "(fused_track_measurement_id, fused_track_state_id, sensor_id_raw, sensor_id_name) "
        "VALUES (?,?,?,?)",
        (meas_id, state_id, sensor_id_raw, sensor_id_name),
    )


def test_view_classifies_transponder_track_as_having_transponder(conn):
    _insert_fused_track(conn, "t1")
    _insert_state(conn, 1, "t1", 1, 0, "OBJECT_CLASS_AIR_VEHICLE")
    _insert_state(conn, 2, "t1", 2, 600, "OBJECT_CLASS_AIR_VEHICLE")
    _insert_measurement(conn, 1, 1, "TOWER_SENSOR_TRANSPONDER", 6)
    conn.commit()

    row = conn.execute(
        "SELECT has_transponder_measurement, dominant_object_class_name, duration_seconds "
        "FROM v_fused_track_type_basis WHERE fused_track_id='t1'"
    ).fetchone()
    assert row == (1, "OBJECT_CLASS_AIR_VEHICLE", 600.0)


def test_view_classifies_radar_only_track_as_no_transponder(conn):
    _insert_fused_track(conn, "t2")
    _insert_state(conn, 3, "t2", 3, 0, "OBJECT_CLASS_AIR_VEHICLE")
    _insert_measurement(conn, 2, 3, "TOWER_SENSOR_RADAR", 1)
    conn.commit()

    row = conn.execute(
        "SELECT has_transponder_measurement FROM v_fused_track_type_basis WHERE fused_track_id='t2'"
    ).fetchone()
    assert row == (0,)


def test_view_dominant_class_is_the_plurality_class(conn):
    # 3 states: BIRD, BIRD, AIR_VEHICLE -- BIRD should win as dominant.
    _insert_fused_track(conn, "t3")
    _insert_state(conn, 4, "t3", 4, 0, "OBJECT_CLASS_BIRD", object_class_raw=10)
    _insert_state(conn, 5, "t3", 5, 1, "OBJECT_CLASS_BIRD", object_class_raw=10)
    _insert_state(conn, 6, "t3", 6, 2, "OBJECT_CLASS_AIR_VEHICLE")
    _insert_measurement(conn, 3, 4, "TOWER_SENSOR_RADAR", 1)
    conn.commit()

    row = conn.execute(
        "SELECT dominant_object_class_name FROM v_fused_track_type_basis WHERE fused_track_id='t3'"
    ).fetchone()
    assert row == ("OBJECT_CLASS_BIRD",)


def test_view_track_with_no_measurements_defaults_to_no_transponder(conn):
    # A fused_track_states row with zero fused_track_measurements children
    # must not disappear from the view or error -- COALESCE should give 0.
    _insert_fused_track(conn, "t4")
    _insert_state(conn, 7, "t4", 7, 0, "OBJECT_CLASS_AIR_VEHICLE")
    conn.commit()

    row = conn.execute(
        "SELECT has_transponder_measurement FROM v_fused_track_type_basis WHERE fused_track_id='t4'"
    ).fetchone()
    assert row == (0,)


def test_duration_query_classifies_and_excludes_bird(conn):
    # t1: transponder, AIR_VEHICLE, duration 600s -> Airplane
    _insert_fused_track(conn, "t1")
    _insert_state(conn, 1, "t1", 1, 0, "OBJECT_CLASS_AIR_VEHICLE")
    _insert_state(conn, 2, "t1", 2, 600, "OBJECT_CLASS_AIR_VEHICLE")
    _insert_measurement(conn, 1, 1, "TOWER_SENSOR_TRANSPONDER", 6)

    # t2: no transponder, AIR_VEHICLE, duration 30s -> Drone
    _insert_fused_track(conn, "t2")
    _insert_state(conn, 3, "t2", 3, 100, "OBJECT_CLASS_AIR_VEHICLE")
    _insert_state(conn, 4, "t2", 4, 130, "OBJECT_CLASS_AIR_VEHICLE")
    _insert_measurement(conn, 2, 3, "TOWER_SENSOR_RADAR", 1)

    # t3: no transponder, BIRD -> excluded from both groups
    _insert_fused_track(conn, "t3")
    _insert_state(conn, 5, "t3", 5, 200, "OBJECT_CLASS_BIRD", object_class_raw=10)
    _insert_measurement(conn, 3, 5, "TOWER_SENSOR_RADAR", 1)
    conn.commit()

    results = _run_duration_query(conn)
    assert set(results.keys()) == {"Airplane", "Drone", "Excluded (BIRD)"}
    assert results["Airplane"]["track_count"] == 1
    assert results["Airplane"]["arithmetic_mean_duration_seconds"] == 600.0
    assert results["Drone"]["track_count"] == 1
    assert results["Drone"]["arithmetic_mean_duration_seconds"] == 30.0
    assert results["Excluded (BIRD)"]["track_count"] == 1


def test_duration_query_median_matches_manual_calculation_odd_n(conn):
    # 3 Drone tracks with durations 10, 20, 90 -- median must be 20
    # (the middle value), mean must be 40 (arithmetic average).
    for i, dur in enumerate([10, 20, 90], start=1):
        fid = f"drone{i}"
        _insert_fused_track(conn, fid)
        _insert_state(conn, i * 10, fid, i * 10, 0, "OBJECT_CLASS_AIR_VEHICLE")
        _insert_state(conn, i * 10 + 1, fid, i * 10 + 1, dur, "OBJECT_CLASS_AIR_VEHICLE")
        _insert_measurement(conn, i, i * 10, "TOWER_SENSOR_RADAR", 1)
    conn.commit()

    results = _run_duration_query(conn)
    assert results["Drone"]["track_count"] == 3
    assert results["Drone"]["arithmetic_mean_duration_seconds"] == 40.0
    assert results["Drone"]["median_duration_seconds_supplementary_only"] == 20.0


def test_duration_query_median_matches_manual_calculation_even_n(conn):
    # 4 Drone tracks with durations 10, 20, 30, 100 -- median must be
    # the average of the two middle values (20, 30) = 25.
    for i, dur in enumerate([10, 20, 30, 100], start=1):
        fid = f"drone{i}"
        _insert_fused_track(conn, fid)
        _insert_state(conn, i * 10, fid, i * 10, 0, "OBJECT_CLASS_AIR_VEHICLE")
        _insert_state(conn, i * 10 + 1, fid, i * 10 + 1, dur, "OBJECT_CLASS_AIR_VEHICLE")
        _insert_measurement(conn, i, i * 10, "TOWER_SENSOR_RADAR", 1)
    conn.commit()

    results = _run_duration_query(conn)
    assert results["Drone"]["track_count"] == 4
    assert results["Drone"]["median_duration_seconds_supplementary_only"] == 25.0
    assert results["Drone"]["arithmetic_mean_duration_seconds"] == 40.0


# ===========================================================================
# INTEGRATION TESTS -- real data/input/sanitized.mcap, freshly rebuilt
# ===========================================================================


@pytest.fixture(scope="module")
def real_built_connection(tmp_path_factory) -> sqlite3.Connection:
    db_path = tmp_path_factory.mktemp("checksum_queries") / "real.db"
    connection = database.initialize_database(db_path)
    extracted = extract.extract_mcap()
    tables = transform.transform_all(extracted)
    load.load_phase1(connection, tables)
    load.load_phase2(connection, tables)
    yield connection
    connection.close()


def test_real_mcap_view_covers_every_fused_track_exactly_once(real_built_connection):
    row = real_built_connection.execute(
        "SELECT COUNT(*), COUNT(DISTINCT fused_track_id) FROM v_fused_track_type_basis"
    ).fetchone()
    assert row == (103, 103)


def test_real_mcap_duration_query_group_counts(real_built_connection):
    # Regression guard on the population split documented in
    # docs/CHECKSUM_RESOLUTION.md -- these counts must stay exact and
    # stable across rebuilds (the pipeline is fully deterministic).
    results = _run_duration_query(real_built_connection)
    assert results["Airplane"]["track_count"] == 36
    assert results["Drone"]["track_count"] == 51
    assert results["Excluded (BIRD)"]["track_count"] == 16
    total = sum(r["track_count"] for r in results.values())
    assert total == 103


def test_real_mcap_airplane_duration_within_documented_tolerance(real_built_connection):
    # Documented evidence-supported result: mean ~614.68s, median ~606.18s
    # (docs/CHECKSUM_RESOLUTION.md Section 0/2.3). This asserts the query
    # keeps reproducing that observed result -- it is NOT an assertion
    # that the ~600s assignment target is matched to a tighter tolerance
    # than the evidence supports (though in this group's case, it happens
    # to be a close match).
    results = _run_duration_query(real_built_connection)
    airplane = results["Airplane"]
    assert 610.0 <= airplane["arithmetic_mean_duration_seconds"] <= 620.0
    assert 600.0 <= airplane["median_duration_seconds_supplementary_only"] <= 612.0


def test_real_mcap_drone_duration_within_documented_tolerance(real_built_connection):
    # Documented evidence-supported result: mean ~35.86s, median ~30.26s.
    # The mean is reported honestly as ~19.5% above the ~30s assignment
    # target (docs/CHECKSUM_RESOLUTION.md Section 2.4) -- this test
    # asserts stability of that observed mean, not a claim that it
    # matches the target within a tight tolerance. The median is
    # asserted separately and explicitly labeled supplementary -- it is
    # never used in place of the mean.
    results = _run_duration_query(real_built_connection)
    drone = results["Drone"]
    assert 33.0 <= drone["arithmetic_mean_duration_seconds"] <= 39.0
    assert 28.0 <= drone["median_duration_seconds_supplementary_only"] <= 33.0


def test_real_mcap_query_matches_independent_python_reimplementation(real_built_connection):
    # Cross-check the SQL query's numbers against an independently
    # computed set of numbers using plain Python aggregation over the
    # same view, as a defense against a subtle SQL logic error (e.g. in
    # the window-function median technique) that could still produce a
    # plausible-looking but wrong number.
    import statistics

    rows = real_built_connection.execute(
        "SELECT has_transponder_measurement, dominant_object_class_name, duration_seconds "
        "FROM v_fused_track_type_basis"
    ).fetchall()

    drone_durations = [
        d for has_transp, cls, d in rows
        if has_transp == 0 and cls in ("OBJECT_CLASS_AIR_VEHICLE", "OBJECT_CLASS_UNKNOWN_AIR_VEHICLE")
    ]
    airplane_durations = [d for has_transp, _, d in rows if has_transp == 1]

    results = _run_duration_query(real_built_connection)

    assert len(drone_durations) == results["Drone"]["track_count"]
    assert round(sum(drone_durations) / len(drone_durations), 2) == results["Drone"]["arithmetic_mean_duration_seconds"]
    assert round(statistics.median(drone_durations), 2) == results["Drone"]["median_duration_seconds_supplementary_only"]

    assert len(airplane_durations) == results["Airplane"]["track_count"]
    assert round(sum(airplane_durations) / len(airplane_durations), 2) == results["Airplane"]["arithmetic_mean_duration_seconds"]
    assert round(statistics.median(airplane_durations), 2) == results["Airplane"]["median_duration_seconds_supplementary_only"]
