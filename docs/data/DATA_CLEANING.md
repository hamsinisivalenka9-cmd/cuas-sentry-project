# Data Cleaning — Stage 6 ETL

This document records every cleaning, normalization, or exclusion rule
actually implemented in `src/cuas_etl/transform.py` and
`src/cuas_etl/load.py`, with the evidence that justified it and the
observed count it produced against the real
`data/input/sanitized.mcap` file. It does not restate the schema
design rationale — that lives in `docs/architecture/DATABASE_DESIGN.md` and
`docs/architecture/SCHEMA_REVIEW.md`. This document is about what the code *does*
to a value on its way from protobuf into a SQLite row, not about why
a table or column exists.

Nothing in this document was invented ahead of the data. Every rule
below traces back to a Stage 2/3/4/5A finding already on record, or to
a finding made directly during Stage 6 build/validation and reported
to the user at the time (the microsecond-timestamp discovery).

## How to read the matrix

| Rule | Source path | Condition | Output action | Count | Flagged? | Reason |
|---|---|---|---|---|---|---|

- **Source path**: the protobuf field(s) the rule reads, in the same
  dotted notation used in `docs/architecture/DATABASE_DESIGN.md` Section 5.
- **Condition**: exactly when the rule fires.
- **Output action**: what value ends up in the SQLite row.
- **Count**: the number of rows/values affected, from the real
  57,266-message file, as produced by `scripts/build_database.py
  --rebuild` and cross-checked by `src/cuas_etl/validation.py`.
- **Flagged?**: whether the rule also writes a `data_quality_issues`
  row (rule 12: never silently discard).

---

## 1. Timestamp handling

| Rule | Source path | Condition | Output action | Count | Flagged? | Reason |
|---|---|---|---|---|---|---|
| Nested `Timestamp` → ns | `CVDetectionFrame.capture_time`, `CVTrackFrame.capture_time`, `RadarFrame.capture_time` | Field is set (`HasField` true) | `seconds * 1_000_000_000 + nanos`, stored as `capture_time_ns` (INTEGER) | all populated occurrences (57,266 source messages × their respective frame) | No | `google.protobuf.Timestamp` is a standard 2-field (seconds, nanos) message; integer arithmetic avoids any float rounding (CLAUDE.md rule 5: preserve nanosecond precision). |
| Nested `Timestamp` → ns, unset | same three fields | Field is unset | `capture_time_ns = NULL` | 0 observed (CONFIRMED populated on every sampled/full-dataset row per `docs/architecture/DATABASE_DESIGN.md` 5.6/5.2) | No | `HasField` presence is authoritative for a singular nested message; no default-zero fabrication. |
| Plain `int64` microsecond fields → ns | `TrackState.create_timestamp`, `TrackState.last_measurement_timestamp`, `MeasurementAssociation.timestamp` | Always (no presence tracking on a plain `int64`) | `raw_value * 1_000` (`MICROSECONDS_TO_NANOSECONDS`), stored in the `*_ns` columns | 11,630 state rows + 11,992 measurement rows, all converted | No | **Discovered during Stage 6 validation, not assumed.** `check_timestamp_magnitude` flagged these three columns as ~1000x too small versus each message's own CONFIRMED-nanosecond `log_time_ns`. Direct measurement: `last_measurement_timestamp` and `measurements[].timestamp` divided by the message's own `log_time_ns`-scale reference gave a ratio of exactly `1000.0000000...` (8+ significant figures) across every sample; `create_timestamp` gave a ratio close to but not exactly 1000, exactly as expected since it reflects an earlier instant (track creation), not the current message. This proved the fields are microseconds despite their `_ns`-suffixed destination columns — a transform-layer bug fix, not a schema change (the INTEGER column type was already correct). Reported to the user as a progress-report finding at the time it was found. |
| `log_time_ns` / `publish_time_ns` | MCAP record envelope (`log_time`, `publish_time`) | Always | Stored verbatim, no conversion | 57,266 | No | Already nanoseconds at the MCAP layer (CLAUDE.md rule 5); no transformation needed or applied. |

## 2. Identifier and presence handling

