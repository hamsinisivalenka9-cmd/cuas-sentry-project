# Table Grain Reference

Stage 4 deliverable, reviewed in Stage 5A (`docs/architecture/SCHEMA_REVIEW.md`) — no
table's grain, PK, or row count changed as a result of that review, so
this reference document is otherwise unchanged. A quick-reference
companion to `docs/architecture/DATABASE_DESIGN.md` — every table's exact grain
statement, source, and row count in one place, so "what does one row
mean here?" never has to be re-derived from the full design document. All
row counts are CONFIRMED exact (Stage 2/3, or a targeted full-dataset
check run during Stage 4 planning or the Stage 5A review — see
`docs/architecture/DATABASE_DESIGN.md` Section 1) unless marked otherwise. This document
does not repeat column lists, keys, or constraints — see
`docs/architecture/DATABASE_DESIGN.md` Section 5 for those.

Getting a table's grain wrong is one of the most common and most expensive
mistakes in database design, because every later query, join, and
constraint depends on it. Every statement below follows the exact form
"One row represents..." for that reason.

---

## 1. `source_messages`

**One row represents one raw MCAP message, from any of the four topics.**

- Source: MCAP envelope (all 4 channels) — not a protobuf message field.
- Row count: **57,266** (35,613 + 11,630 + 7,121 + 2,902).
- Kind: append-only envelope/provenance table.
- Everything else in the schema ultimately traces back to a row here.

## 2. `cv_detections`

**One row represents one individual CV detection event** — a single raw
camera-based detection, reported once, non-recurring.

- Source: topic `cv_detections`, path `CVDetectionFrame.detections[]`.
- Row count: **1,911**.
- Kind: append-only entity table. CONFIRMED 100% unique on `detection_id`
  — this detection never recurs as a separate row.

## 3. `cv_tracks`

**One row represents one persistent CV track identity** — the real-world
tracked object, independent of how many times it was restated across
frames.

- Source: topic `cv_tracks`, derived from distinct
  `CVTrackFrame.tracks[].track_id` values.
- Row count: **17**.
- Kind: static identity/reference table. Contains only the identity column
  — no derived timestamps (see `v_cv_track_summary` in
  `docs/architecture/DATABASE_DESIGN.md` Section 5.11).
- **Loading note (`docs/architecture/SCHEMA_REVIEW.md` finding F2):** must be
  populated by a complete upfront scan before any `cv_track_states` row
  is inserted — see `docs/architecture/DATABASE_DESIGN.md` Section 5.12.

## 4. `cv_track_states`

