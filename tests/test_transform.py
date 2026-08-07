"""Tests for src/cuas_etl/transform.py.

Testing strategy note: the row-producing functions in transform.py
(transform_cv_detections, transform_cv_track_states, etc.) operate on
REAL protobuf message types (CVDetectionFrame, CVTrackFrame, ...) whose
Python classes are generated dynamically from the FileDescriptorSet
embedded inside data/input/sanitized.mcap itself -- they are not a
separately importable Python package, so there is no way to construct a
"synthetic CVDetectionFrame" without either (a) building an entire
synthetic replica of Anduril's/proto.tower's real, large schema trees by
hand (impractical and not something this project owns), or (b) using a
small slice of the real, already-decoded file.

This test file therefore uses two tiers, exactly as the project's
overall testing instructions intend:

- UNIT TESTS (below the first marker): the module's GENERIC helper
  functions (resolve_enum_name, timestamp conversions, json_array) are
  tested with fully synthetic protobuf fixtures (a small message/enum
  built from scratch, the same programmatic-descriptor technique already
  used in tests/conftest.py). derive_cv_detection_track_links, which
  operates on plain Python dicts (not protobuf messages at all), is
  tested with fully synthetic dict fixtures -- this is where dedup,
  orphan-handling, and history-retention behavior is proven, with no
  dependency on real data whatsoever.

- INTEGRATION TESTS (function names prefixed test_real_mcap_): a small
  slice of the REAL file is extracted and run through the table-specific
  transform functions, asserting on structural invariants (types,
  presence handling, enum resolution actually working, deterministic
  JSON) rather than hardcoded exact values -- this is the only practical
  way to test code whose input shape is defined by data this project
  does not control the schema of.
"""

from __future__ import annotations

import json

import pytest
from google.protobuf import descriptor_pb2 as dpb
from google.protobuf.descriptor_pool import DescriptorPool
from google.protobuf.message_factory import GetMessageClass
from google.protobuf.timestamp_pb2 import Timestamp

from cuas_etl import extract, transform


# ===========================================================================
# UNIT TESTS -- synthetic fixtures only
# ===========================================================================


@pytest.fixture(scope="module")
def synthetic_enum_message():
    """A tiny synthetic message with one enum field, built the same way
    tests/conftest.py builds its synthetic schema -- self-contained, no
    dependency on real MCAP data or a protoc binary."""
    f = dpb.FileDescriptorProto()
    f.name = "transform_test_schema.proto"
    f.package = "transformtest"
    f.syntax = "proto3"

    enum = f.enum_type.add()
    enum.name = "Color"
    v0 = enum.value.add(); v0.name = "COLOR_UNKNOWN"; v0.number = 0
    v1 = enum.value.add(); v1.name = "COLOR_RED"; v1.number = 1

    msg = f.message_type.add()
    msg.name = "Sample"
    field = msg.field.add()
    field.name = "color"
    field.number = 1
    field.type = dpb.FieldDescriptorProto.TYPE_ENUM
    field.type_name = ".transformtest.Color"
    field.label = dpb.FieldDescriptorProto.LABEL_OPTIONAL

    pool = DescriptorPool()
    pool.Add(f)
    descriptor = pool.FindMessageTypeByName("transformtest.Sample")
    return GetMessageClass(descriptor)()


def test_resolve_enum_name_known_value(synthetic_enum_message):
    field_descriptor = synthetic_enum_message.DESCRIPTOR.fields_by_name["color"]
    assert transform.resolve_enum_name(field_descriptor, 1) == "COLOR_RED"


def test_resolve_enum_name_unknown_value_returns_none_not_invented(synthetic_enum_message):
    # 99 is not a declared value on this enum -- must return None, never
    # a fabricated name (requirement: "preserve unknown numeric values
    # with a NULL name").
    field_descriptor = synthetic_enum_message.DESCRIPTOR.fields_by_name["color"]
    assert transform.resolve_enum_name(field_descriptor, 99) is None


def test_timestamp_message_to_ns_uses_integer_arithmetic():
    ts = Timestamp(seconds=100, nanos=250)
    result = transform.timestamp_message_to_ns(ts)
    assert result == 100_000_000_250
    assert isinstance(result, int)  # never a float


