"""Tests for the pure key-analysis functions in
``mcap_inspection.key_analysis``.

These use small hand-built occurrence lists / records rather than the real
MCAP file, so they run fast and pin down the exact semantics (blank vs
null, within- vs across-message repetition, parent-scoped uniqueness,
composite-key collisions, namespace comparison, pair dedup, orphans).
"""

from __future__ import annotations

from mcap_inspection.key_analysis import (
    IdentifierOccurrence,
    classify_field_grain,
    classify_repetition_expectation,
    compare_identifier_namespaces,
    compute_identifier_field_stats,
    dedupe_detection_track_pairs,
    find_orphans,
    check_composite_key_collisions,
)


# ---------------------------------------------------------------------------
# classify_field_grain
# ---------------------------------------------------------------------------


def test_classify_field_grain_batch_detection_field():
    structure = {"classification": "batch_of_entities", "primary_entity_field": "detections"}
    assert classify_field_grain("detections.detection_id", structure) == "detection"


def test_classify_field_grain_batch_member_field():
    structure = {"classification": "batch_of_entities", "primary_entity_field": "tracks"}
    assert classify_field_grain("tracks.track_id", structure) == "batch_member"


def test_classify_field_grain_batch_association_field():
    structure = {"classification": "batch_of_entities", "primary_entity_field": "tracks"}
    assert classify_field_grain("tracks.last_associated_detection_id", structure) == "association"


def test_classify_field_grain_companion_array_not_confused_with_detections():
    # "detectors" (sensor hardware metadata) must NOT be classified as
    # "detection" just because it substring-contains "detect" -- only the
    # identified primary entity array ("detections") counts.
    structure = {"classification": "batch_of_entities", "primary_entity_field": "detections"}
    assert classify_field_grain("detectors.detector_id", structure) == "batch_member"


def test_classify_field_grain_batch_nested_child():
    structure = {"classification": "batch_of_entities", "primary_entity_field": "detections"}
    assert classify_field_grain("detections.detection_metadata.echoshield.lifetime", structure) == "nested_child"


def test_classify_field_grain_single_entity_top_level_is_state_update():
    structure = {"classification": "single_entity_or_update", "primary_entity_field": None}
    assert classify_field_grain("track_id", structure) == "state_update"


def test_classify_field_grain_single_entity_nested_association():
    structure = {"classification": "single_entity_or_update", "primary_entity_field": None}
    assert classify_field_grain("associated_detections.topic_id", structure) == "association"


def test_classify_field_grain_single_entity_nested_child():
    structure = {"classification": "single_entity_or_update", "primary_entity_field": None}
    assert classify_field_grain("sensors.sensor_index", structure) == "nested_child"


# ---------------------------------------------------------------------------
# compute_identifier_field_stats -- uniqueness / distinct counting
# ---------------------------------------------------------------------------


def test_stats_all_unique_values():
    occs = [
        IdentifierOccurrence(value=v, has_field=True, message_index=i)
        for i, v in enumerate(["a", "b", "c"])
    ]
    stats = compute_identifier_field_stats(occs)
    assert stats.distinct == 3
    assert stats.populated == 3
    assert stats.uniqueness_ratio == 1.0
    assert stats.repeated_occurrence_count == 0
    assert stats.min_occurrences == 1
    assert stats.max_occurrences == 1


# ---------------------------------------------------------------------------
# compute_identifier_field_stats -- blank vs null handling
# ---------------------------------------------------------------------------


def test_stats_distinguishes_blank_string_from_null_or_unset():
    occs = [
        IdentifierOccurrence(value="", has_field=False, message_index=0),  # unset
        IdentifierOccurrence(value="", has_field=True, message_index=1),  # explicitly blank
        IdentifierOccurrence(value="x", has_field=True, message_index=2),  # populated
    ]
    stats = compute_identifier_field_stats(occs)
    assert stats.null_or_unset == 1
    assert stats.blank_string == 1
    assert stats.populated == 1
    assert stats.total_examined == 3


def test_stats_numeric_zero_is_not_treated_as_blank():
    # Blank-string tracking only applies to strings; a populated numeric 0
    # (with has_field True, i.e. presence-tracked and explicitly set) counts
    # as populated, not blank/null.
    occs = [IdentifierOccurrence(value=0, has_field=True, message_index=0)]
    stats = compute_identifier_field_stats(occs)
    assert stats.blank_string == 0
    assert stats.null_or_unset == 0
    assert stats.populated == 1


# ---------------------------------------------------------------------------
# compute_identifier_field_stats -- within- vs across-message repetition
# ---------------------------------------------------------------------------


def test_stats_within_message_repeat_detected():
    # Same value twice inside message_index=0 -- a structural anomaly for
    # an identifier-shaped field.
    occs = [
        IdentifierOccurrence(value="dup", has_field=True, message_index=0),
        IdentifierOccurrence(value="dup", has_field=True, message_index=0),
    ]
    stats = compute_identifier_field_stats(occs)
    assert stats.within_message_repeat_count == 1
    assert stats.across_message_repeat_count == 0


