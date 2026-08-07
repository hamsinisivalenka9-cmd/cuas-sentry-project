"""Transform phase: map extracted protobuf data into rows matching the
reviewed SQLite schema (sql/schema.sql).

This module implements ONLY transformations already justified by Stage
2 (docs/MCAP_INSPECTION.md), Stage 3 (docs/KEY_ANALYSIS.md), Stage 4/5A
(docs/DATABASE_DESIGN.md, docs/SCHEMA_REVIEW.md), and
docs/NORMALIZATION_DECISIONS.md. It never executes SQL and never opens
the source file -- it consumes only the ExtractedMcapData produced by
extract.py.

Every row-producing function returns plain dicts keyed by the exact
SQLite column names in sql/schema.sql, so load.py can insert them
directly without any further field-name translation.

Cleaning rules implemented here (see docs/DATA_CLEANING.md for the full,
evidence-cited matrix):

- Enum fields: always store the raw integer AND resolve the name via the
  field's own protobuf descriptor (resolve_enum_name) -- never a
  handwritten mapping. An unrecognized raw value keeps its integer and
  gets a NULL name, never a fabricated one.
- Timestamps: nanoseconds as Python int throughout, no float conversion.
  Nested google.protobuf.Timestamp fields (frame-level capture_time) are
  converted with seconds * 1_000_000_000 + nanos. Plain int64 timestamp
  fields on TrackState/MeasurementAssociation (create_timestamp,
  last_measurement_timestamp, measurements[].timestamp) are stored as
  MICROSECONDS in the source protobuf, despite the "_ns"-suffixed
  destination column names implying nanoseconds -- this was not assumed,
  it was directly measured: comparing each message's own log_time_ns
  (CONFIRMED nanoseconds) against its last_measurement_timestamp and its
  measurements[].timestamp gives a ratio of exactly 1000.0000000... (to
  8+ significant figures) across every sample checked, and
  create_timestamp (which reflects an earlier point in time -- when the
  track was first created, not the current message's instant) gives a
  ratio consistently close to but not exactly 1000, exactly as expected
  for a microsecond field sampled at a different moment. This module
  therefore multiplies all three fields by 1_000 (integer arithmetic) so
  the stored "_ns" values are genuinely nanoseconds, matching their
  column names. See docs/DATA_CLEANING.md for the full measurement
  record; this is a transform-layer correction, not a schema change --
  the destination columns were always correctly typed INTEGER, they
  simply needed the right conversion applied.
- Presence: every singular nested-message field this module reads
  (bounding_box, parent_object_*_id, capture_time, elevation and its
  sibling wrapped DoubleValues, object_type, lla_pos) is confirmed
  has_presence=True in data/output/mcap_schema_report.json -- HasField()
  is used before reading it, and an unset field becomes SQL NULL, never
  a fabricated zero.
- The ONE approved zero-to-NULL convention: cv_track_states.tracks[].
  last_associated_detection_id == 0 is treated as "not populated" (this
  plain uint64 scalar has no presence tracking, and 0 is not a valid
  detection_id -- this exact convention is what Stage 3/4 already used
  when computing the CV-incorporation figures). This conversion is
  applied ONLY to this one field, nowhere else.
- Booleans: stored as SQLite INTEGER 0/1, always explicit (never NULL
  for a scalar bool field, since protobuf bool has no separate
  presence/None state at proto3 default).
- Strings: stored exactly as decoded, including empty strings -- no
  trimming, no blank-to-NULL conversion anywhere in this module (no
  reviewed rule permits it for any field this module handles).
- Repeated fields stored as JSON (radar cluster_json,
  fused_track_measurements.detection_ids_json): always a valid JSON
  array, "[]" for a genuinely empty repeated field, never NULL.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from google.protobuf.json_format import MessageToDict

from cuas_etl.extract import ExtractedMcapData, ExtractedMessage


# ---------------------------------------------------------------------------
# Generic, reusable helpers
# ---------------------------------------------------------------------------


def resolve_enum_name(field_descriptor: Any, raw_value: int) -> str | None:
    """Resolve an enum field's raw integer to its declared name, using
    the field's own protobuf descriptor -- never a handwritten mapping.

    Returns None if raw_value is not a value declared on this enum type,
    preserving the unknown integer in the *_raw column without inventing
    a name for it.
    """
    entry = field_descriptor.enum_type.values_by_number.get(raw_value)
    return entry.name if entry is not None else None


def timestamp_message_to_ns(timestamp_message: Any) -> int:
    """Convert a google.protobuf.Timestamp-shaped message (.seconds,
    .nanos) to integer nanoseconds. Integer arithmetic only."""
    return timestamp_message.seconds * 1_000_000_000 + timestamp_message.nanos


# proto.tower's plain int64 timestamp fields (TrackState.create_timestamp,
# TrackState.last_measurement_timestamp, MeasurementAssociation.timestamp)
# are MICROSECONDS since epoch, empirically confirmed (see module
# docstring) by comparing them against each message's own
# CONFIRMED-nanosecond log_time_ns. This constant makes that conversion
# explicit and gives future readers one place to find the evidence
# reference instead of a bare "* 1000" scattered through the code.
MICROSECONDS_TO_NANOSECONDS = 1_000


def microsecond_timestamp_to_ns(raw_microseconds: int) -> int:
    """Convert a proto.tower plain-int64 microsecond timestamp to
    nanoseconds. Integer arithmetic only -- see MICROSECONDS_TO_NANOSECONDS."""
    return raw_microseconds * MICROSECONDS_TO_NANOSECONDS


def frame_capture_time_ns(frame: Any) -> int | None:
    """capture_time is a singular nested Timestamp message at the top of
    CVDetectionFrame/CVTrackFrame/RadarFrame, CONFIRMED has_presence=True
    for all three (data/output/mcap_schema_report.json). Returns None if
    unset on this particular frame."""
    if not frame.HasField("capture_time"):
        return None
    return timestamp_message_to_ns(frame.capture_time)


def json_array(values: Iterable) -> str:
    """Deterministic JSON array serialization for a repeated scalar
    field. Always a valid JSON array -- "[]" for a genuinely empty
    repeated field, never NULL, since an empty repeated field is a
    distinguishable state from an unset/NULL field."""
    return json.dumps(list(values), separators=(",", ":"), ensure_ascii=True)


def cluster_json(cluster_members: Iterable) -> str:
    """Serialize RadarDetection.cluster[] (a repeated, self-referential
    message field, CONFIRMED always empty in this file) as a compact
    JSON array. Uses protobuf's own MessageToDict for each member,
    rather than a handwritten serializer, so any field actually present
    on a cluster member is faithfully represented if this field is ever
    populated in a future file. Behavior for a populated cluster is
    covered by a synthetic unit test (tests/test_transform.py), since no
    real example exists in this file to derive it from."""
    members = [
        MessageToDict(member, preserving_proto_field_name=True)
        for member in cluster_members
    ]
    return json.dumps(members, separators=(",", ":"), ensure_ascii=True)


def _lookup_class_distribution_confidence(track: Any) -> float | None:
    """Find the class_distribution entry whose classification matches
    this track's own object_class, and return its probability_score.
    Returns None if class_distribution is empty or has no matching
    entry -- never fabricated (docs/SCHEMA_REVIEW.md finding F5)."""
    for entry in track.class_distribution:
        if entry.classification == track.object_class:
            return entry.probability_score
    return None


# ---------------------------------------------------------------------------
# source_messages
# ---------------------------------------------------------------------------


def transform_source_messages(extracted: ExtractedMcapData) -> list[dict]:
    """One row per raw MCAP message, across all four topics, ordered by
    the deterministic source_message_id assigned in extract.py."""
    all_messages: list[ExtractedMessage] = (
        extracted.cv_detections
        + extracted.cv_tracks
        + extracted.radar_detections
        + extracted.track_states
    )
    all_messages.sort(key=lambda m: m.envelope.source_message_id)
    return [
        {
            "source_message_id": m.envelope.source_message_id,
            "channel_id": m.envelope.channel_id,
            "topic": m.envelope.topic,
            "schema_id": m.envelope.schema_id,
            "sequence": m.envelope.sequence,
            "log_time_ns": m.envelope.log_time_ns,
            "publish_time_ns": m.envelope.publish_time_ns,
        }
        for m in all_messages
    ]


# ---------------------------------------------------------------------------
# cv_detections
# ---------------------------------------------------------------------------


def transform_cv_detections(extracted: ExtractedMcapData) -> list[dict]:
    """One row per CVDetectionFrame.detections[] element."""
    rows: list[dict] = []
    for msg in extracted.cv_detections:
        frame = msg.decoded
        capture_time_ns = frame_capture_time_ns(frame)
        for detection in frame.detections:
            fields = detection.DESCRIPTOR.fields_by_name
            parent_id = (
                detection.parent_object_detection_id.value
                if detection.HasField("parent_object_detection_id")
                else None
            )
            bbox_present = detection.HasField("bounding_box")
            rows.append({
                "detection_id": detection.detection_id,
                "detection_uid": detection.detection_uid,
                "source_message_id": msg.envelope.source_message_id,
                "capture_time_ns": capture_time_ns,
                "class_name": detection.class_name,
                "object_class_raw": detection.object_class,
                "object_class_name": resolve_enum_name(fields["object_class"], detection.object_class),
                "bbox_left": detection.bounding_box.left if bbox_present else None,
                "bbox_top": detection.bounding_box.top if bbox_present else None,
                "bbox_right": detection.bounding_box.right if bbox_present else None,
                "bbox_bottom": detection.bounding_box.bottom if bbox_present else None,
                "score": detection.score,
                "semantic_confidence_raw": detection.semantic_confidence,
                "semantic_confidence_name": resolve_enum_name(
                    fields["semantic_confidence"], detection.semantic_confidence
                ),
                "focus_quality_raw": detection.focus_quality,
                "focus_quality_name": resolve_enum_name(fields["focus_quality"], detection.focus_quality),
                "focus_score": detection.focus_score.value if detection.HasField("focus_score") else None,
                "sharpness": detection.sharpness.value if detection.HasField("sharpness") else None,
                "detector_index": detection.detector_index,
                "disposition_raw": detection.disposition,
                "disposition_name": resolve_enum_name(fields["disposition"], detection.disposition),
                "motion_state_raw": detection.motion_state,
                "motion_state_name": resolve_enum_name(fields["motion_state"], detection.motion_state),
                "parent_object_detection_id": parent_id,
            })
    return rows


# ---------------------------------------------------------------------------
# cv_tracks (Phase 1 identity extraction) + cv_track_states
# ---------------------------------------------------------------------------


def extract_cv_track_identities(extracted: ExtractedMcapData) -> list[dict]:
    """One row per DISTINCT persistent CV track_id, in first-seen order
    (Phase 1 identity extraction -- docs/DATABASE_DESIGN.md Section
    5.12). track_id alone determines the final table contents
    regardless of traversal order, since this table has no other column,
    but a fixed traversal order is still used for reproducibility."""
    seen: set[int] = set()
    ordered_ids: list[int] = []
    for msg in extracted.cv_tracks:
        for track in msg.decoded.tracks:
            if track.track_id not in seen:
                seen.add(track.track_id)
                ordered_ids.append(track.track_id)
    return [{"track_id": track_id} for track_id in ordered_ids]


def transform_cv_track_states(extracted: ExtractedMcapData) -> list[dict]:
    """One row per CVTrackFrame.tracks[] element -- every restatement of
    a track across every frame it appeared in. History is never
    deduplicated here."""
    rows: list[dict] = []
    cv_track_state_id = 1
    for msg in extracted.cv_tracks:
        frame = msg.decoded
        capture_time_ns = frame_capture_time_ns(frame)
        for track in frame.tracks:
            fields = track.DESCRIPTOR.fields_by_name

            # The ONE approved zero-to-NULL convention in this whole
            # module -- see the module docstring. Applies only here.
            raw_last_assoc = track.last_associated_detection_id
            last_assoc_or_none = raw_last_assoc if raw_last_assoc != 0 else None

            parent_track_id = (
                track.parent_object_track_id.value
                if track.HasField("parent_object_track_id")
                else None
            )
            bbox_present = track.HasField("bounding_box")

            rows.append({
                "cv_track_state_id": cv_track_state_id,
                "source_message_id": msg.envelope.source_message_id,
                "track_id": track.track_id,
                "log_time_ns": msg.envelope.log_time_ns,
                "track_age": track.track_age,
                "status_raw": track.status,
                "status_name": resolve_enum_name(fields["status"], track.status),
                "status_code_raw": track.status_code,
                "status_code_name": resolve_enum_name(fields["status_code"], track.status_code),
                "object_class_raw": track.object_class,
                "object_class_name": resolve_enum_name(fields["object_class"], track.object_class),
                "class_name": track.class_name,
                "bbox_left": track.bounding_box.left if bbox_present else None,
                "bbox_top": track.bounding_box.top if bbox_present else None,
                "bbox_right": track.bounding_box.right if bbox_present else None,
                "bbox_bottom": track.bounding_box.bottom if bbox_present else None,
                "last_associated_detection_id": last_assoc_or_none,
                "num_detection_associations": track.num_detection_associations,
                "object_class_confidence": _lookup_class_distribution_confidence(track),
                "score": track.score,
                "disposition_raw": track.disposition,
                "disposition_name": resolve_enum_name(fields["disposition"], track.disposition),
                "motion_state_raw": track.motion_state,
                "motion_state_name": resolve_enum_name(fields["motion_state"], track.motion_state),
                "is_manual": 1 if track.is_manual else 0,
                "parent_object_track_id": parent_track_id,
                "capture_time_ns": capture_time_ns,
            })
            cv_track_state_id += 1
    return rows


def transform_cv_track_class_distribution(extracted: ExtractedMcapData) -> list[dict]:
    """Preserve every CVTrack.class_distribution[] entry in source order.

    State ids mirror transform_cv_track_states' deterministic traversal;
    child ids are a contiguous one-based sequence in that same traversal.
    Duplicate classifications are intentionally retained.
    """
    rows: list[dict] = []
    cv_track_state_id = 1
    distribution_id = 1
    for msg in extracted.cv_tracks:
        for track in msg.decoded.tracks:
            for source_order, entry in enumerate(track.class_distribution):
                classification_field = entry.DESCRIPTOR.fields_by_name["classification"]
                rows.append({
                    "cv_track_class_distribution_id": distribution_id,
                    "cv_track_state_id": cv_track_state_id,
                    "class_raw": entry.classification,
                    "class_name": resolve_enum_name(classification_field, entry.classification),
                    "probability_score": entry.probability_score,
                    "source_order": source_order,
                })
                distribution_id += 1
            cv_track_state_id += 1
    return rows


# ---------------------------------------------------------------------------
# cv_detection_track_links (derived bridge table, deduplicated)
# ---------------------------------------------------------------------------


def derive_cv_detection_track_links(
    cv_track_state_rows: list[dict],
    valid_detection_ids: set[int],
) -> tuple[list[dict], list[dict]]:
    """Derive the deduplicated detection<->track bridge rows from the raw
    cv_track_states rows (docs/DATABASE_DESIGN.md Section 5.5): one row
    per DISTINCT (detection_id, track_id) pair, excluding any pair whose
    detection_id does not exist in cv_detections.

    Returns (link_rows, orphan_issue_rows), both in deterministic
    (detection_id, track_id) order. orphan_issue_rows still needs
    issue_id and detected_at_utc filled in by the caller (transform_all)
    before it is a complete data_quality_issues row.
    """
    first_seen_log_time: dict[tuple[int, int], int] = {}
    for row in cv_track_state_rows:
        detection_id = row["last_associated_detection_id"]
        if detection_id is None:
            continue
        pair = (detection_id, row["track_id"])
        log_time = row["log_time_ns"]
        if pair not in first_seen_log_time or log_time < first_seen_log_time[pair]:
            first_seen_log_time[pair] = log_time

    valid_pairs = sorted(
        (pair for pair in first_seen_log_time if pair[0] in valid_detection_ids)
    )
    orphan_pairs = sorted(
        (pair for pair in first_seen_log_time if pair[0] not in valid_detection_ids)
    )

    link_rows = [
        {
            "detection_id": detection_id,
            "track_id": track_id,
            "first_observed_log_time_ns": first_seen_log_time[(detection_id, track_id)],
        }
        for detection_id, track_id in valid_pairs
    ]

    orphan_issue_rows = [
        {
            "issue_type": "orphaned_detection_reference",
            "severity": "warning",
            "related_table": "cv_detection_track_links",
            "related_id": f"detection_id={detection_id},track_id={track_id}",
            "description": (
                f"cv_track_states referenced detection_id={detection_id} via "
                f"last_associated_detection_id (track_id={track_id}), but no "
                "matching row exists in cv_detections. The cv_track_states "
                "row is preserved with the raw value; only this bridge row "
                "is omitted."
            ),
        }
        for detection_id, track_id in orphan_pairs
    ]

    return link_rows, orphan_issue_rows


# ---------------------------------------------------------------------------
# radar_detections
# ---------------------------------------------------------------------------


def transform_radar_detections(extracted: ExtractedMcapData) -> list[dict]:
    """One row per RadarFrame.detections[] element."""
    rows: list[dict] = []
    radar_detection_id = 1
    for msg in extracted.radar_detections:
        frame = msg.decoded
        capture_time_ns = frame_capture_time_ns(frame)
        for detection in frame.detections:
            fields = detection.DESCRIPTOR.fields_by_name

            object_type_present = detection.HasField("object_type")
            object_type_class_raw = (
                getattr(detection.object_type, "class") if object_type_present else None
            )
            object_type_class_fd = detection.object_type.DESCRIPTOR.fields_by_name["class"]
            object_type_class_name = (
                resolve_enum_name(object_type_class_fd, object_type_class_raw)
                if object_type_class_raw is not None
                else None
            )

            def wrapped(field_name: str) -> float | None:
                return getattr(detection, field_name).value if detection.HasField(field_name) else None

            rows.append({
                "radar_detection_id": radar_detection_id,
                "source_message_id": msg.envelope.source_message_id,
                "capture_time_ns": capture_time_ns,
                "range": detection.range,
                "azimuth_rad": detection.azimuth,
                "elevation_rad": wrapped("elevation"),
                "range_rate": wrapped("range_rate"),
                "return_strength": wrapped("return_strength"),
                "snr": wrapped("snr"),
                "track_id": detection.track_id,
                "object_type_class_raw": object_type_class_raw,
                "object_type_class_name": object_type_class_name,
                "object_class_raw": detection.object_class,
                "object_class_name": resolve_enum_name(fields["object_class"], detection.object_class),
                "filter_type_raw": detection.filter_type,
                "filter_type_name": resolve_enum_name(fields["filter_type"], detection.filter_type),
                "azimuth_sigma": wrapped("azimuth_sigma"),
                "elevation_sigma": wrapped("elevation_sigma"),
                "range_sigma": wrapped("range_sigma"),
                "range_rate_sigma": wrapped("range_rate_sigma"),
                "estimated_width_meters": wrapped("estimated_width_meters"),
                "is_marked": 1 if detection.is_marked else 0,
                "cluster_json": cluster_json(detection.cluster),
            })
            radar_detection_id += 1
    return rows


# ---------------------------------------------------------------------------
# fused_tracks (Phase 1 identity extraction)
# ---------------------------------------------------------------------------


def extract_fused_track_identities(extracted: ExtractedMcapData) -> tuple[list[dict], list[dict]]:
    """One row per DISTINCT persistent fused track_id2, paired with the
    legacy uint64 track_id from its FIRST occurrence. If a later
    occurrence of the same track_id2 pairs with a different legacy
    track_id, that is recorded as a data_quality_issues row, not
    silently overwritten or invented -- Stage 3 confirmed a consistent
    1:1 pairing in this file, so none is expected, but this is not
    assumed.

    Returns (identity_rows, inconsistency_issue_rows).
    """
    legacy_by_fused_id: dict[str, int] = {}
    ordered_fused_ids: list[str] = []
    inconsistency_issues: list[dict] = []

    for msg in extracted.track_states:
        state = msg.decoded
        fused_id = state.track_id2
        legacy_id = state.track_id
        if fused_id not in legacy_by_fused_id:
            legacy_by_fused_id[fused_id] = legacy_id
            ordered_fused_ids.append(fused_id)
        elif legacy_by_fused_id[fused_id] != legacy_id:
            inconsistency_issues.append({
                "issue_type": "inconsistent_legacy_track_id_pairing",
                "severity": "warning",
                "related_table": "fused_tracks",
                "related_id": f"fused_track_id={fused_id}",
                "description": (
                    f"track_id2={fused_id!r} was first paired with legacy "
                    f"track_id={legacy_by_fused_id[fused_id]}, but "
                    f"source_message_id={msg.envelope.source_message_id} pairs "
                    f"it with track_id={legacy_id} instead. The first-observed "
                    "pairing was kept in fused_tracks."
                ),
            })

    identity_rows = [
        {"fused_track_id": fused_id, "legacy_track_id": legacy_by_fused_id[fused_id]}
        for fused_id in ordered_fused_ids
    ]
    return identity_rows, inconsistency_issues


# ---------------------------------------------------------------------------
# fused_track_states + fused_track_measurements
# (produced together so fused_track_measurement rows can reference the
# exact fused_track_state_id assigned to their parent state row)
# ---------------------------------------------------------------------------


def transform_fused_track_states_and_measurements(
    extracted: ExtractedMcapData,
) -> tuple[list[dict], list[dict]]:
    """One state row per track_states message; one measurement row per
    TrackState.measurements[] element on that message."""
    state_rows: list[dict] = []
    measurement_rows: list[dict] = []
    fused_track_state_id = 1
    fused_track_measurement_id = 1

    for msg in extracted.track_states:
        state = msg.decoded
        fields = state.DESCRIPTOR.fields_by_name
        lla_present = state.HasField("lla_pos")

        this_state_id = fused_track_state_id
        state_rows.append({
            "fused_track_state_id": this_state_id,
            "source_message_id": msg.envelope.source_message_id,
            "fused_track_id": state.track_id2,
            "log_time_ns": msg.envelope.log_time_ns,
            "create_timestamp_ns": microsecond_timestamp_to_ns(state.create_timestamp),
            "last_measurement_timestamp_ns": microsecond_timestamp_to_ns(state.last_measurement_timestamp),
            "lla_lat": state.lla_pos.lat if lla_present else None,
            "lla_lon": state.lla_pos.lon if lla_present else None,
            "lla_alt": state.lla_pos.alt if lla_present else None,
            "track_quality": state.track_quality,
            "object_class_raw": state.object_class,
            "object_class_name": resolve_enum_name(fields["object_class"], state.object_class),
            "disposition_raw": state.disposition,
            "disposition_name": resolve_enum_name(fields["disposition"], state.disposition),
            "track_status_raw": state.track_status,
            "track_status_name": resolve_enum_name(fields["track_status"], state.track_status),
            "parent_track_id": state.parent_track_id,
            "object_class_confidence": state.object_class_confidence,
        })
        fused_track_state_id += 1

        for measurement in state.measurements:
            measurement_fields = measurement.DESCRIPTOR.fields_by_name
            measurement_rows.append({
                "fused_track_measurement_id": fused_track_measurement_id,
                "fused_track_state_id": this_state_id,
                "measurement_timestamp_ns": microsecond_timestamp_to_ns(measurement.timestamp),
                "asset_id2": measurement.asset_id2,
                "sensor_id_raw": measurement.sensor_id,
                "sensor_id_name": resolve_enum_name(measurement_fields["sensor_id"], measurement.sensor_id),
                "frame_counter": measurement.frame_counter,
                "sensor_index": measurement.sensor_index,
                "detection_ids_json": json_array(measurement.detection_ids),
            })
            fused_track_measurement_id += 1

    return state_rows, measurement_rows


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------


@dataclass
class TransformedTables:
    """One list of row-dicts per target table, ready for load.py. Every
    dict's keys are exactly the SQLite column names in sql/schema.sql."""

    source_messages: list[dict]
    cv_detections: list[dict]
    cv_tracks: list[dict]
    cv_track_states: list[dict]
    cv_track_class_distribution: list[dict]
    cv_detection_track_links: list[dict]
    radar_detections: list[dict]
    fused_tracks: list[dict]
    fused_track_states: list[dict]
    fused_track_measurements: list[dict]
    data_quality_issues: list[dict]