def test_microsecond_timestamp_to_ns_conversion():
    # Empirically confirmed conversion factor -- see transform.py's
    # module docstring and docs/DATA_CLEANING.md for the evidence.
    assert transform.microsecond_timestamp_to_ns(1_000) == 1_000_000
    assert transform.microsecond_timestamp_to_ns(0) == 0  # 0 stays 0, not converted to NULL here


def test_json_array_empty_repeated_field_is_bracket_bracket_not_null():
    assert transform.json_array([]) == "[]"


def test_json_array_preserves_order_and_is_valid_json():
    result = transform.json_array(["c", "a", "b"])
    assert result == '["c","a","b"]'  # order preserved, not sorted
    assert json.loads(result) == ["c", "a", "b"]


def test_json_array_is_deterministic_across_calls():
    values = ["x", "y", "z"]
    assert transform.json_array(values) == transform.json_array(values)


# --- derive_cv_detection_track_links: pure-dict fixtures, no protobuf ---


def _state_row(track_id, detection_id, log_time_ns):
    return {"track_id": track_id, "last_associated_detection_id": detection_id, "log_time_ns": log_time_ns}


def test_derive_links_deduplicates_repeated_restatements_into_one_row():
    # The same (track, detection) pair restated 3 times (a track update
    # over time) must collapse to exactly ONE bridge row -- but the raw
    # cv_track_states rows themselves are untouched by this function.
    rows = [_state_row(1, 100, 10), _state_row(1, 100, 20), _state_row(1, 100, 30)]
    links, orphans = transform.derive_cv_detection_track_links(rows, valid_detection_ids={100})
    assert len(links) == 1
    assert links[0] == {"detection_id": 100, "track_id": 1, "first_observed_log_time_ns": 10}
    assert orphans == []


def test_derive_links_first_observed_log_time_is_the_minimum():
    rows = [_state_row(1, 100, 30), _state_row(1, 100, 10), _state_row(1, 100, 20)]
    links, _ = transform.derive_cv_detection_track_links(rows, valid_detection_ids={100})
    assert links[0]["first_observed_log_time_ns"] == 10


def test_derive_links_excludes_orphans_and_records_one_issue_per_distinct_pair():
    rows = [_state_row(1, 999, 10), _state_row(1, 999, 20)]  # same orphan pair restated twice
    links, orphans = transform.derive_cv_detection_track_links(rows, valid_detection_ids=set())
    assert links == []
    assert len(orphans) == 1  # ONE issue for the distinct pair, not one per restatement
    assert orphans[0]["issue_type"] == "orphaned_detection_reference"
    assert orphans[0]["related_id"] == "detection_id=999,track_id=1"


def test_derive_links_none_detection_id_is_excluded_not_treated_as_a_pair():
    # last_associated_detection_id already normalized to None by
    # transform_cv_track_states (the approved zero-to-NULL convention)
    # must never become a fake "pair" with detection_id=None.
    rows = [{"track_id": 1, "last_associated_detection_id": None, "log_time_ns": 10}]
    links, orphans = transform.derive_cv_detection_track_links(rows, valid_detection_ids={100})
    assert links == []
    assert orphans == []


def test_derive_links_distinguishes_valid_and_orphan_pairs_in_same_call():
    rows = [_state_row(1, 100, 10), _state_row(2, 999, 20)]
    links, orphans = transform.derive_cv_detection_track_links(rows, valid_detection_ids={100})
    assert len(links) == 1 and links[0]["detection_id"] == 100
    assert len(orphans) == 1 and "999" in orphans[0]["related_id"]


def test_derive_links_output_is_deterministically_ordered():
    rows = [_state_row(3, 300, 1), _state_row(1, 100, 1), _state_row(2, 200, 1)]
    links, _ = transform.derive_cv_detection_track_links(rows, valid_detection_ids={100, 200, 300})
    pairs = [(r["detection_id"], r["track_id"]) for r in links]
    assert pairs == sorted(pairs)


# ===========================================================================
# INTEGRATION TESTS -- a small slice of the real data/input/sanitized.mcap
# ===========================================================================


@pytest.fixture(scope="module")
def real_extracted_slice():
    """Extract the real file once for this whole test module (fast,
    ~0.5s) and reuse it -- these tests check structural invariants on
    the full extraction, not hand-picked tiny slices, since transform.py
    has no slicing API of its own and building one just for tests would
    be untested extra code."""
    return extract.extract_mcap()


