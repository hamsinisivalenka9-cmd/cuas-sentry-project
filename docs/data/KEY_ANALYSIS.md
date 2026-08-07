# Key / Identifier Analysis

Generated: 2026-08-05T21:44:51.279670+00:00

Read-only analysis built on `scripts/inspect_mcap.py`'s Stage 1 output. The source file `data/input/sanitized.mcap` was never modified. Field names alone are never treated as proof of a relationship -- see Identifier namespace verdicts.

## Concept discovery (assignment-named concepts vs. actual schema)

- **camera_id**: found=False
  - No field literally named 'camera_id' exists in any of the four schemas. Closest real fields: metadata.camera_name.value (google.protobuf.StringValue, string) and metadata.sensor_index (uint32) in cv_tracks/cv_detections.
- **measurement_id**: found=False
  - track_states.measurements (proto.tower.MeasurementAssociation) has no field of its own named 'measurement_id' -- it carries asset_id/asset_id2/sensor_id plus a nested repeated 'detection_ids' collection, but no self-identifying id.
- **sensor_id**: found=True
  - matches: cv_detections.metadata.sensor_id, cv_tracks.metadata.sensor_id, radar_detections.metadata.sensor_id, track_states.counts.sensor_id, track_states.measurements.sensor_id, track_states.sensors.sensor_id
- **asset_id**: found=True
  - matches: cv_detections.assets.asset_id, cv_tracks.assets.asset_id, radar_detections.asset_id, radar_detections.asset_id2, track_states.measurements.asset_id, track_states.measurements.asset_id2, track_states.ranked_camera_feeds.asset_id2, track_states.sensors.asset_id, track_states.sensors.asset_id2, track_states.track_identity_matches.source_asset_id2
- **parent_track_id**: found=True
  - matches: cv_tracks.tracks.parent_object_track_id, track_states.parent_track_id
- **nested_detection_id_collection**: found=True
  - matches: cv_detections.assets.suppressed_detection_ids, cv_detections.detections.detection_id, cv_detections.detections.parent_object_detection_id, cv_tracks.assets.suppressed_detection_ids, cv_tracks.tracks.last_associated_detection_id, track_states.last_image_detection_id, track_states.license_plate.detection_id, track_states.measurements.detection_ids

## Per-field identifier analysis

