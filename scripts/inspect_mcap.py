#!/usr/bin/env python3
"""Read-only structural and statistical inspection of
``data/input/sanitized.mcap``.

This script NEVER modifies, renames, moves, or truncates the source MCAP
file -- it is opened once in ``'rb'`` mode and only read. It performs two
kinds of inspection in a single streaming pass over the file:

1. Structural inspection: for up to 3 representative messages per topic, it
   recursively walks the decoded protobuf descriptor to catalog every field
   (scalar/message/enum/map, repeated/presence/nested status, enum values)
   and records a safely-truncated observed sample.

2. Full-dataset identifier statistics: for every field whose name looks
   identifier-shaped (id/seq/parent-link/timestamp), it decodes *every*
   message in the file and tracks population/null counts, distinct-value
   counts, and duplicate values -- split into duplicates that occur *within*
   a single message (an unexpected structural anomaly) versus duplicates
   that occur only *across* different messages (expected repetition of a
   persistent entity's id in a time series of states/updates). It also
   estimates cross-topic and intra-topic relationship cardinality (1:1,
   1:N, N:1, N:M) for identifier fields that share a normalized name.

All cardinality/relationship results are estimates for later validation --
this script does not declare primary keys or foreign keys, and produces no
schema, database, or ETL code.

Outputs:
    data/output/mcap_schema_report.json  (machine-readable)
    docs/MCAP_INSPECTION.md              (human-readable)
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field as dc_field
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
    FieldObservation,
    identifier_category,
    normalize_identifier_name,
    resolve_field_descriptor_chain,
    summarize_presence,
    truncate_sample,
    walk_descriptor,
)

MCAP_PATH = REPO_ROOT / "data" / "input" / "sanitized.mcap"
JSON_REPORT_PATH = REPO_ROOT / "data" / "output" / "mcap_schema_report.json"
MD_REPORT_PATH = REPO_ROOT / "docs" / "MCAP_INSPECTION.md"

EXPECTED_TOPICS = ("cv_detections", "cv_tracks", "radar_detections", "track_states")
SAMPLE_COUNT = 3
MAX_DUPLICATE_EXAMPLES = 3


# ---------------------------------------------------------------------------
# Per-channel accumulator
# ---------------------------------------------------------------------------


@dataclass
class OnlineMinMaxAvg:
    count: int = 0
    total: int = 0
    minimum: Optional[int] = None
    maximum: Optional[int] = None

    def update(self, value: int) -> None:
        self.count += 1
        self.total += value
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)

    def summary(self) -> dict:
        if self.count == 0:
            return {"min": None, "max": None, "avg": None, "messages_observed": 0}
        return {
            "min": self.minimum,
            "max": self.maximum,
            "avg": round(self.total / self.count, 3),
            "messages_observed": self.count,
        }


@dataclass
class IdentifierFieldStats:
    field_path: str
    category: str
    total_occurrences: int = 0
    null_or_unset: int = 0
    empty: int = 0
    populated: int = 0
    value_total_counter: Counter = dc_field(default_factory=Counter)
    value_message_counter: Counter = dc_field(default_factory=Counter)
    occurrences_per_message: OnlineMinMaxAvg = dc_field(default_factory=OnlineMinMaxAvg)


@dataclass
class ChannelAccumulator:
    channel_id: int
    topic: str
    schema_id: int
    schema_name: str
    message_encoding: str
    schema_encoding: str
    expected_message_count: int

    message_count: int = 0
    min_log_time: Optional[int] = None
    max_log_time: Optional[int] = None
    min_publish_time: Optional[int] = None
    max_publish_time: Optional[int] = None
    out_of_order_log_time_count: int = 0
    _prev_log_time: Optional[int] = None

    prev_sequence: Optional[int] = None
    sequence_increasing_steps: int = 0
    sequence_equal_steps: int = 0
    sequence_decreasing_steps: int = 0
    sequence_value_counter: Counter = dc_field(default_factory=Counter)

    descriptor: Any = None
    field_catalog: list = dc_field(default_factory=list)
    identifier_stats: dict = dc_field(default_factory=dict)  # path -> IdentifierFieldStats
    identifier_chains: dict = dc_field(default_factory=dict)  # path -> list[FieldDescriptor]

    sample_target_indices: set = dc_field(default_factory=set)
    samples: list = dc_field(default_factory=list)  # list of (index, decoded_message)
    running_index: int = 0

    def note_envelope(self, log_time: int, publish_time: int, sequence: int) -> None:
        self.message_count += 1
        self.min_log_time = log_time if self.min_log_time is None else min(self.min_log_time, log_time)
        self.max_log_time = log_time if self.max_log_time is None else max(self.max_log_time, log_time)
        self.min_publish_time = (
            publish_time if self.min_publish_time is None else min(self.min_publish_time, publish_time)
        )
        self.max_publish_time = (
            publish_time if self.max_publish_time is None else max(self.max_publish_time, publish_time)
        )
        if self._prev_log_time is not None and log_time < self._prev_log_time:
            self.out_of_order_log_time_count += 1
        self._prev_log_time = log_time

        if self.prev_sequence is not None:
            if sequence > self.prev_sequence:
                self.sequence_increasing_steps += 1
            elif sequence == self.prev_sequence:
                self.sequence_equal_steps += 1
            else:
                self.sequence_decreasing_steps += 1
        self.prev_sequence = sequence
        self.sequence_value_counter[sequence] += 1

    def sequence_behavior(self) -> dict:
        duplicate_sequence_values = sum(1 for c in self.sequence_value_counter.values() if c > 1)
        return {
            "monotonic_increasing": self.sequence_decreasing_steps == 0 and self.sequence_equal_steps == 0,
            "increasing_steps": self.sequence_increasing_steps,
            "equal_steps": self.sequence_equal_steps,
            "decreasing_steps": self.sequence_decreasing_steps,
            "duplicate_sequence_values": duplicate_sequence_values,
            "min_sequence": min(self.sequence_value_counter) if self.sequence_value_counter else None,
            "max_sequence": max(self.sequence_value_counter) if self.sequence_value_counter else None,
        }


def _is_populated(has_field: Optional[bool], value: Any) -> bool:
    if has_field is False:
        return False
    if isinstance(value, (bytes, str)):
        return len(value) > 0
    if isinstance(value, bool):
        return value is True
    if isinstance(value, (int, float)):
        return value != 0
    return value is not None


# ---------------------------------------------------------------------------
# Message-structure classification (batch vs single-entity, requirement 14)
# ---------------------------------------------------------------------------


def classify_message_structure(topic: str, field_catalog: list) -> dict:
    top_level_repeated_message_fields = [
        f for f in field_catalog if f.depth == 0 and f.repeated and f.proto_kind == "message"
    ]
    top_level_scalar_identifier_fields = [
        f
        for f in field_catalog
        if f.depth == 0 and not f.repeated and identifier_category(f.field_name) is not None
    ]

    topic_key = topic.replace("_", "").lower()
    primary = None
    for f in top_level_repeated_message_fields:
        key = f.field_name.replace("_", "").lower()
        if key in topic_key or topic_key in key:
            primary = f
            break

    companions = [f.field_name for f in top_level_repeated_message_fields if f is not primary]

    if primary is not None:
        return {
            "classification": "batch_of_entities",
            "primary_entity_field": primary.full_path,
            "companion_repeated_fields": companions,
            "basis": (
                f"Top-level repeated field '{primary.full_path}' shares its name with the "
                f"topic '{topic}', so each message appears to be a batch/frame containing "
                "multiple entities of that type."
                + (f" Companion repeated field(s) also present: {companions}." if companions else "")
            ),
        }
    if top_level_scalar_identifier_fields:
        id_names = [f.field_name for f in top_level_scalar_identifier_fields]
        return {
            "classification": "single_entity_or_update",
            "primary_entity_field": None,
            "companion_repeated_fields": [f.field_name for f in top_level_repeated_message_fields],
            "basis": (
                f"No top-level repeated field matches the topic name; top-level scalar "
                f"identifier-shaped field(s) {id_names} suggest one message represents one "
                "entity/update record, with "
                f"{len(top_level_repeated_message_fields)} repeated child/association "
                f"substructure(s): {[f.field_name for f in top_level_repeated_message_fields]}."
            ),
        }
    if top_level_repeated_message_fields:
        return {
            "classification": "ambiguous_batch_candidate",
            "primary_entity_field": None,
            "companion_repeated_fields": [f.field_name for f in top_level_repeated_message_fields],
            "basis": (
                "No top-level scalar identifier field was found, but repeated message "
                f"field(s) are present: {[f.field_name for f in top_level_repeated_message_fields]}. "
                "Needs manual review to determine batch vs. single-entity semantics."
            ),
        }
    return {
        "classification": "single_entity_or_update",
        "primary_entity_field": None,
        "companion_repeated_fields": [],
        "basis": "No top-level repeated message fields; consistent with one message = one record.",
    }


def analyze_radar_detection_track_discrimination(field_catalog: list) -> dict:
    top_level_repeated_message_fields = [
        f for f in field_catalog if f.depth == 0 and f.repeated and f.proto_kind == "message"
    ]
    detection_like = [f for f in top_level_repeated_message_fields if "detect" in f.field_name.lower()]
    track_like = [f for f in top_level_repeated_message_fields if "track" in f.field_name.lower()]

    inline_track_id_fields = [
        f.full_path
        for f in field_catalog
        if f.field_name.lower() == "track_id"
        and any(f.full_path.startswith(d.full_path + ".") for d in detection_like)
    ]
    self_referential_group_fields = [
        f.full_path
        for f in field_catalog
        if f.proto_kind == "message"
        and f.repeated
        and f.message_type is not None
        and f.message_type.split(".")[-1].lower() in f.field_name.lower().replace("_", "")
        or (f.proto_kind == "message" and f.repeated and "cluster" in f.field_name.lower())
    ]

    if track_like:
        finding = (
            f"A separate top-level repeated field distinct from detections was found: "
            f"{[f.full_path for f in track_like]}. This suggests radar tracks are represented "
            "as their own repeated structure, separate from raw detections."
        )
    elif inline_track_id_fields:
        finding = (
            "No separate top-level repeated field for radar tracks was found. Instead, each "
            f"detection record carries an inline track-association field: {inline_track_id_fields}. "
            "This means, in the observed data, radar detections and their track association live "
            "in the SAME record -- there is no distinct 'radar track' message type/topic."
        )
    else:
        finding = (
            "No separate top-level repeated field for radar tracks and no inline track_id field "
            "on individual detections were found. Radar detection-to-track association, if any, "
            "is not directly visible in the top-level RadarDetection structure."
        )

    return {
        "top_level_repeated_fields": [f.full_path for f in top_level_repeated_message_fields],
        "detection_like_fields": [f.full_path for f in detection_like],
        "track_like_fields": [f.full_path for f in track_like],
        "inline_track_id_fields_on_detections": inline_track_id_fields,
        "self_referential_grouping_fields": sorted(set(self_referential_group_fields)),
        "finding": finding,
    }


# ---------------------------------------------------------------------------
# Main inspection pass
# ---------------------------------------------------------------------------


def run_inspection() -> dict:
    if not MCAP_PATH.exists():
        raise FileNotFoundError(f"Source MCAP not found at {MCAP_PATH}")

    channels: dict = {}

    with open(MCAP_PATH, "rb") as f:
        reader = make_reader(f, decoder_factories=[DecoderFactory()])
        summary = reader.get_summary()
        if summary is None:
            raise RuntimeError("MCAP file has no summary section; cannot inspect safely")

        expected_counts = summary.statistics.channel_message_counts

        for channel_id, channel in summary.channels.items():
            schema = summary.schemas[channel.schema_id]
            expected_total = expected_counts.get(channel_id, 0)
            acc = ChannelAccumulator(
                channel_id=channel_id,
                topic=channel.topic,
                schema_id=schema.id,
                schema_name=schema.name,
                message_encoding=channel.message_encoding,
                schema_encoding=schema.encoding,
                expected_message_count=expected_total,
            )
            if expected_total > 0:
                target_first = 0
                target_last = expected_total - 1
                target_mid = expected_total // 2
                acc.sample_target_indices = {target_first, target_mid, target_last}
            channels[channel_id] = acc

        for schema, channel, message, decoded in reader.iter_decoded_messages():
            acc = channels[channel.id]
            acc.note_envelope(message.log_time, message.publish_time, message.sequence)

            if acc.descriptor is None:
                acc.descriptor = decoded.DESCRIPTOR
                acc.field_catalog = walk_descriptor(acc.descriptor)
                for finfo in acc.field_catalog:
                    if identifier_category(finfo.field_name) is None:
                        continue
                    if finfo.proto_kind not in ("scalar", "enum"):
                        # Composite fields (e.g. a nested google.protobuf.Timestamp
                        # message matching the "timestamp" name pattern) are not
                        # hashable scalar values; they stay in the structural field
                        # catalog but are excluded from identifier value statistics.
                        continue
                    try:
                        chain = resolve_field_descriptor_chain(acc.descriptor, finfo.full_path)
                    except ValueError:
                        continue
                    acc.identifier_chains[finfo.full_path] = chain
                    acc.identifier_stats[finfo.full_path] = IdentifierFieldStats(
                        field_path=finfo.full_path,
                        category=identifier_category(finfo.field_name),
                    )

            current_index = acc.running_index
            acc.running_index += 1
            if current_index in acc.sample_target_indices:
                acc.samples.append((current_index, decoded))

            for path, chain in acc.identifier_chains.items():
                stats = acc.identifier_stats[path]
                occurrences = list(_iter_occurrences_safe(decoded, chain))
                stats.occurrences_per_message.update(len(occurrences))
                if not occurrences:
                    continue
                observations = [
                    FieldObservation(has_field=has, is_repeated=False, value=value)
                    for has, value in occurrences
                ]
                presence = summarize_presence(observations)
                stats.total_occurrences += presence["total"]
                stats.null_or_unset += presence["null_or_unset"]
                stats.empty += presence["empty"]

                populated_values = [v for has, v in occurrences if _is_populated(has, v)]
                msg_value_counts = Counter(populated_values)
                for value, count in msg_value_counts.items():
                    stats.value_total_counter[value] += count
                    stats.value_message_counter[value] += 1
                stats.populated += len(populated_values)

    return _build_report(channels)


def _iter_occurrences_safe(message: Any, chain: list):
    """Wrap iter_field_occurrences, tolerating unset intermediate oneof
    branches or similar edge cases without aborting the whole pass."""
    from mcap_inspection.helpers import iter_field_occurrences

    try:
        yield from iter_field_occurrences(message, chain)
    except Exception:
        return


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------


def _field_info_to_dict(finfo, observed: dict, sample_values: list) -> dict:
    d = asdict(finfo)
    d["observed"] = observed
    d["sample_values"] = sample_values
    d["candidate_identifier_category"] = identifier_category(finfo.field_name)
    return d


def _build_report(channels: dict) -> dict:
    found_topics = sorted(acc.topic for acc in channels.values())
    missing_topics = sorted(set(EXPECTED_TOPICS) - set(found_topics))
    unexpected_topics = sorted(set(found_topics) - set(EXPECTED_TOPICS))

    channel_reports = []
    all_identifier_entries = []  # for relationship estimation
    risk_flags = []

    for acc in sorted(channels.values(), key=lambda a: a.channel_id):
        # Observed presence per field, computed from the retained samples.
        observed_by_path: dict = {}
        for idx, sample_msg in acc.samples:
            for finfo in acc.field_catalog:
                observed_by_path.setdefault(finfo.full_path, []).append((finfo, sample_msg))

        field_catalog_out = []
        for finfo in acc.field_catalog:
            sample_pairs = observed_by_path.get(finfo.full_path, [])
            observations = []
            sample_values = []
            for _, sample_msg in sample_pairs:
                try:
                    chain = resolve_field_descriptor_chain(acc.descriptor, finfo.full_path)
                except ValueError:
                    chain = None
                if chain is None:
                    continue
                for has, value in _iter_occurrences_safe(sample_msg, chain):
                    observations.append(FieldObservation(has_field=has, is_repeated=False, value=value))
                    if len(sample_values) < SAMPLE_COUNT:
                        sample_values.append(truncate_sample(value))
            observed = summarize_presence(observations) if observations else {
                "total": 0,
                "null_or_unset": 0,
                "empty": 0,
                "populated": 0,
            }
            field_catalog_out.append(_field_info_to_dict(finfo, observed, sample_values))

        structure = classify_message_structure(acc.topic, acc.field_catalog)

        identifier_stats_out = []
        for path, stats in sorted(acc.identifier_stats.items()):
            distinct_values = len(stats.value_total_counter)
            duplicate_values = [v for v, c in stats.value_total_counter.items() if c > 1]
            within_message_dup = [
                v for v in duplicate_values
                if stats.value_total_counter[v] > stats.value_message_counter[v]
            ]
            within_message_set = set(within_message_dup)
            cross_message_only = [v for v in duplicate_values if v not in within_message_set]

            null_frequency_pct = (
                round(100 * stats.null_or_unset / stats.total_occurrences, 3)
                if stats.total_occurrences
                else None
            )
            uniqueness_ratio = (
                round(distinct_values / stats.populated, 4) if stats.populated else None
            )

            entry = {
                "topic": acc.topic,
                "field_path": path,
                "identifier_category": stats.category,
                "total_occurrences": stats.total_occurrences,
                "populated_occurrences": stats.populated,
                "null_or_unset_occurrences": stats.null_or_unset,
                "empty_occurrences": stats.empty,
                "null_frequency_pct": null_frequency_pct,
                "distinct_values": distinct_values,
                "uniqueness_ratio": uniqueness_ratio,
                "duplicate_values_total": len(duplicate_values),
                "duplicate_values_unexpected_within_message": {
                    "count": len(within_message_dup),
                    "note": (
                        "Same value appears more than once inside a single MCAP message's "
                        "repeated group -- a structural anomaly for an identifier, not "
                        "explained by time-series repetition."
                    ),
                    "examples": [truncate_sample(v) for v in within_message_dup[:MAX_DUPLICATE_EXAMPLES]],
                },
                "duplicate_values_expected_repetition_across_messages": {
                    "count": len(cross_message_only),
                    "note": (
                        "Same value appears in more than one distinct MCAP message but never "
                        "more than once within a single message -- consistent with a "
                        "persistent entity (e.g. a track) being restated across repeated "
                        "state/update messages over time."
                    ),
                    "examples": [truncate_sample(v) for v in cross_message_only[:MAX_DUPLICATE_EXAMPLES]],
                },
                "occurrences_per_message": stats.occurrences_per_message.summary(),
            }
            identifier_stats_out.append(entry)
            all_identifier_entries.append((acc.topic, path, stats))

            if within_message_dup:
                risk_flags.append({
                    "category": "duplicate_looking_identifier",
                    "topic": acc.topic,
                    "field_path": path,
                    "description": (
                        f"{len(within_message_dup)} value(s) of '{path}' repeat within a single "
                        "message's batch, which is unexpected for an identifier-shaped field."
                    ),
                })
            if stats.total_occurrences and stats.null_or_unset / stats.total_occurrences > 0.5:
                risk_flags.append({
                    "category": "sparsely_populated_field",
                    "topic": acc.topic,
                    "field_path": path,
                    "description": (
                        f"'{path}' is null/unset in "
                        f"{null_frequency_pct}% of observed occurrences."
                    ),
                })
            elif stats.total_occurrences and stats.populated == 0:
                risk_flags.append({
                    "category": "always_empty_field",
                    "topic": acc.topic,
                    "field_path": path,
                    "description": (
                        f"'{path}' is present in every one of its "
                        f"{stats.total_occurrences} observed occurrences but always holds the "
                        "scalar default value (e.g. empty string / 0) -- never meaningfully "
                        "populated in this dataset. Possibly scrubbed by sanitization, or "
                        "simply unused by this data source."
                    ),
                })
            elif stats.total_occurrences == 0:
                risk_flags.append({
                    "category": "identifier_never_observed",
                    "topic": acc.topic,
                    "field_path": path,
                    "description": (
                        f"'{path}' is an identifier-shaped field but its containing repeated "
                        "group was empty in every message -- zero occurrences observed across "
                        "the entire dataset."
                    ),
                })

        channel_report = {
            "channel_id": acc.channel_id,
            "topic": acc.topic,
            "schema_id": acc.schema_id,
            "schema_name": acc.schema_name,
            "message_encoding": acc.message_encoding,
            "schema_encoding": acc.schema_encoding,
            "message_count": acc.message_count,
            "log_time": {"min": acc.min_log_time, "max": acc.max_log_time},
            "publish_time": {"min": acc.min_publish_time, "max": acc.max_publish_time},
            "out_of_order_log_time_count": acc.out_of_order_log_time_count,
            "sequence_behavior": acc.sequence_behavior(),
            "message_structure": structure,
            "field_catalog": field_catalog_out,
            "field_count": len(field_catalog_out),
            "samples_used": {
                "count": len(acc.samples),
                "indices": sorted(idx for idx, _ in acc.samples),
            },
            "identifier_statistics": identifier_stats_out,
        }
        if acc.topic == "radar_detections":
            channel_report["radar_detection_vs_track_analysis"] = (
                analyze_radar_detection_track_discrimination(acc.field_catalog)
            )
        channel_reports.append(channel_report)

    if acc_has_out_of_order := any(c["out_of_order_log_time_count"] > 0 for c in channel_reports):
        for c in channel_reports:
            if c["out_of_order_log_time_count"] > 0:
                risk_flags.append({
                    "category": "out_of_order_timestamps",
                    "topic": c["topic"],
                    "field_path": "log_time",
                    "description": (
                        f"{c['out_of_order_log_time_count']} message(s) on topic "
                        f"'{c['topic']}' have a log_time earlier than the previous message."
                    ),
                })

    relationship_estimates = _estimate_relationships(all_identifier_entries)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": {
            "path": str(MCAP_PATH.relative_to(REPO_ROOT)),
            "size_bytes": MCAP_PATH.stat().st_size,
        },
        "topic_check": {
            "expected_topics": sorted(EXPECTED_TOPICS),
            "found_topics": found_topics,
            "missing_topics": missing_topics,
            "unexpected_topics": unexpected_topics,
            "all_expected_present": not missing_topics,
        },
        "channels": channel_reports,
        "relationship_cardinality_estimates": relationship_estimates,
        "risk_flags": risk_flags,
    }
    return report


def _estimate_relationships(all_identifier_entries: list) -> list:
    groups: dict = defaultdict(list)
    for topic, path, stats in all_identifier_entries:
        norm = normalize_identifier_name(path.split(".")[-1])
        groups[norm].append((topic, path, stats))

    estimates = []
    for norm_name, entries in sorted(groups.items()):
        if len(entries) < 2:
            continue
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                topic_a, path_a, stats_a = entries[i]
                topic_b, path_b, stats_b = entries[j]
                if topic_a == topic_b and path_a == path_b:
                    continue

                values_a = set(stats_a.value_total_counter.keys())
                values_b = set(stats_b.value_total_counter.keys())
                overlap = values_a & values_b
                distinct_a = len(values_a)
                distinct_b = len(values_b)
                overlap_count = len(overlap)

                type_a = {type(v).__name__ for v in list(values_a)[:20]}
                type_b = {type(v).__name__ for v in list(values_b)[:20]}
                type_comparable = bool(type_a & type_b) if type_a and type_b else True

                avg_occ_a = (
                    sum(stats_a.value_total_counter[v] for v in overlap) / overlap_count
                    if overlap_count else None
                )
                avg_occ_b = (
                    sum(stats_b.value_total_counter[v] for v in overlap) / overlap_count
                    if overlap_count else None
                )

                if overlap_count == 0:
                    cardinality_estimate = "no_observed_overlap"
                elif avg_occ_a is not None and avg_occ_b is not None:
                    a_is_one = avg_occ_a <= 1.05
                    b_is_one = avg_occ_b <= 1.05
                    if a_is_one and b_is_one:
                        cardinality_estimate = "estimated_1_to_1"
                    elif a_is_one and not b_is_one:
                        cardinality_estimate = f"estimated_1_to_N ({topic_a}.{path_a} : {topic_b}.{path_b})"
                    elif b_is_one and not a_is_one:
                        cardinality_estimate = f"estimated_1_to_N ({topic_b}.{path_b} : {topic_a}.{path_a})"
                    else:
                        cardinality_estimate = "estimated_N_to_M"
                else:
                    cardinality_estimate = "indeterminate"

                estimates.append({
                    "normalized_identifier_name": norm_name,
                    "relationship_kind": "intra_topic" if topic_a == topic_b else "cross_topic",
                    "side_a": {"topic": topic_a, "field_path": path_a, "distinct_values": distinct_a},
                    "side_b": {"topic": topic_b, "field_path": path_b, "distinct_values": distinct_b},
                    "overlap_count": overlap_count,
                    "overlap_ratio_a": round(overlap_count / distinct_a, 4) if distinct_a else None,
                    "overlap_ratio_b": round(overlap_count / distinct_b, 4) if distinct_b else None,
                    "type_comparable": type_comparable,
                    "cardinality_estimate": cardinality_estimate,
                    "disclaimer": (
                        "ESTIMATE ONLY, not a validated or declared relationship, and not a "
                        "primary/foreign key. Based on value-set overlap and average "
                        "occurrences-per-shared-value; requires manual validation before any "
                        "schema design decision."
                    ),
                })
    return estimates


# ---------------------------------------------------------------------------
# Markdown report rendering
# ---------------------------------------------------------------------------


def render_markdown(report: dict) -> str:
    lines = []
    lines.append("# MCAP Inspection Report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at_utc']}")
    lines.append("")
    lines.append(
        "This report is produced by `scripts/inspect_mcap.py`, a read-only inspection "
        "utility. The source file "
        f"`{report['source_file']['path']}` ({report['source_file']['size_bytes']:,} bytes) "
        "was never modified. All relationship-cardinality figures are **estimates for later "
        "validation**, not declared primary/foreign keys."
    )
    lines.append("")

    tc = report["topic_check"]
    lines.append("## Topic check")
    lines.append("")
    lines.append(f"- Expected topics: {', '.join(tc['expected_topics'])}")
    lines.append(f"- Found topics: {', '.join(tc['found_topics'])}")
    lines.append(f"- Missing topics: {', '.join(tc['missing_topics']) or 'none'}")
    lines.append(f"- Unexpected topics: {', '.join(tc['unexpected_topics']) or 'none'}")
    lines.append(f"- All expected topics present: **{tc['all_expected_present']}**")
    lines.append("")

    lines.append("## Channels")
    lines.append("")
    for ch in report["channels"]:
        lines.append(f"### `{ch['topic']}` (channel {ch['channel_id']}, schema `{ch['schema_name']}`)")
        lines.append("")
        lines.append(f"- Message encoding / schema encoding: `{ch['message_encoding']}` / `{ch['schema_encoding']}`")
        lines.append(f"- Message count: {ch['message_count']:,}")
        lines.append(f"- log_time range (ns): {ch['log_time']['min']} .. {ch['log_time']['max']}")
        lines.append(f"- publish_time range (ns): {ch['publish_time']['min']} .. {ch['publish_time']['max']}")
        lines.append(f"- Out-of-order log_time messages: {ch['out_of_order_log_time_count']}")
        sb = ch["sequence_behavior"]
        lines.append(
            f"- Sequence behavior: monotonic_increasing={sb['monotonic_increasing']}, "
            f"increasing_steps={sb['increasing_steps']}, equal_steps={sb['equal_steps']}, "
            f"decreasing_steps={sb['decreasing_steps']}, "
            f"duplicate_sequence_values={sb['duplicate_sequence_values']}, "
            f"range=[{sb['min_sequence']}, {sb['max_sequence']}]"
        )
        lines.append(f"- Field count (recursive): {ch['field_count']}")
        lines.append(f"- Structural samples decoded: {ch['samples_used']['count']} (indices {ch['samples_used']['indices']})")
        lines.append("")
        ms = ch["message_structure"]
        lines.append(f"**Message structure:** `{ms['classification']}`")
        lines.append("")
        lines.append(ms["basis"])
        lines.append("")

        if "radar_detection_vs_track_analysis" in ch:
            ra = ch["radar_detection_vs_track_analysis"]
            lines.append("**Radar detection-vs-track discrimination:**")
            lines.append("")
            lines.append(ra["finding"])
            lines.append("")

        if ch["identifier_statistics"]:
            lines.append("**Candidate identifier field statistics (full dataset):**")
            lines.append("")
            lines.append(
                "| field_path | category | populated | null_freq% | distinct | "
                "uniqueness_ratio | dup_within_msg (unexpected) | dup_cross_msg (expected) | entities/msg (min/avg/max) |"
            )
            lines.append("|---|---|---|---|---|---|---|---|---|")
            for entry in ch["identifier_statistics"]:
                opm = entry["occurrences_per_message"]
                lines.append(
                    f"| `{entry['field_path']}` | {entry['identifier_category']} | "
                    f"{entry['populated_occurrences']} | {entry['null_frequency_pct']} | "
                    f"{entry['distinct_values']} | {entry['uniqueness_ratio']} | "
                    f"{entry['duplicate_values_unexpected_within_message']['count']} | "
                    f"{entry['duplicate_values_expected_repetition_across_messages']['count']} | "
                    f"{opm['min']}/{opm['avg']}/{opm['max']} |"
                )
            lines.append("")

        lines.append("<details><summary>Full recursive field catalog</summary>")
        lines.append("")
        lines.append("| path | kind | type | repeated | presence | observed (null/empty/populated) | sample |")
        lines.append("|---|---|---|---|---|---|---|")
        for f in ch["field_catalog"]:
            type_desc = f["scalar_type"] or f["message_type"] or f["enum_type"] or (
                f"map<{f['map_key_type']},{f['map_value_type']}>" if f["is_map"] else ""
            )
            obs = f["observed"]
            sample = "; ".join(f["sample_values"]) if f["sample_values"] else ""
            lines.append(
                f"| `{f['full_path']}` | {f['proto_kind']} | {type_desc} | {f['repeated']} | "
                f"{f['has_presence']} | {obs['null_or_unset']}/{obs['empty']}/{obs['populated']} | {sample} |"
            )
        lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.append("## Relationship cardinality estimates")
    lines.append("")
    lines.append(
        "**All entries below are estimates only**, derived from value-set overlap and "
        "average occurrences per shared value across the full dataset. None of these are "
        "declared primary or foreign keys -- they require manual validation before any "
        "schema design decision."
    )
    lines.append("")
    if report["relationship_cardinality_estimates"]:
        lines.append("| kind | normalized name | side A | side B | overlap | overlap% A / B | type comparable | cardinality estimate |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for r in report["relationship_cardinality_estimates"]:
            a = r["side_a"]
            b = r["side_b"]
            lines.append(
                f"| {r['relationship_kind']} | {r['normalized_identifier_name']} | "
                f"`{a['topic']}.{a['field_path']}` ({a['distinct_values']}) | "
                f"`{b['topic']}.{b['field_path']}` ({b['distinct_values']}) | "
                f"{r['overlap_count']} | {r['overlap_ratio_a']} / {r['overlap_ratio_b']} | "
                f"{r['type_comparable']} | {r['cardinality_estimate']} |"
            )
        lines.append("")
    else:
        lines.append("No candidate cross-field name matches were found.")
        lines.append("")

    lines.append("## Data-quality risk flags")
    lines.append("")
    if report["risk_flags"]:
        for rf in report["risk_flags"]:
            lines.append(f"- **{rf['category']}** (`{rf['topic']}`, `{rf['field_path']}`): {rf['description']}")
    else:
        lines.append("None automatically detected.")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    print(f"Opening (read-only): {MCAP_PATH}")
    report = run_inspection()

    JSON_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JSON_REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Wrote {JSON_REPORT_PATH}")

    MD_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT_PATH.write_text(render_markdown(report))
    print(f"Wrote {MD_REPORT_PATH}")

    print()
    print("=== Summary ===")
    print(f"Topics found: {report['topic_check']['found_topics']}")
    print(f"All expected topics present: {report['topic_check']['all_expected_present']}")
    for ch in report["channels"]:
        print(f"  {ch['topic']}: {ch['message_count']:,} messages, "
              f"structure={ch['message_structure']['classification']}, "
              f"fields={ch['field_count']}")
    print(f"Relationship estimates: {len(report['relationship_cardinality_estimates'])}")
    print(f"Risk flags: {len(report['risk_flags'])}")


if __name__ == "__main__":
    main()