def test_stats_across_message_repeat_detected():
    # Same value in two different messages, once each -- consistent with a
    # persistent entity restated over time, not a within-message anomaly.
    occs = [
        IdentifierOccurrence(value="trk", has_field=True, message_index=0),
        IdentifierOccurrence(value="trk", has_field=True, message_index=1),
        IdentifierOccurrence(value="trk", has_field=True, message_index=2),
    ]
    stats = compute_identifier_field_stats(occs)
    assert stats.within_message_repeat_count == 0
    assert stats.across_message_repeat_count == 1
    assert stats.max_occurrences == 3


def test_stats_across_timestamp_repeat():
    occs = [
        IdentifierOccurrence(value="trk", has_field=True, message_index=0, log_time=100),
        IdentifierOccurrence(value="trk", has_field=True, message_index=1, log_time=200),
    ]
    stats = compute_identifier_field_stats(occs)
    assert stats.across_timestamp_repeat_count == 1


def test_stats_same_timestamp_not_counted_as_across_timestamp():
    occs = [
        IdentifierOccurrence(value="trk", has_field=True, message_index=0, log_time=100),
        IdentifierOccurrence(value="trk", has_field=True, message_index=1, log_time=100),
    ]
    stats = compute_identifier_field_stats(occs)
    assert stats.across_timestamp_repeat_count == 0
    # but it still repeats across messages
    assert stats.across_message_repeat_count == 1


# ---------------------------------------------------------------------------
# compute_identifier_field_stats -- parent-scoped uniqueness
# ---------------------------------------------------------------------------


def test_stats_parent_scoped_repeat_across_different_parents():
    # detection_id "d1" referenced by two DIFFERENT parent tracks -- a
    # conflicting association worth flagging.
    occs = [
        IdentifierOccurrence(value="d1", has_field=True, message_index=0, parent_key="trackA"),
        IdentifierOccurrence(value="d1", has_field=True, message_index=1, parent_key="trackB"),
    ]
    stats = compute_identifier_field_stats(occs)
    assert stats.across_parent_repeat_count == 1


def test_stats_parent_scoped_repeat_same_parent_not_flagged():
    occs = [
        IdentifierOccurrence(value="d1", has_field=True, message_index=0, parent_key="trackA"),
        IdentifierOccurrence(value="d1", has_field=True, message_index=1, parent_key="trackA"),
    ]
    stats = compute_identifier_field_stats(occs)
    assert stats.across_parent_repeat_count == 0


def test_stats_no_parent_context_yields_none():
    occs = [IdentifierOccurrence(value="d1", has_field=True, message_index=0)]
    stats = compute_identifier_field_stats(occs)
    assert stats.across_parent_repeat_count is None


# ---------------------------------------------------------------------------
# classify_repetition_expectation
# ---------------------------------------------------------------------------


def test_repetition_expected_state_history():
    occs = [
        IdentifierOccurrence(value="trk", has_field=True, message_index=i) for i in range(5)
    ]
    stats = compute_identifier_field_stats(occs)
    structure = {"classification": "single_entity_or_update"}
    result = classify_repetition_expectation("state_update", stats, expected_globally_unique=False)
    assert result == "expected_state_history"


def test_repetition_unexpected_within_message_for_globally_unique_field():
    occs = [
        IdentifierOccurrence(value="det1", has_field=True, message_index=0),
        IdentifierOccurrence(value="det1", has_field=True, message_index=0),
    ]
    stats = compute_identifier_field_stats(occs)
    result = classify_repetition_expectation("detection", stats, expected_globally_unique=True)
    assert result == "unexpected"


def test_repetition_expected_batch_framing():
    occs = [
        IdentifierOccurrence(value="idx0", has_field=True, message_index=0),
        IdentifierOccurrence(value="idx0", has_field=True, message_index=0),
    ]
    stats = compute_identifier_field_stats(occs)
    result = classify_repetition_expectation("batch_member", stats, expected_globally_unique=False)
    assert result == "expected_batch_framing"


def test_repetition_unresolved_when_no_repetition_observed():
    occs = [IdentifierOccurrence(value="only_once", has_field=True, message_index=0)]
    stats = compute_identifier_field_stats(occs)
    result = classify_repetition_expectation("detection", stats, expected_globally_unique=True)
    assert result == "unresolved"


def test_repetition_expected_state_history_for_association_grain():
    # A reference/FK-shaped field (e.g. a track's last_associated_detection_id)
    # cleanly restated across the track's own update frames, never duplicated
    # within a single frame -- same expected pattern as a persistent id.
    occs = [
        IdentifierOccurrence(value="det1", has_field=True, message_index=i) for i in range(4)
    ]
    stats = compute_identifier_field_stats(occs)
    result = classify_repetition_expectation("association", stats, expected_globally_unique=False)
    assert result == "expected_state_history"


