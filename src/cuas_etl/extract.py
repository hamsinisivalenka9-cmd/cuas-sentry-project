"""Extract phase: read and decode data/input/sanitized.mcap.

This module ONLY reads and decodes the source file. It never cleans,
normalizes, deduplicates, or writes data anywhere -- see transform.py and
load.py for those. The source file is opened exactly once, in read-only
binary mode ('rb'), and is never modified, renamed, or deleted.

Deterministic ordering: every extracted message is assigned a
source_message_id equal to its 1-based position in
``reader.iter_decoded_messages(log_time_order=True)``. This ordering was
independently verified, before writing this module, to be deterministic
and reproducible: three full, independent reads of this exact file
produced byte-identical sequences of (channel_id, log_time, publish_time,
sequence) tuples, including stable relative order within the 9,858
same-log_time "tie groups" present in this file (up to 8 messages tied at
once). See docs/DATA_CLEANING.md for the full verification record.
Re-running extract_mcap() against the same, unmodified file therefore
always assigns the same source_message_id to the same logical message.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from mcap.reader import make_reader
from mcap_protobuf.decoder import DecoderFactory

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MCAP_PATH = REPO_ROOT / "data" / "input" / "sanitized.mcap"

EXPECTED_TOPICS: tuple[str, ...] = (
    "cv_detections",
    "cv_tracks",
    "radar_detections",
    "track_states",
)

# CONFIRMED exact count for data/input/sanitized.mcap (Stage 2/3). This is
# a property of this specific, unmodified source file, not a generic
# assumption -- see verify_expected_message_count().
EXPECTED_TOTAL_MESSAGE_COUNT = 57_266


@dataclass(frozen=True)
class SourceEnvelope:
    """The raw MCAP envelope for one message, independent of its topic.

    Every field here is preserved exactly as read from the file -- no
    cleaning or interpretation happens in this module.
    """

    source_message_id: int
    channel_id: int
    topic: str
    schema_id: int
    sequence: int
    log_time_ns: int
    publish_time_ns: int


@dataclass(frozen=True)
class ExtractedMessage:
    """One decoded MCAP message paired with its envelope.

    ``decoded`` is the already-decoded protobuf message object for this
    topic (a CVDetectionFrame, CVTrackFrame, RadarFrame, or TrackState).
    Only one representation of the decoded content is kept -- no
    duplicate copy is made anywhere in this module.
    """

    envelope: SourceEnvelope
    decoded: Any


@dataclass
class ExtractedMcapData:
    """Every message extracted from the source file, grouped by topic, in
    deterministic traversal order. This is the entire output of the
    extract phase -- transform.py consumes this and only this."""

    cv_detections: list[ExtractedMessage] = field(default_factory=list)
    cv_tracks: list[ExtractedMessage] = field(default_factory=list)
    radar_detections: list[ExtractedMessage] = field(default_factory=list)
    track_states: list[ExtractedMessage] = field(default_factory=list)

    @property
    def total_message_count(self) -> int:
        return (
            len(self.cv_detections)
            + len(self.cv_tracks)
            + len(self.radar_detections)
            + len(self.track_states)
        )

    def topic_counts(self) -> dict[str, int]:
        """Extraction counts per topic -- safe to print (counts only, no
        message content)."""
        return {
            "cv_detections": len(self.cv_detections),
            "cv_tracks": len(self.cv_tracks),
            "radar_detections": len(self.radar_detections),
            "track_states": len(self.track_states),
        }


def _build_envelope(source_message_id: int, schema: Any, channel: Any, message: Any) -> SourceEnvelope:
    """Build one SourceEnvelope from the raw mcap Schema/Channel/Message
    records for a single message.

    Pulled out as its own small, pure function (no file I/O) so it can be
    unit-tested with lightweight synthetic stand-ins for Schema/Channel/
    Message, without needing a real MCAP file.
    """
    return SourceEnvelope(
        source_message_id=source_message_id,
        channel_id=channel.id,
        topic=channel.topic,
        schema_id=schema.id if schema is not None else -1,
        sequence=message.sequence,
        log_time_ns=message.log_time,
        publish_time_ns=message.publish_time,
    )


def extract_mcap(mcap_path: Path | str = DEFAULT_MCAP_PATH) -> ExtractedMcapData:
    """Read the source MCAP file once, read-only, and decode every
    message into an ExtractedMcapData container.

    Opens ``mcap_path`` in 'rb' mode inside a ``with`` block, so the file
    handle is closed deterministically on return or on any exception --
    never left open. Raises ValueError immediately if a message on a
    topic outside EXPECTED_TOPICS is encountered, rather than silently
    dropping or misfiling it.
    """
    mcap_path = Path(mcap_path)
    extracted = ExtractedMcapData()

    topic_to_list: dict[str, list[ExtractedMessage]] = {
        "cv_detections": extracted.cv_detections,
        "cv_tracks": extracted.cv_tracks,
        "radar_detections": extracted.radar_detections,
        "track_states": extracted.track_states,
    }

    with open(mcap_path, "rb") as mcap_file:
        reader = make_reader(mcap_file, decoder_factories=[DecoderFactory()])
        source_message_id = 1
        for schema, channel, message, decoded in reader.iter_decoded_messages(log_time_order=True):
            if channel.topic not in topic_to_list:
                raise ValueError(
                    f"Unexpected topic {channel.topic!r} encountered while extracting "
                    f"{mcap_path} -- expected one of {EXPECTED_TOPICS}"
                )
            envelope = _build_envelope(source_message_id, schema, channel, message)
            topic_to_list[channel.topic].append(ExtractedMessage(envelope=envelope, decoded=decoded))
            source_message_id += 1

    return extracted


def verify_expected_message_count(
    extracted: ExtractedMcapData, expected_total: int = EXPECTED_TOTAL_MESSAGE_COUNT
) -> None:
    """Raise a clear RuntimeError if the extracted message count does not
    match the expected total for this source file.

    Kept separate from extract_mcap() itself so extract_mcap() stays
    reusable/testable against smaller inputs (e.g. a future different
    source file) without this specific-file invariant being baked in.
    """
    actual_total = extracted.total_message_count
    if actual_total != expected_total:
        raise RuntimeError(
            f"Extracted {actual_total} messages, expected exactly {expected_total} "
            f"(per topic: {extracted.topic_counts()}). This indicates the source file "
            "has changed, or extraction is not behaving as verified in "
            "docs/DATA_CLEANING.md."
        )