def transform_all(extracted: ExtractedMcapData, now: datetime | None = None) -> TransformedTables:
    """Run every transformation and assemble the complete set of rows for
    all 11 reviewed tables.

    ``now`` is injectable for deterministic testing; defaults to the real
    current UTC time. This is the ONLY non-deterministic value produced
    anywhere in this module (data_quality_issues.detected_at_utc) -- it
    necessarily reflects real wall-clock ETL run time, not a fact derived
    from the source data, so two independent rebuilds are expected to
    differ in this one column while matching in every other respect (see
    docs/DATA_CLEANING.md and the determinism test in
    tests/test_transform.py).
    """
    if now is None:
        now = datetime.now(timezone.utc)
    detected_at_utc = now.isoformat()

    source_messages = transform_source_messages(extracted)
    cv_detections = transform_cv_detections(extracted)
    cv_tracks = extract_cv_track_identities(extracted)
    cv_track_states = transform_cv_track_states(extracted)
    cv_track_class_distribution = transform_cv_track_class_distribution(extracted)

    valid_detection_ids = {row["detection_id"] for row in cv_detections}
    cv_detection_track_links, orphan_issues = derive_cv_detection_track_links(
        cv_track_states, valid_detection_ids
    )

    radar_detections = transform_radar_detections(extracted)
    fused_tracks, legacy_pairing_issues = extract_fused_track_identities(extracted)
    fused_track_states, fused_track_measurements = transform_fused_track_states_and_measurements(extracted)

    # Deterministic issue ordering: orphan issues (already sorted by
    # (detection_id, track_id) inside derive_cv_detection_track_links),
    # then legacy-pairing issues (already in deterministic message
    # traversal order) -- concatenated in this fixed sequence, not
    # re-sorted by a string representation that could disagree with
    # numeric order.
    data_quality_issues = [
        {**issue, "issue_id": idx, "detected_at_utc": detected_at_utc}
        for idx, issue in enumerate(orphan_issues + legacy_pairing_issues, start=1)
    ]

    return TransformedTables(
        source_messages=source_messages,
        cv_detections=cv_detections,
        cv_tracks=cv_tracks,
        cv_track_states=cv_track_states,
        cv_track_class_distribution=cv_track_class_distribution,
        cv_detection_track_links=cv_detection_track_links,
        radar_detections=radar_detections,
        fused_tracks=fused_tracks,
        fused_track_states=fused_track_states,
        fused_track_measurements=fused_track_measurements,
        data_quality_issues=data_quality_issues,
    )
