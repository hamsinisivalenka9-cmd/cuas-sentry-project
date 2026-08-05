"""Tests for the reusable protobuf-inspection helpers in
``mcap_inspection.helpers``.

These tests use a small synthetic protobuf schema (built at runtime in
``conftest.py``, since no ``protoc`` binary is available in this
environment) rather than the real MCAP file, so they run fast and do not
depend on ``data/input/sanitized.mcap``.
"""

from __future__ import annotations

from mcap_inspection.helpers import (
    FieldObservation,
    identifier_category,
    is_candidate_identifier,
    iter_field_occurrences,
    normalize_identifier_name,
    resolve_field_descriptor_chain,
    summarize_presence,
    truncate_sample,
    walk_descriptor,
)


# ---------------------------------------------------------------------------
# walk_descriptor / classify_field
# ---------------------------------------------------------------------------


def _by_path(fields, path):
    matches = [f for f in fields if f.full_path == path]
    assert len(matches) == 1, f"expected exactly one field at {path!r}, got {matches}"
    return matches[0]


def test_walk_descriptor_classifies_plain_scalar_without_presence(synthetic_schema):
    fields = walk_descriptor(synthetic_schema["Sample_descriptor"])
    id_field = _by_path(fields, "id")
    assert id_field.proto_kind == "scalar"
    assert id_field.scalar_type == "string"
    assert id_field.repeated is False
    assert id_field.has_presence is False


def test_walk_descriptor_classifies_proto3_optional_as_presence_tracked(synthetic_schema):
    fields = walk_descriptor(synthetic_schema["Sample_descriptor"])
    nickname_field = _by_path(fields, "nickname")
    assert nickname_field.has_presence is True


def test_walk_descriptor_classifies_repeated_scalar(synthetic_schema):
    fields = walk_descriptor(synthetic_schema["Sample_descriptor"])
    tags_field = _by_path(fields, "tags")
    assert tags_field.proto_kind == "scalar"
    assert tags_field.repeated is True


def test_walk_descriptor_recurses_into_nested_message(synthetic_schema):
    fields = walk_descriptor(synthetic_schema["Sample_descriptor"])
    inner_field = _by_path(fields, "inner")
    assert inner_field.proto_kind == "message"
    assert inner_field.nested is True
    assert inner_field.message_type == "testpkg.Inner"
    # Nested field should be reachable via the dotted path.
    inner_value_field = _by_path(fields, "inner.value")
    assert inner_value_field.scalar_type == "int32"
    inner_id_field = _by_path(fields, "inner.inner_id")
    assert inner_id_field.scalar_type == "string"


def test_walk_descriptor_recurses_into_repeated_nested_message(synthetic_schema):
    fields = walk_descriptor(synthetic_schema["Sample_descriptor"])
    inners_field = _by_path(fields, "inners")
    assert inners_field.repeated is True
    assert inners_field.nested is True
    # Field names inside repeated nested messages are still discoverable.
    inners_value_field = _by_path(fields, "inners.value")
    assert inners_value_field.scalar_type == "int32"


def test_walk_descriptor_classifies_enum_with_values(synthetic_schema):
    fields = walk_descriptor(synthetic_schema["Sample_descriptor"])
    status_field = _by_path(fields, "status")
    assert status_field.proto_kind == "enum"
    assert status_field.enum_type == "testpkg.Status"
    names = {v["name"] for v in status_field.enum_values}
    assert names == {"STATUS_UNKNOWN", "STATUS_OK"}


def test_walk_descriptor_classifies_map_field(synthetic_schema):
    fields = walk_descriptor(synthetic_schema["Sample_descriptor"])
    attributes_field = _by_path(fields, "attributes")
    assert attributes_field.proto_kind == "map"
    assert attributes_field.is_map is True
    assert attributes_field.map_key_type == "string"
    assert attributes_field.map_value_type == "int32"
    # Map fields must not be recursed into as nested messages.
    assert not any(f.full_path.startswith("attributes.") for f in fields)