| topic | field_path | grain | type | total | populated | null/unset | blank | distinct | uniq. ratio | within-msg | across-msg | across-ts | across-parent | min/max occ | repetition |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `cv_detections` | `detections.detection_id` | detection | uint64 | 1911 | 1911 | 0 | 0 | 1911 | 1.0 | 0 | 0 | 0 | None | 1/1 | unresolved |
| `cv_detections` | `detections.detection_uid` | detection | string | 1911 | 1911 | 0 | 0 | 1911 | 1.0 | 0 | 0 | 0 | None | 1/1 | unresolved |
| `cv_detections` | `detections.parent_object_detection_id.value` | nested_child | uint64 | 0 | 0 | 0 | 0 | 0 | None | 0 | 0 | 0 | None | None/None | unresolved |
| `cv_detections` | `detectors.detector_id` | batch_member | string | 7121 | 0 | 0 | 7121 | 0 | None | 0 | 0 | 0 | None | None/None | unresolved |
| `cv_detections` | `metadata.sensor_id` | nested_child | string | 7121 | 0 | 0 | 7121 | 0 | None | 0 | 0 | 0 | None | None/None | unresolved |
| `cv_detections` | `assets.asset_id` | batch_member | string | 0 | 0 | 0 | 0 | 0 | None | 0 | 0 | 0 | None | None/None | unresolved |
| `cv_detections` | `assets.suppressed_detection_ids` | association | uint64 | 0 | 0 | 0 | 0 | 0 | None | 0 | 0 | 0 | None | None/None | unresolved |
| `cv_tracks` | `tracks.track_id` | batch_member | uint64 | 9496 | 9496 | 0 | 0 | 17 | 0.0018 | 0 | 17 | 17 | None | 4/1676 | expected_state_history |
| `cv_tracks` | `tracks.last_associated_detection_id` | association | uint64 | 9496 | 9496 | 0 | 0 | 1868 | 0.1967 | 0 | 1865 | 1865 | 0 | 1/27 | expected_state_history |
| `cv_tracks` | `tracks.parent_object_track_id.value` | nested_child | uint64 | 9496 | 0 | 9496 | 0 | 0 | None | 0 | 0 | 0 | None | None/None | unresolved |
| `cv_tracks` | `trackers.tracker_id` | batch_member | string | 35613 | 35613 | 0 | 0 | 1 | 0.0 | 0 | 1 | 1 | None | 35613/35613 | expected_state_history |
| `cv_tracks` | `metadata.sensor_id` | nested_child | string | 35613 | 0 | 0 | 35613 | 0 | None | 0 | 0 | 0 | None | None/None | unresolved |
| `cv_tracks` | `assets.asset_id` | batch_member | string | 0 | 0 | 0 | 0 | 0 | None | 0 | 0 | 0 | None | None/None | unresolved |
| `cv_tracks` | `assets.suppressed_detection_ids` | association | uint64 | 0 | 0 | 0 | 0 | 0 | None | 0 | 0 | 0 | None | None/None | unresolved |
| `radar_detections` | `detections.track_id` | detection | string | 2929 | 2929 | 0 | 0 | 81 | 0.0277 | 0 | 73 | 73 | None | 1/291 | unresolved |
| `radar_detections` | `id` | nested_child | string | 2902 | 0 | 0 | 2902 | 0 | None | 0 | 0 | 0 | None | None/None | unresolved |
| `radar_detections` | `asset_id` | nested_child | uint32 | 2902 | 2902 | 0 | 0 | 1 | 0.0003 | 0 | 1 | 1 | None | 2902/2902 | unresolved |
| `radar_detections` | `asset_id2` | nested_child | string | 2902 | 2902 | 0 | 0 | 1 | 0.0003 | 0 | 1 | 1 | None | 2902/2902 | unresolved |
| `radar_detections` | `metadata.sensor_id` | nested_child | string | 2902 | 0 | 0 | 2902 | 0 | None | 0 | 0 | 0 | None | None/None | unresolved |
| `track_states` | `track_id` | state_update | uint64 | 11630 | 11630 | 0 | 0 | 103 | 0.0089 | 0 | 97 | 97 | None | 1/521 | expected_state_history |
| `track_states` | `track_id2` | state_update | string | 11630 | 11630 | 0 | 0 | 103 | 0.0089 | 0 | 97 | 97 | None | 1/521 | expected_state_history |
| `track_states` | `parent_track_id` | state_update | string | 11630 | 0 | 0 | 11630 | 0 | None | 0 | 0 | 0 | None | None/None | unresolved |
| `track_states` | `target_uid` | state_update | string | 11630 | 0 | 0 | 11630 | 0 | None | 0 | 0 | 0 | None | None/None | unresolved |
| `track_states` | `measurements.asset_id` | nested_child | uint32 | 11992 | 11992 | 0 | 0 | 1 | 0.0001 | 1 | 1 | 1 | None | 11992/11992 | unresolved |
| `track_states` | `measurements.asset_id2` | nested_child | string | 11992 | 11992 | 0 | 0 | 1 | 0.0001 | 1 | 1 | 1 | None | 11992/11992 | unresolved |
| `track_states` | `measurements.sensor_id` | nested_child | proto.tower.SensorId | 11992 | 11992 | 0 | 0 | 3 | 0.0003 | 1 | 3 | 3 | None | 1604/7653 | unresolved |
| `track_states` | `measurements.detection_ids` | nested_child | string | 13596 | 13596 | 0 | 0 | 1717 | 0.1263 | 65 | 107 | 107 | None | 1/521 | unresolved |
| `track_states` | `sensors.asset_id` | nested_child | uint32 | 13591 | 13591 | 0 | 0 | 1 | 0.0001 | 1 | 1 | 1 | None | 13591/13591 | unresolved |
| `track_states` | `sensors.asset_id2` | nested_child | string | 13591 | 13591 | 0 | 0 | 1 | 0.0001 | 1 | 1 | 1 | None | 13591/13591 | unresolved |
| `track_states` | `sensors.sensor_id` | nested_child | proto.tower.SensorId | 13591 | 13591 | 0 | 0 | 3 | 0.0002 | 0 | 3 | 3 | None | 1961/7653 | unresolved |
| `track_states` | `track_identity_matches.matched_track_id` | association | uint64 | 0 | 0 | 0 | 0 | 0 | None | 0 | 0 | 0 | None | None/None | unresolved |
| `track_states` | `track_identity_matches.matched_track_id2` | association | string | 0 | 0 | 0 | 0 | 0 | None | 0 | 0 | 0 | None | None/None | unresolved |

## Persistent entity vs. update analysis

### `cv_tracks.tracks.track_id`

- Distinct persistent IDs: 17
- Messages per ID (min/avg/max): 4/558.588/1676
- Updates per ID (min/avg/max): 4/558.588/1676
- First/last observed log_time: 1761244500011495000 .. 1761245644648624000
- IDs with same-timestamp collision: 0
- yes -- this id alone repeats across many rows; (id, log_time) appears collision-free in this dataset, but a surrogate key is still the safer general recommendation

