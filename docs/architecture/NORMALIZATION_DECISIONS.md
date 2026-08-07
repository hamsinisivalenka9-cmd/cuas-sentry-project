# Normalization Decisions

Stage 4 deliverable, reviewed in Stage 5A (`docs/architecture/SCHEMA_REVIEW.md`) — see
the new rows below for `class_distribution`, `object_class_confidence`,
`object_class_external`, and the radar unit/population corrections; no
table's fate (own table / flattened / JSON / omitted) was reversed by the
review. This document explains, structure by structure, how
the real nested/repeated protobuf data found in Stage 2/3 was turned into
(or deliberately kept out of) the 10-table relational design in
`docs/architecture/DATABASE_DESIGN.md`. It also covers the standard normalization forms
(1NF/2NF/3NF), the different "kinds" of table used, and why the design
does not go further than it does. The explicit goal, per instruction, is
**analytical simplicity, not maximum normalization.**

---

## 1. Inventory: every repeated/nested structure found, and its fate

This table is the heart of this document — every genuinely repeated or
nested protobuf structure identified in Stage 2, and exactly what happened
to it.

| Protobuf structure | Topic | Repeated? | Fate | Reasoning |
|---|---|---|---|---|
| `CVDetectionFrame.detections[]` | cv_detections | yes | → `cv_detections` table | Distinct entity, CONFIRMED 100% unique — the clearest possible case for its own table |
| `CVDetectionFrame.detections[].bounding_box` | cv_detections | no (1:1) | Flattened to `bbox_*` columns | 1:1 nested message; no repetition, no benefit from a separate table |
| `CVDetectionFrame.capture_time` | cv_detections | no (1:1, frame-level) | Flattened to `capture_time_ns` on every detection row | 1:1 per frame; rather than a separate frame table (see Section 4), denormalized directly |
| `CVDetectionFrame.detectors[]` | cv_detections | yes | **Omitted entirely** | CONFIRMED always-empty in this file (Stage 2); a companion array, not the primary entity; adds a join with zero analytical value |
| `CVDetectionFrame.assets[]` | cv_detections | yes | **Omitted entirely** | Same reasoning — CONFIRMED always-empty |
| `CVTrackFrame.tracks[]` | cv_tracks | yes | → `cv_track_states` table | Repeated, timestamped, genuinely the batch's primary content |
| `CVTrackFrame.tracks[].track_id` (distinct values) | cv_tracks | n/a (derived) | → `cv_tracks` table | A genuinely new table not present 1:1 in the protobuf — see Section 2 |
| `CVTrackFrame.tracks[].bounding_box`, `.track_estimate` | cv_tracks | no (1:1) | Flattened (`bounding_box`) / **omitted** (`track_estimate`) | `track_estimate` is a deeply nested pose/velocity structure (4+ levels, dozens of scalar leaves) not needed by any required query — a documented scope decision, not silently dropped (source MCAP remains authoritative) |
| `CVTrackFrame.tracks[].class_distribution[]` | cv_tracks | yes | Child table `cv_track_class_distribution`; existing derived `object_class_confidence` retained | Schema version 2 preserves all 37,984 entries, source order, duplicate classifications, raw/name enum values, and exact decoded probabilities. |
| `TrackState.object_class_confidence` (scalar, not repeated) | track_states | no | → `fused_track_states.object_class_confidence` column | Not previously analyzed in Stage 2/3 or included in the original Stage 4 design at all. CONFIRMED populated on all 11,630 rows (range ~0.50–1.0) during the Stage 5A schema review, `docs/architecture/SCHEMA_REVIEW.md` finding F5 — added as a plain scalar column, zero normalization cost |
| `TrackState.object_class_external[]` | track_states | yes | **Confirmed correctly omitted** | Originally omitted as a scope decision; CONFIRMED always empty (length 0, all 11,630 rows) during the Stage 5A schema review, `docs/architecture/SCHEMA_REVIEW.md` finding F5 — the original decision was safe, now with evidence rather than assumption |
| `CVTrackFrame.tracks[].last_associated_detection_id` | cv_tracks | no (scalar) | Kept as a raw column on `cv_track_states` **and** used to derive `cv_detection_track_links` | Both a per-row raw fact (rule 12) and the source of a genuine many-to-many relationship — see Section 3 |
| `CVTrackFrame.tracks[].parent_object_track_id` | cv_tracks | no (1:1 wrapper) | Flattened to a nullable column, **not FK-enforced** | Stage 3: weak_heuristic, 0 populated — see `docs/architecture/DATABASE_DESIGN.md` Section 6 |
| `CVTrackFrame.trackers[]`, `.assets[]` | cv_tracks | yes | **Omitted entirely** | Companion arrays, CONFIRMED always-empty or near-constant with no analytical value |
| `RadarFrame.detections[]` | radar_detections | yes | → `radar_detections` table | Distinct entity, no natural id — surrogate PK |
| `RadarFrame.detections[].cluster[]` | radar_detections | yes (self-type) | `cluster_json` column | CONFIRMED always empty (length 0, all 2,929 rows); no id field exists to build a self-FK from even if populated — see Section 3 |
| `RadarFrame.detections[].detection_metadata.echoshield.*`, `.spatial_kinematics`, `.debug.*` | radar_detections | mixed | **Omitted entirely** | Deeply nested vendor/debug metadata; not needed by any required query |
| `RadarFrame.detections[].azimuth`, `.elevation` | radar_detections | no (scalar/wrapper) | Flattened to `azimuth_rad`/`elevation_rad` | Not a repeated-structure decision, but a units-clarity correction, `docs/architecture/SCHEMA_REVIEW.md` finding F4: units were never stated or verified in the original Stage 4 design; CONFIRMED radians from observed value ranges (azimuth `[0.0376, 6.2788]` ≈ `[0, 2π]`), columns renamed accordingly |
| `RadarFrame.detections[].range`, `.range_rate`, `.snr`, `.filter_type`, `.estimated_width_meters`, `.is_marked` | radar_detections | no (each scalar/wrapper) | Flattened, kept nullable | CONFIRMED (Stage 5A review, full dataset) always `0`/unset/`false` in this file — same "retain as nullable, don't discard structure" treatment as other sanitized fields (rule 12), now with full-dataset evidence rather than being unchecked |
| `TrackState` (whole message) | track_states | no (not batched) | → `fused_track_states` table | Stage 2 confirmed this topic is `single_entity_or_update`, not batched |
| `TrackState.track_id2` (distinct values) | track_states | n/a (derived) | → `fused_tracks` table | New table, same reasoning as `cv_tracks` — see Section 2 |
| `TrackState.measurements[]` | track_states | yes | → `fused_track_measurements` table | Genuinely repeated, directly serves the sensor-contribution query |
| `TrackState.measurements[].detection_ids[]` | track_states | yes (2 levels deep) | `detection_ids_json` column | Evaluated explicitly — see Section 3 |
| `TrackState.sensors[]` | track_states | yes | **Omitted entirely** | Redundant summary of `measurements` (same sensor-contribution information, largely overlapping purpose) — kept only one of the two to avoid near-duplicate tables |
| `TrackState.associated_detections[]`, `.license_plate[]`, `.counts[]`, `.object_class_confidence_distribution[]`, `.max_object_class_confidence[]`, `.identifiers[]`, `.disposition_external[]`, `.ranked_camera_feeds[]`, `.signal_summaries[]`, `.track_identity_matches[]` | track_states | yes (each) | **Omitted entirely** | Every one of these was checked in Stage 2/3 evidence and found either always-empty in this file or not needed by any of the 6 required queries; none is silently dropped — each is a documented scope decision, and the source MCAP remains available. (`object_class_external[]` has its own dedicated row above, since it received a fresh full-dataset re-check in the Stage 5A schema review rather than only the original Stage 2/3 evidence.) |
| `TrackState.identity.identity_descriptor[]` (repeated float) | track_states | yes | **Omitted entirely** | A numeric feature vector, not a relational structure — normalizing it into one row per float would add a large table with no analytical use |

