"""Shared pytest fixtures for the mcap_inspection helper tests.

Builds a small synthetic protobuf schema at runtime (no ``protoc`` binary is
available in this environment) covering every field shape the real MCAP
schemas exercise: plain scalars, presence-tracked (proto3 ``optional``)
scalars, repeated scalars, nested messages, repeated nested messages, enums,
map fields, and a self-referential message (to exercise the descriptor
cycle guard).
"""

from __future__ import annotations

import pytest
from google.protobuf import descriptor_pb2 as dpb
from google.protobuf.descriptor_pool import DescriptorPool
from google.protobuf.message_factory import GetMessageClass


def _build_file_descriptor() -> dpb.FileDescriptorProto:
    f = dpb.FileDescriptorProto()
    f.name = "mcap_inspection_test_schema.proto"
    f.package = "testpkg"
    f.syntax = "proto3"

    # Enum
    enum = f.enum_type.add()
    enum.name = "Status"
    v0 = enum.value.add()
    v0.name = "STATUS_UNKNOWN"
    v0.number = 0
    v1 = enum.value.add()
    v1.name = "STATUS_OK"
    v1.number = 1

    # Inner message (used for singular + repeated nested-message fields)
    inner = f.message_type.add()
    inner.name = "Inner"
    inner_field = inner.field.add()
    inner_field.name = "value"
    inner_field.number = 1
    inner_field.type = dpb.FieldDescriptorProto.TYPE_INT32
    inner_field.label = dpb.FieldDescriptorProto.LABEL_OPTIONAL
    inner_id_field = inner.field.add()
    inner_id_field.name = "inner_id"
    inner_id_field.number = 2
    inner_id_field.type = dpb.FieldDescriptorProto.TYPE_STRING
    inner_id_field.label = dpb.FieldDescriptorProto.LABEL_OPTIONAL

    # Node message: self-referential, to exercise the cycle guard.
    node = f.message_type.add()
    node.name = "Node"
    node_id = node.field.add()
    node_id.name = "id"
    node_id.number = 1
    node_id.type = dpb.FieldDescriptorProto.TYPE_STRING
    node_id.label = dpb.FieldDescriptorProto.LABEL_OPTIONAL
    node_children = node.field.add()
    node_children.name = "children"
    node_children.number = 2
    node_children.type = dpb.FieldDescriptorProto.TYPE_MESSAGE
    node_children.type_name = ".testpkg.Node"
    node_children.label = dpb.FieldDescriptorProto.LABEL_REPEATED

    # Sample message: the main test subject.
    sample = f.message_type.add()
    sample.name = "Sample"

    f1 = sample.field.add()
    f1.name = "id"
    f1.number = 1
    f1.type = dpb.FieldDescriptorProto.TYPE_STRING
    f1.label = dpb.FieldDescriptorProto.LABEL_OPTIONAL

    oneof = sample.oneof_decl.add()
    oneof.name = "_nickname"
    f2 = sample.field.add()
    f2.name = "nickname"
    f2.number = 2
    f2.type = dpb.FieldDescriptorProto.TYPE_STRING
    f2.label = dpb.FieldDescriptorProto.LABEL_OPTIONAL
    f2.proto3_optional = True
    f2.oneof_index = 0

    f3 = sample.field.add()
    f3.name = "count"
    f3.number = 3
    f3.type = dpb.FieldDescriptorProto.TYPE_INT32
    f3.label = dpb.FieldDescriptorProto.LABEL_OPTIONAL

    f4 = sample.field.add()
    f4.name = "tags"
    f4.number = 4
    f4.type = dpb.FieldDescriptorProto.TYPE_INT32
    f4.label = dpb.FieldDescriptorProto.LABEL_REPEATED

    f5 = sample.field.add()
    f5.name = "inner"
    f5.number = 5
    f5.type = dpb.FieldDescriptorProto.TYPE_MESSAGE
    f5.type_name = ".testpkg.Inner"
    f5.label = dpb.FieldDescriptorProto.LABEL_OPTIONAL

    f6 = sample.field.add()
    f6.name = "inners"
    f6.number = 6
    f6.type = dpb.FieldDescriptorProto.TYPE_MESSAGE
    f6.type_name = ".testpkg.Inner"
    f6.label = dpb.FieldDescriptorProto.LABEL_REPEATED

    f7 = sample.field.add()
    f7.name = "status"
    f7.number = 7
    f7.type = dpb.FieldDescriptorProto.TYPE_ENUM
    f7.type_name = ".testpkg.Status"
    f7.label = dpb.FieldDescriptorProto.LABEL_OPTIONAL

    map_entry = sample.nested_type.add()
    map_entry.name = "AttributesEntry"
    map_entry.options.map_entry = True
    mk = map_entry.field.add()
    mk.name = "key"
    mk.number = 1
    mk.type = dpb.FieldDescriptorProto.TYPE_STRING
    mk.label = dpb.FieldDescriptorProto.LABEL_OPTIONAL
    mv = map_entry.field.add()
    mv.name = "value"
    mv.number = 2
    mv.type = dpb.FieldDescriptorProto.TYPE_INT32
    mv.label = dpb.FieldDescriptorProto.LABEL_OPTIONAL
    f8 = sample.field.add()
    f8.name = "attributes"
    f8.number = 8
    f8.type = dpb.FieldDescriptorProto.TYPE_MESSAGE
    f8.type_name = ".testpkg.Sample.AttributesEntry"
    f8.label = dpb.FieldDescriptorProto.LABEL_REPEATED

    f9 = sample.field.add()
    f9.name = "root"
    f9.number = 9
    f9.type = dpb.FieldDescriptorProto.TYPE_MESSAGE
    f9.type_name = ".testpkg.Node"
    f9.label = dpb.FieldDescriptorProto.LABEL_OPTIONAL

    return f


@pytest.fixture(scope="session")
def synthetic_schema():
    pool = DescriptorPool()
    pool.Add(_build_file_descriptor())
    sample_descriptor = pool.FindMessageTypeByName("testpkg.Sample")
    inner_descriptor = pool.FindMessageTypeByName("testpkg.Inner")
    node_descriptor = pool.FindMessageTypeByName("testpkg.Node")
    sample_cls = GetMessageClass(sample_descriptor)
    inner_cls = GetMessageClass(inner_descriptor)
    node_cls = GetMessageClass(node_descriptor)
    return {
        "Sample": sample_cls,
        "Inner": inner_cls,
        "Node": node_cls,
        "Sample_descriptor": sample_descriptor,
        "Node_descriptor": node_descriptor,
    }