def test_walk_descriptor_self_referential_type_does_not_infinite_loop(synthetic_schema):
    # "root" is a Node, which contains a repeated Node "children" field --
    # a genuine self-reference. Without a cycle guard this would recurse
    # forever.
    fields = walk_descriptor(synthetic_schema["Sample_descriptor"], max_depth=8)
    root_children_paths = [f.full_path for f in fields if f.full_path.startswith("root.")]
    assert "root.id" in root_children_paths
    assert "root.children" in root_children_paths
    # The recursion must have been cut off rather than exploding.
    assert len(fields) < 200


# ---------------------------------------------------------------------------
# summarize_presence
# ---------------------------------------------------------------------------


def test_summarize_presence_counts_null_unset():
    observations = [FieldObservation(has_field=False, is_repeated=False, value="")]
    result = summarize_presence(observations)
    assert result == {"total": 1, "null_or_unset": 1, "empty": 0, "populated": 0}


def test_summarize_presence_counts_empty_scalar_default():
    observations = [FieldObservation(has_field=None, is_repeated=False, value=0)]
    result = summarize_presence(observations)
    assert result == {"total": 1, "null_or_unset": 0, "empty": 1, "populated": 0}


def test_summarize_presence_counts_populated_scalar():
    observations = [FieldObservation(has_field=True, is_repeated=False, value="abc")]
    result = summarize_presence(observations)
    assert result == {"total": 1, "null_or_unset": 0, "empty": 0, "populated": 1}


def test_summarize_presence_counts_empty_and_populated_repeated():
    observations = [
        FieldObservation(has_field=None, is_repeated=True, value=[]),
        FieldObservation(has_field=None, is_repeated=True, value=[1, 2]),
    ]
    result = summarize_presence(observations)
    assert result == {"total": 2, "null_or_unset": 0, "empty": 1, "populated": 1}


def test_summarize_presence_mixed_batch():
    observations = [
        FieldObservation(has_field=False, is_repeated=False, value=""),
        FieldObservation(has_field=True, is_repeated=False, value=""),
        FieldObservation(has_field=True, is_repeated=False, value="x"),
    ]
    result = summarize_presence(observations)
    assert result == {"total": 3, "null_or_unset": 1, "empty": 1, "populated": 1}


# ---------------------------------------------------------------------------
# truncate_sample
# ---------------------------------------------------------------------------


def test_truncate_sample_short_string_unchanged():
    assert truncate_sample("hello") == "hello"


def test_truncate_sample_long_string_truncated():
    long_value = "a" * 500
    result = truncate_sample(long_value, max_len=10)
    assert len(result) <= 11  # 10 chars + ellipsis
    assert result.endswith("…")


def test_truncate_sample_bytes_never_dumped_raw():
    result = truncate_sample(b"\x00\x01\x02binarydata" * 1000)
    assert "bytes len=" in result
    assert "\\x00" not in result


def test_truncate_sample_empty_repeated():
    assert truncate_sample([]) == "<empty repeated, len=0>"


def test_truncate_sample_populated_repeated_shows_count_not_full_contents():
    big_list = list(range(10000))
    result = truncate_sample(big_list)
    assert "len=10000" in result
    assert "9999" not in result  # full contents must not be dumped


def test_truncate_sample_map_shows_count_only():
    result = truncate_sample({"a": 1, "b": 2})
    assert result == "<map len=2>"


def test_truncate_sample_numeric_and_none():
    assert truncate_sample(42) == "42"
    assert truncate_sample(None) == "None"


# ---------------------------------------------------------------------------
# identifier_category / is_candidate_identifier
# ---------------------------------------------------------------------------


def test_identifier_category_matches_expected_names():
    assert identifier_category("detection_id") == "identifier"
    assert identifier_category("track_id") == "identifier"
    assert identifier_category("sensor_id") == "identifier"
    assert identifier_category("camera_id") == "identifier"
    assert identifier_category("linked_detection_ids") == "identifier"
    assert identifier_category("sequence") == "sequence"
    assert identifier_category("seq_num") == "sequence"
    assert identifier_category("parent_track_id") == "identifier"  # id pattern wins
    assert identifier_category("timestamp") == "timestamp"