---

## 2. New tables that are not 1:1 with any protobuf structure

Two tables — `cv_tracks` and `fused_tracks` — do not correspond to any
single protobuf message. They are derived by the ETL process from the
*distinct values* of an identifier field (`track_id`, `track_id2`) that
Stage 3 proved behaves as a persistent entity identity. This is a
deliberate normalization step: the raw data only ever states "here is a
track's status right now," repeated every time that status is restated;
nothing in the protobuf schema itself provides a single row per real-world
track. Extracting that distinct set into its own table is exactly what
lets `PRAGMA foreign_keys = ON` (CLAUDE.md rule 8) mean something for
these two relationships, and is the direct database-design consequence of
Stage 3's "persistent entity vs. update" analysis.

`cv_detection_track_links` is a third table not directly present in the
protobuf — see Section 3.

---

## 3. First, Second, and Third Normal Form — where this design sits

**First Normal Form (1NF)** requires every column to hold a single,
atomic value — no repeating groups inside a cell. The design honors this
everywhere **except** two explicitly-labeled JSON columns
(`radar_detections.cluster_json`, `fused_track_measurements.detection_ids_json`).
These are a deliberate, documented exception, not an oversight — see the
"JSON vs. bridge table" discussion below.

**Second Normal Form (2NF)** requires every non-key column to depend on
the *whole* primary key, not part of it (relevant for tables with
composite keys). `cv_detection_track_links` has a composite PK
`(detection_id, track_id)`; its one extra column,
`first_observed_log_time_ns`, depends on the pair as a whole (when *this
specific pairing* was first seen), not on either half alone — 2NF holds.