def test_real_mcap_cv_detections_field_mapping_and_types(real_extracted_slice):
    rows = transform.transform_cv_detections(real_extracted_slice)
    assert len(rows) == 1_911
    sample = rows[0]
    assert isinstance(sample["detection_id"], int)
    assert isinstance(sample["detection_uid"], str)
    assert isinstance(sample["source_message_id"], int)
    # object_class_raw/name enum resolution actually works end-to-end:
    assert isinstance(sample["object_class_raw"], int)
    assert sample["object_class_name"] is not None
    assert sample["object_class_name"].startswith("OBJECT_CLASSIFICATION_")
    assert sample["focus_quality_name"].startswith("FOCUS_SEMANTIC_QUALITY_")
    assert isinstance(sample["focus_score"], float)
    assert isinstance(sample["sharpness"], float)


def test_real_mcap_cv_detection_quality_values_match_raw(real_extracted_slice):
    rows = transform.transform_cv_detections(real_extracted_slice)
    raw = [d for msg in real_extracted_slice.cv_detections for d in msg.decoded.detections]
    for detection, row in zip(raw, rows):
        assert row["focus_quality_raw"] == detection.focus_quality
        assert row["focus_score"] == detection.focus_score.value
        assert row["sharpness"] == detection.sharpness.value


def test_real_mcap_class_distribution_preserves_every_entry_and_order(real_extracted_slice):
    rows = transform.transform_cv_track_class_distribution(real_extracted_slice)
    states = [track for msg in real_extracted_slice.cv_tracks for track in msg.decoded.tracks]
    assert len(rows) == 37_984
    offset = 0
    for state_id, track in enumerate(states, start=1):
        child_rows = rows[offset:offset + len(track.class_distribution)]
        assert [row["source_order"] for row in child_rows] == list(range(len(track.class_distribution)))
        for source_order, (entry, row) in enumerate(zip(track.class_distribution, child_rows)):
            assert row["cv_track_state_id"] == state_id
            assert row["class_raw"] == entry.classification
            assert row["probability_score"] == entry.probability_score
            assert row["source_order"] == source_order
        offset += len(track.class_distribution)
    assert offset == len(rows)
    assert [row["cv_track_class_distribution_id"] for row in rows] == list(range(1, 37_985))


def test_real_mcap_cv_detections_parent_id_hasfield_handling(real_extracted_slice):
    # CONFIRMED (Stage 3): parent_object_detection_id is unpopulated on
    # every real detection in this file -- proves the HasField-guarded
    # NULL path is exercised, not just the populated path.
    rows = transform.transform_cv_detections(real_extracted_slice)
    assert all(row["parent_object_detection_id"] is None for row in rows)


def test_real_mcap_cv_track_states_last_associated_detection_id_conversion_rule(real_extracted_slice):
    """Verify the zero-to-NULL conversion rule directly against the raw
    source values (not by assuming this file happens to contain a zero
    example): every row's transformed value must equal its raw value,
    except that raw 0 must become None.

    CONFIRMED (Stage 3/4, re-confirmed here): every track-state row in
    this file already has a genuinely non-zero raw value -- a CV track
    cannot exist without having been created from an initial detection,
    so this file never actually exercises the zero case. The conversion
    rule itself is still verified structurally below, against the raw
    values, rather than skipped.
    """
    rows = transform.transform_cv_track_states(real_extracted_slice)
    raw_values = [
        track.last_associated_detection_id
        for msg in real_extracted_slice.cv_tracks
        for track in msg.decoded.tracks
    ]
    assert len(raw_values) == len(rows)
    for raw, row in zip(raw_values, rows):
        expected = raw if raw != 0 else None
        assert row["last_associated_detection_id"] == expected

    assert all(v != 0 for v in raw_values)  # CONFIRMED: this file never has a raw 0
    assert all(row["last_associated_detection_id"] is not None for row in rows)
    assert all(row["last_associated_detection_id"] != 0 for row in rows)  # never a literal 0 in output


def test_real_mcap_cv_track_states_object_class_confidence_populated(real_extracted_slice):
    # CONFIRMED (Schema Review finding F5): populated on all 9,496 rows
    # once derived from class_distribution.
    rows = transform.transform_cv_track_states(real_extracted_slice)
    assert len(rows) == 9_496
    assert all(row["object_class_confidence"] is not None for row in rows)