**One row represents one CV track's state as restated within one
`cv_tracks` batch message** — one track's appearance in one frame. This is
explicitly *not* the persistent track (that's `cv_tracks`, 17 rows) — it
is every one of that track's restatements across every frame.

- Source: topic `cv_tracks`, path `CVTrackFrame.tracks[]`.
- Row count: **9,496**.
- Kind: append-only history table.

## 5. `cv_detection_track_links`

**One row represents one distinct (detection, track) pairing ever
observed** — deduplicated across every track update that restates the
same association. Not "one row per restatement."

- Source: derived (ETL) from `cv_tracks.tracks[].last_associated_detection_id`
  paired with `cv_tracks.tracks[].track_id`, deduplicated.
- Row count: **1,868** distinct pairs (out of 1,865 *extra*, non-distinct
  restatements observed on top of that — see
  `docs/architecture/DATABASE_DESIGN.md` Section 5.5).
- Kind: bridge table (many-to-many between `cv_detections` and `cv_tracks`).
- **Important caveat:** this table's row count is *not* validated as "the"
  answer to CLAUDE.md's ~81% incorporation question — see
  `docs/architecture/DATABASE_DESIGN.md` Section 2 (unresolved discrepancy).

## 6. `radar_detections`

**One row represents one individual radar detection reading** — including
any cluster-grouped sub-detections, which are preserved as JSON on the
same row rather than as separate linked rows (see Section 6 below).

- Source: topic `radar_detections`, path `RadarFrame.detections[]`.
- Row count: **2,929**.
- Kind: append-only entity table.
- **Scope note (`docs/architecture/SCHEMA_REVIEW.md` finding F4):** most measurement/
  classification columns on this table are CONFIRMED constant or empty in
  this file — only `azimuth_rad`, `elevation_rad` (units confirmed by
  observed value range), `track_id`, and `capture_time_ns` carry real
  signal. See `docs/architecture/DATABASE_DESIGN.md` Section 5.6.

## 7. `fused_tracks`

**One row represents one persistent fused-track identity** — the
tower/fusion system's tracked object, independent of how many state
updates it received.

- Source: topic `track_states`, derived from distinct
  `TrackState.track_id2` values.
- Row count: **103**.
- Kind: static identity/reference table. Identity + one stable provenance
  attribute (`legacy_track_id`) only — no derived timestamps (see
  `v_fused_track_summary`, `docs/architecture/DATABASE_DESIGN.md` Section 5.11).
- **Loading note (`docs/architecture/SCHEMA_REVIEW.md` finding F2):** same complete-
  upfront-scan requirement as `cv_tracks` — see
  `docs/architecture/DATABASE_DESIGN.md` Section 5.12.

## 8. `fused_track_states`

**One row represents one fused-track state/update — exactly one
`track_states` MCAP message.** Unlike the CV topics, `track_states` is not
batched, so this table maps one-to-one with the raw messages on that
topic.

- Source: topic `track_states`, the whole `proto.tower.TrackState` message.
- Row count: **11,630**.
- Kind: append-only history table.

## 9. `fused_track_measurements`

**One row represents one sensor measurement contributing to one
fused-track state.**

- Source: topic `track_states`, path `TrackState.measurements[]`.
- Row count: **11,992**.
- Kind: append-only child table.
- Nested repeated `detection_ids` are preserved as JSON on this same row,
  not as a separate table — see `docs/architecture/DATABASE_DESIGN.md` Section 5.9
  and `docs/architecture/NORMALIZATION_DECISIONS.md`.

## 10. `data_quality_issues`

**One row represents one detected data-quality finding**, generated by
ETL validation logic — not sourced from any protobuf field.

- Source: none (ETL-generated).
- Row count: **0 at schema creation**; grows as ETL validation rules run
  (at minimum 4, for the confirmed orphaned `cv_detection_track_links`
  references — see `docs/architecture/DATABASE_DESIGN.md` Section 5.5).
- Kind: append-only log/audit table.

---

## Grain summary table

| Table | Grain in one line | Row count |
|---|---|---|
| `source_messages` | one raw MCAP message | 57,266 |
| `cv_detections` | one CV detection event | 1,911 |
| `cv_tracks` | one persistent CV track | 17 |
| `cv_track_states` | one CV track's state in one frame | 9,496 |
| `cv_track_class_distribution` | one ordered class candidate per CV track state | 37,984 |
| `cv_detection_track_links` | one distinct (detection, track) pair | 1,868 |
| `radar_detections` | one radar detection reading | 2,929 |
| `fused_tracks` | one persistent fused track | 103 |
| `fused_track_states` | one fused-track state/update | 11,630 |
| `fused_track_measurements` | one measurement contributing to one state | 11,992 |
| `data_quality_issues` | one detected data-quality finding | 0, growing |

Two things worth noticing about this table: first, the four "state/event"
tables (`cv_detections`, `cv_track_states`, `radar_detections`,
`fused_track_states`) sum to 1,911 + 9,496 + 2,929 + 11,630 = 25,966 —
noticeably less than `source_messages`' 57,266, because `cv_track_states`
and `radar_detections` each collapse *many* per-message repeated entities
into rows counted once each, while `source_messages` counts every raw
message once regardless of how many entities it contained. Second, the
two identity tables (`cv_tracks`, `fused_tracks`) are tiny (17 and 103
rows) compared to their own state tables (9,496 and 11,630 rows) — this
size gap *is* the persistent-entity-vs-update distinction Stage 3
established, made visible directly in the row counts.
## 4a. `cv_track_class_distribution`

- Grain: one row per ordered `CVTrack.class_distribution[]` entry for one CV track state.
- Source: `CVTrackFrame.tracks[].class_distribution[]`.
- Expected rows: 37,984, exactly four per each of 9,496 parent states.
- PK: `cv_track_class_distribution_id`.
- FK: `cv_track_state_id` → `cv_track_states`.
- `source_order` is zero-based and preserves duplicate classifications.