| Rule | Source path | Condition | Output action | Count | Flagged? | Reason |
|---|---|---|---|---|---|---|
| Wrapped `UInt64Value` / `DoubleValue` unwrap | `CVDetection.parent_object_detection_id`, `CVTrack.parent_object_track_id`, `RadarDetection.elevation`/`range_rate`/`return_strength`/`snr`/`azimuth_sigma`/`elevation_sigma`/`range_sigma`/`range_rate_sigma`/`estimated_width_meters` | `HasField(...)` true | `.value` unwrapped into the plain column | varies per field, see `docs/architecture/DATABASE_DESIGN.md` 5.6 | No | Wrapper types exist specifically to carry presence for a scalar; `HasField` is authoritative, confirmed `has_presence=True` for every field this project reads this way (`data/output/mcap_schema_report.json`, checked directly, not assumed). |
| Wrapped value unwrap, unset | same fields | `HasField(...)` false | Column = `NULL` | `parent_object_detection_id`: 0 populated of 1,911 (CONFIRMED, Stage 3); `parent_object_track_id`: 0 populated of 9,496 (CONFIRMED, Stage 3) | No | Absence of a wrapped value is a genuine "not set" state, distinct from a real zero — never defaulted to 0. |
| `object_type.class` field access | `RadarDetection.object_type.class` | `HasField("object_type")` true | Read via `getattr(obj, "class")` since `class` is a Python reserved word, then resolved to raw+name like any other enum | all 2,929 radar detections (object_type CONFIRMED always present) | No | `class` cannot be accessed as `detection.object_type.class` in Python syntax; `getattr` is the standard workaround, not a semantic transformation. |
| `last_associated_detection_id == 0` → NULL | `CVTrack.last_associated_detection_id` (plain `uint64`, no presence tracking) | Raw value is exactly `0` | Stored as `NULL` instead of `0` | 0 rows matched this condition in the real file (every CV track state has a nonzero association from creation onward — CONFIRMED by direct comparison of every transformed row against its raw source value in `tests/test_transform.py`) | No | **The one, narrow, approved zero-to-NULL exception in the whole pipeline** (per explicit user instruction). `0` is not a valid `detection_id` in this dataset (`detection_id` values start at 1), and this is the exact convention Stage 3/4 already used when computing the CV-incorporation figures — applied here for consistency with that established analysis, and nowhere else. |

## 3. Enum handling