**Third Normal Form (3NF)** requires every non-key column to depend only
on the key, not on another non-key column. The design honors this for
every table with one deliberate, explained exception:
`fused_tracks.legacy_track_id` is fully determined by `fused_track_id`
(CONFIRMED 1:1 pairing, Stage 3), which is technically a "key determines
non-key value" relationship already satisfying 3NF, not a violation — it
is called out here because a stricter normalizer might argue the legacy
id belongs in a separate one-row mapping table. It was kept as a plain
column instead, because splitting a single 1:1 scalar fact into its own
table would be exactly the kind of over-normalization the compact-design
goal explicitly warns against, for a fact that is never independently
queried.

**Where the design deliberately does not chase 3NF further:** every enum
column is stored as *two* columns, `_raw` (the integer) and `_name` (the
resolved string) — e.g. `object_class_raw`/`object_class_name`. A purist
3NF argument would put every enum in its own lookup table (`enum_value_id`
→ `enum_name`) and reference it by foreign key. This was considered and
rejected — see Section 6.

---

## 4. Why there are no per-topic "frame" tables

The original ~28–32 table proposal included a frame/batch table for each
of the three batched topics (`cv_detection_frames`, `cv_track_frames`,
`radar_frames`), to hold frame-level metadata (sensor pose, camera
intrinsics, capture time) separately from the individual entities inside
each frame. This was removed in the compact redesign:

- Stage 2 CONFIRMED almost all of that frame-level metadata (camera
  intrinsics, mount pose, sensor_id) is always empty in this file.
- The one piece of frame-level metadata worth keeping — `capture_time` —
  is a single scalar per frame. Rather than a whole extra table (and an
  extra join for every query) for one column, it is **denormalized**:
  copied onto every entity row belonging to that frame
  (`cv_detections.capture_time_ns`, `cv_track_states.capture_time_ns`,
  `radar_detections.capture_time_ns`).
- Frame membership itself is not lost by removing these tables — every
  entity row still carries `source_message_id`, so "which other entities
  were in the same batch message" is fully recoverable by grouping on
  that column.

This is a deliberate trade-off: a small amount of repeated data
(`capture_time_ns` duplicated across every entity in a frame) in exchange
for one fewer join in every query and three fewer tables overall — the
right trade for an analytics-oriented, compact design.

---

## 5. JSON columns vs. bridge tables — the two cases evaluated

Two structures were repeated, real, and genuinely candidates for their
own bridge table. Both were evaluated the same way; they got different
answers because the evidence differed.

### `radar_detections.cluster_json`

`RadarDetection.cluster[]` is self-referential (a `RadarDetection` can
contain more `RadarDetection`s) and, per Stage 4 verification, **always
empty (length 0) across all 2,929 detections in this file.** Even
setting population aside, `RadarDetection` has no identifier field of its
own — there is no stable value a self-referencing foreign key could point
to, populated or not. A bridge/self-FK table was therefore not just
unnecessary but **not constructible** from this schema. JSON preserves
the structure for a future file where it might be populated, at zero
relational cost today.

