#!/usr/bin/env python3
"""Read-only identifier, message-grain, and relationship (key) analysis over
``data/input/sanitized.mcap``, building on the Stage 1 structural report at
``data/output/mcap_schema_report.json``.

This script NEVER modifies the source MCAP file -- it is opened once in
``'rb'`` mode and only read. It does not create a database, schema.sql, or
ETL loaders; it only produces the two reports below plus their tests.

Outputs:
    data/output/key_analysis.json  (machine-readable)
    docs/KEY_ANALYSIS.md           (human-readable)
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcap.reader import make_reader  # noqa: E402
from mcap_protobuf.decoder import DecoderFactory  # noqa: E402

from mcap_inspection.helpers import (  # noqa: E402
    iter_field_occurrences,
    resolve_field_descriptor_chain,
    truncate_sample,
)
from mcap_inspection.key_analysis import (  # noqa: E402
    IdentifierOccurrence,
    check_composite_key_collisions,
    classify_field_grain,
    classify_repetition_expectation,
    compare_identifier_namespaces,
    compute_identifier_field_stats,
    dedupe_detection_track_pairs,
    find_orphans,
)

MCAP_PATH = REPO_ROOT / "data" / "input" / "sanitized.mcap"
STAGE1_REPORT_PATH = REPO_ROOT / "data" / "output" / "mcap_schema_report.json"
JSON_REPORT_PATH = REPO_ROOT / "data" / "output" / "key_analysis.json"
MD_REPORT_PATH = REPO_ROOT / "docs" / "KEY_ANALYSIS.md"

MAX_EXAMPLES = 3


# ---------------------------------------------------------------------------
# Curated identifier fields to deep-dive.
#
# Grounded in the *actual* field paths verified against
# data/output/mcap_schema_report.json (Stage 1). `expected_globally_unique`
# is domain judgment supplied here (data cannot tell us what a field is
# *for*): True for fields meant to identify one raw event exactly once,
# False for fields that are expected to recur (persistent-entity ids,
# reference/FK-shaped fields, categorical/enum-like reference fields).
# ---------------------------------------------------------------------------

CURATED_FIELDS = [
    # cv_detections
    {"topic": "cv_detections", "field_path": "detections.detection_id",
     "concept": "detection_id", "expected_globally_unique": True},
    {"topic": "cv_detections", "field_path": "detections.detection_uid",
     "concept": "detection_uid", "expected_globally_unique": True},
    {"topic": "cv_detections", "field_path": "detections.parent_object_detection_id.value",
     "concept": "parent_detection_id", "expected_globally_unique": False},
    {"topic": "cv_detections", "field_path": "detectors.detector_id",
     "concept": "detector_id", "expected_globally_unique": False},
    {"topic": "cv_detections", "field_path": "metadata.sensor_id",
     "concept": "sensor_id", "expected_globally_unique": False},
    {"topic": "cv_detections", "field_path": "assets.asset_id",
     "concept": "asset_id", "expected_globally_unique": False},
    {"topic": "cv_detections", "field_path": "assets.suppressed_detection_ids",
     "concept": "nested_detection_id_collection", "expected_globally_unique": False},
    # cv_tracks
    {"topic": "cv_tracks", "field_path": "tracks.track_id",
     "concept": "track_id", "expected_globally_unique": False},
    {"topic": "cv_tracks", "field_path": "tracks.last_associated_detection_id",
     "concept": "last_associated_detection_id", "expected_globally_unique": False,
     "structural_hint": "named_reference"},
    {"topic": "cv_tracks", "field_path": "tracks.parent_object_track_id.value",
     "concept": "parent_track_id", "expected_globally_unique": False},
    {"topic": "cv_tracks", "field_path": "trackers.tracker_id",
     "concept": "tracker_id", "expected_globally_unique": False},
    {"topic": "cv_tracks", "field_path": "metadata.sensor_id",
     "concept": "sensor_id", "expected_globally_unique": False},
    {"topic": "cv_tracks", "field_path": "assets.asset_id",
     "concept": "asset_id", "expected_globally_unique": False},
    {"topic": "cv_tracks", "field_path": "assets.suppressed_detection_ids",
     "concept": "nested_detection_id_collection", "expected_globally_unique": False},
    # radar_detections
    {"topic": "radar_detections", "field_path": "detections.track_id",
     "concept": "track_id", "expected_globally_unique": False},
    {"topic": "radar_detections", "field_path": "id",
     "concept": "frame_id", "expected_globally_unique": False},
    {"topic": "radar_detections", "field_path": "asset_id",
     "concept": "asset_id", "expected_globally_unique": False},
    {"topic": "radar_detections", "field_path": "asset_id2",
     "concept": "asset_id", "expected_globally_unique": False},
    {"topic": "radar_detections", "field_path": "metadata.sensor_id",
     "concept": "sensor_id", "expected_globally_unique": False},
    # track_states
    {"topic": "track_states", "field_path": "track_id",
     "concept": "track_id", "expected_globally_unique": False},
    {"topic": "track_states", "field_path": "track_id2",
     "concept": "track_id", "expected_globally_unique": False},
    {"topic": "track_states", "field_path": "parent_track_id",
     "concept": "parent_track_id", "expected_globally_unique": False},
    {"topic": "track_states", "field_path": "target_uid",
     "concept": "target_uid", "expected_globally_unique": False},
    {"topic": "track_states", "field_path": "measurements.asset_id",
     "concept": "asset_id", "expected_globally_unique": False},
    {"topic": "track_states", "field_path": "measurements.asset_id2",
     "concept": "asset_id", "expected_globally_unique": False},
    {"topic": "track_states", "field_path": "measurements.sensor_id",
     "concept": "sensor_id", "expected_globally_unique": False},
    {"topic": "track_states", "field_path": "measurements.detection_ids",
     "concept": "nested_detection_id_collection", "expected_globally_unique": False},
    {"topic": "track_states", "field_path": "sensors.asset_id",
     "concept": "asset_id", "expected_globally_unique": False},
    {"topic": "track_states", "field_path": "sensors.asset_id2",
     "concept": "asset_id", "expected_globally_unique": False},
    {"topic": "track_states", "field_path": "sensors.sensor_id",
     "concept": "sensor_id", "expected_globally_unique": False},
    {"topic": "track_states", "field_path": "track_identity_matches.matched_track_id",
     "concept": "track_id", "expected_globally_unique": False},
    {"topic": "track_states", "field_path": "track_identity_matches.matched_track_id2",
     "concept": "track_id", "expected_globally_unique": False},
]

# Concepts the assignment brief names that must be checked for existence,
# with keywords used to search the actual Stage 1 field catalog. Any concept
# with no keyword hits is reported as genuinely absent -- not assumed.
CONCEPT_DISCOVERY_KEYWORDS = {
    "camera_id": ["camera_id", "cameraid"],
    "measurement_id": ["measurement_id", "measurementid"],
    "sensor_id": ["sensor_id"],
    "asset_id": ["asset_id"],
    "parent_track_id": ["parent_track_id", "parent_object_track_id"],
    "nested_detection_id_collection": ["detection_id", "detection_ids"],
}


# ---------------------------------------------------------------------------
# Stage 1 report loading
# ---------------------------------------------------------------------------


def load_stage1_report() -> dict:
    if not STAGE1_REPORT_PATH.exists():
        raise FileNotFoundError(
            f"Stage 1 report not found at {STAGE1_REPORT_PATH}; run "
            "scripts/inspect_mcap.py first."
        )
    return json.loads(STAGE1_REPORT_PATH.read_text())


def discover_concepts(stage1: dict) -> dict:
    all_paths_by_topic = {
        ch["topic"]: [f["full_path"] for f in ch["field_catalog"]] for ch in stage1["channels"]
    }
    results = {}
    for concept, keywords in CONCEPT_DISCOVERY_KEYWORDS.items():
        matches = []
        for topic, paths in all_paths_by_topic.items():
            for p in paths:
                leaf = p.split(".")[-1].lower()
                if any(kw in leaf for kw in keywords):
                    matches.append(f"{topic}.{p}")
        results[concept] = {
            "found": len(matches) > 0,
            "matching_field_paths": sorted(set(matches)),
        }
    # Explicit call-outs the assignment brief names that are NOT present.
    results["camera_id"]["note"] = (
        "No field literally named 'camera_id' exists in any of the four schemas. "
        "Closest real fields: metadata.camera_name.value (google.protobuf.StringValue, "
        "string) and metadata.sensor_index (uint32) in cv_tracks/cv_detections."
    )
    results["measurement_id"]["note"] = (
        "track_states.measurements (proto.tower.MeasurementAssociation) has no field "
        "of its own named 'measurement_id' -- it carries asset_id/asset_id2/sensor_id "
        "plus a nested repeated 'detection_ids' collection, but no self-identifying id."
    )
    return results


def message_structure_by_topic(stage1: dict) -> dict:
    return {ch["topic"]: ch["message_structure"] for ch in stage1["channels"]}


def repeated_top_level_fields_by_topic(stage1: dict) -> dict:
    result = {}
    for ch in stage1["channels"]:
        result[ch["topic"]] = {
            f["field_name"] for f in ch["field_catalog"] if f["depth"] == 0 and f["repeated"]
        }
    return result


def scalar_or_enum_type(stage1: dict, topic: str, field_path: str) -> str:
    for ch in stage1["channels"]:
        if ch["topic"] != topic:
            continue
        for f in ch["field_catalog"]:
            if f["full_path"] == field_path:
                return f["scalar_type"] or f["enum_type"] or f["message_type"] or "unknown"
    return "unknown"


def containing_message_and_parent(stage1: dict, topic: str, field_path: str) -> dict:
    segments = field_path.split(".")
    parent_path = ".".join(segments[:-1])
    for ch in stage1["channels"]:
        if ch["topic"] != topic:
            continue
        schema_name = ch["schema_name"]
        if not parent_path:
            return {"repeated_parent_path": None, "containing_message": schema_name}
        for f in ch["field_catalog"]:
            if f["full_path"] == parent_path:
                return {
                    "repeated_parent_path": parent_path,
                    "containing_message": f["message_type"] or schema_name,
                }
    return {"repeated_parent_path": parent_path or None, "containing_message": "unknown"}


# ---------------------------------------------------------------------------
# Full decode pass: collect envelope records + curated field occurrences +
# the specific joined tuples needed for detection<->track and persistent-
# entity analysis.
# ---------------------------------------------------------------------------


# These two fields need "parent entity" context (the enclosing track's own
# track_id) that the generic per-field chain walk below does not carry, so
# they are collected via the dedicated cv_track_rows extraction instead
# (see the re-derivation step at the end of run_full_pass) and skipped here.
PARENT_DERIVED_KEYS = {
    ("cv_tracks", "tracks.last_associated_detection_id"),
    ("cv_tracks", "tracks.parent_object_track_id.value"),
}


def run_full_pass(stage1: dict) -> dict:
    descriptors: dict = {}
    occurrences_by_field: dict = defaultdict(list)
    envelope_records: list = []

    cv_track_rows: list = []       # (track_id, last_associated_detection_id, parent_track_id, log_time, msg_idx)
    cv_detection_rows: list = []   # (detection_id, detection_uid, log_time, msg_idx)
    track_state_rows: list = []    # (track_id, track_id2, log_time, msg_idx)
    radar_detection_rows: list = []  # (track_id, log_time, msg_idx)

    field_chains: dict = {}  # (topic, field_path) -> resolved descriptor chain

    with open(MCAP_PATH, "rb") as f:
        reader = make_reader(f, decoder_factories=[DecoderFactory()])
        source_message_index = 0
        for schema, channel, message, decoded in reader.iter_decoded_messages():
            topic = channel.topic
            if topic not in descriptors:
                descriptors[topic] = decoded.DESCRIPTOR
                for cf in CURATED_FIELDS:
                    if cf["topic"] != topic:
                        continue
                    key = (topic, cf["field_path"])
                    if key in PARENT_DERIVED_KEYS:
                        continue
                    try:
                        field_chains[key] = resolve_field_descriptor_chain(
                            decoded.DESCRIPTOR, cf["field_path"]
                        )
                    except (ValueError, KeyError):
                        field_chains[key] = None

            envelope_records.append({
                "channel_id": channel.id,
                "topic": topic,
                "schema_id": schema.id if schema else None,
                "sequence": message.sequence,
                "log_time": message.log_time,
                "publish_time": message.publish_time,
                "source_message_index": source_message_index,
            })

            for cf in CURATED_FIELDS:
                if cf["topic"] != topic:
                    continue
                key = (topic, cf["field_path"])
                chain = field_chains.get(key)
                if chain is None:
                    continue
                try:
                    occs = list(iter_field_occurrences(decoded, chain))
                except Exception:
                    occs = []
                for has, value in occs:
                    occurrences_by_field[key].append(
                        IdentifierOccurrence(
                            value=value,
                            has_field=has,
                            message_index=source_message_index,
                            log_time=message.log_time,
                        )
                    )

            if topic == "cv_tracks":
                for t in decoded.tracks:
                    parent_id = (
                        t.parent_object_track_id.value
                        if t.HasField("parent_object_track_id")
                        else None
                    )
                    cv_track_rows.append((
                        t.track_id, t.last_associated_detection_id, parent_id,
                        message.log_time, source_message_index,
                    ))
            if topic == "cv_detections":
                for d in decoded.detections:
                    cv_detection_rows.append((
                        d.detection_id, d.detection_uid, message.log_time, source_message_index,
                    ))
            if topic == "track_states":
                track_state_rows.append((
                    decoded.track_id, decoded.track_id2, message.log_time, source_message_index,
                ))
            if topic == "radar_detections":
                for d in decoded.detections:
                    radar_detection_rows.append((d.track_id, message.log_time, source_message_index))

            source_message_index += 1

    # Re-derive parent_key for the two fields where it matters, from the
    # directly-collected cv_track_rows (simpler & more reliable than
    # threading parent context through the generic chain walk above).
    la_det_key = ("cv_tracks", "tracks.last_associated_detection_id")
    occurrences_by_field[la_det_key] = [
        IdentifierOccurrence(
            value=last_det, has_field=True, message_index=msg_idx,
            log_time=log_time, parent_key=track_id,
        )
        for (track_id, last_det, _parent, log_time, msg_idx) in cv_track_rows
        if last_det != 0
    ] + [
        IdentifierOccurrence(value=0, has_field=False, message_index=msg_idx, log_time=log_time)
        for (track_id, last_det, _parent, log_time, msg_idx) in cv_track_rows
        if last_det == 0
    ]
    parent_trk_key = ("cv_tracks", "tracks.parent_object_track_id.value")
    occurrences_by_field[parent_trk_key] = [
        IdentifierOccurrence(
            value=parent, has_field=True, message_index=msg_idx,
            log_time=log_time, parent_key=track_id,
        )
        for (track_id, _last_det, parent, log_time, msg_idx) in cv_track_rows
        if parent is not None
    ] + [
        IdentifierOccurrence(value=None, has_field=False, message_index=msg_idx, log_time=log_time)
        for (track_id, _last_det, parent, log_time, msg_idx) in cv_track_rows
        if parent is None
    ]

    return {
        "occurrences_by_field": occurrences_by_field,
        "envelope_records": envelope_records,
        "cv_track_rows": cv_track_rows,
        "cv_detection_rows": cv_detection_rows,
        "track_state_rows": track_state_rows,
        "radar_detection_rows": radar_detection_rows,
    }


# ---------------------------------------------------------------------------
# 1-15 point per-field identifier analysis
# ---------------------------------------------------------------------------


def build_identifier_field_analysis(stage1: dict, pass_data: dict) -> list:
    structures = message_structure_by_topic(stage1)
    repeated_fields = repeated_top_level_fields_by_topic(stage1)
    results = []
    for cf in CURATED_FIELDS:
        topic, path = cf["topic"], cf["field_path"]
        occs = pass_data["occurrences_by_field"].get((topic, path), [])
        stats = compute_identifier_field_stats(occs)
        grain = classify_field_grain(path, structures[topic], repeated_fields.get(topic))
        repetition = classify_repetition_expectation(
            grain, stats, cf["expected_globally_unique"]
        )
        parent_info = containing_message_and_parent(stage1, topic, path)
        results.append({
            "topic": topic,
            "field_path": path,
            "concept": cf["concept"],
            "protobuf_type": scalar_or_enum_type(stage1, topic, path),
            "containing_message": parent_info["containing_message"],
            "repeated_parent_path": parent_info["repeated_parent_path"],
            "grain": grain,
            "total_examined": stats.total_examined,
            "populated_count": stats.populated,
            "null_or_unset_count": stats.null_or_unset,
            "blank_string_count": stats.blank_string,
            "distinct_count": stats.distinct,
            "repeated_occurrence_count": stats.repeated_occurrence_count,
            "repeated_within_message_count": stats.within_message_repeat_count,
            "repeated_across_message_count": stats.across_message_repeat_count,
            "repeated_across_timestamp_count": stats.across_timestamp_repeat_count,
            "repeated_across_parent_entity_count": stats.across_parent_repeat_count,
            "uniqueness_ratio": (
                round(stats.uniqueness_ratio, 4) if stats.uniqueness_ratio is not None else None
            ),
            "min_occurrences_per_value": stats.min_occurrences,
            "max_occurrences_per_value": stats.max_occurrences,
            "repetition_expected": repetition,
            "expected_globally_unique": cf["expected_globally_unique"],
            "example_repeated_values": [
                truncate_sample(v) for v in stats.example_repeated_values[:MAX_EXAMPLES]
            ],
        })
    return results


# ---------------------------------------------------------------------------
# Persistent entity vs update analysis
# ---------------------------------------------------------------------------


def _analyze_persistent_ids(rows: list, id_idx: int, log_time_idx: int, msg_idx_idx: int, label: str) -> dict:
    per_id_messages: dict = defaultdict(set)
    per_id_timestamps: dict = defaultdict(list)
    for row in rows:
        id_val = row[id_idx]
        if id_val in (None, 0, ""):
            continue
        per_id_messages[id_val].add(row[msg_idx_idx])
        per_id_timestamps[id_val].append(row[log_time_idx])

    distinct_ids = len(per_id_messages)
    messages_per_id = [len(v) for v in per_id_messages.values()]
    updates_per_id = [len(v) for v in per_id_timestamps.values()]
    ids_with_same_timestamp_collision = sum(
        1 for ts in per_id_timestamps.values() if len(ts) != len(set(ts))
    )
    all_timestamps = [t for ts in per_id_timestamps.values() for t in ts]

    def _summary(values):
        if not values:
            return {"min": None, "max": None, "avg": None}
        return {"min": min(values), "max": max(values), "avg": round(sum(values) / len(values), 3)}

    return {
        "label": label,
        "distinct_persistent_ids": distinct_ids,
        "messages_per_id": _summary(messages_per_id),
        "updates_per_id": _summary(updates_per_id),
        "first_observed_log_time": min(all_timestamps) if all_timestamps else None,
        "last_observed_log_time": max(all_timestamps) if all_timestamps else None,
        "ids_with_same_timestamp_collision": ids_with_same_timestamp_collision,
        "requires_composite_or_surrogate_key": (
            "yes -- this id alone repeats across many rows; "
            + (
                "even (id, log_time) is not collision-free, a surrogate key is recommended"
                if ids_with_same_timestamp_collision > 0
                else "(id, log_time) appears collision-free in this dataset, but a surrogate "
                "key is still the safer general recommendation"
            )
        ),
    }


def build_persistent_entity_analysis(pass_data: dict) -> list:
    return [
        _analyze_persistent_ids(pass_data["cv_track_rows"], 0, 3, 4, "cv_tracks.tracks.track_id"),
        _analyze_persistent_ids(pass_data["track_state_rows"], 1, 2, 3, "track_states.track_id2"),
        _analyze_persistent_ids(
            pass_data["radar_detection_rows"], 0, 1, 2, "radar_detections.detections.track_id"
        ),
    ]


# ---------------------------------------------------------------------------
# CV detection <-> track relationship analysis
# ---------------------------------------------------------------------------


def build_detection_track_relationship(pass_data: dict) -> dict:
    existing_detection_ids = {
        d_id for (d_id, _uid, _lt, _mi) in pass_data["cv_detection_rows"] if d_id != 0
    }
    referenced = {
        last_det
        for (_tid, last_det, _parent, _lt, _mi) in pass_data["cv_track_rows"]
        if last_det != 0
    }
    orphan_analysis = find_orphans(referenced, existing_detection_ids)

    pairs = [
        (last_det, track_id)
        for (track_id, last_det, _parent, _lt, _mi) in pass_data["cv_track_rows"]
        if last_det != 0
    ]
    pair_analysis = dedupe_detection_track_pairs(pairs)

    never_referenced = existing_detection_ids - referenced

    return {
        "distinct_cv_detections_existing": len(existing_detection_ids),
        "distinct_cv_detections_referenced_by_tracks": len(referenced),
        "orphaned_references": orphan_analysis["orphaned_reference_count"],
        "orphaned_reference_examples": [truncate_sample(v) for v in orphan_analysis["orphaned_examples"]],
        "never_referenced_detection_count": len(never_referenced),
        "never_referenced_examples": [
            truncate_sample(v) for v in sorted(never_referenced)[:MAX_EXAMPLES]
        ],
        "distinct_detection_to_track_pairs": pair_analysis["distinct_pairs"],
        "pairs_repeated_across_track_updates": pair_analysis["repeated_pair_count"],
        "repeated_pair_extra_occurrences": pair_analysis["repeated_pair_extra_occurrences"],
        "detections_linked_to_multiple_persistent_tracks": pair_analysis["conflicting_detection_count"],
        "conflicting_examples": [
            {"detection_id": truncate_sample(d), "track_ids": [truncate_sample(t) for t in ts]}
            for d, ts in pair_analysis["conflicting_examples"]
        ],
        "detections_linked_to_exactly_one_track": pair_analysis["single_persistent_track_detection_count"],
        "grain_and_uniqueness_recommendation": (
            "A future detection<->track bridge table's natural grain is one row per "
            "(detection_id, persistent track_id) pair -- i.e. UNIQUE(detection_id, track_id) -- "
            "NOT one row per cv_tracks message, since the same pair is legitimately restated "
            "on every track update. "
            + (
                f"{pair_analysis['conflicting_detection_count']} detection(s) were observed "
                "linked to more than one distinct track id; these need explicit handling "
                "(e.g. keep the most recent association, or model as N:M) rather than a naive "
                "UNIQUE(detection_id) constraint."
                if pair_analysis["conflicting_detection_count"]
                else "No detections were observed linked to more than one distinct track id in "
                "this dataset, so UNIQUE(detection_id) in the bridge table is plausible but "
                "should still be validated against future data before being enforced."
            )
        ),
    }


# ---------------------------------------------------------------------------
# Identifier namespace verdicts
# ---------------------------------------------------------------------------


def build_namespace_verdicts(stage1: dict, pass_data: dict) -> list:
    occ = pass_data["occurrences_by_field"]

    def populated_values(topic, path):
        return [o.value for o in occ.get((topic, path), []) if o.has_field is not False]

    def ptype(topic, path):
        return scalar_or_enum_type(stage1, topic, path)

    pairs = [
        {
            "pair_label": "cv_detections.detections.detection_id <-> cv_tracks.tracks.last_associated_detection_id",
            "a": ("cv_detections", "detections.detection_id"),
            "b": ("cv_tracks", "tracks.last_associated_detection_id"),
            "structural_hint": "named_reference",
        },
        {
            "pair_label": "cv_tracks.tracks.track_id <-> track_states.track_id2",
            "a": ("cv_tracks", "tracks.track_id"),
            "b": ("track_states", "track_id2"),
            "structural_hint": None,
        },
        {
            "pair_label": "track_states.track_id2 <-> radar_detections.detections.track_id",
            "a": ("track_states", "track_id2"),
            "b": ("radar_detections", "detections.track_id"),
            "structural_hint": None,
        },
        {
            "pair_label": "cv_tracks.tracks.track_id <-> radar_detections.detections.track_id",
            "a": ("cv_tracks", "tracks.track_id"),
            "b": ("radar_detections", "detections.track_id"),
            "structural_hint": None,
        },
        {
            "pair_label": "track_states.measurements.asset_id2 <-> track_states.sensors.asset_id2",
            "a": ("track_states", "measurements.asset_id2"),
            "b": ("track_states", "sensors.asset_id2"),
            "structural_hint": None,
        },
        {
            "pair_label": "track_states.measurements.asset_id2 <-> radar_detections.asset_id2",
            "a": ("track_states", "measurements.asset_id2"),
            "b": ("radar_detections", "asset_id2"),
            "structural_hint": None,
        },
        {
            "pair_label": "track_states.measurements.sensor_id <-> track_states.sensors.sensor_id",
            "a": ("track_states", "measurements.sensor_id"),
            "b": ("track_states", "sensors.sensor_id"),
            "structural_hint": None,
        },
        {
            "pair_label": "cv_tracks.tracks.parent_object_track_id.value <-> cv_tracks.tracks.track_id",
            "a": ("cv_tracks", "tracks.parent_object_track_id.value"),
            "b": ("cv_tracks", "tracks.track_id"),
            "structural_hint": "named_reference",
        },
    ]

    results = []
    for p in pairs:
        topic_a, path_a = p["a"]
        topic_b, path_b = p["b"]
        cmp = compare_identifier_namespaces(
            values_a=populated_values(topic_a, path_a),
            type_a=ptype(topic_a, path_a),
            values_b=populated_values(topic_b, path_b),
            type_b=ptype(topic_b, path_b),
            structural_hint=p["structural_hint"],
        )
        cmp["pair_label"] = p["pair_label"]
        cmp["side_a"] = f"{topic_a}.{path_a}"
        cmp["side_b"] = f"{topic_b}.{path_b}"
        results.append(cmp)
    return results


# ---------------------------------------------------------------------------
# Source MCAP message identity
# ---------------------------------------------------------------------------


def build_source_message_identity(pass_data: dict) -> dict:
    records = pass_data["envelope_records"]
    candidates = [
        ("topic", "sequence"),
        ("channel_id", "sequence"),
        ("topic", "log_time", "sequence"),
        ("channel_id", "log_time", "sequence"),
        ("channel_id", "log_time"),  # supplementary: sequence is degenerate (Stage 1 finding)
        ("source_message_index",),
    ]
    results = [check_composite_key_collisions(records, key) for key in candidates]

    collision_free_natural = [
        r for r in results if r["collision_free"] and r["key_fields"] != ["source_message_index"]
    ]
    if collision_free_natural:
        best = min(collision_free_natural, key=lambda r: len(r["key_fields"]))
        recommendation = (
            f"A collision-free natural/composite key exists: {best['key_fields']}. "
            "It can be used directly, though a surrogate key is still reasonable for "
            "downstream ergonomics."
        )
    else:
        recommendation = (
            "No tested natural/composite key (topic+sequence, channel_id+sequence, "
            "with/without log_time) is collision-free across the whole file -- MCAP "
            "'sequence' is degenerate (observed as constant/zero per Stage 1) and does not "
            "disambiguate messages. A generated surrogate source_message_id (e.g. the "
            "monotonic read-order index used in this analysis) is the safer recommendation "
            "for uniquely identifying a source MCAP message row."
        )

    return {
        "candidates_tested": results,
        "recommendation": recommendation,
        "unique_constraint_recommendation": (
            "Recommend a UNIQUE constraint on the surrogate source_message_id (or, if a "
            "natural composite key above is collision-free, on that composite instead). "
            "channel_id, log_time, and publish_time should be retained as provenance "
            "columns but not relied upon alone for uniqueness."
        ),
    }


# ---------------------------------------------------------------------------
# Candidate key recommendations synthesis
# ---------------------------------------------------------------------------


def build_candidate_key_recommendations(
    identifier_analysis: list, detection_track: dict, source_identity: dict
) -> list:
    recs = []

    det_id_row = next(
        r for r in identifier_analysis
        if r["topic"] == "cv_detections" and r["field_path"] == "detections.detection_id"
    )
    recs.append({
        "entity_concept": "cv_detections.detections (one raw CV detection event)",
        "status": (
            "confirmed_natural_key" if det_id_row["uniqueness_ratio"] == 1.0
            else "candidate_natural_key_requires_validation"
        ),
        "detail": (
            f"detection_id is {det_id_row['uniqueness_ratio']} unique across "
            f"{det_id_row['populated_count']} observed detections in this file. Note this is "
            "still only a snapshot of one sanitized file, not a cross-file guarantee."
        ),
        "recommended_unique_constraint": "UNIQUE(detection_id)",
    })

    track_row = next(
        r for r in identifier_analysis
        if r["topic"] == "cv_tracks" and r["field_path"] == "tracks.track_id"
    )
    recs.append({
        "entity_concept": "persistent CV track (conceptual entity, not a stored row)",
        "status": "candidate_natural_key_requires_validation",
        "detail": (
            f"track_id ({track_row['distinct_count']} distinct values) repeats "
            f"{track_row['repeated_occurrence_count']} times across messages with "
            f"{track_row['repeated_within_message_count']} within-message duplicates -- "
            "consistent with a persistent entity restated every batch frame, not with "
            "track_id identifying a single row. A dedicated persistent_tracks table (future "
            "work) could use track_id as its natural key IF it is confirmed stable/unique "
            "per physical object across the full deployment, which this single-file snapshot "
            "cannot confirm alone."
        ),
        "recommended_unique_constraint": "none at the cv_tracks row grain; UNIQUE(track_id) only if/when materialized into a persistent_tracks table",
    })

    recs.append({
        "entity_concept": "cv_tracks.tracks row (one track's state within one batch frame)",
        "status": "candidate_composite_key",
        "detail": "Row grain is (source_message_id, track_id) -- track_id alone is not unique at this grain.",
        "recommended_unique_constraint": "UNIQUE(source_message_id, track_id)",
    })

    recs.append({
        "entity_concept": "track_states row (one fused-track state/update)",
        "status": "candidate_composite_key",
        "detail": (
            "track_id2 (string, active) and track_id (uint64, legacy) are both fully "
            "populated with identical distinct counts and repeat across many state rows -- "
            "one row per state, not per entity. A (track_id, log_time) composite was tested "
            "and its collision behavior is reported in persistent_entity_analysis."
        ),
        "recommended_unique_constraint": "recommended_surrogate_key (state_id) preferred over a natural composite, given observed timestamp-collision risk -- see persistent_entity_analysis",
    })

    recs.append({
        "entity_concept": "source MCAP message (envelope row)",
        "status": "recommended_surrogate_key",
        "detail": source_identity["recommendation"],
        "recommended_unique_constraint": "UNIQUE(source_message_id surrogate)",
    })

    recs.append({
        "entity_concept": "cv_detections.detections.detection_id -> cv_tracks.tracks.last_associated_detection_id",
        "status": "candidate_foreign_key",
        "detail": (
            f"{detection_track['orphaned_references']} orphaned reference(s) observed "
            f"(referenced detection_id not present in cv_detections) and "
            f"{detection_track['detections_linked_to_multiple_persistent_tracks']} detection(s) "
            "linked to more than one persistent track. "
            + (
                "Because orphans exist, this should NOT be enforced as a hard FK without "
                "staging/nullable handling for the orphaned rows."
                if detection_track["orphaned_references"]
                else "No orphans observed in this file, but validate against more data before "
                "enforcing as a hard FK."
            )
        ),
        "recommended_unique_constraint": "n/a (bridge table) -- see detection_track_relationship.grain_and_uniqueness_recommendation",
    })

    recs.append({
        "entity_concept": "track_id sharing the same name across cv_tracks / track_states / radar_detections",
        "status": "relationship_should_not_be_enforced_as_fk",
        "detail": (
            "Despite the shared field name, cv_tracks.tracks.track_id, track_states.track_id2, "
            "and radar_detections.detections.track_id show zero observed value overlap (and "
            "cv_tracks.track_id is a different protobuf type, uint64, from the two string "
            "fields). These are different identifier namespaces and must not be joined on name "
            "alone -- see identifier_namespace_verdicts."
        ),
        "recommended_unique_constraint": "n/a",
    })

    recs.append({
        "entity_concept": "track_states.measurements (nested per-state sensor contribution)",
        "status": "relationship_requires_bridge_table",
        "detail": (
            "measurements has no own identifier; it carries a nested repeated "
            "detection_ids collection linking a state row's measurement to one or more CV "
            "detections. This needs a bridge/child table keyed on (state_id, measurement "
            "index, detection_id), not a scalar FK column."
        ),
        "recommended_unique_constraint": "n/a (child/bridge table)",
    })

    recs.append({
        "entity_concept": "sensor_id / asset_id / camera identity fields broadly",
        "status": "relationship_requires_staging_or_nullable_handling",
        "detail": (
            "Most sensor_id/asset_id/camera-adjacent fields observed in this file are always "
            "empty (see Stage 1 risk flags), consistent with sanitization. Any future FK to a "
            "sensors/assets dimension table must be nullable and staged, not assumed populated."
        ),
        "recommended_unique_constraint": "n/a",
    })

    return recs


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_markdown(report: dict) -> str:
    lines = []
    lines.append("# Key / Identifier Analysis")
    lines.append("")
    lines.append(f"Generated: {report['generated_at_utc']}")
    lines.append("")
    lines.append(
        "Read-only analysis built on `scripts/inspect_mcap.py`'s Stage 1 output. The source "
        f"file `{report['source_file']['path']}` was never modified. Field names alone are "
        "never treated as proof of a relationship -- see Identifier namespace verdicts."
    )
    lines.append("")

    lines.append("## Concept discovery (assignment-named concepts vs. actual schema)")
    lines.append("")
    for concept, info in report["concept_discovery"].items():
        lines.append(f"- **{concept}**: found={info['found']}")
        if info.get("note"):
            lines.append(f"  - {info['note']}")
        if info["matching_field_paths"]:
            lines.append(f"  - matches: {', '.join(info['matching_field_paths'][:10])}")
    lines.append("")

    lines.append("## Per-field identifier analysis")
    lines.append("")
    lines.append(
        "| topic | field_path | grain | type | total | populated | null/unset | blank | distinct | "
        "uniq. ratio | within-msg | across-msg | across-ts | across-parent | min/max occ | repetition |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for e in report["identifier_field_analysis"]:
        lines.append(
            f"| `{e['topic']}` | `{e['field_path']}` | {e['grain']} | {e['protobuf_type']} | "
            f"{e['total_examined']} | {e['populated_count']} | {e['null_or_unset_count']} | "
            f"{e['blank_string_count']} | {e['distinct_count']} | {e['uniqueness_ratio']} | "
            f"{e['repeated_within_message_count']} | {e['repeated_across_message_count']} | "
            f"{e['repeated_across_timestamp_count']} | {e['repeated_across_parent_entity_count']} | "
            f"{e['min_occurrences_per_value']}/{e['max_occurrences_per_value']} | {e['repetition_expected']} |"
        )
    lines.append("")

    lines.append("## Persistent entity vs. update analysis")
    lines.append("")
    for pe in report["persistent_entity_analysis"]:
        lines.append(f"### `{pe['label']}`")
        lines.append("")
        lines.append(f"- Distinct persistent IDs: {pe['distinct_persistent_ids']}")
        lines.append(f"- Messages per ID (min/avg/max): {pe['messages_per_id']['min']}/{pe['messages_per_id']['avg']}/{pe['messages_per_id']['max']}")
        lines.append(f"- Updates per ID (min/avg/max): {pe['updates_per_id']['min']}/{pe['updates_per_id']['avg']}/{pe['updates_per_id']['max']}")
        lines.append(f"- First/last observed log_time: {pe['first_observed_log_time']} .. {pe['last_observed_log_time']}")
        lines.append(f"- IDs with same-timestamp collision: {pe['ids_with_same_timestamp_collision']}")
        lines.append(f"- {pe['requires_composite_or_surrogate_key']}")
        lines.append("")

    dt = report["detection_track_relationship"]
    lines.append("## CV detection-to-track relationship analysis")
    lines.append("")
    lines.append(f"- Distinct CV detections existing: {dt['distinct_cv_detections_existing']}")
    lines.append(f"- Distinct CV detections referenced by tracks: {dt['distinct_cv_detections_referenced_by_tracks']}")
    lines.append(f"- Orphaned references (referenced but missing): {dt['orphaned_references']} {dt['orphaned_reference_examples']}")
    lines.append(f"- Never-referenced detections: {dt['never_referenced_detection_count']} {dt['never_referenced_examples']}")
    lines.append(f"- Distinct (detection, track) pairs: {dt['distinct_detection_to_track_pairs']}")
    lines.append(f"- Pairs repeated across track updates (expected): {dt['pairs_repeated_across_track_updates']} (+{dt['repeated_pair_extra_occurrences']} extra occurrences)")
    lines.append(f"- Detections linked to exactly one track: {dt['detections_linked_to_exactly_one_track']}")
    lines.append(f"- Detections linked to multiple distinct tracks (conflicting): {dt['detections_linked_to_multiple_persistent_tracks']} {dt['conflicting_examples']}")
    lines.append("")
    lines.append(f"**Recommendation:** {dt['grain_and_uniqueness_recommendation']}")
    lines.append("")

    lines.append("## Identifier namespace verdicts")
    lines.append("")
    lines.append("| pair | type A | type B | comparable | distinct A/B | overlap | overlap% A/B | verdict | reason |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for v in report["identifier_namespace_verdicts"]:
        ra = round(v["overlap_ratio_a"], 3) if v["overlap_ratio_a"] is not None else None
        rb = round(v["overlap_ratio_b"], 3) if v["overlap_ratio_b"] is not None else None
        lines.append(
            f"| {v['pair_label']} | {v['type_a']} | {v['type_b']} | {v['type_comparable']} | "
            f"{v['distinct_a']}/{v['distinct_b']} | {v['overlap_count']} | {ra}/{rb} | "
            f"**{v['label']}** | {v['reason']} |"
        )
    lines.append("")

    smi = report["source_message_identity"]
    lines.append("## Source MCAP message identity")
    lines.append("")
    lines.append("| candidate key | total records | distinct key values | collision-free | colliding keys | records in collisions | max collision size |")
    lines.append("|---|---|---|---|---|---|---|")
    for c in smi["candidates_tested"]:
        lines.append(
            f"| {'+'.join(c['key_fields'])} | {c['total_records']} | {c['distinct_key_values']} | "
            f"{c['collision_free']} | {c['colliding_key_count']} | {c['records_involved_in_collisions']} | "
            f"{c['max_collision_size']} |"
        )
    lines.append("")
    lines.append(f"**Recommendation:** {smi['recommendation']}")
    lines.append("")
    lines.append(f"**UNIQUE constraint recommendation:** {smi['unique_constraint_recommendation']}")
    lines.append("")

    lines.append("## Candidate key recommendations")
    lines.append("")
    for r in report["candidate_key_recommendations"]:
        lines.append(f"### {r['entity_concept']}")
        lines.append("")
        lines.append(f"- Status: **{r['status']}**")
        lines.append(f"- {r['detail']}")
        lines.append(f"- Recommended constraint: {r['recommended_unique_constraint']}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print(f"Loading Stage 1 report: {STAGE1_REPORT_PATH}")
    stage1 = load_stage1_report()

    print(f"Opening (read-only): {MCAP_PATH}")
    pass_data = run_full_pass(stage1)

    concept_discovery = discover_concepts(stage1)
    identifier_field_analysis = build_identifier_field_analysis(stage1, pass_data)
    persistent_entity_analysis = build_persistent_entity_analysis(pass_data)
    detection_track_relationship = build_detection_track_relationship(pass_data)
    identifier_namespace_verdicts = build_namespace_verdicts(stage1, pass_data)
    source_message_identity = build_source_message_identity(pass_data)
    candidate_key_recommendations = build_candidate_key_recommendations(
        identifier_field_analysis, detection_track_relationship, source_message_identity
    )

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": {
            "path": str(MCAP_PATH.relative_to(REPO_ROOT)),
            "size_bytes": MCAP_PATH.stat().st_size,
        },
        "stage1_report_used": str(STAGE1_REPORT_PATH.relative_to(REPO_ROOT)),
        "concept_discovery": concept_discovery,
        "identifier_field_analysis": identifier_field_analysis,
        "persistent_entity_analysis": persistent_entity_analysis,
        "detection_track_relationship": detection_track_relationship,
        "identifier_namespace_verdicts": identifier_namespace_verdicts,
        "source_message_identity": source_message_identity,
        "candidate_key_recommendations": candidate_key_recommendations,
    }

    JSON_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JSON_REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Wrote {JSON_REPORT_PATH}")

    MD_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT_PATH.write_text(render_markdown(report))
    print(f"Wrote {MD_REPORT_PATH}")

    print()
    print("=== Summary ===")
    print(f"Envelope records: {len(pass_data['envelope_records'])}")
    print(f"Identifier fields analyzed: {len(identifier_field_analysis)}")
    print(f"Namespace verdicts: {len(identifier_namespace_verdicts)}")
    print(f"Detection-track orphans: {detection_track_relationship['orphaned_references']}")
    print(f"Source message identity recommendation: {source_message_identity['recommendation']}")


if __name__ == "__main__":
    main()