def test_real_mcap_cv_track_identity_extraction_matches_confirmed_count(real_extracted_slice):
    identities = transform.extract_cv_track_identities(real_extracted_slice)
    assert len(identities) == 17
    assert len({row["track_id"] for row in identities}) == 17  # no duplicates


def test_real_mcap_fused_track_identity_extraction_matches_confirmed_count(real_extracted_slice):
    identities, issues = transform.extract_fused_track_identities(real_extracted_slice)
    assert len(identities) == 103
    # Stage 3 confirmed a consistent 1:1 legacy pairing in this file --
    # no inconsistency issues expected.
    assert issues == []


def test_real_mcap_radar_detections_cluster_json_is_always_valid_empty_array(real_extracted_slice):
    # CONFIRMED (Schema Review finding F4): cluster is always empty in
    # this file -- proves the empty-repeated-to-"[]" path, not NULL.
    rows = transform.transform_radar_detections(real_extracted_slice)
    assert len(rows) == 2_929
    assert all(row["cluster_json"] == "[]" for row in rows)


def test_real_mcap_radar_detections_azimuth_elevation_are_radians_range(real_extracted_slice):
    rows = transform.transform_radar_detections(real_extracted_slice)
    azimuths = [r["azimuth_rad"] for r in rows]
    assert min(azimuths) >= 0.0
    assert max(azimuths) <= 6.30  # confirmed radians, not degrees (Schema Review F4)


def test_real_mcap_fused_track_states_and_measurements_share_consistent_state_ids(real_extracted_slice):
    state_rows, measurement_rows = transform.transform_fused_track_states_and_measurements(real_extracted_slice)
    assert len(state_rows) == 11_630
    assert len(measurement_rows) == 11_992
    valid_state_ids = {row["fused_track_state_id"] for row in state_rows}
    # Every measurement must reference a state id that really exists in
    # the sibling list produced by the SAME function call.
    assert all(row["fused_track_state_id"] in valid_state_ids for row in measurement_rows)


def test_real_mcap_fused_track_measurements_detection_ids_json_valid(real_extracted_slice):
    _, measurement_rows = transform.transform_fused_track_states_and_measurements(real_extracted_slice)
    for row in measurement_rows:
        parsed = json.loads(row["detection_ids_json"])
        assert isinstance(parsed, list)
        assert all(isinstance(x, str) for x in parsed)


def test_real_mcap_transform_all_produces_history_not_deduplicated(real_extracted_slice):
    # History retention: cv_track_states must have MANY more rows than
    # cv_tracks (many restatements per persistent track) -- proves
    # per-state rows were never collapsed the way identities/bridge rows
    # deliberately are.
    tables = transform.transform_all(real_extracted_slice)
    assert len(tables.cv_track_states) > len(tables.cv_tracks) * 100
    assert len(tables.fused_track_states) > len(tables.fused_tracks) * 10
    # And the raw source-of-truth counts are untouched no-dedup facts:
    assert len(tables.cv_detections) == 1_911
    assert len(tables.radar_detections) == 2_929


def test_real_mcap_transform_all_data_quality_issues_match_known_orphan_count(real_extracted_slice):
    tables = transform.transform_all(real_extracted_slice)
    orphan_issues = [i for i in tables.data_quality_issues if i["issue_type"] == "orphaned_detection_reference"]
    assert len(orphan_issues) == 4  # CONFIRMED, Stage 3/4
    # Combined with the bridge-row count, reproduces Stage 3/4's total
    # distinct-pairs figure exactly: 1864 valid + 4 orphaned = 1868.
    assert len(tables.cv_detection_track_links) + len(orphan_issues) == 1_868


def test_real_mcap_transform_all_is_deterministic_across_two_runs(real_extracted_slice):
    from datetime import datetime, timezone

    fixed_now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    tables1 = transform.transform_all(real_extracted_slice, now=fixed_now)
    tables2 = transform.transform_all(real_extracted_slice, now=fixed_now)

    for table_name in (
        "source_messages", "cv_detections", "cv_tracks", "cv_track_states",
        "cv_track_class_distribution",
        "cv_detection_track_links", "radar_detections", "fused_tracks",
        "fused_track_states", "fused_track_measurements", "data_quality_issues",
    ):
        assert getattr(tables1, table_name) == getattr(tables2, table_name), (
            f"{table_name} differed between two transform_all() runs on identical input"
        )
