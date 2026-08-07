"""Load phase: insert already-transformed rows into the SQLite database.

This module contains NO protobuf-specific field-navigation logic -- it
only knows about plain Python dicts (produced by transform.py) and SQL.
Every INSERT is parameterized (never string-formatted) and every table's
column list is declared once, in TableLoadSpec, so it can be directly
compared against sql/schema.sql by a reviewer.

Error handling policy (do not weaken without updating this comment):
- The ONLY row exclusion this module's callers are expected to produce
  is the known, approved orphan-bridge-row case, which transform.py
  already excludes BEFORE rows ever reach this module -- load.py never
  special-cases orphans itself.
- Every other constraint violation (unexpected duplicate PK, unexpected
  UNIQUE collision, unexpected FK failure, an invalid CHECK value, a
  missing required parent record, or a type-conversion failure) is
  FATAL: the failing batch's savepoint is rolled back, a LoadError with
  full diagnostic detail (table, source_message_id if present, and the
  exact row values) is raised, and the caller (scripts/build_database.py)
  is expected to roll back the whole phase transaction and exit nonzero.
  This module never catches sqlite3.IntegrityError and silently
  continues, and never uses INSERT OR IGNORE.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from cuas_etl.transform import TransformedTables

BATCH_SIZE = 5_000


class LoadError(RuntimeError):
    """Raised when a load fails in a way that must abort the whole
    build. Always carries a human-readable message identifying the
    table and, where available, the specific row and source_message_id
    involved."""


@dataclass(frozen=True)
class TableLoadSpec:
    """The column list for one table's INSERT statement, in the same
    order as sql/schema.sql, so the two files can be compared directly."""

    table_name: str
    columns: tuple[str, ...]

    @property
    def insert_sql(self) -> str:
        quoted_columns = ", ".join(f'"{c}"' for c in self.columns)
        placeholders = ", ".join(f":{c}" for c in self.columns)
        return f"INSERT INTO {self.table_name} ({quoted_columns}) VALUES ({placeholders})"


SOURCE_MESSAGES_SPEC = TableLoadSpec("source_messages", (
    "source_message_id", "channel_id", "topic", "schema_id", "sequence",
    "log_time_ns", "publish_time_ns",
))
CV_DETECTIONS_SPEC = TableLoadSpec("cv_detections", (
    "detection_id", "detection_uid", "source_message_id", "capture_time_ns",
    "class_name", "object_class_raw", "object_class_name",
    "bbox_left", "bbox_top", "bbox_right", "bbox_bottom", "score",
    "semantic_confidence_raw", "semantic_confidence_name", "detector_index",
    "focus_quality_raw", "focus_quality_name", "focus_score", "sharpness",
    "disposition_raw", "disposition_name", "motion_state_raw", "motion_state_name",
    "parent_object_detection_id",
))
CV_TRACKS_SPEC = TableLoadSpec("cv_tracks", ("track_id",))
CV_TRACK_STATES_SPEC = TableLoadSpec("cv_track_states", (
    "cv_track_state_id", "source_message_id", "track_id", "log_time_ns",
    "track_age", "status_raw", "status_name", "status_code_raw", "status_code_name",
    "object_class_raw", "object_class_name", "class_name",
    "bbox_left", "bbox_top", "bbox_right", "bbox_bottom",
    "last_associated_detection_id", "num_detection_associations",
    "object_class_confidence", "score", "disposition_raw", "disposition_name",
    "motion_state_raw", "motion_state_name", "is_manual", "parent_object_track_id",
    "capture_time_ns",
))
CV_TRACK_CLASS_DISTRIBUTION_SPEC = TableLoadSpec("cv_track_class_distribution", (
    "cv_track_class_distribution_id", "cv_track_state_id", "class_raw", "class_name",
    "probability_score", "source_order",
))
CV_DETECTION_TRACK_LINKS_SPEC = TableLoadSpec("cv_detection_track_links", (
    "detection_id", "track_id", "first_observed_log_time_ns",
))
RADAR_DETECTIONS_SPEC = TableLoadSpec("radar_detections", (
    "radar_detection_id", "source_message_id", "capture_time_ns", "range",
    "azimuth_rad", "elevation_rad", "range_rate", "return_strength", "snr",
    "track_id", "object_type_class_raw", "object_type_class_name",
    "object_class_raw", "object_class_name", "filter_type_raw", "filter_type_name",
    "azimuth_sigma", "elevation_sigma", "range_sigma", "range_rate_sigma",
    "estimated_width_meters", "is_marked", "cluster_json",
))
FUSED_TRACKS_SPEC = TableLoadSpec("fused_tracks", ("fused_track_id", "legacy_track_id"))
FUSED_TRACK_STATES_SPEC = TableLoadSpec("fused_track_states", (
    "fused_track_state_id", "source_message_id", "fused_track_id", "log_time_ns",
    "create_timestamp_ns", "last_measurement_timestamp_ns",
    "lla_lat", "lla_lon", "lla_alt", "track_quality",
    "object_class_raw", "object_class_name", "disposition_raw", "disposition_name",
    "track_status_raw", "track_status_name", "parent_track_id", "object_class_confidence",
))
FUSED_TRACK_MEASUREMENTS_SPEC = TableLoadSpec("fused_track_measurements", (
    "fused_track_measurement_id", "fused_track_state_id", "measurement_timestamp_ns",
    "asset_id2", "sensor_id_raw", "sensor_id_name", "frame_counter", "sensor_index",
    "detection_ids_json",
))
DATA_QUALITY_ISSUES_SPEC = TableLoadSpec("data_quality_issues", (
    "issue_id", "issue_type", "severity", "related_table", "related_id",
    "description", "detected_at_utc",
))

PHASE_1_SPECS: tuple[tuple[TableLoadSpec, str], ...] = (
    (SOURCE_MESSAGES_SPEC, "source_messages"),
    (CV_TRACKS_SPEC, "cv_tracks"),
    (FUSED_TRACKS_SPEC, "fused_tracks"),
)
PHASE_2_SPECS: tuple[tuple[TableLoadSpec, str], ...] = (
    (CV_DETECTIONS_SPEC, "cv_detections"),
    (CV_TRACK_STATES_SPEC, "cv_track_states"),
    (CV_TRACK_CLASS_DISTRIBUTION_SPEC, "cv_track_class_distribution"),
    (CV_DETECTION_TRACK_LINKS_SPEC, "cv_detection_track_links"),
    (RADAR_DETECTIONS_SPEC, "radar_detections"),
    (FUSED_TRACK_STATES_SPEC, "fused_track_states"),
    (FUSED_TRACK_MEASUREMENTS_SPEC, "fused_track_measurements"),
    (DATA_QUALITY_ISSUES_SPEC, "data_quality_issues"),
)


def _diagnose_and_raise(
    connection: sqlite3.Connection,
    spec: TableLoadSpec,
    batch: list[dict],
    original_exc: sqlite3.Error,
) -> None:
    """A batch insert failed and has already been rolled back to the
    pre-batch savepoint. Re-attempt the same rows one at a time (each
    individually rolled back via its own savepoint) to identify exactly
    which row caused the failure, then raise LoadError with full
    diagnostic detail. Never returns normally."""
    for row in batch:
        connection.execute("SAVEPOINT row_diagnosis")
        try:
            connection.execute(spec.insert_sql, row)
        except sqlite3.Error as row_exc:
            connection.execute("ROLLBACK TO SAVEPOINT row_diagnosis")
            connection.execute("RELEASE SAVEPOINT row_diagnosis")
            source_message_id = row.get("source_message_id", "n/a")
            raise LoadError(
                f"Failed to insert into {spec.table_name!r}: {row_exc}\n"
                f"  source_message_id: {source_message_id}\n"
                f"  row values: {row}"
            ) from row_exc
        else:
            connection.execute("ROLLBACK TO SAVEPOINT row_diagnosis")
            connection.execute("RELEASE SAVEPOINT row_diagnosis")

    # Every row succeeded in isolation -- the failure only happens when
    # they are inserted together (e.g. two rows in the same batch
    # collide with each other's PK/UNIQUE, not with pre-existing data).
    raise LoadError(
        f"Failed to insert a batch of {len(batch)} rows into {spec.table_name!r} "
        f"(no single row failed in isolation -- likely an in-batch collision): "
        f"{original_exc}"
    ) from original_exc


def _insert_rows(connection: sqlite3.Connection, spec: TableLoadSpec, rows: list[dict]) -> int:
    """Insert `rows` into `spec.table_name` in fixed-size batches, using
    parameterized SQL. Returns the number of rows inserted. Raises
    LoadError with full diagnostic detail on any failure -- never
    silently skips a row."""
    if not rows:
        return 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        connection.execute("SAVEPOINT batch_insert")
        try:
            connection.executemany(spec.insert_sql, batch)
        except sqlite3.Error as exc:
            connection.execute("ROLLBACK TO SAVEPOINT batch_insert")
            connection.execute("RELEASE SAVEPOINT batch_insert")
            _diagnose_and_raise(connection, spec, batch, exc)
        else:
            connection.execute("RELEASE SAVEPOINT batch_insert")
    return len(rows)


def load_phase1(connection: sqlite3.Connection, tables: TransformedTables) -> dict[str, int]:
    """Load source_messages, cv_tracks, fused_tracks -- the envelope and
    the two derived identity tables every Phase 2 table's foreign keys
    depend on (docs/DATABASE_DESIGN.md Section 5.12).

    Commits only if all three loads succeed. On any failure, rolls back
    everything inserted so far in this phase and re-raises as LoadError
    -- never leaves a partially-loaded phase committed.
    """
    counts: dict[str, int] = {}
    try:
        counts["source_messages"] = _insert_rows(connection, SOURCE_MESSAGES_SPEC, tables.source_messages)
        counts["cv_tracks"] = _insert_rows(connection, CV_TRACKS_SPEC, tables.cv_tracks)
        counts["fused_tracks"] = _insert_rows(connection, FUSED_TRACKS_SPEC, tables.fused_tracks)
    except LoadError:
        connection.rollback()
        raise
    connection.commit()
    return counts


def load_phase2(connection: sqlite3.Connection, tables: TransformedTables) -> dict[str, int]:
    """Load the remaining 8 tables, in FK-respecting order, after Phase 1
    has committed. Commits only if every insert succeeds; rolls back the
    entire phase on any failure."""
    counts: dict[str, int] = {}
    try:
        counts["cv_detections"] = _insert_rows(connection, CV_DETECTIONS_SPEC, tables.cv_detections)
        counts["cv_track_states"] = _insert_rows(connection, CV_TRACK_STATES_SPEC, tables.cv_track_states)
        counts["cv_track_class_distribution"] = _insert_rows(
            connection, CV_TRACK_CLASS_DISTRIBUTION_SPEC, tables.cv_track_class_distribution
        )
        counts["cv_detection_track_links"] = _insert_rows(
            connection, CV_DETECTION_TRACK_LINKS_SPEC, tables.cv_detection_track_links
        )
        counts["radar_detections"] = _insert_rows(connection, RADAR_DETECTIONS_SPEC, tables.radar_detections)
        counts["fused_track_states"] = _insert_rows(
            connection, FUSED_TRACK_STATES_SPEC, tables.fused_track_states
        )
        counts["fused_track_measurements"] = _insert_rows(
            connection, FUSED_TRACK_MEASUREMENTS_SPEC, tables.fused_track_measurements
        )
        counts["data_quality_issues"] = _insert_rows(
            connection, DATA_QUALITY_ISSUES_SPEC, tables.data_quality_issues
        )
    except LoadError:
        connection.rollback()
        raise
    connection.commit()
    return counts


def load_all(connection: sqlite3.Connection, tables: TransformedTables) -> dict[str, int]:
    """Run Phase 1 then Phase 2 and return the combined per-table row
    counts actually inserted. Requires PRAGMA foreign_keys = ON to
    already be set on `connection` (see src/cuas_etl/database.py) --
    this function does not set it itself."""
    counts = load_phase1(connection, tables)
    counts.update(load_phase2(connection, tables))
    return counts


def database_already_populated(connection: sqlite3.Connection) -> bool:
    """True if source_messages already has at least one row -- used by
    scripts/build_database.py to decide whether a non-rebuild run should
    validate-and-exit instead of attempting to load again (idempotency
    is achieved primarily through deterministic keys, the explicit
    --rebuild workflow, and this check -- not through INSERT OR IGNORE)."""
    row = connection.execute("SELECT COUNT(*) FROM source_messages").fetchone()
    return row[0] > 0
