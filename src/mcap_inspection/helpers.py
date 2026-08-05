"""Reusable, pure helper functions for inspecting protobuf descriptors and
decoded protobuf messages.

These functions have no file or MCAP-specific I/O: they operate on protobuf
``Descriptor`` / ``FieldDescriptor`` objects and on already-decoded protobuf
message instances. This keeps them independently unit-testable and reusable
outside of the MCAP inspection script.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Optional

from google.protobuf.descriptor import FieldDescriptor

# ---------------------------------------------------------------------------
# Descriptor walking / field classification
# ---------------------------------------------------------------------------

_SCALAR_TYPE_NAMES = {
    FieldDescriptor.TYPE_DOUBLE: "double",
    FieldDescriptor.TYPE_FLOAT: "float",
    FieldDescriptor.TYPE_INT64: "int64",
    FieldDescriptor.TYPE_UINT64: "uint64",
    FieldDescriptor.TYPE_INT32: "int32",
    FieldDescriptor.TYPE_FIXED64: "fixed64",
    FieldDescriptor.TYPE_FIXED32: "fixed32",
    FieldDescriptor.TYPE_BOOL: "bool",
    FieldDescriptor.TYPE_STRING: "string",
    FieldDescriptor.TYPE_BYTES: "bytes",
    FieldDescriptor.TYPE_UINT32: "uint32",
    FieldDescriptor.TYPE_SFIXED32: "sfixed32",
    FieldDescriptor.TYPE_SFIXED64: "sfixed64",
    FieldDescriptor.TYPE_SINT32: "sint32",
    FieldDescriptor.TYPE_SINT64: "sint64",
}


@dataclass
class FieldInfo:
    """Classification of a single protobuf field, reachable via a dotted
    ``full_path`` from some root message descriptor."""

    full_path: str
    field_name: str
    depth: int
    proto_kind: str  # "scalar" | "message" | "enum" | "map"
    scalar_type: Optional[str]
    message_type: Optional[str]
    enum_type: Optional[str]
    enum_values: Optional[list]
    repeated: bool
    is_map: bool
    map_key_type: Optional[str]
    map_value_type: Optional[str]
    has_presence: bool
    nested: bool


def classify_field(
    fd: FieldDescriptor, path_prefix: str = "", depth: int = 0
) -> FieldInfo:
    """Classify a single ``FieldDescriptor`` without recursing into it."""
    full_path = f"{path_prefix}.{fd.name}" if path_prefix else fd.name
    is_map = bool(fd.message_type is not None and fd.message_type.GetOptions().map_entry)

    if is_map:
        key_fd = fd.message_type.fields_by_name["key"]
        val_fd = fd.message_type.fields_by_name["value"]
        map_key_type = _SCALAR_TYPE_NAMES.get(key_fd.type, str(key_fd.type))
        if val_fd.type == FieldDescriptor.TYPE_MESSAGE:
            map_value_type = val_fd.message_type.full_name
        elif val_fd.type == FieldDescriptor.TYPE_ENUM:
            map_value_type = val_fd.enum_type.full_name
        else:
            map_value_type = _SCALAR_TYPE_NAMES.get(val_fd.type, str(val_fd.type))
        return FieldInfo(
            full_path=full_path,
            field_name=fd.name,
            depth=depth,
            proto_kind="map",
            scalar_type=None,
            message_type=None,
            enum_type=None,
            enum_values=None,
            repeated=True,
            is_map=True,
            map_key_type=map_key_type,
            map_value_type=map_value_type,
            has_presence=False,
            nested=False,
        )

    if fd.type == FieldDescriptor.TYPE_MESSAGE:
        return FieldInfo(
            full_path=full_path,
            field_name=fd.name,
            depth=depth,
            proto_kind="message",
            scalar_type=None,
            message_type=fd.message_type.full_name,
            enum_type=None,
            enum_values=None,
            repeated=fd.is_repeated,
            is_map=False,
            map_key_type=None,
            map_value_type=None,
            has_presence=fd.has_presence,
            nested=True,
        )

    if fd.type == FieldDescriptor.TYPE_ENUM:
        values = [{"name": v.name, "number": v.number} for v in fd.enum_type.values]
        return FieldInfo(
            full_path=full_path,
            field_name=fd.name,
            depth=depth,
            proto_kind="enum",
            scalar_type=None,
            message_type=None,
            enum_type=fd.enum_type.full_name,
            enum_values=values,
            repeated=fd.is_repeated,
            is_map=False,
            map_key_type=None,
            map_value_type=None,
            has_presence=fd.has_presence,
            nested=False,
        )

    scalar_type = _SCALAR_TYPE_NAMES.get(fd.type, str(fd.type))
    return FieldInfo(
        full_path=full_path,
        field_name=fd.name,
        depth=depth,
        proto_kind="scalar",
        scalar_type=scalar_type,
        message_type=None,
        enum_type=None,
        enum_values=None,
        repeated=fd.is_repeated,
        is_map=False,
        map_key_type=None,
        map_value_type=None,
        has_presence=fd.has_presence,
        nested=False,
    )


def walk_descriptor(
    descriptor: Any,
    path_prefix: str = "",
    depth: int = 0,
    max_depth: int = 8,
    _chain: tuple = (),
) -> list:
    """Recursively walk every field of a protobuf message ``Descriptor``,
    including fields nested inside child messages.

    A cycle guard (based on the chain of message full-names already visited
    on the current path) prevents infinite recursion for self-referential
    message types. ``max_depth`` is a secondary safety net.
    """
    results: list = []
    for fd in descriptor.fields:
        info = classify_field(fd, path_prefix, depth)
        results.append(info)
        if info.nested and not info.is_map:
            child_full_name = fd.message_type.full_name
            if child_full_name in _chain or depth >= max_depth:
                continue
            results.extend(
                walk_descriptor(
                    fd.message_type,
                    path_prefix=info.full_path,
                    depth=depth + 1,
                    max_depth=max_depth,
                    _chain=_chain + (child_full_name,),
                )
            )
    return results


# ---------------------------------------------------------------------------
# Presence summarization
# ---------------------------------------------------------------------------


@dataclass
class FieldObservation:
    """One observed occurrence of a field on a decoded message.

    ``has_field`` is ``True``/``False`` when presence is trackable (proto3
    ``optional`` scalars, proto2 fields, or singular message fields), and
    ``None`` when the field has no presence tracking (plain proto3 scalar or
    enum) -- in that case a default value cannot be distinguished from an
    explicitly-set default.
    """

    has_field: Optional[bool]
    is_repeated: bool
    value: Any


def _is_default_scalar(value: Any) -> bool:
    if isinstance(value, (bytes, str)):
        return len(value) == 0
    if isinstance(value, bool):
        return value is False
    if isinstance(value, (int, float)):
        return value == 0
    return value is None


def summarize_presence(observations: Iterable[FieldObservation]) -> dict:
    """Classify a sequence of :class:`FieldObservation` into null/unset,
    empty, and populated counts."""
    null_or_unset = 0
    empty = 0
    populated = 0
    total = 0
    for obs in observations:
        total += 1
        if obs.is_repeated:
            length = len(obs.value) if obs.value is not None else 0
            if length == 0:
                empty += 1
            else:
                populated += 1
            continue
        if obs.has_field is False:
            null_or_unset += 1
        elif _is_default_scalar(obs.value):
            empty += 1
        else:
            populated += 1
    return {
        "total": total,
        "null_or_unset": null_or_unset,
        "empty": empty,
        "populated": populated,
    }


# ---------------------------------------------------------------------------
# Safe value truncation
# ---------------------------------------------------------------------------


def truncate_sample(value: Any, max_len: int = 120) -> str:
    """Produce a short, safe preview of ``value``.

    Never returns raw bytes, complete images, or full repeated collections --
    only counts and a truncated preview of the first element, where relevant.
    """
    if value is None:
        return "None"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, bytes):
        return f"<bytes len={len(value)}>"
    if isinstance(value, str):
        return value if len(value) <= max_len else value[:max_len] + "…"
    if hasattr(value, "DESCRIPTOR") and not hasattr(value, "__len__"):
        return f"<message {value.DESCRIPTOR.name}>"
    if isinstance(value, dict) or (hasattr(value, "keys") and hasattr(value, "__len__")):
        return f"<map len={len(value)}>"
    if hasattr(value, "__len__"):
        n = len(value)
        if n == 0:
            return "<empty repeated, len=0>"
        try:
            first = value[0]
        except Exception:
            first = None
        return f"<repeated len={n}, first={truncate_sample(first, 40)}>"
    s = str(value)
    return s if len(s) <= max_len else s[:max_len] + "…"


# ---------------------------------------------------------------------------
# Candidate identifier detection
# ---------------------------------------------------------------------------

_ID_PATTERN = re.compile(
    r"(^id\d*$|_id\d*$|^ids$|_ids$|^uid$|_uid$|^uuid$|_uuid$|^guid$|_guid$)",
    re.IGNORECASE,
)
_SEQUENCE_PATTERN = re.compile(r"seq(uence)?", re.IGNORECASE)
_PARENT_LINK_PATTERN = re.compile(r"(parent|_ref$|^ref_|linked|link_)", re.IGNORECASE)
_TIMESTAMP_PATTERN = re.compile(r"(timestamp|_ts$|^ts_|time)", re.IGNORECASE)


def identifier_category(field_name: str) -> Optional[str]:
    """Return a candidate-identifier category for a field name, or ``None``.

    Categories: "identifier", "sequence", "parent_link", "timestamp".
    This is a naming heuristic only -- it does not imply uniqueness.
    """
    name = field_name.strip()
    if _ID_PATTERN.search(name):
        return "identifier"
    if _SEQUENCE_PATTERN.search(name):
        return "sequence"
    if _PARENT_LINK_PATTERN.search(name):
        return "parent_link"
    if _TIMESTAMP_PATTERN.search(name):
        return "timestamp"
    return None


def is_candidate_identifier(field_name: str) -> bool:
    return identifier_category(field_name) is not None


_NORMALIZE_PREFIXES = (
    "last_associated_",
    "parent_object_",
    "matched_",
    "source_",
    "target_",
    "parent_",
    "suppressed_",
    "primary_",
    "related_",
    "linked_",
)


def normalize_identifier_name(field_name: str) -> str:
    """Reduce an identifier-shaped field name to a comparable "core" form,
    so that e.g. ``last_associated_detection_id`` and ``detection_id``, or
    ``track_id`` and its legacy/replacement pair ``track_id2``, can be
    grouped as referring to the same conceptual identifier.

    This is a naming heuristic used to surface *candidate* relationships for
    later validation -- it does not assert that two fields are related.
    """
    name = field_name.strip().lower()
    changed = True
    while changed:
        changed = False
        for prefix in _NORMALIZE_PREFIXES:
            if name.startswith(prefix) and len(name) > len(prefix):
                name = name[len(prefix):]
                changed = True
    name = re.sub(r"\d+$", "", name)
    if name.endswith("ids"):
        name = name[:-1]
    return name


# ---------------------------------------------------------------------------
# Value extraction from decoded messages via a descriptor path
# ---------------------------------------------------------------------------


def resolve_field_descriptor_chain(root_descriptor: Any, dotted_path: str) -> list:
    """Resolve a dotted field path (as produced by :func:`walk_descriptor`)
    into a list of ``FieldDescriptor`` objects, one per path segment."""
    segments = dotted_path.split(".")
    chain = []
    descriptor = root_descriptor
    for i, seg in enumerate(segments):
        fd = descriptor.fields_by_name[seg]
        chain.append(fd)
        if i < len(segments) - 1:
            if fd.message_type is None:
                raise ValueError(
                    f"Path segment '{seg}' in '{dotted_path}' is not a message "
                    "field; cannot descend further"
                )
            descriptor = fd.message_type
    return chain


def iter_field_occurrences(
    message: Any, field_chain: list
) -> Iterator[tuple]:
    """Walk ``message`` along ``field_chain`` (as returned by
    :func:`resolve_field_descriptor_chain`), yielding one
    ``(has_field, value)`` pair per leaf occurrence.

    Intermediate repeated message fields are expanded (fanned out) so that,
    for example, a path like ``tracks.track_id`` yields one occurrence per
    element of the repeated ``tracks`` field. An unset intermediate singular
    message field yields no occurrences for that message.
    """
    fd = field_chain[0]
    rest = field_chain[1:]
    if not rest:
        if fd.is_repeated:
            for v in getattr(message, fd.name):
                yield (True, v)
        else:
            has = message.HasField(fd.name) if fd.has_presence else None
            yield (has, getattr(message, fd.name))
        return

    if fd.is_repeated:
        for sub in getattr(message, fd.name):
            yield from iter_field_occurrences(sub, rest)
    else:
        if fd.has_presence and not message.HasField(fd.name):
            return
        sub = getattr(message, fd.name)
        yield from iter_field_occurrences(sub, rest)
