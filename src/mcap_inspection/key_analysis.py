"""Reusable, pure functions for identifier/key analysis over already-decoded
MCAP data.

These functions take plain Python values (tuples, dicts, sets) collected by
``scripts/analyze_keys.py`` -- they perform no file or MCAP I/O themselves,
which keeps them independently unit-testable.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field as dc_field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Field-grain classification
# ---------------------------------------------------------------------------

ENVELOPE_GRAIN = "source_mcap_envelope"
VALID_GRAINS = {
    "persistent_entity",
    "state_update",
    "detection",
    "nested_child",
    "association",
    "batch_member",
    ENVELOPE_GRAIN,
}

_ASSOCIATION_KEYWORDS = ("associat", "suppress", "matched", "linked", "parent")


def classify_field_grain(
    field_path: str, message_structure: dict, repeated_top_level_fields: Optional[set] = None
) -> str:
    """Classify the grain of the *record containing* ``field_path``.

    ``message_structure`` is the per-channel dict produced by Stage 1
    (``classify_message_structure`` in ``scripts/inspect_mcap.py``), with
    keys ``classification`` ("batch_of_entities" | "single_entity_or_update")
    and ``primary_entity_field`` (the dotted top-level repeated field name,
    or ``None``).

    ``repeated_top_level_fields``, when supplied, is the set of top-level
    field names in this topic that are themselves repeated (i.e. actual
    batch/detection arrays, e.g. {"tracks", "trackers", "assets"}). A
    depth-1 field whose top segment is NOT in this set (e.g. a singular
    per-message "metadata" block) is a child of the envelope-level message,
    not a batch row, and is classified as "nested_child" instead. When
    omitted, every depth<=1 field under a "batch_of_entities" topic is
    treated as if its top segment were a repeated array (the coarser,
    backward-compatible default).

    This is a structural + light naming heuristic, not a semantic model: it
    answers "what kind of row does this field live on", using only facts
    already established about the topic's message shape.
    """
    segments = field_path.split(".")
    leaf = segments[-1].lower()
    depth = len(segments) - 1  # 0 == top-level field

    if message_structure["classification"] == "batch_of_entities":
        top_is_repeated = (
            True if repeated_top_level_fields is None else segments[0] in repeated_top_level_fields
        )
        if not top_is_repeated:
            # A singular per-frame field (e.g. "metadata") is a child of the
            # envelope-level batch message, not a batch/detection row.
            return "nested_child"
        primary = message_structure.get("primary_entity_field")
        primary_top = primary.split(".")[0] if primary else None
        # Only the identified *primary* entity array counts as "detection" --
        # a loose substring match on "detect" would also catch companion
        # arrays like "detectors" (sensor hardware metadata, not events).
        if segments[0] == primary_top and primary_top and "detect" in primary_top.lower():
            return "detection" if depth <= 1 else "nested_child"
        if depth <= 1:
            if any(k in leaf for k in _ASSOCIATION_KEYWORDS):
                return "association"
            return "batch_member"
        return "nested_child"

    # single_entity_or_update: the whole message is one state/update row.
    if depth == 0:
        return "state_update"
    top = segments[0].lower()
    if any(k in top for k in ("associat", "match")) or any(
        k in leaf for k in _ASSOCIATION_KEYWORDS
    ):
        return "association"
    return "nested_child"


# ---------------------------------------------------------------------------
# Per-field identifier statistics
# ---------------------------------------------------------------------------


@dataclass
class IdentifierOccurrence:
    """One observed occurrence of an identifier-shaped field.

    ``parent_key`` is the identity of the immediately-enclosing repeated
    element (e.g. a track's own ``track_id`` when the field in question is
    that track's ``last_associated_detection_id``), or ``None`` when no such
    parent-scoping concept applies to this field.
    """

    value: Any
    has_field: Optional[bool]
    message_index: int
    log_time: Optional[int] = None
    parent_key: Optional[Any] = None


@dataclass
class IdentifierFieldStats:
    total_examined: int
    populated: int
    null_or_unset: int
    blank_string: int
    distinct: int
    repeated_occurrence_count: int
    within_message_repeat_count: int
    across_message_repeat_count: int
    across_timestamp_repeat_count: int
    across_parent_repeat_count: Optional[int]
    uniqueness_ratio: Optional[float]
    min_occurrences: Optional[int]
    max_occurrences: Optional[int]
    example_repeated_values: list = dc_field(default_factory=list)


def compute_identifier_field_stats(
    occurrences: list,
) -> IdentifierFieldStats:
    """Compute the full identifier statistics for one field's occurrences.

    Null/unset (``has_field is False``) and blank-string (``value == ""``)
    are tracked as *separate* counts, since a blank string is a populated-
    but-empty value while null/unset means the field was never set.
    """
    total = len(occurrences)
    null_or_unset = sum(1 for o in occurrences if o.has_field is False)
    blank_string = sum(
        1
        for o in occurrences
        if o.has_field is not False and isinstance(o.value, str) and o.value == ""
    )
    populated_occ = [
        o
        for o in occurrences
        if o.has_field is not False
        and not (isinstance(o.value, str) and o.value == "")
    ]

    value_total: Counter = Counter(o.value for o in populated_occ)
    value_messages: dict = defaultdict(set)
    value_timestamps: dict = defaultdict(set)
    value_parents: dict = defaultdict(set)
    any_parent_context = False
    for o in populated_occ:
        value_messages[o.value].add(o.message_index)
        if o.log_time is not None:
            value_timestamps[o.value].add(o.log_time)
        if o.parent_key is not None:
            value_parents[o.value].add(o.parent_key)
            any_parent_context = True

    distinct = len(value_total)
    repeated_values = [v for v, c in value_total.items() if c > 1]
    within_message = [
        v for v in repeated_values if value_total[v] > len(value_messages[v])
    ]
    across_message = [v for v in repeated_values if len(value_messages[v]) > 1]
    across_timestamp = [
        v for v in repeated_values if len(value_timestamps.get(v, ())) > 1
    ]
    across_parent = [v for v in repeated_values if len(value_parents.get(v, ())) > 1]

    occurrence_counts = list(value_total.values())
    populated_count = len(populated_occ)

    return IdentifierFieldStats(
        total_examined=total,
        populated=populated_count,
        null_or_unset=null_or_unset,
        blank_string=blank_string,
        distinct=distinct,
        repeated_occurrence_count=len(repeated_values),
        within_message_repeat_count=len(within_message),
        across_message_repeat_count=len(across_message),
        across_timestamp_repeat_count=len(across_timestamp),
        across_parent_repeat_count=len(across_parent) if any_parent_context else None,
        uniqueness_ratio=(distinct / populated_count) if populated_count else None,
        min_occurrences=min(occurrence_counts) if occurrence_counts else None,
        max_occurrences=max(occurrence_counts) if occurrence_counts else None,
        example_repeated_values=repeated_values[:3],
    )


# ---------------------------------------------------------------------------
# Repetition-expectation classification
# ---------------------------------------------------------------------------


def classify_repetition_expectation(
    grain: str, stats: IdentifierFieldStats, expected_globally_unique: bool
) -> str:
    """Classify observed repetition as expected-state-history,
    expected-batch-framing, unexpected, or unresolved.

    ``expected_globally_unique`` is supplied by the caller per field (e.g.
    True for a raw detection id, False for a persistent track id) -- this is
    domain knowledge about what the field is *for*, which cannot be derived
    from the data alone.
    """
    if stats.populated == 0 or stats.repeated_occurrence_count == 0:
        return "unresolved"

    if stats.within_message_repeat_count > 0 and expected_globally_unique:
        return "unexpected"

    if grain in ("state_update", "batch_member", "association") and (
        stats.across_message_repeat_count > 0 and stats.within_message_repeat_count == 0
    ):
        # Covers both an entity's own persistent id (state_update/batch_member)
        # and a reference/FK-shaped field on that entity (association) being
        # cleanly restated every time the containing row is restated -- e.g.
        # a track's last_associated_detection_id repeating across its own
        # update frames without ever duplicating inside a single frame.
        return "expected_state_history"

    if grain == "batch_member" and stats.within_message_repeat_count > 0:
        return "expected_batch_framing"

    if grain == "detection" and stats.repeated_occurrence_count > 0:
        return "unexpected" if expected_globally_unique else "unresolved"

    return "unresolved"


# ---------------------------------------------------------------------------
# Composite-key collision testing
# ---------------------------------------------------------------------------


def check_composite_key_collisions(records: list, key_fields: tuple) -> dict:
    """Test whether ``key_fields`` (a tuple of dict keys) form a
    collision-free composite key over ``records`` (a list of dicts)."""
    counter: Counter = Counter(tuple(r[k] for k in key_fields) for r in records)
    total = len(records)
    colliding = {k: c for k, c in counter.items() if c > 1}
    return {
        "key_fields": list(key_fields),
        "total_records": total,
        "distinct_key_values": len(counter),
        "collision_free": len(colliding) == 0,
        "colliding_key_count": len(colliding),
        "records_involved_in_collisions": sum(colliding.values()),
        "max_collision_size": max(colliding.values()) if colliding else 0,
    }


# ---------------------------------------------------------------------------
# Cross-topic identifier namespace comparison
# ---------------------------------------------------------------------------


def compare_identifier_namespaces(
    values_a: list,
    type_a: str,
    values_b: list,
    type_b: str,
    structural_hint: Optional[str] = None,
) -> dict:
    """Compare two identifier value populations, preserving exact protobuf
    scalar type: values are only ever compared when ``type_a == type_b``
    (e.g. a ``uint64`` id and a ``string`` id are never coerced together).

    ``structural_hint`` may be ``"named_reference"`` when the field's own
    name/containing-message structure explicitly encodes the relationship
    (e.g. a field literally named ``last_associated_detection_id``).
    """
    set_a, set_b = set(values_a), set(values_b)
    distinct_a, distinct_b = len(set_a), len(set_b)
    type_comparable = type_a == type_b

    overlap = (set_a & set_b) if type_comparable else set()
    overlap_count = len(overlap)
    overlap_ratio_a = (overlap_count / distinct_a) if distinct_a else None
    overlap_ratio_b = (overlap_count / distinct_b) if distinct_b else None
    best_ratio = max((r for r in (overlap_ratio_a, overlap_ratio_b) if r is not None), default=0.0)

    if not type_comparable:
        label = "rejected"
        reason = (
            f"Protobuf types differ ({type_a} vs {type_b}); values are never "
            "coerced across representations, so no comparison was made."
        )
    elif distinct_a == 0 or distinct_b == 0:
        label = "weak_heuristic"
        reason = "One or both sides have no populated values in this dataset; cannot verify."
    elif overlap_count == 0:
        label = "rejected"
        reason = (
            "Same scalar type, but zero observed value overlap across populated "
            "data on both sides -- values appear to live in different namespaces."
        )
    elif structural_hint == "named_reference" and best_ratio > 0.5:
        label = "confirmed"
        reason = (
            "Field name/containing-message structure explicitly encodes the "
            "relationship, and observed overlap is substantial."
        )
    elif best_ratio > 0.3:
        label = "strongly_supported"
        reason = "Same scalar type and substantial observed value overlap."
    else:
        label = "weak_heuristic"
        reason = "Same scalar type with some observed overlap, but the ratio is low."

    return {
        "type_a": type_a,
        "type_b": type_b,
        "type_comparable": type_comparable,
        "distinct_a": distinct_a,
        "distinct_b": distinct_b,
        "overlap_count": overlap_count,
        "overlap_ratio_a": overlap_ratio_a,
        "overlap_ratio_b": overlap_ratio_b,
        "label": label,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# Detection <-> persistent-track pair analysis
# ---------------------------------------------------------------------------


def dedupe_detection_track_pairs(pairs: list) -> dict:
    """Analyze (detection_id, track_id) pairs observed across track updates.

    Distinguishes distinct pairs from repeated restatement of the same pair
    (expected: a track restates its associated detection on every update),
    and flags detections referenced by more than one distinct track id
    (a conflicting/ambiguous association)."""
    pair_counter: Counter = Counter((d, t) for d, t in pairs)
    distinct_pairs = len(pair_counter)
    repeated_pairs = {k: c for k, c in pair_counter.items() if c > 1}

    detection_to_tracks: dict = defaultdict(set)
    for (d, t) in pair_counter:
        detection_to_tracks[d].add(t)
    conflicting = {d: ts for d, ts in detection_to_tracks.items() if len(ts) > 1}
    single_track = {d: ts for d, ts in detection_to_tracks.items() if len(ts) == 1}

    return {
        "total_pair_observations": len(pairs),
        "distinct_pairs": distinct_pairs,
        "repeated_pair_count": len(repeated_pairs),
        "repeated_pair_extra_occurrences": sum(c - 1 for c in repeated_pairs.values()),
        "conflicting_detection_count": len(conflicting),
        "conflicting_examples": [
            (d, sorted(ts)) for d, ts in list(conflicting.items())[:3]
        ],
        "single_persistent_track_detection_count": len(single_track),
    }


# ---------------------------------------------------------------------------
# Orphan / unreferenced detection
# ---------------------------------------------------------------------------


def find_orphans(referenced: set, existing: set) -> dict:
    """Compare a set of referenced ids against a set of existing ids."""
    orphaned = referenced - existing
    never_referenced = existing - referenced
    matched = referenced & existing
    return {
        "distinct_referenced": len(referenced),
        "distinct_existing": len(existing),
        "matched_count": len(matched),
        "orphaned_reference_count": len(orphaned),
        "orphaned_examples": sorted(orphaned, key=str)[:3],
        "never_referenced_count": len(never_referenced),
        "never_referenced_examples": sorted(never_referenced, key=str)[:3],
    }