# ---------------------------------------------------------------------------
# check_composite_key_collisions
# ---------------------------------------------------------------------------


def test_composite_key_collision_free():
    records = [
        {"channel_id": 1, "sequence": 0, "log_time": 100},
        {"channel_id": 1, "sequence": 0, "log_time": 200},
        {"channel_id": 2, "sequence": 0, "log_time": 100},
    ]
    result = check_composite_key_collisions(records, ("channel_id", "log_time"))
    assert result["collision_free"] is True
    assert result["distinct_key_values"] == 3


def test_composite_key_with_collisions():
    records = [
        {"topic": "cv_tracks", "sequence": 0},
        {"topic": "cv_tracks", "sequence": 0},
        {"topic": "cv_tracks", "sequence": 0},
    ]
    result = check_composite_key_collisions(records, ("topic", "sequence"))
    assert result["collision_free"] is False
    assert result["colliding_key_count"] == 1
    assert result["records_involved_in_collisions"] == 3
    assert result["max_collision_size"] == 3


def test_composite_key_source_message_index_always_unique():
    records = [{"source_message_index": i} for i in range(1000)]
    result = check_composite_key_collisions(records, ("source_message_index",))
    assert result["collision_free"] is True
    assert result["distinct_key_values"] == 1000


# ---------------------------------------------------------------------------
# compare_identifier_namespaces
# ---------------------------------------------------------------------------


def test_namespace_rejected_on_type_mismatch_even_with_matching_names():
    result = compare_identifier_namespaces(
        values_a=[1, 2, 3], type_a="uint64", values_b=["1", "2", "3"], type_b="string"
    )
    assert result["type_comparable"] is False
    assert result["label"] == "rejected"
    assert result["overlap_count"] == 0


def test_namespace_rejected_on_zero_overlap_same_type():
    result = compare_identifier_namespaces(
        values_a=["a", "b"], type_a="string", values_b=["x", "y"], type_b="string"
    )
    assert result["type_comparable"] is True
    assert result["overlap_count"] == 0
    assert result["label"] == "rejected"


def test_namespace_confirmed_with_named_reference_and_high_overlap():
    result = compare_identifier_namespaces(
        values_a=[1, 2, 3, 4], type_a="uint64", values_b=[1, 2, 3], type_b="uint64",
        structural_hint="named_reference",
    )
    assert result["label"] == "confirmed"
    assert result["overlap_count"] == 3


def test_namespace_strongly_supported_without_named_reference():
    result = compare_identifier_namespaces(
        values_a=[1, 2, 3, 4], type_a="uint64", values_b=[1, 2, 3], type_b="uint64",
    )
    assert result["label"] == "strongly_supported"


def test_namespace_weak_heuristic_low_overlap():
    result = compare_identifier_namespaces(
        values_a=list(range(100)), type_a="uint64", values_b=[1, 2] + list(range(200, 300)),
        type_b="uint64",
    )
    assert result["label"] == "weak_heuristic"


# ---------------------------------------------------------------------------
# dedupe_detection_track_pairs
# ---------------------------------------------------------------------------


def test_dedupe_pairs_repeated_across_updates_not_double_counted_as_distinct():
    pairs = [("d1", "t1"), ("d1", "t1"), ("d1", "t1")]
    result = dedupe_detection_track_pairs(pairs)
    assert result["distinct_pairs"] == 1
    assert result["repeated_pair_count"] == 1
    assert result["repeated_pair_extra_occurrences"] == 2
    assert result["conflicting_detection_count"] == 0


def test_dedupe_pairs_conflicting_detection_flagged():
    pairs = [("d1", "t1"), ("d1", "t2")]
    result = dedupe_detection_track_pairs(pairs)
    assert result["distinct_pairs"] == 2
    assert result["conflicting_detection_count"] == 1
    assert result["single_persistent_track_detection_count"] == 0


def test_dedupe_pairs_single_track_detection_counted():
    pairs = [("d1", "t1"), ("d2", "t1")]
    result = dedupe_detection_track_pairs(pairs)
    assert result["conflicting_detection_count"] == 0
    assert result["single_persistent_track_detection_count"] == 2


# ---------------------------------------------------------------------------
# find_orphans
# ---------------------------------------------------------------------------


def test_find_orphans_detects_dangling_references():
    referenced = {"d1", "d2", "d3"}
    existing = {"d1", "d2"}
    result = find_orphans(referenced, existing)
    assert result["orphaned_reference_count"] == 1
    assert "d3" in result["orphaned_examples"]
    assert result["never_referenced_count"] == 0


def test_find_orphans_detects_never_referenced():
    referenced = {"d1"}
    existing = {"d1", "d2", "d3"}
    result = find_orphans(referenced, existing)
    assert result["never_referenced_count"] == 2
    assert result["orphaned_reference_count"] == 0
    assert result["matched_count"] == 1