### `fused_track_measurements.detection_ids_json`

`MeasurementAssociation.detection_ids[]` **is** populated (13,596 total
occurrences, 1,717 distinct values, Stage 2/3/4) and **does** have a real
target it could reference (`cv_detections.detection_id`). This was a
genuine, closer call. **Recommendation: JSON (Option A), not a bridge
table (Option B).** Reasoning:

- None of the 6 required analytical queries (`docs/architecture/DATABASE_DESIGN.md`
  Section 9) need a relational join on these specific ids.
- The relationship this would represent is essentially the Section 2
  detection-incorporation question, asked again from the fused side —
  valuable future work, but not a current requirement, and Section 2's
  own version of that question is already unresolved; adding a second,
  parallel bridge table before the first is settled adds complexity
  without adding answered questions.
- **Trade-off:** SQL cannot directly filter or join on individual
  detection ids inside the JSON without SQLite's JSON1 functions — a real
  cost if this relationship becomes analytically important later.
  **Upgrade path:** the JSON already holds full fidelity, so promoting it
  to a real `fused_measurement_detection_links(fused_track_measurement_id,
  detection_id)` table later is a straightforward migration with zero
  data loss — nothing about choosing JSON now forecloses that option.

---

## 6. Why there are no enum lookup tables

Every enum-typed column (for example, `object_class_raw`/`object_class_name`)
is stored as a raw integer plus its resolved name, directly on the row —
not as a foreign key into a separate `enum_values` dimension table.

- **Reasoning:** a protobuf enum's set of valid values is fixed by the
  *schema*, not by the *data* — it cannot gain or lose members at ETL
  time the way a real dimension table (like a customer or product list)
  can. A lookup table's usual purpose (avoid repeating a long value,
  allow the set of valid values to grow independently of the fact table)
  does not apply here.
- **Alternative considered:** one shared `enum_values(enum_type,
  raw_value, name)` table, referenced by FK from every enum column.
- **Why rejected:** it would add a join to essentially every analytical
  query in Section 9 of `docs/architecture/DATABASE_DESIGN.md` (which currently need
  none for this purpose), for a benefit — avoiding duplicate storage of
  short integer/string pairs — that does not matter at this data volume,
  directly contradicting the "no joins without analytical value"
  instruction.

---

## 7. Table taxonomy used in this design

The 11 tables fall into five kinds, each with different expected update
behavior (also stated per-table in `docs/architecture/DATABASE_DESIGN.md` Section 5):

- **Envelope/provenance table:** `source_messages`. Append-only; every
  other table's traceability back to the raw file runs through here.
- **Entity tables:** `cv_detections`, `radar_detections`. One row per
  distinct, one-time real-world event. Append-only.
- **Identity/reference tables:** `cv_tracks`, `fused_tracks`. One row per
  distinct persistent real-world object, holding only identity (no
  derived facts). Effectively static; new rows only when a genuinely new
  entity first appears.
- **History/state tables:** `cv_track_states`, `fused_track_states`. One
  row per restatement of an entity's state over time. Append-only; this
  *is* the "history table" pattern — new rows are added, never overwritten.
- **Child/bridge tables:** `cv_detection_track_links` (bridge — many-to-
  many between two entity tables), `fused_track_measurements` (child —
  many-to-one to a state row). Append-only.
- **Log/audit table:** `data_quality_issues`. Append-only, ETL-generated,
  no protobuf source.

No **lookup table** (a table whose rows are a fixed, small vocabulary
referenced by many other rows, distinct from an identity/reference table
for real-world entities) appears in this design — see Section 6 for why
enums, the obvious lookup-table candidate, were handled differently.

---

## 8. Why the design does not go further

Every additional table considered and rejected in Section 1 failed at
least one of the four tests from the approved compact-design requirements:
does it represent a distinct entity, a time-series history, a many-to-many
relationship, or repeated data actually needed for the 6 required
analytical queries? Where the honest answer was "no" — companion arrays
confirmed always-empty, deeply nested debug/vendor metadata, a fully
redundant second sensor-contribution structure, a numeric feature vector —
the structure was flattened, stored as JSON, or omitted with a documented
reason, rather than turned into a table for its own sake. This is the
direct, evidence-driven implementation of "the goal is analytical
simplicity, not maximum normalization."
