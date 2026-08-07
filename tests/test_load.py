"""Tests for src/cuas_etl/load.py.

All tests here use a fresh, temporary, schema-initialized SQLite
database (via the `conn` fixture, reusing src/cuas_etl/database.py) and
small, fully synthetic row dicts -- no dependency on the real MCAP file
anywhere in this file.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cuas_etl import database, load
from cuas_etl.transform import TransformedTables


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    connection = database.initialize_database(tmp_path / "test.db")
    yield connection
    connection.close()


def _empty_tables(**overrides) -> TransformedTables:
    base = dict(
        source_messages=[], cv_detections=[], cv_tracks=[], cv_track_states=[],
        cv_track_class_distribution=[],
        cv_detection_track_links=[], radar_detections=[], fused_tracks=[],
        fused_track_states=[], fused_track_measurements=[], data_quality_issues=[],
    )
    base.update(overrides)
    return TransformedTables(**base)


def _source_message_row(source_message_id=1):
    return {
        "source_message_id": source_message_id, "channel_id": 1, "topic": "cv_detections",
        "schema_id": 1, "sequence": 0, "log_time_ns": 100, "publish_time_ns": 100,
    }


# ---------------------------------------------------------------------------
# Phase ordering: parents before children
# ---------------------------------------------------------------------------


def test_phase1_loads_source_messages_cv_tracks_fused_tracks(conn):
    tables = _empty_tables(
        source_messages=[_source_message_row()],
        cv_tracks=[{"track_id": 1}],
        fused_tracks=[{"fused_track_id": "ft1", "legacy_track_id": 1}],
    )
    counts = load.load_phase1(conn, tables)
    assert counts == {"source_messages": 1, "cv_tracks": 1, "fused_tracks": 1}
    assert conn.execute("SELECT COUNT(*) FROM source_messages").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM cv_tracks").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM fused_tracks").fetchone()[0] == 1


def test_phase2_requires_phase1_parents_to_already_exist(conn):
    # cv_detections FKs to source_messages, which Phase 1 must have
    # already loaded -- without it, Phase 2 must fail, not silently skip.
    tables = _empty_tables(
        cv_detections=[{
            "detection_id": 1, "detection_uid": "u1", "source_message_id": 1,
            "capture_time_ns": None, "class_name": "", "object_class_raw": None,
            "object_class_name": None, "bbox_left": None, "bbox_top": None,
            "bbox_right": None, "bbox_bottom": None, "score": None,
            "semantic_confidence_raw": None, "semantic_confidence_name": None,
            "focus_quality_raw": None, "focus_quality_name": None,
            "focus_score": None, "sharpness": None,
            "detector_index": None, "disposition_raw": None, "disposition_name": None,
            "motion_state_raw": None, "motion_state_name": None,
            "parent_object_detection_id": None,
        }],
    )
    with pytest.raises(load.LoadError):
        load.load_phase2(conn, tables)
    # And nothing was left committed:
    assert conn.execute("SELECT COUNT(*) FROM cv_detections").fetchone()[0] == 0


def test_phase2_succeeds_once_phase1_parents_are_loaded(conn):
    phase1_tables = _empty_tables(
        source_messages=[_source_message_row()],
        cv_tracks=[{"track_id": 1}],
        fused_tracks=[{"fused_track_id": "ft1", "legacy_track_id": 1}],
    )
    load.load_phase1(conn, phase1_tables)

    phase2_tables = _empty_tables(
        cv_detections=[{
            "detection_id": 1, "detection_uid": "u1", "source_message_id": 1,
            "capture_time_ns": None, "class_name": "", "object_class_raw": None,
            "object_class_name": None, "bbox_left": None, "bbox_top": None,
            "bbox_right": None, "bbox_bottom": None, "score": None,
            "semantic_confidence_raw": None, "semantic_confidence_name": None,
            "focus_quality_raw": None, "focus_quality_name": None,
            "focus_score": None, "sharpness": None,
            "detector_index": None, "disposition_raw": None, "disposition_name": None,
            "motion_state_raw": None, "motion_state_name": None,
            "parent_object_detection_id": None,
        }],
    )
    counts = load.load_phase2(conn, phase2_tables)
    assert counts["cv_detections"] == 1


def test_phase2_loads_ordered_class_distribution_children(conn):
    load.load_phase1(
        conn,
        _empty_tables(
            source_messages=[_source_message_row()],
            cv_tracks=[{"track_id": 1}],
        ),
    )
    state = {
        "cv_track_state_id": 1, "source_message_id": 1, "track_id": 1,
        "log_time_ns": 100, "track_age": 1, "status_raw": 1, "status_name": "S",
        "status_code_raw": 1, "status_code_name": "C", "object_class_raw": 21,
        "object_class_name": "AIR", "class_name": "AIR", "bbox_left": None,
        "bbox_top": None, "bbox_right": None, "bbox_bottom": None,
        "last_associated_detection_id": None, "num_detection_associations": 0,
        "object_class_confidence": 0.8, "score": 0.8, "disposition_raw": 0,
        "disposition_name": "UNKNOWN", "motion_state_raw": 0,
        "motion_state_name": "UNKNOWN", "is_manual": 0,
        "parent_object_track_id": None, "capture_time_ns": None,
    }
    children = [
        {"cv_track_class_distribution_id": 1, "cv_track_state_id": 1,
         "class_raw": 21, "class_name": "AIR", "probability_score": 0.8, "source_order": 0},
        {"cv_track_class_distribution_id": 2, "cv_track_state_id": 1,
         "class_raw": 11, "class_name": "BIRD", "probability_score": 0.1, "source_order": 1},
    ]
    counts = load.load_phase2(
        conn, _empty_tables(cv_track_states=[state], cv_track_class_distribution=children)
    )
    assert counts["cv_track_class_distribution"] == 2
    assert conn.execute(
        "SELECT class_raw, source_order FROM cv_track_class_distribution ORDER BY source_order"
    ).fetchall() == [(21, 0), (11, 1)]


# ---------------------------------------------------------------------------
# FK enforcement during load
# ---------------------------------------------------------------------------


def test_unexpected_fk_violation_is_fatal_and_rolled_back(conn):
    load.load_phase1(conn, _empty_tables(source_messages=[_source_message_row()]))
    tables = _empty_tables(
        radar_detections=[{
            "radar_detection_id": 1, "source_message_id": 9999,  # does not exist
            "capture_time_ns": None, "range": None, "azimuth_rad": None, "elevation_rad": None,
            "range_rate": None, "return_strength": None, "snr": None, "track_id": None,
            "object_type_class_raw": None, "object_type_class_name": None,
            "object_class_raw": None, "object_class_name": None,
            "filter_type_raw": None, "filter_type_name": None,
            "azimuth_sigma": None, "elevation_sigma": None, "range_sigma": None,
            "range_rate_sigma": None, "estimated_width_meters": None, "is_marked": 0,
            "cluster_json": "[]",
        }],
    )
    with pytest.raises(load.LoadError, match="radar_detections"):
        load.load_phase2(conn, tables)
    assert conn.execute("SELECT COUNT(*) FROM radar_detections").fetchone()[0] == 0


def test_load_error_message_includes_source_message_id_and_row_values(conn):
    load.load_phase1(conn, _empty_tables(source_messages=[_source_message_row()]))
    bad_row = {
        "radar_detection_id": 1, "source_message_id": 9999,
        "capture_time_ns": None, "range": None, "azimuth_rad": None, "elevation_rad": None,
        "range_rate": None, "return_strength": None, "snr": None, "track_id": None,
        "object_type_class_raw": None, "object_type_class_name": None,
        "object_class_raw": None, "object_class_name": None,
        "filter_type_raw": None, "filter_type_name": None,
        "azimuth_sigma": None, "elevation_sigma": None, "range_sigma": None,
        "range_rate_sigma": None, "estimated_width_meters": None, "is_marked": 0,
        "cluster_json": "[]",
    }
    tables = _empty_tables(radar_detections=[bad_row])
    with pytest.raises(load.LoadError) as excinfo:
        load.load_phase2(conn, tables)
    message = str(excinfo.value)
    assert "radar_detections" in message
    assert "9999" in message


# ---------------------------------------------------------------------------
# Unexpected duplicate PK / UNIQUE collisions are fatal, not swallowed
# ---------------------------------------------------------------------------


def test_unexpected_duplicate_pk_is_fatal(conn):
    load.load_phase1(conn, _empty_tables(cv_tracks=[{"track_id": 1}]))
    with pytest.raises(load.LoadError):
        load.load_phase1(conn, _empty_tables(cv_tracks=[{"track_id": 1}]))


def test_batch_insertion_across_multiple_batches(conn, monkeypatch):
    # Force a tiny batch size so a >1-batch insert path is exercised.
    monkeypatch.setattr(load, "BATCH_SIZE", 2)
    rows = [{"track_id": i} for i in range(1, 6)]  # 5 rows, batch size 2 -> 3 batches
    counts = load.load_phase1(conn, _empty_tables(cv_tracks=rows))
    assert counts["cv_tracks"] == 5
    assert conn.execute("SELECT COUNT(*) FROM cv_tracks").fetchone()[0] == 5


# ---------------------------------------------------------------------------
# database_already_populated
# ---------------------------------------------------------------------------


def test_database_already_populated_false_on_empty_db(conn):
    assert load.database_already_populated(conn) is False


def test_database_already_populated_true_after_phase1(conn):
    load.load_phase1(conn, _empty_tables(source_messages=[_source_message_row()]))
    assert load.database_already_populated(conn) is True
