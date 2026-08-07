"""Tests for src/cuas_etl/extract.py.

UNIT TESTS (below the marker) use lightweight synthetic stand-ins for
mcap's Schema/Channel/Message records -- no real file needed.

INTEGRATION TESTS (function names prefixed test_real_mcap_) open the
real data/input/sanitized.mcap file, read-only. They are the only tests
in this file that touch real data.
"""

from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest

from cuas_etl import extract


# ===========================================================================
# UNIT TESTS -- synthetic fixtures only
# ===========================================================================


def _fake_schema(schema_id: int = 3) -> SimpleNamespace:
    return SimpleNamespace(id=schema_id)


def _fake_channel(channel_id: int = 2, topic: str = "cv_detections") -> SimpleNamespace:
    return SimpleNamespace(id=channel_id, topic=topic)


def _fake_message(sequence: int = 0, log_time: int = 100, publish_time: int = 100) -> SimpleNamespace:
    return SimpleNamespace(sequence=sequence, log_time=log_time, publish_time=publish_time)


def test_build_envelope_preserves_all_fields():
    envelope = extract._build_envelope(
        source_message_id=7,
        schema=_fake_schema(schema_id=3),
        channel=_fake_channel(channel_id=2, topic="cv_detections"),
        message=_fake_message(sequence=5, log_time=1000, publish_time=1001),
    )
    assert envelope.source_message_id == 7
    assert envelope.channel_id == 2
    assert envelope.topic == "cv_detections"
    assert envelope.schema_id == 3
    assert envelope.sequence == 5
    assert envelope.log_time_ns == 1000
    assert envelope.publish_time_ns == 1001


def test_build_envelope_handles_missing_schema():
    envelope = extract._build_envelope(
        source_message_id=1,
        schema=None,
        channel=_fake_channel(),
        message=_fake_message(),
    )
    assert envelope.schema_id == -1


def test_extracted_mcap_data_topic_counts_and_total():
    data = extract.ExtractedMcapData()
    data.cv_detections.append(
        extract.ExtractedMessage(envelope=extract._build_envelope(1, _fake_schema(), _fake_channel(), _fake_message()), decoded=None)
    )
    data.cv_tracks.append(
        extract.ExtractedMessage(envelope=extract._build_envelope(2, _fake_schema(), _fake_channel(), _fake_message()), decoded=None)
    )
    assert data.topic_counts() == {
        "cv_detections": 1, "cv_tracks": 1, "radar_detections": 0, "track_states": 0,
    }
    assert data.total_message_count == 2


def test_verify_expected_message_count_passes_on_match():
    data = extract.ExtractedMcapData()
    for _ in range(5):
        data.cv_detections.append(
            extract.ExtractedMessage(envelope=extract._build_envelope(1, _fake_schema(), _fake_channel(), _fake_message()), decoded=None)
        )
    extract.verify_expected_message_count(data, expected_total=5)  # must not raise


def test_verify_expected_message_count_raises_on_mismatch():
    data = extract.ExtractedMcapData()
    data.cv_detections.append(
        extract.ExtractedMessage(envelope=extract._build_envelope(1, _fake_schema(), _fake_channel(), _fake_message()), decoded=None)
    )
    with pytest.raises(RuntimeError, match="Extracted 1 messages, expected exactly 5"):
        extract.verify_expected_message_count(data, expected_total=5)


# ===========================================================================
# INTEGRATION TESTS -- real data/input/sanitized.mcap (read-only)
# ===========================================================================


def _mcap_md5() -> str:
    digest = hashlib.md5()
    with open(extract.DEFAULT_MCAP_PATH, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_real_mcap_extract_produces_expected_topic_counts():
    data = extract.extract_mcap()
    assert data.topic_counts() == {
        "cv_detections": 7_121,
        "cv_tracks": 35_613,
        "radar_detections": 2_902,
        "track_states": 11_630,
    }
    extract.verify_expected_message_count(data)  # must not raise


def test_real_mcap_source_message_ids_are_1_based_and_contiguous():
    data = extract.extract_mcap()
    all_ids = sorted(
        m.envelope.source_message_id
        for topic_list in (data.cv_detections, data.cv_tracks, data.radar_detections, data.track_states)
        for m in topic_list
    )
    assert all_ids == list(range(1, extract.EXPECTED_TOTAL_MESSAGE_COUNT + 1))


def test_real_mcap_extraction_does_not_modify_the_source_file():
    checksum_before = _mcap_md5()
    extract.extract_mcap()
    checksum_after = _mcap_md5()
    assert checksum_before == checksum_after


def test_real_mcap_extraction_ordering_is_deterministic_across_two_runs():
    data1 = extract.extract_mcap()
    data2 = extract.extract_mcap()

    def fingerprint(data: extract.ExtractedMcapData) -> list[tuple]:
        all_msgs = data.cv_detections + data.cv_tracks + data.radar_detections + data.track_states
        return sorted(
            (m.envelope.source_message_id, m.envelope.channel_id, m.envelope.log_time_ns, m.envelope.sequence)
            for m in all_msgs
        )

    assert fingerprint(data1) == fingerprint(data2)