| Rule | Source path | Condition | Output action | Count | Flagged? | Reason |
|---|---|---|---|---|---|---|
| Enum raw + name, recognized | every `*_raw`/`*_name` column pair (e.g. `object_class`, `status`, `disposition`, `motion_state`, `semantic_confidence`, `filter_type`, `sensor_id`, `track_status`) | Raw integer matches a declared enum value on that field's own descriptor | `*_raw` = raw int, `*_name` = the schema-declared name, resolved via `field_descriptor.enum_type.values_by_number` (never a handwritten Python dict) | all populated enum occurrences across all 6 enum-bearing tables | No | Resolving from the protobuf descriptor itself guarantees the name can never drift from what the `.proto` file actually declares — no hand-maintained mapping to fall out of sync (CLAUDE.md rule 3: do not invent field/value names). |
| Enum raw + name, unrecognized | same fields | Raw integer does NOT match any declared value | `*_raw` = raw int (preserved), `*_name` = `NULL` | 0 observed in the real file (every enum value found was independently confirmed against Stage 2's captured value lists) | Would be caught by `validation.check_enum_raw_name_consistency` as a `warning`-level check if it ever occurred; none fired on this file | Preserves the raw fact even when the code doesn't recognize it, rather than fabricating a name or dropping the row — this is what makes the pipeline safe to run against a slightly different `.proto` version later. |

## 4. Repeated-field serialization

| Rule | Source path | Condition | Output action | Count | Flagged? | Reason |
|---|---|---|---|---|---|---|
| `cluster[]` → JSON | `RadarDetection.cluster` | Always (per detection) | Compact JSON array via `MessageToDict` per member, `"[]"` if empty | 2,929 rows, all `"[]"` (CONFIRMED: `cluster` is always empty in this file, per `docs/architecture/DATABASE_DESIGN.md` 5.6) | No | An empty repeated field is a real, distinguishable state (genuinely zero cluster members) — never stored as `NULL`, which would conflate "empty" with "unknown." |
| `measurements[].detection_ids[]` → JSON | `MeasurementAssociation.detection_ids` | Always (per measurement) | Compact JSON array, `"[]"` if empty | 11,992 rows; 13,596 total id occurrences, 1,717 distinct (CONFIRMED, `docs/architecture/DATABASE_DESIGN.md` 5.9) | No | Chosen over an 11th bridge table (Issue 4 decision, already reviewed in Stage 4/5A) — no required analytical query needs a relational join on these ids. Full fidelity is preserved; JSON is a serialization choice, not data loss. |

## 5. Deduplication

| Rule | Source path | Condition | Output action | Count | Flagged? | Reason |
|---|---|---|---|---|---|---|
| `cv_tracks` identity extraction | `CVTrackFrame.tracks[].track_id` across all `cv_tracks` messages | Distinct `track_id` values | One `cv_tracks` row per distinct id, first-seen order | 17 distinct ids (CONFIRMED, Stage 3) from 9,496 raw track-state restatements | No | `cv_tracks` is the persistent-entity table (grain: one row per real-world tracked object); `cv_track_states` retains every restatement, undeduplicated, as its own history table. |
| `fused_tracks` identity extraction | `TrackState.track_id2` across all `track_states` messages | Distinct `track_id2` values | One `fused_tracks` row per distinct id, first-seen order, paired with the legacy `track_id` from its first occurrence | 103 distinct ids (CONFIRMED, Stage 3) from 11,630 raw state messages | No | Same reasoning as `cv_tracks` — persistent identity vs. full state history are two different grains, each with its own table. |
| `cv_detection_track_links` bridge dedup | `CVTrack.track_id` paired with `CVTrack.last_associated_detection_id`, across all `cv_track_states` restatements | Distinct `(detection_id, track_id)` pairs with a non-NULL `detection_id` | One bridge row per distinct pair, `first_observed_log_time_ns` = the minimum `log_time_ns` at which that pair was seen | 1,864 distinct valid pairs (see Section 6 below for the 4 excluded) | No (the dedup itself isn't flagged; the excluded orphans are — see Section 6) | Without dedup, the same pairing would be double/triple-counted every time a track restates the same association across frames — CONFIRMED 1,865 extra restatements would otherwise inflate any incorporation-percentage query (`docs/architecture/DATABASE_DESIGN.md` 5.5). |
| Everything else | `source_messages`, `cv_detections`, `cv_track_states`, `radar_detections`, `fused_track_states`, `fused_track_measurements` | N/A | No deduplication applied | N/A | N/A | Per explicit instruction: these are event/history tables by design — two rows sharing similar or even identical field values (other than their key) are two genuinely distinct real-world observations, not duplicates to be merged. |
| CV class distribution | `CVTrack.class_distribution[]` | Every entry in original order | One `cv_track_class_distribution` row per entry; duplicate class values retained | 37,984 rows, four per state | No | Schema version 2 source-fidelity correction. Float values are copied exactly from decoded protobuf values and enum names use descriptor reflection. |

Schema version 2 also copies `CVDetection.focus_quality`, `focus_score`, and
`sharpness` without filtering or thresholds. These fields do not participate
in either checksum formula.

## 6. Orphan / referential-integrity exclusions

| Rule | Source path | Condition | Output action | Count | Flagged? | Reason |
|---|---|---|---|---|---|---|
| Orphaned detection reference | `CVTrack.last_associated_detection_id` | The referenced `detection_id` does not exist in the loaded `cv_detections` set | The `(detection_id, track_id)` pair is **excluded** from `cv_detection_track_links` (which has a real, enforced `FOREIGN KEY (detection_id) REFERENCES cv_detections`) | 4 distinct pairs excluded (CONFIRMED, Stage 3, re-confirmed at Stage 6 build time) | **Yes** — one `data_quality_issues` row per excluded pair, `issue_type='orphaned_detection_reference'`, `severity='warning'`, with the raw `detection_id`/`track_id` values preserved in `related_id` and `description` | `cv_detection_track_links.detection_id` is a real, enforced FK (rule 8: `PRAGMA foreign_keys = ON`); these 4 pairs would violate it if inserted. The raw fact is never discarded (rule 12) — the underlying `cv_track_states` row is preserved with its original, unmodified `last_associated_detection_id` value; only the *derived bridge row* is omitted, and the omission itself is logged. |
| Inconsistent legacy/fused id pairing | `TrackState.track_id2` paired with `TrackState.track_id` | A `track_id2` value is later seen paired with a *different* legacy `track_id` than its first occurrence | The first-observed pairing is kept in `fused_tracks`; the later occurrence's legacy id is **not** used to overwrite it | 0 observed in the real file (Stage 3 confirmed a consistent 1:1 pairing across all 11,630 rows) — this rule exists defensively and is exercised by a synthetic unit test in `tests/test_transform.py`, not by real data | Yes, if it ever fires — `issue_type='inconsistent_legacy_track_id_pairing'`, `severity='warning'` | Guards against silently overwriting an established identity pairing with a later, conflicting one; keeps the first-observed value deterministic and auditable rather than picking "last write wins" implicitly. |

## 7. Booleans and strings

| Rule | Source path | Condition | Output action | Count | Flagged? | Reason |
|---|---|---|---|---|---|---|
| Boolean → 0/1 | `CVTrack.is_manual`, `RadarDetection.is_marked` | Always (proto3 `bool` has no separate presence state) | `1` if true, `0` if false — never `NULL` | all rows in both tables | No | A proto3 scalar `bool` always has a concrete value (`false` is the wire default, not "unset"); SQLite has no native boolean type, so `INTEGER` 0/1 is the standard representation. |
| Strings preserved exactly | every `TEXT` column (`class_name`, `detection_uid`, `fused_track_id`, `track_id` on radar, `asset_id2`, etc.) | Always | Stored byte-for-byte as decoded, including empty strings | N/A | No | No reviewed rule permits trimming, casing, or blank-to-NULL conversion for any field this project handles — an empty string and a NULL are kept distinguishable throughout. |

## 8. What was deliberately NOT cleaned or transformed

These are documented scope decisions (CLAUDE.md rule 16), not omissions:

- **Deeply nested vendor/debug metadata** on `RadarDetection`
  (`detection_metadata.echoshield.*`, `debug.rada_v6_debug.*`,
  `spatial_kinematics` ECEF fields, `panel_id`) — never read by
  `transform.py` at all. None of the 6 required analytical queries
  need this detail; the source MCAP file (never modified, rule 1)
  remains the record of truth if it is ever needed.
- **`TrackState.enu_pos`, `relative_pos`, and all covariance/velocity/
  acceleration fields** — only `lla_pos` is flattened into
  `fused_track_states`. Same reasoning as above.
- **Confirmed-constant/always-empty fields** (`radar_detections.range`,
  `range_rate`, `snr`, `filter_type`, `estimated_width_meters`,
  `is_marked`, `object_type_class`, `object_class`;
  `fused_track_states.track_quality`, `parent_track_id`) — still
  extracted and stored (rule 12: never silently discard), just not
  further transformed or normalized, since there is no variation in
  this file to clean.
- **The Drone/Airplane classification question and the exact ~81%
  CV-incorporation figure** — deliberately left unresolved by the
  transform layer. `object_class_raw`/`object_class_name` on
  `fused_track_states` are stored exactly as observed from
  `proto.tower.TrackObjectClass`, which CONFIRMED has no `DRONE` or
  `AIRPLANE` value at all (`docs/architecture/DATABASE_DESIGN.md` Section 3) — no
  value is remapped or invented to force a match. The CV-incorporation
  percentage actually observed once the database is built is
  **97.54%** (1,864 of 1,911 `cv_detections` rows have at least one
  row in `cv_detection_track_links`), not ~81% — this is reported
  as an actual finding, not silently reconciled to match the
  assignment's stated target. See `docs/architecture/DATABASE_DESIGN.md` Section 2
  for the full discrepancy investigation.

## 9. Fatal vs. recoverable, at load time

`src/cuas_etl/load.py` treats exactly one class of condition as
recoverable at load time: the 4 orphaned `cv_detection_track_links`
pairs above, which are excluded in `transform.py` *before* they ever
reach `load.py` — they are never presented to SQLite as an insert
attempt in the first place. Every other constraint violation
(unexpected duplicate primary key, unexpected `UNIQUE` collision,
unexpected foreign-key failure, a failing `CHECK`, or a type-conversion
error) is treated as **fatal**: the responsible `SAVEPOINT` is rolled
back, the exact table, `source_message_id`, field, and offending row
values are reported, and the process exits nonzero. No blanket
`INSERT OR IGNORE` and no blanket `except sqlite3.IntegrityError:
continue` exist anywhere in this codebase — this was an explicit,
non-negotiable requirement, and the implementation in `load.py`
(`_insert_rows` / `_diagnose_and_raise`) has no code path that could
swallow an unrecognized error and still report success.