### `track_states.track_id2`

- Distinct persistent IDs: 103
- Messages per ID (min/avg/max): 1/112.913/521
- Updates per ID (min/avg/max): 1/112.913/521
- First/last observed log_time: 1761244500017288000 .. 1761245699943885000
- IDs with same-timestamp collision: 0
- yes -- this id alone repeats across many rows; (id, log_time) appears collision-free in this dataset, but a surrogate key is still the safer general recommendation

### `radar_detections.detections.track_id`

- Distinct persistent IDs: 81
- Messages per ID (min/avg/max): 1/36.16/291
- Updates per ID (min/avg/max): 1/36.16/291
- First/last observed log_time: 1761244500152824000 .. 1761245699884594000
- IDs with same-timestamp collision: 0
- yes -- this id alone repeats across many rows; (id, log_time) appears collision-free in this dataset, but a surrogate key is still the safer general recommendation

## CV detection-to-track relationship analysis

- Distinct CV detections existing: 1911
- Distinct CV detections referenced by tracks: 1868
- Orphaned references (referenced but missing): 4 ['81780', '82034', '82604']
- Never-referenced detections: 47 ['82022', '82023', '82024']
- Distinct (detection, track) pairs: 1868
- Pairs repeated across track updates (expected): 1865 (+7628 extra occurrences)
- Detections linked to exactly one track: 1868
- Detections linked to multiple distinct tracks (conflicting): 0 []

**Recommendation:** A future detection<->track bridge table's natural grain is one row per (detection_id, persistent track_id) pair -- i.e. UNIQUE(detection_id, track_id) -- NOT one row per cv_tracks message, since the same pair is legitimately restated on every track update. No detections were observed linked to more than one distinct track id in this dataset, so UNIQUE(detection_id) in the bridge table is plausible but should still be validated against future data before being enforced.

## Identifier namespace verdicts

| pair | type A | type B | comparable | distinct A/B | overlap | overlap% A/B | verdict | reason |
|---|---|---|---|---|---|---|---|---|
| cv_detections.detections.detection_id <-> cv_tracks.tracks.last_associated_detection_id | uint64 | uint64 | True | 1911/1868 | 1864 | 0.975/0.998 | **confirmed** | Field name/containing-message structure explicitly encodes the relationship, and observed overlap is substantial. |
| cv_tracks.tracks.track_id <-> track_states.track_id2 | uint64 | string | False | 17/103 | 0 | 0.0/0.0 | **rejected** | Protobuf types differ (uint64 vs string); values are never coerced across representations, so no comparison was made. |
| track_states.track_id2 <-> radar_detections.detections.track_id | string | string | True | 103/81 | 0 | 0.0/0.0 | **rejected** | Same scalar type, but zero observed value overlap across populated data on both sides -- values appear to live in different namespaces. |
| cv_tracks.tracks.track_id <-> radar_detections.detections.track_id | uint64 | string | False | 17/81 | 0 | 0.0/0.0 | **rejected** | Protobuf types differ (uint64 vs string); values are never coerced across representations, so no comparison was made. |
| track_states.measurements.asset_id2 <-> track_states.sensors.asset_id2 | string | string | True | 1/1 | 1 | 1.0/1.0 | **strongly_supported** | Same scalar type and substantial observed value overlap. |
| track_states.measurements.asset_id2 <-> radar_detections.asset_id2 | string | string | True | 1/1 | 1 | 1.0/1.0 | **strongly_supported** | Same scalar type and substantial observed value overlap. |
| track_states.measurements.sensor_id <-> track_states.sensors.sensor_id | proto.tower.SensorId | proto.tower.SensorId | True | 3/3 | 3 | 1.0/1.0 | **strongly_supported** | Same scalar type and substantial observed value overlap. |
| cv_tracks.tracks.parent_object_track_id.value <-> cv_tracks.tracks.track_id | uint64 | uint64 | True | 0/17 | 0 | None/0.0 | **weak_heuristic** | One or both sides have no populated values in this dataset; cannot verify. |

## Source MCAP message identity

| candidate key | total records | distinct key values | collision-free | colliding keys | records in collisions | max collision size |
|---|---|---|---|---|---|---|
| topic+sequence | 57266 | 4 | False | 4 | 57266 | 35613 |
| channel_id+sequence | 57266 | 4 | False | 4 | 57266 | 35613 |
| topic+log_time+sequence | 57266 | 52890 | False | 2737 | 7113 | 8 |
| channel_id+log_time+sequence | 57266 | 52890 | False | 2737 | 7113 | 8 |
| channel_id+log_time | 57266 | 52890 | False | 2737 | 7113 | 8 |
| source_message_index | 57266 | 57266 | True | 0 | 0 | 0 |

