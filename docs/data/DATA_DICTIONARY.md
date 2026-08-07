# Data Dictionary — `data/output/sentry.db`

Quick-reference manual for every table, view, and column in this
database. No prior MCAP/protobuf knowledge assumed — read the next two
sections and you're ready to write SQL. Deep implementation detail
lives in the [Implementation Notes](#implementation-notes) appendix,
not repeated per table.

## What this database contains

```
MCAP file  →  ETL pipeline  →  SQLite database  →  Analytics  →  Dashboard
```

A counter-UAS (drone-detection) recording, captured by three sensor
systems — **CV** (camera), **Radar**, and **Fusion** ("tower": CV +
radar + other inputs combined into one track per object) — decoded
once and loaded here so it can be queried with plain SQL instead of
custom decoder code.

**11 analytical tables**, grouped by sensor system, plus one
infrastructure table (`schema_version`). Every table traces back to
[`source_messages`](#source_messages), the provenance record for every
raw message.

## How to read this document

| Table kind | Meaning |
|---|---|
| **Entity** | One row per real-world object (identity only, not history). |
| **State/history** | One row per *update* to an object — the same object appears many times. |
| **Bridge** | Resolves a many-to-many relationship by storing pairs of keys. |
| **Child** | Stores a repeated/nested list, one row per list entry. |
| **Infrastructure** | Not analytical data — pipeline bookkeeping. |
| **View** | A saved query, computed live every time it's read. |

Naming conventions used throughout: columns ending in `_ns` are
nanoseconds since epoch; `*_raw`/`*_name` pairs store the same enum
twice (raw code + resolved name — see appendix).

## Database summary

| Table | Kind | Rows | Source |
|---|---|---|---|
| [`source_messages`](#source_messages) | Entity (provenance) | 57,266 | MCAP envelope (all topics) |
| [`cv_detections`](#cv_detections) | Entity | 1,911 | `cv_detections` topic |
| [`cv_tracks`](#cv_tracks) | Entity | 17 | `cv_tracks` topic |
| [`cv_track_states`](#cv_track_states) | State/history | 9,496 | `cv_tracks` topic |
| [`cv_track_class_distribution`](#cv_track_class_distribution) | Child | 37,984 | `cv_tracks` topic |
| [`cv_detection_track_links`](#cv_detection_track_links) | Bridge | 1,864 | Derived (ETL) |
| [`radar_detections`](#radar_detections) | Entity | 2,929 | `radar_detections` topic |
| [`fused_tracks`](#fused_tracks) | Entity | 103 | `track_states` topic |
| [`fused_track_states`](#fused_track_states) | State/history | 11,630 | `track_states` topic |
| [`fused_track_measurements`](#fused_track_measurements) | Child | 11,992 | `track_states` topic |
| [`data_quality_issues`](#data_quality_issues) | Entity (audit log) | 4 | ETL-generated |
| [`schema_version`](#schema_version) | Infrastructure | 1 | ETL-generated |

```
MCAP → source_messages → CV / Radar / Fusion tables → Views → SQL queries → Dashboard
```

## Table of contents

[source_messages](#source_messages) · [cv_detections](#cv_detections) ·
[cv_tracks](#cv_tracks) · [cv_track_states](#cv_track_states) ·
[cv_track_class_distribution](#cv_track_class_distribution) ·
[cv_detection_track_links](#cv_detection_track_links) ·
[radar_detections](#radar_detections) · [fused_tracks](#fused_tracks) ·
[fused_track_states](#fused_track_states) ·
[fused_track_measurements](#fused_track_measurements) ·
[data_quality_issues](#data_quality_issues) ·
[schema_version](#schema_version) · [Views](#views) ·
[Common queries](#common-queries) ·
[Implementation Notes](#implementation-notes)

---

# CV tables

`source_messages → cv_detections → cv_detection_track_links → cv_tracks → cv_track_states → cv_track_class_distribution`

## `source_messages`

### Why this table exists

One row per raw MCAP message, any topic. Lets every other table trace
back to its original message and timestamp.

### At a glance

| Attribute | Value |
|---|---|
| Purpose | Provenance record for every raw message |
| Grain | One row = one raw MCAP message |
| Rows | 57,266 |
| PK | Generated id (see appendix) |
| FK | None — root table |
| Source | MCAP record envelope, all four topics |
| Derived From | Direct source |

### Relationships

Parent
• None

Children
• `cv_detections`
• `cv_track_states`
• `radar_detections`
• `fused_track_states`

```
source_messages
      │
      ▼
(every other table)
```

### Columns

| Column | Type | PK | FK | Nullable | Description |
|---|---|---|---|---|---|
| `source_message_id` | INTEGER | Yes | | No | Generated id, in file-read order. |
| `channel_id` | INTEGER | | | No | Internal channel/stream id. |
| `topic` | TEXT | | | No | Topic name: `cv_detections`, `cv_tracks`, `radar_detections`, or `track_states`. |
| `schema_id` | INTEGER | | | No | Which protobuf message type this decodes as. |
| `sequence` | INTEGER | | | No | Recording sequence number; degenerate (4 distinct values) — don't use for ordering. |
| `log_time_ns` | INTEGER | | | No | When the message was logged. |
| `publish_time_ns` | INTEGER | | | No | When the message was published. |

---

## `cv_detections`

### Why this table exists

One row per object the camera spotted in a single frame. Kept apart
from `cv_track_states` — a detection is a raw sighting, not a tracked
object.

### At a glance

| Attribute | Value |
|---|---|
| Purpose | Raw camera detection events |
| Grain | One row = one detection in one video frame |
| Rows | 1,911 |
| PK | Native id from source data |
| FK | `source_message_id → source_messages` |
| Source | `cv_detections` topic, `CVDetectionFrame.detections[]` |
| Derived From | Direct source |

### Relationships

Parent
• `source_messages`

Children
• `cv_detection_track_links`

```
source_messages
      │
      ▼
cv_detections
      │
      ▼
cv_detection_track_links
```

### Columns

| Column | Type | PK | FK | Nullable | Description |
|---|---|---|---|---|---|
| `detection_id` | INTEGER | Yes | | No | Native detection identifier. |
| `detection_uid` | TEXT | | | No | Secondary string-form identifier. |
| `source_message_id` | INTEGER | | → `source_messages` | No | Parent raw message. |
| `capture_time_ns` | INTEGER | | | Yes | When the frame was captured. |
| `class_name` | TEXT | | | Yes | Free-text class label, e.g. `"AIR_VEHICLE"`. |
| `object_class_raw` | INTEGER | | | Yes | Raw classification value. |
| `object_class_name` | TEXT | | | Yes | Resolved classification name. |
| `bbox_left` | REAL | | | Yes | Left edge of bounding box (see appendix). |
| `bbox_top` | REAL | | | Yes | Top edge of bounding box. |
| `bbox_right` | REAL | | | Yes | Right edge of bounding box. |
| `bbox_bottom` | REAL | | | Yes | Bottom edge of bounding box. |
| `score` | REAL | | | Yes | Detector confidence score (see appendix). |
| `semantic_confidence_raw` | INTEGER | | | Yes | Confidence category, raw value. |
| `semantic_confidence_name` | TEXT | | | Yes | Confidence category, resolved name (e.g. `"HIGH"`). |
| `focus_quality_raw` | INTEGER | | | Yes | Focus-quality category (schema v2). |
| `focus_quality_name` | TEXT | | | Yes | Resolved name (schema v2). |
| `focus_score` | REAL | | | Yes | Numeric focus-quality score (schema v2, always populated). |
| `sharpness` | REAL | | | Yes | Numeric image-sharpness measurement (schema v2, always populated). |
| `detector_index` | INTEGER | | | Yes | Internal detector index, if more than one exists. |
| `disposition_raw` | INTEGER | | | Yes | Intent/threat classification; always `0`. |
| `disposition_name` | TEXT | | | Yes | Resolved name. |
| `motion_state_raw` | INTEGER | | | Yes | Moving-vs-stationary classification. |
| `motion_state_name` | TEXT | | | Yes | Resolved name. |
| `parent_object_detection_id` | INTEGER | | (not enforced) | Yes | Unused parent-detection link. |

---

## `cv_tracks`

### Why this table exists

One row per real-world object the camera followed — identity only.
Kept apart from `cv_track_states` so "object exists" is never confused
with "object was updated."

### At a glance

| Attribute | Value |
|---|---|
| Purpose | Persistent camera-tracked object identities |
| Grain | One row = one camera-tracked object |
| Rows | 17 |
| PK | Native id from source data |
| FK | None — root identity table |
| Source | `cv_tracks` topic, distinct `CVTrackFrame.tracks[].track_id` values |
| Derived From | Normalized entity |

### Relationships

Parent
• None

Children
• `cv_track_states`
• `cv_detection_track_links`

```
cv_track_states, cv_detection_track_links
      │
      ▼
cv_tracks
```

### Columns

| Column | Type | PK | FK | Nullable | Description |
|---|---|---|---|---|---|
| `track_id` | INTEGER | Yes | | No | Persistent camera-track identifier. |

---

## `cv_track_states`

### Why this table exists

One row per update to a tracked object, restated on every `cv_tracks`
message. Kept apart from `cv_tracks` since one object restates many
times (up to 1,676).

### At a glance

| Attribute | Value |
|---|---|
| Purpose | Full state history of every camera track |
| Grain | One row = one track restatement per frame |
| Rows | 9,496 |
| PK | Generated id (see appendix) |
| FK | `source_message_id → source_messages`; `track_id → cv_tracks` |
| Source | `cv_tracks` topic, `CVTrackFrame.tracks[]` |
| Derived From | Direct source |

### Relationships

Parent
• `cv_tracks`
• `source_messages`

Children
• `cv_track_class_distribution`

```
cv_tracks
      │
      ▼
cv_track_states
      │
      ▼
cv_track_class_distribution
```

### Columns

| Column | Type | PK | FK | Nullable | Description |
|---|---|---|---|---|---|
| `cv_track_state_id` | INTEGER | Yes | | No | Generated id, in read order. |
| `source_message_id` | INTEGER | | → `source_messages` | No | Parent raw message. |
| `track_id` | INTEGER | | → `cv_tracks` | No | Persistent track this update is about. |
| `log_time_ns` | INTEGER | | | No | When this update happened. |
| `track_age` | INTEGER | | | Yes | How long the track has existed so far (see appendix). |
| `status_raw` | INTEGER | | | Yes | High-level status. |
| `status_name` | TEXT | | | Yes | Resolved name (e.g. `"CV_TRACK_STATUS_ACTIVE"`). |
| `status_code_raw` | INTEGER | | | Yes | Detailed status code. |
| `status_code_name` | TEXT | | | Yes | Resolved name. |
| `object_class_raw` | INTEGER | | | Yes | Track's current classification. |
| `object_class_name` | TEXT | | | Yes | Resolved name — only `AIR_VEHICLE`/`BIRD` observed. |
| `class_name` | TEXT | | | Yes | Free-text class label. |
| `bbox_left` | REAL | | | Yes | Left edge of current bounding box. |
| `bbox_top` | REAL | | | Yes | Top edge of current bounding box. |
| `bbox_right` | REAL | | | Yes | Right edge of current bounding box. |
| `bbox_bottom` | REAL | | | Yes | Bottom edge of current bounding box. |
| `last_associated_detection_id` | INTEGER | | (not enforced) | Yes | Most recently linked detection id (see appendix). |
| `num_detection_associations` | INTEGER | | | Yes | Running count of detections ever linked to this track. |
| `object_class_confidence` | REAL | | | Yes | Classification confidence, from the candidate list (see appendix). |
| `score` | REAL | | | Yes | Track's overall confidence score (see appendix). |
| `disposition_raw` | INTEGER | | | Yes | Intent/threat classification. |
| `disposition_name` | TEXT | | | Yes | Resolved name. |
| `motion_state_raw` | INTEGER | | | Yes | Moving-vs-stationary classification. |
| `motion_state_name` | TEXT | | | Yes | Resolved name. |
| `is_manual` | INTEGER | | | Yes | `1` if a human created/adjusted this track, else `0`. |
| `parent_object_track_id` | INTEGER | | (not enforced) | Yes | Unused parent-track link. |
| `capture_time_ns` | INTEGER | | | Yes | When this frame was captured. |

---

## `cv_track_class_distribution`

### Why this table exists

Every candidate classification the tracker considered per track
state, not just the winner. Kept as its own table since it's a
repeated, nested list in the source.

### At a glance

| Attribute | Value |
|---|---|
| Purpose | Every candidate classification considered per track state |
| Grain | One row = one candidate-classification entry |
| Rows | 37,984 (9,496 states × 4 entries each) |
| PK | Generated id |
| FK | `cv_track_state_id → cv_track_states` |
| Source | `cv_tracks` topic, `CVTrack.class_distribution[]` |
| Derived From | Child table |

### Relationships

Parent
• `cv_track_states`

Children
• None

```
cv_track_states
      │
      ▼
cv_track_class_distribution
```

### Columns

| Column | Type | PK | FK | Nullable | Description |
|---|---|---|---|---|---|
| `cv_track_class_distribution_id` | INTEGER | Yes | | No | Generated id, by traversal order. |
| `cv_track_state_id` | INTEGER | | → `cv_track_states` | No | Parent track state. |
| `class_raw` | INTEGER | | | No | Candidate classification, raw enum number. |
| `class_name` | TEXT | | | Yes | Resolved name. |
| `probability_score` | REAL | | | No | Tracker's confidence in this candidate (e.g. `0.928`). |
| `source_order` | INTEGER | | UNIQUE with parent | No | Zero-based position in the original candidate list. |

---

## `cv_detection_track_links`

### Why this table exists

One row per distinct (detection, track) pairing, deduplicated from
repeated restatements. Avoids recomputing "detections that became
tracks" from scratch each query.

### At a glance

| Attribute | Value |
|---|---|
| Purpose | Deduplicated detection ↔ track associations |
| Grain | One row = one distinct (detection, track) pairing |
| Rows | 1,864 |
| PK | Composite (`detection_id`, `track_id`) — the pairing is the identity |
| FK | `detection_id → cv_detections`; `track_id → cv_tracks` |
| Source | Derived from `CVTrack.track_id` + `.last_associated_detection_id` |
| Derived From | Bridge table |

### Relationships

Parent
• `cv_detections`
• `cv_tracks`

Children
• None

```
cv_detections   cv_tracks
        │           │
        ▼           ▼
   cv_detection_track_links
```

### Columns

| Column | Type | PK | FK | Nullable | Description |
|---|---|---|---|---|---|
| `detection_id` | INTEGER | Yes (composite) | → `cv_detections` | No | The detection that was linked. |
| `track_id` | INTEGER | Yes (composite) | → `cv_tracks` | No | The track it was linked to. |
| `first_observed_log_time_ns` | INTEGER | | | Yes | Earliest time this pairing was seen. |

> This table's row count is not the ~81% checksum target — observed
> incorporation is 97.54%. See `docs/analytics/CHECKSUM_RESOLUTION.md`.

---

# Radar table

`source_messages → radar_detections`

## `radar_detections`

### Why this table exists

One row per radar reading, including any cluster-grouped
sub-detections. Kept flat — this file's radar data has no persistent
track structure of its own.

### At a glance

| Attribute | Value |
|---|---|
| Purpose | Raw radar detection readings |
| Grain | One row = one radar reading |
| Rows | 2,929 |
| PK | Generated id (no native id exists) |
| FK | `source_message_id → source_messages` |
| Source | `radar_detections` topic, `RadarFrame.detections[]` |
| Derived From | Direct source |

### Relationships

Parent
• `source_messages`

Children
• None

```
source_messages
      │
      ▼
radar_detections
```

### Columns

| Column | Type | PK | FK | Nullable | Description |
|---|---|---|---|---|---|
| `radar_detection_id` | INTEGER | Yes | | No | Generated id. |
| `source_message_id` | INTEGER | | → `source_messages` | No | Parent raw message. |
| `capture_time_ns` | INTEGER | | | Yes | When the frame was captured. |
| `range` | REAL | | | Yes | Distance to object; always `0.0`. |
| `azimuth_rad` | REAL | | | Yes | Horizontal bearing angle, in radians. |
| `elevation_rad` | REAL | | | Yes | Vertical angle, in radians. |
| `range_rate` | REAL | | | Yes | Closing/opening speed; never populated. |
| `return_strength` | REAL | | | Yes | Radar return signal strength. |
| `snr` | REAL | | | Yes | Signal-to-noise ratio; never populated. |
| `track_id` | TEXT | | (not enforced) | Yes | Radar's own track reference (see appendix). |
| `object_type_class_raw` | INTEGER | | | Yes | General object-type classification; always `0`. |
| `object_type_class_name` | TEXT | | | Yes | Resolved name. |
| `object_class_raw` | INTEGER | | | Yes | Classification; always `OBJECT_CLASS_UNCLASSIFIED`. |
| `object_class_name` | TEXT | | | Yes | Resolved name. |
| `filter_type_raw` | INTEGER | | | Yes | Radar filtering mode; always `FILTER_TYPE_UNKNOWN`. |
| `filter_type_name` | TEXT | | | Yes | Resolved name. |
| `azimuth_sigma` | REAL | | | Yes | Uncertainty estimate for azimuth. |
| `elevation_sigma` | REAL | | | Yes | Uncertainty estimate for elevation. |
| `range_sigma` | REAL | | | Yes | Uncertainty estimate for range. |
| `range_rate_sigma` | REAL | | | Yes | Uncertainty estimate for range rate. |
| `estimated_width_meters` | REAL | | | Yes | Estimated physical width; never populated. |
| `is_marked` | INTEGER | | | Yes | Whether an operator manually flagged this reading; always `false`. |
| `cluster_json` | TEXT | | | Yes | Sub-detections as JSON; always `[]` (see appendix). |

> Most columns above are constant or empty. Only
> `azimuth_rad`, `elevation_rad`, `track_id`, and `capture_time_ns`
> actually vary.

---

# Fusion tables

`source_messages → fused_track_states → fused_tracks → fused_track_measurements`

## `fused_tracks`

### Why this table exists

One row per real-world object the fusion system followed — identity
only. Kept apart from `fused_track_states`, same reason as
`cv_tracks`.

### At a glance

| Attribute | Value |
|---|---|
| Purpose | Persistent fused (multi-sensor) track identities |
| Grain | One row = one fusion-tracked object |
| Rows | 103 |
| PK | Native id from source data |
| FK | None — root identity table |
| Source | `track_states` topic, distinct `TrackState.track_id2` values |
| Derived From | Normalized entity |

### Relationships

Parent
• None

Children
• `fused_track_states`

```
fused_track_states
      │
      ▼
fused_tracks
```

### Columns

| Column | Type | PK | FK | Nullable | Description |
|---|---|---|---|---|---|
| `fused_track_id` | TEXT | Yes | | No | Persistent fused-track identifier. |
| `legacy_track_id` | INTEGER | | | Yes | Legacy numeric identifier (provenance only). |

---

## `fused_track_states`

### Why this table exists

One row per fusion-system update, mapping one-to-one with raw
`track_states` messages. Kept apart from `fused_tracks` so full
history stays queryable without losing a restatement.

### At a glance

| Attribute | Value |
|---|---|
| Purpose | Full state history of every fused track |
| Grain | One row = one fused-track update (= one message) |
| Rows | 11,630 |
| PK | Generated id |
| FK | `source_message_id → source_messages`; `fused_track_id → fused_tracks` |
| Source | `track_states` topic, whole `proto.tower.TrackState` message |
| Derived From | Direct source |

### Relationships

Parent
• `fused_tracks`
• `source_messages`

Children
• `fused_track_measurements`

```
fused_tracks
      │
      ▼
fused_track_states
      │
      ▼
fused_track_measurements
```

### Columns

| Column | Type | PK | FK | Nullable | Description |
|---|---|---|---|---|---|
| `fused_track_state_id` | INTEGER | Yes | | No | Generated id, in read order. |
| `source_message_id` | INTEGER | | → `source_messages` | No | Parent raw message. |
| `fused_track_id` | TEXT | | → `fused_tracks` | No | Persistent fused track this update is about. |
| `log_time_ns` | INTEGER | | | No | When this update happened. |
| `create_timestamp_ns` | INTEGER | | | Yes | When fusion created this track (unit-converted, see appendix). |
| `last_measurement_timestamp_ns` | INTEGER | | | Yes | Most recent measurement's time (same conversion). |
| `lla_lat` | REAL | | | Yes | Latitude, in degrees. |
| `lla_lon` | REAL | | | Yes | Longitude, in degrees. |
| `lla_alt` | REAL | | | Yes | Altitude, in meters. |
| `track_quality` | INTEGER | | | Yes | Quality score; always `0`. |
| `object_class_raw` | INTEGER | | | Yes | Classification (no DRONE/AIRPLANE value — see appendix). |
| `object_class_name` | TEXT | | | Yes | Resolved name. |
| `disposition_raw` | INTEGER | | | Yes | Intent/threat classification (genuinely varies). |
| `disposition_name` | TEXT | | | Yes | Resolved name (e.g. `"ASSUMED_FRIENDLY"`). |
| `track_status_raw` | INTEGER | | | Yes | Maturity/verification status. |
| `track_status_name` | TEXT | | | Yes | Resolved name (e.g. `"MATURE"`). |
| `parent_track_id` | TEXT | | | Yes | Meant to link to a parent track; always empty. |
| `object_class_confidence` | REAL | | | Yes | Fusion's classification confidence; populated on every row. |

---

## `fused_track_measurements`

### Why this table exists

One row per sensor measurement contributing to a fused-track update.
Kept separate since one update can draw on several sensors at once.

### At a glance

| Attribute | Value |
|---|---|
| Purpose | Per-sensor measurement contributions to fused tracks |
| Grain | One row = one measurement per update |
| Rows | 11,992 |
| PK | Generated id |
| FK | `fused_track_state_id → fused_track_states` |
| Source | `track_states` topic, `TrackState.measurements[]` |
| Derived From | Child table |

### Relationships

Parent
• `fused_track_states`

Children
• None

```
fused_track_states
      │
      ▼
fused_track_measurements
```

### Columns

| Column | Type | PK | FK | Nullable | Description |
|---|---|---|---|---|---|
| `fused_track_measurement_id` | INTEGER | Yes | | No | Generated id. |
| `fused_track_state_id` | INTEGER | | → `fused_track_states` | No | Parent fused-track update. |
| `measurement_timestamp_ns` | INTEGER | | | Yes | When this measurement was taken (unit-converted, see appendix). |
| `asset_id2` | TEXT | | | Yes | Sensor asset (string id) that produced this. |
| `sensor_id_raw` | INTEGER | | | Yes | Sensor type (resolves Drone/Airplane checksum — see appendix). |
| `sensor_id_name` | TEXT | | | Yes | Resolved name (e.g. `"TOWER_SENSOR_TRANSPONDER"`). |
| `frame_counter` | INTEGER | | | Yes | Contributing sensor's frame counter. |
| `sensor_index` | INTEGER | | | Yes | Specific sensor instance index. |
| `detection_ids_json` | TEXT | | | Yes | CV/radar detection ids, as JSON (see appendix). |

---

# Data quality table

## `data_quality_issues`

### Why this table exists

One row per data-quality problem the ETL pipeline found while
loading. Kept standalone since one issue can involve several tables
at once.

### At a glance

| Attribute | Value |
|---|---|
| Purpose | ETL-generated audit log of data-quality findings |
| Grain | One row = one detected finding |
| Rows | 4 (current build) |
| PK | Generated id |
| FK | None — `related_table`/`related_id` are free text |
| Source | None — generated by the ETL pipeline itself |
| Derived From | ETL-generated |

### Relationships

Parent
• None

Children
• None

```
(standalone — no parent or child tables)
```

### Columns

| Column | Type | PK | FK | Nullable | Description |
|---|---|---|---|---|---|
| `issue_id` | INTEGER | Yes | | No | Generated id. |
| `issue_type` | TEXT | | | No | Short code for the kind of issue, e.g. `"orphaned_detection_reference"`. |
| `severity` | TEXT | | | No | One of `info`, `warning`, `error` (CHECK-enforced). |
| `related_table` | TEXT | | (not enforced) | Yes | Which table the issue relates to. |
| `related_id` | TEXT | | | Yes | The specific id(s) involved, as free text. |
| `description` | TEXT | | | No | Human-readable explanation of the issue. |
| `detected_at_utc` | TEXT | | | No | When the issue was found (not derived from source data). |

---

# Infrastructure table

## `schema_version`

### Why this table exists

One row per schema version ever applied. Lets the ETL pipeline
confirm initialization without guessing.

### At a glance

| Attribute | Value |
|---|---|
| Purpose | Which schema version has been applied |
| Grain | One row = one distinct schema version ever applied |
| Rows | 1 (current build) |
| PK | Version number itself |
| FK | None |
| Source | None — generated by the ETL pipeline |
| Derived From | ETL-generated |

### Relationships

Parent
• None

Children
• None

```
(standalone — infrastructure, not analytical data)
```

### Columns

| Column | Type | PK | FK | Nullable | Description |
|---|---|---|---|---|---|
| `version` | INTEGER | Yes | | No | Schema version number. |
| `applied_at_utc` | TEXT | | | No | When this version was applied. |
| `description` | TEXT | | | No | Human-readable note describing what changed. |

---

## Views

| View | Kind | Purpose | Grain | Used by |
|---|---|---|---|---|
| `v_cv_track_summary` | View | First/last-seen time, state count, duration per CV track | Per `cv_tracks.track_id` | `longest_lived_tracks.sql`, `cv_detection_quality_vs_track_persistence.sql` |
| `v_fused_track_summary` | View | Same, for fused tracks | Per `fused_tracks.fused_track_id` | `fused_track_duration_by_type.sql`, `longest_lived_tracks.sql` |
| `v_fused_track_type_basis` | View | Transponder involvement, dominant class, duration — Drone/Airplane classification inputs | Per `fused_tracks.fused_track_id` | `fused_track_duration_by_type.sql` |

None are stored as columns — they recompute live (see appendix) and
none resolve "the" track classification by themselves.

## Common queries

**Database inspection**

```sql
.tables
.schema cv_detections
```

**Validation**

```sql
PRAGMA integrity_check;
PRAGMA foreign_key_check;
```
```
python scripts/run_validation.py
```

**Track history**

```sql
SELECT * FROM cv_track_states WHERE track_id = ? ORDER BY log_time_ns;
SELECT * FROM v_fused_track_summary ORDER BY duration_seconds DESC;
```

**Analytics**

```sql
-- CV incorporation percentage (97.54%, not the ~81% assignment target
-- — see docs/analytics/CHECKSUM_RESOLUTION.md)
SELECT
  (SELECT COUNT(*) FROM cv_detections) AS total,
  (SELECT COUNT(DISTINCT detection_id) FROM cv_detection_track_links) AS incorporated,
  ROUND(100.0 * (SELECT COUNT(DISTINCT detection_id) FROM cv_detection_track_links)
        / (SELECT COUNT(*) FROM cv_detections), 2) AS pct;
```
```
sqlite3 data/output/sentry.db < queries/fused_track_duration_by_type.sql
```

---

## Implementation Notes

Deep implementation detail, referenced from the tables above but not
repeated per column. This appendix answers "how did the ETL transform
the source," not "what tables exist."

**Generated primary keys.** `source_message_id`, `cv_track_state_id`,
`fused_track_state_id`, and similar surrogate keys exist because no
raw-data field is reliably unique (see `docs/data/KEY_ANALYSIS.md`).
Confirmed-unique natural keys (`detection_id`, `track_id`,
`fused_track_id`) are used directly instead.

**Timestamp unit conversion.** `fused_track_states.create_timestamp_ns`,
`.last_measurement_timestamp_ns`, and
`fused_track_measurements.measurement_timestamp_ns` convert
**microseconds to nanoseconds** at load time — the raw fields store
microseconds despite their names (`docs/data/DATA_CLEANING.md` Section
1). Every other `*_ns` column is already nanoseconds.

**Enum handling.** Every `*_raw`/`_name` pair stores one protobuf enum
twice: the raw integer, and its schema-resolved name (never
hand-typed) — enabling both filtering (`_raw`) and readability
(`_name`).

**Protobuf wrapper fields.** `focus_score`, `sharpness`, and similar
columns come from protobuf wrapper types, distinguishing "explicitly
0" from "never set." Unwrapped to nullable columns; `NULL` means never
set.

**JSON serialization.** `cluster_json` and `detection_ids_json` store
repeated sub-structures as compact JSON instead of a child table,
since no required query joins on their elements. Both are empty or
near-empty.

**Cleaning rule.** `last_associated_detection_id`: a raw `0` becomes
`NULL`, since `0` is never a real `detection_id` — the one bespoke
cleaning rule in the project (`docs/data/DATA_CLEANING.md`).

**Orphaned detection references.** 4 `cv_track_states.last_associated_detection_id`
values point to a nonexistent `detection_id`. Since
`cv_detection_track_links` enforces a real FK, these 4 are excluded
there and logged in `data_quality_issues` instead.

**`object_class_confidence` lookup.** Not a direct copy — computed by
matching `object_class_raw` against the source's `class_distribution[]`
list and taking that entry's score.

**Source-fidelity correction (schema v2).**
`cv_detections.focus_quality_raw/_name`, `.focus_score`, `.sharpness`
were added after a review found they existed in the source but
weren't yet captured (`docs/data/DATA_CLEANING.md`,
`docs/architecture/SCHEMA_REVIEW.md`).

**Unresolved units.** Bounding-box, confidence-style `score`, and
`track_age` columns likely use normalized coordinates, 0–1
probabilities, or seconds, but were never confirmed against an
external reference — marked "unresolved" rather than guessed.

**Separate identifier spaces.** `radar_detections.track_id` shares
zero values with any CV/fused track-id field despite the similar name
— confirmed, not assumed, and deliberately not a foreign key
(`docs/architecture/DATABASE_DESIGN.md` Section 6).

**Views recompute live.** No duration/summary fact is stored on
`cv_tracks`/`fused_tracks` — both state tables are append-only, so a
stored value would go stale the moment a new row arrived.

**Drone/Airplane classification.** Not stored anywhere. A fused track
is **Airplane** if any `fused_track_measurements` row has
`sensor_id_name = 'TOWER_SENSOR_TRANSPONDER'`, else **Drone** (with a
BIRD-dominant exclusion) — `TrackObjectClass` has no DRONE/AIRPLANE
value at all (`docs/analytics/CHECKSUM_RESOLUTION.md`).

**Constraints and indexes.** Exact PK/FK/UNIQUE/CHECK constraints and
every index are in `sql/schema.sql` and `sql/indexes.sql`, matching
this document exactly.