def test_identifier_category_matches_legacy_id2_and_uid_suffixes():
    # Real schemas in this project pair a legacy numeric id with a string
    # "id2"/"uid" replacement (e.g. track_id/track_id2, detection_uid).
    assert identifier_category("track_id2") == "identifier"
    assert identifier_category("asset_id2") == "identifier"
    assert identifier_category("detection_uid") == "identifier"
    assert identifier_category("target_uid") == "identifier"
    assert identifier_category("update_uid") == "identifier"


def test_identifier_category_avoids_false_positive_substrings():
    # "valid" and "grid" contain "id" as a substring but are not
    # identifier-shaped field names.
    assert identifier_category("valid") is None
    assert identifier_category("grid") is None
    assert identifier_category("solid") is None


def test_identifier_category_unrelated_field_returns_none():
    assert identifier_category("velocity") is None
    assert identifier_category("classification") is None


def test_is_candidate_identifier_wraps_category():
    assert is_candidate_identifier("track_id") is True
    assert is_candidate_identifier("velocity") is False


# ---------------------------------------------------------------------------
# normalize_identifier_name
# ---------------------------------------------------------------------------


def test_normalize_identifier_name_strips_legacy_digit_suffix():
    assert normalize_identifier_name("track_id2") == "track_id"
    assert normalize_identifier_name("track_id") == "track_id"


def test_normalize_identifier_name_strips_known_prefixes():
    assert normalize_identifier_name("last_associated_detection_id") == "detection_id"
    assert normalize_identifier_name("parent_object_track_id") == "track_id"


def test_normalize_identifier_name_normalizes_plural():
    assert normalize_identifier_name("suppressed_detection_ids") == "detection_id"


# ---------------------------------------------------------------------------
# resolve_field_descriptor_chain / iter_field_occurrences
# ---------------------------------------------------------------------------


def test_iter_field_occurrences_top_level_scalar_with_presence(synthetic_schema):
    Sample = synthetic_schema["Sample"]
    chain = resolve_field_descriptor_chain(synthetic_schema["Sample_descriptor"], "nickname")
    msg = Sample(id="a")  # nickname left unset
    occurrences = list(iter_field_occurrences(msg, chain))
    assert occurrences == [(False, "")]

    msg2 = Sample(id="a", nickname="bob")
    occurrences2 = list(iter_field_occurrences(msg2, chain))
    assert occurrences2 == [(True, "bob")]


def test_iter_field_occurrences_nested_repeated_message(synthetic_schema):
    Sample = synthetic_schema["Sample"]
    chain = resolve_field_descriptor_chain(synthetic_schema["Sample_descriptor"], "inners.inner_id")
    msg = Sample(id="a")
    msg.inners.add(inner_id="x1")
    msg.inners.add(inner_id="x2")
    msg.inners.add()  # inner_id left as default empty string
    occurrences = list(iter_field_occurrences(msg, chain))
    # inner_id has no presence tracking (plain proto3 scalar) -> has_field is None
    assert occurrences == [(None, "x1"), (None, "x2"), (None, "")]


def test_iter_field_occurrences_empty_repeated_yields_nothing(synthetic_schema):
    Sample = synthetic_schema["Sample"]
    chain = resolve_field_descriptor_chain(synthetic_schema["Sample_descriptor"], "inners.inner_id")
    msg = Sample(id="a")  # no inners added
    occurrences = list(iter_field_occurrences(msg, chain))
    assert occurrences == []


def test_iter_field_occurrences_unset_singular_nested_message_yields_nothing(synthetic_schema):
    Sample = synthetic_schema["Sample"]
    chain = resolve_field_descriptor_chain(synthetic_schema["Sample_descriptor"], "inner.inner_id")
    msg = Sample(id="a")  # inner left unset entirely
    occurrences = list(iter_field_occurrences(msg, chain))
    assert occurrences == []


def test_resolve_field_descriptor_chain_raises_on_scalar_intermediate_segment(synthetic_schema):
    import pytest

    with pytest.raises(ValueError):
        resolve_field_descriptor_chain(synthetic_schema["Sample_descriptor"], "id.nonexistent")