**Recommendation:** No tested natural/composite key (topic+sequence, channel_id+sequence, with/without log_time) is collision-free across the whole file -- MCAP 'sequence' is degenerate (observed as constant/zero per Stage 1) and does not disambiguate messages. A generated surrogate source_message_id (e.g. the monotonic read-order index used in this analysis) is the safer recommendation for uniquely identifying a source MCAP message row.

**UNIQUE constraint recommendation:** Recommend a UNIQUE constraint on the surrogate source_message_id (or, if a natural composite key above is collision-free, on that composite instead). channel_id, log_time, and publish_time should be retained as provenance columns but not relied upon alone for uniqueness.

## Candidate key recommendations

### cv_detections.detections (one raw CV detection event)

- Status: **confirmed_natural_key**
- detection_id is 1.0 unique across 1911 observed detections in this file. Note this is still only a snapshot of one sanitized file, not a cross-file guarantee.
- Recommended constraint: UNIQUE(detection_id)

### persistent CV track (conceptual entity, not a stored row)

- Status: **candidate_natural_key_requires_validation**
- track_id (17 distinct values) repeats 17 times across messages with 0 within-message duplicates -- consistent with a persistent entity restated every batch frame, not with track_id identifying a single row. A dedicated persistent_tracks table (future work) could use track_id as its natural key IF it is confirmed stable/unique per physical object across the full deployment, which this single-file snapshot cannot confirm alone.
- Recommended constraint: none at the cv_tracks row grain; UNIQUE(track_id) only if/when materialized into a persistent_tracks table

### cv_tracks.tracks row (one track's state within one batch frame)

- Status: **candidate_composite_key**
- Row grain is (source_message_id, track_id) -- track_id alone is not unique at this grain.
- Recommended constraint: UNIQUE(source_message_id, track_id)

### track_states row (one fused-track state/update)

- Status: **candidate_composite_key**
- track_id2 (string, active) and track_id (uint64, legacy) are both fully populated with identical distinct counts and repeat across many state rows -- one row per state, not per entity. A (track_id, log_time) composite was tested and its collision behavior is reported in persistent_entity_analysis.
- Recommended constraint: recommended_surrogate_key (state_id) preferred over a natural composite, given observed timestamp-collision risk -- see persistent_entity_analysis

### source MCAP message (envelope row)

- Status: **recommended_surrogate_key**
- No tested natural/composite key (topic+sequence, channel_id+sequence, with/without log_time) is collision-free across the whole file -- MCAP 'sequence' is degenerate (observed as constant/zero per Stage 1) and does not disambiguate messages. A generated surrogate source_message_id (e.g. the monotonic read-order index used in this analysis) is the safer recommendation for uniquely identifying a source MCAP message row.
- Recommended constraint: UNIQUE(source_message_id surrogate)

### cv_detections.detections.detection_id -> cv_tracks.tracks.last_associated_detection_id

- Status: **candidate_foreign_key**
- 4 orphaned reference(s) observed (referenced detection_id not present in cv_detections) and 0 detection(s) linked to more than one persistent track. Because orphans exist, this should NOT be enforced as a hard FK without staging/nullable handling for the orphaned rows.
- Recommended constraint: n/a (bridge table) -- see detection_track_relationship.grain_and_uniqueness_recommendation

### track_id sharing the same name across cv_tracks / track_states / radar_detections

- Status: **relationship_should_not_be_enforced_as_fk**
- Despite the shared field name, cv_tracks.tracks.track_id, track_states.track_id2, and radar_detections.detections.track_id show zero observed value overlap (and cv_tracks.track_id is a different protobuf type, uint64, from the two string fields). These are different identifier namespaces and must not be joined on name alone -- see identifier_namespace_verdicts.
- Recommended constraint: n/a

### track_states.measurements (nested per-state sensor contribution)

- Status: **relationship_requires_bridge_table**
- measurements has no own identifier; it carries a nested repeated detection_ids collection linking a state row's measurement to one or more CV detections. This needs a bridge/child table keyed on (state_id, measurement index, detection_id), not a scalar FK column.
- Recommended constraint: n/a (child/bridge table)

### sensor_id / asset_id / camera identity fields broadly

- Status: **relationship_requires_staging_or_nullable_handling**
- Most sensor_id/asset_id/camera-adjacent fields observed in this file are always empty (see Stage 1 risk flags), consistent with sanitization. Any future FK to a sensors/assets dimension table must be nullable and staged, not assumed populated.
- Recommended constraint: n/a
