# Database Design — CUAS Sentry Sentry SQLite Schema

Stage 4 deliverable. This document is a **design**, not an implementation:
no `schema.sql`, no SQLite database, no ETL code, no views, and no
analytical SQL are created by this document. It exists so the eventual
implementation stage has a single, evidence-grounded reference to build
from.

## How to read this document

Every claim below is tagged, explicitly or by section, as one of:

- **CONFIRMED** — measured directly from the full 57,266-message source
  file (Stage 2, Stage 3, or a targeted full-dataset check run during Stage
  4 planning, each cited).
- **DESIGN DECISION** — a choice made by the author, with reasoning and a
  rejected alternative.
- **ASSUMPTION** — something believed true but not independently
  re-verified at full-dataset scale in this project (for example, a
  population percentage based only on Stage 2's 3 structural samples per
  topic, not a full scan).
- **UNRESOLVED** — a real, open question this schema does not answer, and
  should not be assumed away.

Where a number is stated without a tag, it is CONFIRMED and its source is
named nearby.

---

## 1. Evidence base

This design is built entirely on:

- `docs/MCAP_INSPECTION.md` and `data/output/mcap_schema_report.json`
  (Stage 2 — structural inspection of the real file).
- `docs/KEY_ANALYSIS.md` and `data/output/key_analysis.json` (Stage 3 —
  identifier, grain, and relationship analysis).
- A small number of additional full-dataset, read-only queries run
  directly against `data/input/sanitized.mcap` during Stage 4 planning,
  specifically to resolve the CV-incorporation and object-classification
  questions below (each finding below states that it came from this
  targeted Stage 4 check, so it is not confused with a Stage 2/3 report
  number).
- `CLAUDE.md` / `AGENTS.md` (identical project rules and the two
  analytical target questions).

No field name, relationship, or population statistic in this document was
invented. Where a value could not be verified, it is marked UNRESOLVED or
ASSUMPTION, not stated as fact.

---

## 2. The CV detection-incorporation discrepancy (read this before trusting the % answer)

CLAUDE.md/AGENTS.md give an *approximate validation target* of "approximately
81%" for "what percentage of CV detections were incorporated into CV
tracks." Before finalizing `cv_detection_track_links`, this was
investigated directly against the real data, per an explicit instruction
not to finalize the design or claim the question solved until the
discrepancy was understood.

### What was checked (all CONFIRMED, full-dataset, Stage 4 targeted queries)

1. **Every field on the `CVTrack` protobuf message was enumerated directly
   via reflection** (not assumed). The only detection-reference-shaped
   field is `last_associated_detection_id` (a `uint64`). There is no
   repeated/history field of past detection associations anywhere on the
   track message — only a single "most recent" pointer.

2. **`num_detection_associations`** (a `uint64` cumulative counter on
   `CVTrack`, not previously analyzed in Stage 2/3) was checked as an
   independent cross-validation signal. Summing its *maximum observed
   value per persistent track*, across all 17 persistent CV tracks, gives
   **1,910** — i.e., a second, independent field says essentially all
   1,911 real detections (99.9%) were eventually associated with some
   track.

3. **The existing method** (count of distinct `detection_id` values that
   ever appear as some track's `last_associated_detection_id`, anywhere in
   the file) gives **1,868 / 1,911 ≈ 97.8%**.

4. **A denominator-narrowing filter was searched for and not found.**
   `cv_detections.disposition` is `DISPOSITION_UNKNOWN` (raw value `0`)
   for all 1,911 detections, and `static_suppression_label` is never set
   on any detection. There is no data-driven signal in the detection data
   itself to justify excluding any subset of detections from the
   denominator.

5. **A numerator-narrowing filter was searched for and not found.**
   `cv_tracks.tracks.status` is `CV_TRACK_STATUS_ACTIVE` for 9,468 of
   9,496 track-rows (99.7%); filtering to ACTIVE-only tracks changes the
   result negligibly. No combination of track-status filtering found
   brings the result materially toward 81%.

### Conclusion

**No definition constructible from this file's actual fields reproduces
approximately 81%.** Every honestly-computed variant found lands between
**97.8% and 99.9%** — all materially *higher* than the target, not lower,
and the two independent methods (direct reference count, and the
cumulative counter cross-check) agree with each other, which is evidence
the 97.8%–99.9% range is a real property of this file, not a computation
error.

**This is recorded as UNRESOLVED, not solved, and not forced to match
81%.** Plausible explanations that cannot be confirmed or ruled out from
this file alone: the ~81% reference may have been computed against a
different recording session or file than this sanitized excerpt; or it
may encode a business rule not visible in the schema (for example, a
time-windowed "was this detection incorporated within N seconds"
requirement, rather than "ever, anywhere in the file"). **This requires
human or business-rule clarification before the eventual ETL stage reports
a final percentage as "the" answer.**

### What the schema does about it

`cv_detection_track_links` is still built (grain: one row per distinct
`(detection_id, track_id)` pair, sourced from `last_associated_detection_id`
— see Table 5 below), because it *is* the only structurally-supported
relationship. `cv_track_states.num_detection_associations` is added as a
new column specifically so the cumulative-counter cross-check above can be
re-run at any time against the loaded database, not just against the raw
file. The schema does not encode, assume, or hard-code any particular
percentage (CLAUDE.md rule 14).

---

## 3. The fused-track Drone/Airplane classification problem

CLAUDE.md/AGENTS.md's second target question asks for "average fused-track
duration for Drone objects compared with Airplane objects." This was
investigated directly, per instruction not to invent a mapping or assume
CV and fused object classes are interchangeable.

### What was checked (CONFIRMED, full-dataset, Stage 4 targeted queries, verified via direct protobuf enum reflection — not recollection)

1. **`track_states.object_class`** uses the enum type
   `proto.tower.TrackObjectClass`. Every one of its declared enum values
   was enumerated directly from the protobuf descriptor: **it contains no
   value named anything like DRONE, and no value named anything like
   AIRPLANE.** Its values are coarser categories (`OBJECT_CLASS_AIR_VEHICLE`,
   `OBJECT_CLASS_UNKNOWN_AIR_VEHICLE`, `OBJECT_CLASS_BIRD`, etc.). This is
   a structural fact about the schema, not a data-population issue — the
   fused/tower classification system cannot represent "Drone" or
   "Airplane" as distinct values, under any amount of additional data.

2. **The values actually observed** in `track_states.object_class` across
   all 11,630 fused-track state rows are: `OBJECT_CLASS_AIR_VEHICLE` (raw
   `4`, 10,062 rows), `OBJECT_CLASS_UNKNOWN_AIR_VEHICLE` (raw `9`, 884
   rows), and `OBJECT_CLASS_BIRD` (raw `10`, 684 rows). No other values
   occur.

3. **By contrast, `cv_tracks.tracks.object_class`** uses
   `anduril.sensors.cv.v1.ObjectClassification`, which *does* declare
   explicit `OBJECT_CLASSIFICATION_DRONE` and `OBJECT_CLASSIFICATION_AIRPLANE`
   values. However, the values actually observed across all 9,496 CV
   track-state rows in this file are only `OBJECT_CLASSIFICATION_AIR_VEHICLE`
   (raw `21`, 8,381 rows) and `OBJECT_CLASSIFICATION_BIRD` (raw `11`, 1,115
   rows) — **DRONE and AIRPLANE, while representable by the CV schema, are
   never actually used in this file's data.**

4. **Stage 3 already confirmed** (`docs/KEY_ANALYSIS.md`) that CV
   `track_id` and fused `track_id`/`track_id2` are unrelated identifier
   namespaces with zero observed value overlap, so even if a class mapping
   existed, there is no confirmed way to join a CV track's classification
   onto a specific fused track.

### Conclusion

This is recorded as **UNRESOLVED**, on two independent grounds: (a) the
fused/tower classification taxonomy structurally cannot express
"Drone"/"Airplane" as distinct categories, and (b) even the richer CV
taxonomy, which can, never actually uses those specific values in this
file. **Evidence still needed before this question can be answered
reliably:** either a different source file/session where CV tracks are
actually classified as Drone or Airplane, or an explicit, documented,
human-approved mapping from the coarser fused categories (e.g.
`AIR_VEHICLE`) to "Drone"/"Airplane" — which this project will not invent
on its own, since doing so would be asserting a fact the data does not
support.

### What the schema does about it

`fused_track_states.object_class_raw` / `object_class_name` are stored
exactly as observed (raw enum integer plus its real, schema-derived name —
never invented). No column anywhere in this schema is named or implies
"drone" or "airplane." The recommended `v_fused_track_summary` view (see
Table 7) deliberately does **not** attempt to resolve "the" class for a
track — that resolution is left as an explicit, documented decision for
whoever answers this question, informed by the evidence above.

---

## 4. Final table list (10 tables)

| # | Table | Grain (one row = ) | Row count | Kind |
|---|---|---|---|---|
| 1 | `source_messages` | one raw MCAP message, any topic | 57,266 (CONFIRMED) | Append-only envelope |
| 2 | `cv_detections` | one CV detection event | 1,911 (CONFIRMED) | Append-only entity |
| 3 | `cv_tracks` | one persistent CV track identity | 17 (CONFIRMED) | Static identity/reference |
| 4 | `cv_track_states` | one CV track's state within one batch frame | 9,496 (CONFIRMED) | Append-only history |
| 5 | `cv_detection_track_links` | one distinct (detection, track) pairing | 1,868 (CONFIRMED) | Bridge (many-to-many) |
| 6 | `radar_detections` | one radar detection reading | 2,929 (CONFIRMED) | Append-only entity |
| 7 | `fused_tracks` | one persistent fused track identity | 103 (CONFIRMED) | Static identity/reference |
| 8 | `fused_track_states` | one fused-track state/update (= one message) | 11,630 (CONFIRMED) | Append-only history |
| 9 | `fused_track_measurements` | one sensor measurement contributing to one fused-track state | 11,992 (CONFIRMED) | Append-only child |
| 10 | `data_quality_issues` | one detected data-quality finding | 0 at creation, grows during ETL (not sourced from protobuf) | ETL-generated log |

All row counts above are exact, verified full-dataset counts (Stage 2/3,
or the targeted Stage 4 checks in Sections 2–3), not estimates, except
`data_quality_issues`, which by design has no fixed count — it is
populated by ETL validation rules as they run.

---

## 5. Per-table specifications

### 5.1 `source_messages`

- **Grain:** "One row represents one raw MCAP message, from any of the
  four topics." This table is the envelope/provenance layer every other
  table ultimately traces back to (CLAUDE.md rule 5: preserve `log_time`
  and `publish_time` in nanoseconds).
- **Source topic(s):** all four (`cv_detections`, `cv_tracks`,
  `radar_detections`, `track_states`).
- **Source path:** not a protobuf message field — this is the MCAP
  record envelope itself (`channel_id`, `sequence`, `log_time`,
  `publish_time`) plus the channel's `topic` and `schema_id`.
- **Why its own table:** every downstream row needs traceability back to
  the exact raw message it came from, and no natural key exists to fold
  this into another table.
- **Approximate row count:** 57,266 (CONFIRMED exact, Stage 2/3: sum of
  per-channel message counts).

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `source_message_id` | INTEGER | NOT NULL | Surrogate PK. |
| `channel_id` | INTEGER | NOT NULL | Raw MCAP channel id. |
| `topic` | TEXT | NOT NULL | One of the 4 confirmed topic names. |
| `schema_id` | INTEGER | NOT NULL | Raw MCAP schema id. |
| `sequence` | INTEGER | NOT NULL | Raw MCAP sequence number. Preserved for provenance despite being CONFIRMED degenerate (Stage 3: collapses to 4 distinct values across all 57,266 messages) — **not usable for ordering or uniqueness.** |
| `log_time_ns` | INTEGER | NOT NULL | Nanoseconds. CLAUDE.md rule 5. |
| `publish_time_ns` | INTEGER | NOT NULL | Nanoseconds. CLAUDE.md rule 5. |

- **Primary key:** `source_message_id` (surrogate, `INTEGER PRIMARY KEY`
  which SQLite treats as an alias for `rowid`, auto-incrementing).
  **Why:** Stage 3 (`docs/KEY_ANALYSIS.md`, "Source MCAP message
  identity") tested every plausible natural/composite key
  (`topic+sequence`, `channel_id+sequence`, both plus `log_time`) across
  the full 57,266-message file and found **none collision-free** — the
  best natural combination reached only 52,890 of 57,266 distinct values.
  Only a generated position counter was collision-free. A surrogate key
  is therefore not a convenience choice here; it is the only option Stage
  3 proved works.
- **Candidate natural key:** none. **Rejected** — see above, directly
  CONFIRMED by Stage 3's full-file collision test.
- **Surrogate key:** yes, `source_message_id`. Justified above.
- **Foreign keys:** none (root table).
- **Nullable columns:** none. Every column here is a raw MCAP envelope
  field, always present by construction for every message in the file.
- **UNIQUE constraints:** none beyond the PK. A `UNIQUE(channel_id,
  log_time_ns, sequence)` constraint was considered and **rejected**,
  because Stage 3 proved this exact combination is *not* collision-free
  (52,890 of 57,266 distinct) — adding it would cause valid messages to
  fail to load.
- **CHECK constraints:** none needed; no numeric range or enumerated
  value applies to these columns.
- **Recommended indexes:** `idx_source_messages_topic(topic)` (message
  counts by topic); `idx_source_messages_log_time(log_time_ns)` (time-
  range queries, track-history-over-time joins).
- **Loading order:** 1st — every other table's `source_message_id` FK
  depends on this table being loaded first.
- **Expected update behavior:** append-only. A source message, once
  loaded, never changes.

---

### 5.2 `cv_detections`

- **Grain:** "One row represents one individual CV detection event."
- **Source topic:** `cv_detections`.
- **Source protobuf path:** `CVDetectionFrame.detections[]`
  (`anduril.sensors.cv.v1.CVDetection`).
- **Why its own table:** a distinct, one-time real-world event (Stage 2
  classified this as grain `detection`), and the only field in the entire
  schema CONFIRMED (Stage 3) to be 100% naturally unique — it deserves to
  be the anchor entity table, not folded into anything else.
- **Approximate row count:** 1,911 (CONFIRMED exact, Stage 3).

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `detection_id` | INTEGER | NOT NULL | PK. Native `uint64`. |
| `detection_uid` | TEXT | NOT NULL | Also CONFIRMED 100% unique (Stage 3: 1,911/1,911). Kept as an alternate identity/provenance column, not the PK, since `detection_id` is the native numeric identity on the message. |
| `source_message_id` | INTEGER | NOT NULL | FK → `source_messages`. |
| `capture_time_ns` | INTEGER | NULLABLE | Flattened from frame-level `CVDetectionFrame.capture_time` (a 1:1 nested `Timestamp`, denormalized onto each detection row rather than kept in a separate frame table). ASSUMPTION: observed populated in all 3 Stage 2 structural samples; full-dataset population not independently re-verified in Stage 4. |
| `class_name` | TEXT | NULLABLE | |
| `object_class_raw` | INTEGER | NULLABLE | Raw `anduril.sensors.cv.v1.ObjectClassification` enum int. |
| `object_class_name` | TEXT | NULLABLE | Resolved enum name (schema-derived, never invented). |
| `bbox_left`, `bbox_top`, `bbox_right`, `bbox_bottom` | REAL | NULLABLE | Flattened 1:1 `BoundingBox`. |
| `score` | REAL | NULLABLE | |
| `semantic_confidence_raw` | INTEGER | NULLABLE | Raw enum int. |
| `semantic_confidence_name` | TEXT | NULLABLE | Resolved enum name. |
| `detector_index` | INTEGER | NULLABLE | |
| `disposition_raw` | INTEGER | NULLABLE | CONFIRMED (Stage 4 targeted check): always `0` (`DISPOSITION_UNKNOWN`) for all 1,911 rows in this file. Kept for schema completeness (CLAUDE.md rule 12), documented as currently non-discriminating. |
| `disposition_name` | TEXT | NULLABLE | |
| `motion_state_raw` | INTEGER | NULLABLE | |
| `motion_state_name` | TEXT | NULLABLE | |
| `parent_object_detection_id` | INTEGER | NULLABLE | Self-referencing candidate (wrapped `UInt64Value`). CONFIRMED (Stage 3 `key_analysis.json`): 0 populated occurrences in this file. **Not enforced as a foreign key** — see Section 6. |

- **Primary key:** `detection_id`. **Why:** it is a genuine, CONFIRMED
  natural key (100% unique across the full dataset) — adding a surrogate
  on top would be pure overhead with no benefit (rule 7: use keys only
  when justified; a natural key exists, so a surrogate is not justified
  here).
- **Candidate natural key:** `detection_id` (accepted, as above) and
  `detection_uid` (also 100% unique, but kept as a UNIQUE column instead
  of the PK, since `detection_id` is the message's native numeric
  identity and simpler to index/join on).
- **Surrogate key:** not used. Justified above.
- **Foreign keys:** `source_message_id` → `source_messages.source_message_id`.
  `parent_object_detection_id` is a candidate self-reference to this same
  table, explicitly **not enforced** (see Section 6).
- **Nullable columns:** all columns except `detection_id`,
  `detection_uid`, and `source_message_id` are nullable, because every one
  of them is either an optional protobuf field, a field CONFIRMED
  always-empty in this file (`disposition`), or a field whose population
  was not independently re-verified (`capture_time_ns`) — none should be
  declared `NOT NULL` without stronger evidence.
- **UNIQUE constraints:** `UNIQUE(detection_uid)`.
- **CHECK constraints:** none required by evidence gathered; `score`
  is a raw float with no confirmed valid range documented in the schema
  itself, so no `CHECK` is imposed rather than inventing a range.
- **Recommended indexes:** `idx_cv_detections_source_message(source_message_id)`;
  `idx_cv_detections_object_class(object_class_raw)` (supports
  classification-based queries).
- **Loading order:** 2nd (after `source_messages`; before
  `cv_detection_track_links`, which references it).
- **Expected update behavior:** append-only entity table. A detection,
  once recorded, does not change.

---

### 5.3 `cv_tracks`

- **Grain:** "One row represents one persistent CV track identity" — the
  real-world tracked object, not any single observation of it.
- **Source topic:** `cv_tracks` (derived, not a direct 1:1 protobuf
  field — populated from the distinct values of
  `CVTrackFrame.tracks[].track_id`).
- **Source protobuf path:** `CVTrackFrame.tracks[].track_id`.
- **Why its own table:** Stage 3 (`docs/KEY_ANALYSIS.md`, "Persistent
  entity vs. update analysis") CONFIRMED `track_id` behaves as a
  persistent entity identifier (17 distinct values, restated up to 1,676
  times each, zero within-message duplicates). Without this table,
  neither `cv_track_states.track_id` nor
  `cv_detection_track_links.track_id` could be a real, enforced foreign
  key (rule 8: `PRAGMA foreign_keys = ON`) — there would be no single-row
  entity for them to point to.
- **Approximate row count:** 17 (CONFIRMED exact, Stage 3).

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `track_id` | INTEGER | NOT NULL | PK. Native `uint64`. |

- **Primary key:** `track_id` — a CONFIRMED natural key at this grain
  (distinct persistent identity).
- **Candidate natural key:** `track_id` (accepted).
- **Surrogate key:** not used — unnecessary given a clean natural key.
- **Foreign keys:** none (referenced by `cv_track_states` and
  `cv_detection_track_links`).
- **Nullable columns:** none — the table has exactly one column, the key
  itself.
- **UNIQUE constraints:** the PK itself.
- **CHECK constraints:** none.
- **Recommended indexes:** none beyond the PK — a 17-row table needs no
  secondary index.
- **Loading order:** 3rd (after `cv_detections`; before
  `cv_track_states`, which FKs to it).
- **Expected update behavior:** static reference/identity table — new
  rows only when a genuinely new persistent track id is first observed;
  existing rows never change.
- **Deliberately NOT stored here:** `first_observed_log_time`,
  `last_observed_log_time`, or `duration` — per explicit instruction,
  these are derived facts computed from `cv_track_states`, not stored,
  authoritative columns. See the recommended view
  `v_cv_track_summary` in Section 5.11.

---

### 5.4 `cv_track_states`

- **Grain:** "One row represents one CV track's state as restated within
  one `cv_tracks` batch message" — i.e., one track's appearance in one
  frame. This is explicitly **not** the persistent track (that's `cv_tracks`,
  17 rows) — it is every restatement of that track across every frame it
  appeared in.
- **Source topic:** `cv_tracks`.
- **Source protobuf path:** `CVTrackFrame.tracks[]`
  (`anduril.sensors.cv.v1.CVTrack`).
- **Why its own table:** Stage 2 confirmed `cv_tracks` messages are
  `batch_of_entities` (one MCAP message = many track rows); each track
  row is itself a distinct, timestamped observation and must not be
  collapsed into the frame or into the persistent-entity table.
- **Approximate row count:** 9,496 (CONFIRMED exact, Stage 3).

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `cv_track_state_id` | INTEGER | NOT NULL | Surrogate PK. |
| `source_message_id` | INTEGER | NOT NULL | FK → `source_messages`. |
| `track_id` | INTEGER | NOT NULL | FK → `cv_tracks`. |
| `log_time_ns` | INTEGER | NOT NULL | Denormalized copy of `source_messages.log_time_ns` for this row, so time-range and history queries do not require a join. This is the row's own timestamp, not a computed aggregate — does not conflict with the "no derived duration" rule, which applies to the *persistent identity* tables (`cv_tracks`/`fused_tracks`), not this state table. |
| `track_age` | INTEGER | NULLABLE | Native `uint64`. |
| `status_raw` / `status_name` | INTEGER / TEXT | NULLABLE | `CVTrackStatus` enum. CONFIRMED (Stage 4 check) distribution: `ACTIVE`=9,468, `LOST`=22, `INACTIVE`=6. |
| `status_code_raw` / `status_code_name` | INTEGER / TEXT | NULLABLE | `CVTrackStatusCode` enum. CONFIRMED distribution: `NO_UPDATE`=7,631, `DETECTION_ASSOCIATION`=1,865. |
| `object_class_raw` / `object_class_name` | INTEGER / TEXT | NULLABLE | CONFIRMED distribution in this file: `OBJECT_CLASSIFICATION_AIR_VEHICLE`=8,381, `OBJECT_CLASSIFICATION_BIRD`=1,115. See Section 3 — DRONE/AIRPLANE never observed here. |
| `class_name` | TEXT | NULLABLE | |
| `bbox_left`, `bbox_top`, `bbox_right`, `bbox_bottom` | REAL | NULLABLE | Flattened 1:1 `BoundingBox`. |
| `last_associated_detection_id` | INTEGER | NULLABLE | Raw provenance column — the value `cv_detection_track_links` is derived from. Kept here in addition to the bridge table so per-row raw fidelity is never lost (rule 12). |
| `num_detection_associations` | INTEGER | NULLABLE | **New column, added directly from the Section 2 investigation.** Cumulative counter; enables the cross-check that produced the 99.9% alternative figure to be re-run against the loaded database. |
| `score` | REAL | NULLABLE | |
| `disposition_raw` / `disposition_name` | INTEGER / TEXT | NULLABLE | |
| `motion_state_raw` / `motion_state_name` | INTEGER / TEXT | NULLABLE | |
| `is_manual` | INTEGER | NULLABLE | Boolean, stored `0`/`1`. |
| `parent_object_track_id` | INTEGER | NULLABLE | Self-referencing candidate to `cv_tracks.track_id`. CONFIRMED (Stage 3): weak_heuristic verdict, 0 populated in this file. **Not enforced as a foreign key** — see Section 6. |
| `capture_time_ns` | INTEGER | NULLABLE | Flattened frame-level timestamp, denormalized (same reasoning as `cv_detections.capture_time_ns`). ASSUMPTION — see that entry. |

- **Primary key:** `cv_track_state_id` (surrogate). **Why:** the natural
  composite `(source_message_id, track_id)` is CONFIRMED collision-free in
  this file (Stage 2: zero within-message duplicate `track_id` values),
  but per Stage 3's own explicit general guidance ("a surrogate key is
  still the safer general recommendation" — `docs/KEY_ANALYSIS.md`,
  persistent entity analysis), a surrogate is used so a future file that
  happens to violate this composite-uniqueness assumption fails a
  `UNIQUE` constraint (a normal, catchable data-quality event) rather than
  making the row un-insertable at the primary-key level.
- **Candidate natural key:** `(source_message_id, track_id)` — accepted
  as a `UNIQUE` constraint, not the PK, for the reason above.
- **Surrogate key:** yes, `cv_track_state_id`. Justified above.
- **Foreign keys:** `source_message_id` → `source_messages`; `track_id`
  → `cv_tracks`. `parent_object_track_id` explicitly **not enforced**
  (Section 6).
- **Nullable columns:** everything except the PK and the two required
  FKs plus `log_time_ns` (a raw envelope fact, always present). Every
  nullable column is either an optional protobuf field or one whose
  full-dataset population was not independently confirmed.
- **UNIQUE constraints:** `UNIQUE(source_message_id, track_id)`.
- **CHECK constraints:** none — no confirmed valid range for `score` or
  `track_age` was established in Stage 2/3.
- **Recommended indexes:**
  `idx_cv_track_states_track_id(track_id)` (history-over-time, joins to
  `cv_tracks`); `idx_cv_track_states_source_message(source_message_id)`;
  `idx_cv_track_states_last_assoc_det(last_associated_detection_id)`
  (supports the incorporation-percentage query in Section 2).
- **Loading order:** 4th (after `cv_tracks`, `source_messages`; before
  `cv_detection_track_links`).
- **Expected update behavior:** append-only history table.

---

### 5.5 `cv_detection_track_links`

- **Grain:** "One row represents one distinct (detection, track) pairing
  ever observed" — deduplicated across every track update that restates
  the same association. This is a **derived bridge table**, not a direct
  1:1 protobuf structure.
- **Source topic:** `cv_tracks` (derived from `tracks[].track_id` paired
  with `tracks[].last_associated_detection_id`, deduplicated by the ETL
  process, not present as its own protobuf message).
- **Why its own table:** Stage 3 explicitly recommended this exact grain
  ("A future detection<->track bridge table's natural grain is one row
  per (detection_id, persistent track_id) pair" — `docs/KEY_ANALYSIS.md`).
  Without deduplication, the same pairing would be double-counted 1,865
  extra times (CONFIRMED, Stage 3) across every track-update restatement,
  corrupting any incorporation-percentage query.
- **Approximate row count:** 1,868 distinct pairs (CONFIRMED exact,
  Stage 3 and re-confirmed Stage 4). See Section 2 for why this number
  should not be read as "the" answer to the 81% question without further
  clarification.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `detection_id` | INTEGER | NOT NULL | FK → `cv_detections`. |
| `track_id` | INTEGER | NOT NULL | FK → `cv_tracks`. |
| `first_observed_log_time_ns` | INTEGER | NULLABLE | When this specific pairing was first seen. An ETL-computed audit fact about *this bridge row*, not a persistent-track summary statistic — does not conflict with the "no stored duration on identity tables" rule. |

- **Primary key:** composite `(detection_id, track_id)`. **Why:** this
  table's entire purpose is exactly this deduplicated pair; nothing else
  in the schema needs to FK to an individual link row, so a surrogate
  would add overhead with no benefit.
- **Candidate natural key:** `(detection_id, track_id)` — accepted as
  the PK.
- **Surrogate key:** not used. Justified above.
- **Foreign keys:** `detection_id` → `cv_detections.detection_id`;
  `track_id` → `cv_tracks.track_id`.
- **Nullable columns:** `first_observed_log_time_ns` only (an ETL
  convenience fact, not always guaranteed depending on load order
  details).
- **UNIQUE constraints:** the PK itself enforces this.
- **CHECK constraints:** none.
- **Recommended indexes:** `idx_cv_detection_track_links_track(track_id)`
  (reverse lookups: "which detections fed this track").
- **Loading order:** 5th (after `cv_detections`, `cv_tracks`, and
  `cv_track_states`, since it is derived from track-state data).
- **Expected update behavior:** append-only bridge table (a new pairing
  is only ever added, never removed once observed).
- **Cleaning rule (documented for future ETL, not implemented now):**
  Stage 3 CONFIRMED 4 orphaned references exist — a `last_associated_detection_id`
  value with no matching `detection_id` in `cv_detections`. Because
  `detection_id` is a real, enforced FK here (rule 8), these 4 rows
  **cannot** be loaded into this table without breaking referential
  integrity. The ETL cleaning rule: these 4 pairings are **rejected from
  this table** and instead **recorded in `data_quality_issues`** with
  their raw `detection_id`/`track_id` values preserved, so the
  information is never silently discarded (rule 12) — it is simply moved
  to the table designed to hold exactly this kind of finding.

---

### 5.6 `radar_detections`

- **Grain:** "One row represents one individual radar detection reading."
- **Source topic:** `radar_detections`.
- **Source protobuf path:** `RadarFrame.detections[]`
  (`anduril.sensors.radar.v1.RadarDetection`).
- **Why its own table:** Stage 2 confirmed `radar_detections` is
  `batch_of_entities` with no separate radar-track structure — each
  reading is its own event, directly analogous in grain to `cv_detections`.
- **Approximate row count:** 2,929 (CONFIRMED exact, Stage 4 targeted
  check; consistent with Stage 3's 2,929 population count for
  `detections.track_id`).

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `radar_detection_id` | INTEGER | NOT NULL | Surrogate PK. |
| `source_message_id` | INTEGER | NOT NULL | FK → `source_messages`. |
| `capture_time_ns` | INTEGER | NULLABLE | Flattened frame-level timestamp (`RadarFrame.capture_time`, confirmed present in the schema structurally; full-dataset population not independently verified — ASSUMPTION). |
| `range`, `azimuth` | REAL | NULLABLE | |
| `elevation`, `range_rate` | REAL | NULLABLE | Flattened from wrapped `DoubleValue`. |
| `return_strength`, `snr` | REAL | NULLABLE | Flattened from wrapped `DoubleValue`. |
| `track_id` | TEXT | NULLABLE | Raw string. **Explicitly not a foreign key to anything** — Stage 3 CONFIRMED zero value overlap against every CV/fused track_id-family field, including the one pairing with matching types. Kept as a plain, indexed column for grouping only. |
| `object_type_class_raw` / `_name` | INTEGER / TEXT | NULLABLE | `anduril.ontology.v1.Class`. CONFIRMED (Stage 4 check): always `0` (`CLASS_UNKNOWN`) across all 2,929 rows in this file. |
| `object_class_raw` / `_name` | INTEGER / TEXT | NULLABLE | `proto.tower.TrackObjectClass` (same enum type as `fused_track_states.object_class`). CONFIRMED (Stage 4 check): always raw `12` (`OBJECT_CLASS_UNCLASSIFIED`, per Stage 2's captured enum value list for this type) across all 2,929 rows. |
| `filter_type_raw` / `_name` | INTEGER / TEXT | NULLABLE | |
| `azimuth_sigma`, `elevation_sigma`, `range_sigma`, `range_rate_sigma` | REAL | NULLABLE | Flattened wrapped `DoubleValue`s. |
| `estimated_width_meters` | REAL | NULLABLE | |
| `is_marked` | INTEGER | NULLABLE | Boolean, `0`/`1`. |
| `cluster_json` | TEXT | NULLABLE | Compact JSON preserving any cluster-member detail. CONFIRMED (Stage 4 check): the `cluster` repeated field has length 0 for all 2,929 detections in this file — always empty. Kept nullable for schema completeness (rule 12) and because a future file could populate it; **no self-referencing foreign key is created**, because `RadarDetection` has no identifier field of its own to construct a stable reference from, even where `cluster` is populated — see Section 6. |

  **Deliberately omitted from this table** (documented scope decision, not
  a silent drop): deeply nested vendor/debug metadata
  (`detection_metadata.echoshield.*` internals, `debug.rada_v6_debug.*`
  counters, `spatial_kinematics` ECEF position/velocity/covariance
  matrices, `panel_id`). None of the six required analytical queries need
  this detail, and it adds dozens of low-value columns. The source MCAP
  file itself (never modified, per rule 1) remains the authoritative
  record if this detail is ever needed.

- **Primary key:** `radar_detection_id` (surrogate). **Why:**
  CONFIRMED — `RadarDetection` has no identifier field of any kind on the
  message itself; no natural key is possible.
- **Candidate natural key:** none. **Rejected** — no field exists to
  serve as one.
- **Surrogate key:** yes. Justified above.
- **Foreign keys:** `source_message_id` → `source_messages`. `track_id`
  explicitly **not** a foreign key (Section 6).
- **Nullable columns:** all measurement/classification columns, since
  every one is either optional in the protobuf schema or a field whose
  full population was not independently confirmed (`capture_time_ns`).
- **UNIQUE constraints:** none beyond the PK.
- **CHECK constraints:** none imposed — no confirmed valid range for
  `range`/`azimuth`/etc. was established from evidence gathered.
- **Recommended indexes:** `idx_radar_detections_source_message(source_message_id)`;
  `idx_radar_detections_track_id(track_id)` (supports radar-side grouping
  despite no FK enforcement).
- **Loading order:** 6th (after `source_messages`; independent of the CV
  and fused tables).
- **Expected update behavior:** append-only entity table.

---

### 5.7 `fused_tracks`

- **Grain:** "One row represents one persistent fused-track identity."
- **Source topic:** `track_states` (derived from the distinct values of
  `TrackState.track_id2`, the CONFIRMED-active string identifier).
- **Source protobuf path:** `TrackState.track_id2` (string; paired 1:1
  with the legacy `TrackState.track_id`, `uint64`).
- **Why its own table:** Stage 3 CONFIRMED `track_id2` behaves as a
  persistent entity identifier (103 distinct values, restated up to 521
  times each). Without this table, `fused_track_states.fused_track_id`
  could not be a real, enforced foreign key.
- **Approximate row count:** 103 (CONFIRMED exact, Stage 3).

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `fused_track_id` | TEXT | NOT NULL | PK. = `track_id2`, the populated, active string identifier (Stage 2/3: the legacy numeric `track_id` follows the project's observed "legacy numeric + populated string replacement" pattern). |
| `legacy_track_id` | INTEGER | NULLABLE | The legacy `uint64 track_id`. CONFIRMED 1:1 paired with `track_id2` in this file (both show 103 distinct values against the same 11,630 populated rows). This is a stable, static identity attribute — not a derived aggregate — so storing it here does not conflict with the "no stored duration" rule. |

- **Primary key:** `fused_track_id` (= `track_id2`). **Why:** a
  CONFIRMED natural key at this grain, and the field Stage 3 identified
  as the actively-used one (versus the legacy numeric field).
- **Candidate natural key:** `fused_track_id` (accepted);
  `legacy_track_id` alone was considered and **rejected** as the PK,
  since Stage 2 found the numeric legacy fields in this general pattern
  are often the less-trustworthy half of the pair (e.g. `asset_id` vs
  `asset_id2`) — kept as a plain provenance column instead.
- **Surrogate key:** not used — unnecessary given a clean natural key.
- **Foreign keys:** none (referenced by `fused_track_states`).
- **Nullable columns:** `legacy_track_id` only.
- **UNIQUE constraints:** the PK itself; `legacy_track_id` is not
  declared UNIQUE, since its 1:1 pairing, while observed, was not
  stress-tested the way `fused_track_id` was.
- **CHECK constraints:** none.
- **Recommended indexes:** none beyond the PK — a 103-row table needs no
  secondary index.
- **Loading order:** 7th.
- **Expected update behavior:** static reference/identity table.
- **Deliberately NOT stored here:** `first_observed_log_time`,
  `last_observed_log_time`, or `duration`. See the recommended view
  `v_fused_track_summary` in Section 5.11 — and Section 3's warning that
  this view does not, and should not, resolve the Drone/Airplane
  classification question on its own.

---

### 5.8 `fused_track_states`

- **Grain:** "One row represents one fused-track state/update — exactly
  one `track_states` MCAP message." Unlike the CV topics, Stage 2
  confirmed `track_states` is `single_entity_or_update` (no batching), so
  this table maps one-to-one with the raw messages on this topic.
- **Source topic:** `track_states`.
- **Source protobuf path:** the whole `proto.tower.TrackState` message.
- **Why its own table:** the central "fused track" state-history table;
  CLAUDE.md's second analytical target question depends directly on it.
- **Approximate row count:** 11,630 (CONFIRMED exact — equals the
  `track_states` message count, Stage 2).

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `fused_track_state_id` | INTEGER | NOT NULL | Surrogate PK. |
| `source_message_id` | INTEGER | NOT NULL | FK → `source_messages`. |
| `fused_track_id` | TEXT | NOT NULL | FK → `fused_tracks`. |
| `log_time_ns` | INTEGER | NOT NULL | Denormalized from `source_messages`, same reasoning as `cv_track_states.log_time_ns`. |
| `create_timestamp_ns` | INTEGER | NULLABLE | Native protobuf field (`create_timestamp`) — the source system's own record of when it first created this track. A per-row raw fact, not an ETL-derived aggregate. |
| `last_measurement_timestamp_ns` | INTEGER | NULLABLE | Native protobuf field. Same reasoning. |
| `lla_lat`, `lla_lon`, `lla_alt` | REAL | NULLABLE | Flattened from `lla_pos`. Deliberately the *only* position representation kept — `enu_pos`, `relative_pos`, and all covariance/velocity/acceleration fields are omitted as a documented scope decision (not needed by any of the 6 required queries; the source MCAP remains available if needed later). |
| `track_quality` | INTEGER | NULLABLE | CONFIRMED (Stage 4 check): always `0` across all 11,630 rows in this file — currently non-discriminating, kept for schema completeness. |
| `object_class_raw` / `object_class_name` | INTEGER / TEXT | NULLABLE | `proto.tower.TrackObjectClass`. See Section 3 — CONFIRMED this enum has no DRONE/AIRPLANE value at all. |
| `disposition_raw` / `disposition_name` | INTEGER / TEXT | NULLABLE | `anduril.ontology.v1.Disposition`. CONFIRMED (Stage 4 check) populated and discriminating: `UNKNOWN`=1,969, `SUSPICIOUS`=1,601, `ASSUMED_FRIENDLY`=7,653, `NEUTRAL`=407. One of the few genuinely useful classification-adjacent fields found on this topic. |
| `track_status_raw` / `track_status_name` | INTEGER / TEXT | NULLABLE | `proto.tower.TrackStatus`. ASSUMPTION — population not independently re-verified beyond Stage 2 samples. |
| `parent_track_id` | TEXT | NULLABLE | CONFIRMED (Stage 2): always empty across all 11,630 rows in this file. Kept nullable per rule 12; documented as currently unused. |

- **Primary key:** `fused_track_state_id` (surrogate). **Why:** same
  reasoning as `cv_track_states` — `(fused_track_id, log_time_ns)`
  CONFIRMED collision-free in this file (Stage 3: 0 same-timestamp
  collisions for `track_states.track_id2`), but Stage 3 explicitly
  recommends a surrogate as the safer general choice; used here for
  consistency with that guidance and with `cv_track_states`.
- **Candidate natural key:** `(fused_track_id, log_time_ns)` — accepted
  as a `UNIQUE` constraint, not the PK.
- **Surrogate key:** yes, `fused_track_state_id`. Justified above.
- **Foreign keys:** `source_message_id` → `source_messages`;
  `fused_track_id` → `fused_tracks`.
- **Nullable columns:** everything except the PK, the two FKs, and
  `log_time_ns`.
- **UNIQUE constraints:** `UNIQUE(fused_track_id, log_time_ns)`.
- **CHECK constraints:** none imposed.
- **Recommended indexes:** `idx_fused_track_states_fused_track_id(fused_track_id)`;
  `idx_fused_track_states_log_time(log_time_ns)`;
  `idx_fused_track_states_source_message(source_message_id)`.
- **Loading order:** 8th (after `fused_tracks`, `source_messages`).
- **Expected update behavior:** append-only history table.

---

### 5.9 `fused_track_measurements`

- **Grain:** "One row represents one sensor measurement contributing to
  one fused-track state."
- **Source topic:** `track_states`.
- **Source protobuf path:** `TrackState.measurements[]`
  (`proto.tower.MeasurementAssociation`).
- **Why its own table:** a genuinely repeated child structure (Stage 2),
  and the field CONFIRMED to directly serve the "sensor contribution"
  required analytical query (via `sensor_id`).
- **Approximate row count:** 11,992 (CONFIRMED exact, Stage 4 targeted
  full-dataset count).

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `fused_track_measurement_id` | INTEGER | NOT NULL | Surrogate PK. `MeasurementAssociation` has no identifier field of its own — CONFIRMED. |
| `fused_track_state_id` | INTEGER | NOT NULL | FK → `fused_track_states`. |
| `measurement_timestamp_ns` | INTEGER | NULLABLE | |
| `asset_id2` | TEXT | NULLABLE | CONFIRMED (Stage 2/3): populated on essentially every measurement (11,992/11,992), single distinct value in this file. The legacy numeric `asset_id` is deliberately **omitted** as a column (CONFIRMED always empty, Stage 2), rather than kept as dead weight — a different call than `fused_tracks.legacy_track_id`, since that field is a central entity-identity attribute worth preserving while this one is high-volume, per-row noise. |
| `sensor_id_raw` / `sensor_id_name` | INTEGER / TEXT | NULLABLE | `proto.tower.SensorId`. CONFIRMED 3 distinct populated values in this file. |
| `frame_counter` | INTEGER | NULLABLE | |
| `sensor_index` | INTEGER | NULLABLE | |
| `detection_ids_json` | TEXT | NULLABLE | Compact JSON array of the repeated `detection_ids` (string) field. CONFIRMED populated: 13,596 total id occurrences, 1,717 distinct, across this dataset. See Issue 4 decision below. |

- **Primary key:** `fused_track_measurement_id` (surrogate). **Why:**
  no natural key exists — `MeasurementAssociation` has no own identity,
  and `asset_id2` alone is not unique per state (many measurements can
  share the same sensor within one state).
- **Candidate natural key:** none usable. **Rejected.**
- **Surrogate key:** yes. Justified above.
- **Foreign keys:** `fused_track_state_id` → `fused_track_states`.
- **Nullable columns:** all columns except the two keys, since every
  field is optional on the source message or (for `asset_id2`/`sensor_id`)
  not guaranteed on every single measurement despite near-universal
  observed population.
- **UNIQUE constraints:** none.
- **CHECK constraints:** none.
- **Recommended indexes:** `idx_fused_track_measurements_state(fused_track_state_id)`;
  `idx_fused_track_measurements_sensor(sensor_id_raw)` (supports the
  sensor-contribution analytical query).
- **Loading order:** 9th (after `fused_track_states`).
- **Expected update behavior:** append-only child table.
- **`detection_ids_json` decision (Issue 4):** **Option A (compact JSON)
  chosen over Option B (an 11th bridge table,
  `fused_measurement_detection_links`).** None of the 6 required
  analytical queries need a relational join on these ids; this link would
  extend the Section 2 detection-incorporation question onto the fused
  side, which is valuable but not currently requested. Trade-off: Option A
  keeps the schema at 10 tables and avoids a 2-levels-deep bridge table
  for a not-yet-required relationship, at the cost that SQL cannot
  directly join or filter on individual detection ids inside the JSON
  without SQLite's JSON functions. **Upgrade path, if ever needed:** the
  JSON already contains full fidelity, so promoting it to a real
  `fused_measurement_detection_links(fused_track_measurement_id,
  detection_id)` table later is a straightforward migration with no data
  loss.

---

### 5.10 `data_quality_issues`

- **Grain:** "One row represents one detected data-quality finding,"
  generated by ETL validation logic — not sourced from any protobuf
  field.
- **Source:** none (ETL-generated), referencing evidence from Stage 2/3/4
  (for example, the 4 CONFIRMED orphaned detection references from
  Section 5.5).
- **Why its own table:** CLAUDE.md's expected analytical checks
  explicitly include data-quality reporting; a single log table lets every
  cleaning rule across every other table report findings in one place
  instead of silently dropping rows.
- **Approximate row count:** 0 at schema creation; **at least 4** once the
  ETL cleaning rule in Section 5.5 runs (the confirmed orphaned
  `cv_detection_track_links` references), growing as additional rules are
  implemented. Not a fixed count by design.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `issue_id` | INTEGER | NOT NULL | Surrogate PK. |
| `issue_type` | TEXT | NOT NULL | e.g. `'orphaned_detection_reference'`. |
| `severity` | TEXT | NOT NULL | `CHECK(severity IN ('info','warning','error'))`. |
| `related_table` | TEXT | NULLABLE | Loosely typed — see below. |
| `related_id` | TEXT | NULLABLE | Text representation of whatever id(s) are relevant; deliberately not a foreign key. |
| `description` | TEXT | NOT NULL | |
| `detected_at_utc` | TEXT | NOT NULL | ISO-8601 ETL run timestamp — when the issue was found, not a source-message timestamp. |

- **Primary key:** `issue_id` (surrogate).
- **Candidate natural key:** none — issues are ETL-generated events, not
  entities with an inherent identity.
- **Surrogate key:** yes.
- **Foreign keys:** intentionally **none**. `related_table`/`related_id`
  are a loose, polymorphic reference (they may point to rows in different
  tables depending on `issue_type`) and cannot be a single real foreign
  key without over-constraining the design.
- **Nullable columns:** `related_table`, `related_id` — some issue types
  may be dataset-wide rather than tied to one row.
- **UNIQUE constraints:** none.
- **CHECK constraints:** `severity IN ('info','warning','error')`.
- **Recommended indexes:** `idx_data_quality_issues_type(issue_type)`;
  `idx_data_quality_issues_table(related_table)`.
- **Loading order:** 10th, last — logically depends on validation having
  run against the other 9 tables' loaded data.
- **Expected update behavior:** append-only log/audit table.

---

### 5.11 Recommended views (described, not created)

Per instruction, `first_observed_log_time`, `last_observed_log_time`, and
`duration` are **not** stored as columns on `cv_tracks` or `fused_tracks`.
Instead, two views are recommended for the future implementation stage
(illustrative SQL shown for design clarity only — this is documentation,
not `schema.sql`):

```sql
-- v_cv_track_summary (illustrative, not created in this stage)
SELECT
  track_id,
  MIN(log_time_ns) AS first_observed_log_time_ns,
  MAX(log_time_ns) AS last_observed_log_time_ns,
  COUNT(*) AS state_count,
  (MAX(log_time_ns) - MIN(log_time_ns)) / 1e9 AS duration_seconds
FROM cv_track_states
GROUP BY track_id;

-- v_fused_track_summary (illustrative, not created in this stage)
SELECT
  fused_track_id,
  MIN(log_time_ns) AS first_observed_log_time_ns,
  MAX(log_time_ns) AS last_observed_log_time_ns,
  COUNT(*) AS state_count,
  (MAX(log_time_ns) - MIN(log_time_ns)) / 1e9 AS duration_seconds
FROM fused_track_states
GROUP BY fused_track_id;
```

**Why views instead of stored columns:** a stored `duration` column would
be a fact computed from `cv_track_states`/`fused_track_states` at load
time, and could silently go stale or contradict the state rows the moment
new states are appended (an append-only history table is, by definition,
always growing). A view recomputes from the current state rows every
time, so the duplicated fact can never become inconsistent with its
source. **`v_fused_track_summary` deliberately does not attempt to
resolve "the" object class for a track** — see Section 3.

---

## 6. Relationships explicitly NOT enforced (and why)

| Candidate relationship | Verdict | Evidence | Treatment in schema |
|---|---|---|---|
| `cv_track_states.parent_object_track_id` → `cv_tracks.track_id` | Unenforced candidate | Stage 3: weak_heuristic, 0 populated in this file | Nullable column, no FK constraint |
| `cv_detections.parent_object_detection_id` → `cv_detections.detection_id` | Unenforced candidate | Stage 3 (`key_analysis.json`): 0 populated occurrences | Nullable column, no FK constraint |
| `radar_detections` cluster self-reference | Rejected as an FK | Stage 4 check: `cluster` length is 0 for all 2,929 rows; `RadarDetection` has no id field to reference even if populated | `cluster_json`, no self-FK column at all |
| `radar_detections.track_id` ↔ `cv_tracks.track_id` / `fused_tracks.fused_track_id` | Rejected | Stage 3: zero observed value overlap in every tested pairing, including the one pairing with matching types | Plain indexed `TEXT` column, no FK |
| `track_states.track_identity_matches.matched_track_id(2)` → `fused_tracks` | Not modeled | Stage 3: field CONFIRMED always empty in this file; not included in the compact 10-table design at all | Omitted entirely (see `docs/NORMALIZATION_DECISIONS.md`) |

---

## 7. Alternative designs considered

### Alternative 1 — the original ~28–32 table, fully-normalized design (first Stage 4 proposal, superseded)

Every genuinely repeated nested protobuf structure across all four topics
got its own table (per-topic frame tables, every `track_states` child
array as a separate child table, enum lookup tables, etc.).

- **Advantages:** maximum fidelity — every nested structure has an exact
  relational counterpart; no JSON columns anywhere; textbook 3NF.
- **Disadvantages:** far too complex for an assessment meant to be
  read and understood quickly by another engineer; many of those tables
  (companion `assets`/`detectors`/`trackers` arrays, camera-intrinsics
  metadata) were CONFIRMED always-empty in this file and would add joins
  with zero analytical value; harder to write and explain the 6 required
  analytical queries, several of which would need 4–6 table joins instead
  of 1–2.
- **Why the chosen (10-table) architecture is preferred:** directly
  addresses the user's explicit requirement that the goal is "analytical
  simplicity," not maximum normalization — every one of the 6 required
  queries is answerable with at most 2–3 joins in the final design (see
  Section 9).

### Alternative 2 — fully denormalized, one wide table per topic (not previously proposed, considered fresh here)

Instead of any bridge tables or separate identity tables, every batch
message's repeated entities get flattened into one wide table per topic
(e.g. all of `cv_tracks`' track+detection-link information in a single
table), with no `cv_tracks`/`fused_tracks` identity tables and no
`cv_detection_track_links` bridge — every fact repeated on every row.

- **Advantages:** the absolute simplest possible design — zero joins for
  any single-topic query; trivial to load.
- **Disadvantages:** cannot enforce `PRAGMA foreign_keys = ON`
  meaningfully at all (rule 8 becomes decorative); the detection-to-track
  many-to-many relationship (one detection can, in principle, relate to
  more than one track — Section 5.5) cannot be represented without either
  duplicating detection rows or losing information; the CV
  incorporation-percentage query (Section 2) becomes harder to write
  correctly, not easier, because deduplication logic would need to be
  reimplemented in every query instead of once at load time in
  `cv_detection_track_links`.
- **Why the chosen architecture is preferred:** the 10-table design is
  barely more complex to query (1–2 joins instead of 0) but gets real
  referential integrity and a correct, reusable answer to the one
  question (incorporation %) this dataset's structure makes genuinely
  relational.

---

## 8. Data cleaning plan (documented for the future ETL stage; not implemented now)

| Rule | Applies to | Why it exists | Rows: corrected / retained / rejected / flagged |
|---|---|---|---|
| Prefer populated string `_id2`/`_uid` fields as canonical identity; retain legacy numeric fields as unenforced provenance columns | `fused_tracks.legacy_track_id`; `cv_detections.detection_uid` vs `detection_id` (both populated, no preference needed there) | Stage 2 found a systemic legacy-numeric + populated-string pairing; the numeric side is frequently empty elsewhere in the schema | Retained (both columns kept where both exist) |
| Null vs. blank-string distinction | all nullable TEXT columns | Stage 2/3 distinguished "never set" from "set but empty" — collapsing them would lose a real signal (e.g. sanitization vs. genuine absence) | Retained as-is; no correction attempted |
| Orphan detection-reference handling | `cv_detection_track_links` | 4 CONFIRMED orphaned references (Section 2) would violate the enforced FK to `cv_detections` | **Rejected** from the bridge table; **flagged** in `data_quality_issues` with raw ids preserved |
| Missing/always-empty sanitized fields | `cv_detections.disposition`, `cv_track_states.parent_object_track_id`, `fused_track_states.parent_track_id`/`track_quality`, `radar_detections.object_type_class`/`object_class`, etc. | Consistent, field-specific emptiness across the whole file, matching the file's own name ("sanitized.mcap") | **Retained** as nullable columns, not omitted — CLAUDE.md rule 12 |
| Enum normalization | every `_raw`/`_name` column pair | Preserve the exact source integer (rule: don't invent data) alongside a human-readable name resolved from the real protobuf enum definition (never invented) | Both columns retained; no row rejected |
| Duplicate/repeated-state handling | `cv_track_states`, `fused_track_states` | Stage 2/3 confirmed this repetition is the *expected* shape of persistent-entity state history, not a defect | Retained — this is the intended grain, not something to deduplicate |
| Repeated-association handling | `cv_detection_track_links` | The same (detection, track) pairing legitimately repeats 1,865 times (Section 5.5) across track updates | Deduplicated at load time into one row per distinct pair; raw repetition remains visible via `cv_track_states.last_associated_detection_id` |
| Range/type validation | numeric columns generally | No confirmed valid range was established in Stage 2/3 for most numeric fields (score, range, azimuth, etc.) | No `CHECK` constraints imposed without evidence; out-of-range values, if ever found, would be a future `data_quality_issues` finding, not silently corrected |
| CV incorporation percentage | `cv_detection_track_links` / `cv_detections` | Section 2 — the ~81% target is not reproduced by any evidence-supported definition | **Not corrected to match 81%.** Reported as computed (~97.8%–99.9% depending on method), with the discrepancy itself recorded as a `data_quality_issues`-style finding at the analysis level, not the row level |

---

## 9. SQL analytics review — how this schema keeps the required queries simple

1. **CV incorporation %:** `COUNT(*) FROM cv_detections` vs.
   `COUNT(DISTINCT detection_id) FROM cv_detection_track_links` — one
   table each, no joins. (See Section 2 for why the *interpretation* of
   this number is still open.)
2. **Fused-track duration by class:** `v_fused_track_summary` (Section
   5.11) joined to `fused_track_states.object_class_raw`/`_name` — one
   view, one table, `GROUP BY`. (See Section 3 for the class-resolution
   caveat.)
3. **Message counts by topic:** `GROUP BY topic` on `source_messages`
   alone.
4. **Track history over time:** `SELECT * FROM cv_track_states WHERE
   track_id = ? ORDER BY log_time_ns` (or the `fused_track_states`
   equivalent) — one table, indexed on both columns already.
5. **Sensor contribution:** `GROUP BY sensor_id_raw` on
   `fused_track_measurements` — one table.
6. **Data quality reporting:** `SELECT * FROM data_quality_issues` — one
   table, no joins at all.

No required query needs more than a two-table join plus, at most, one of
the two recommended views.

---

## 10. Performance

- **SQLite indexes:** every FK column and every column used to `GROUP BY`
  or filter by in Section 9's queries has a recommended index (listed per
  table in Section 5). SQLite does not automatically index foreign keys
  (unlike some other databases), so these are load-bearing, not optional.
- **Query performance:** at this data volume (57,266 envelope rows;
  largest child table `fused_track_measurements` at 11,992 rows), every
  query in Section 9 is expected to run in well under a second on typical
  hardware, index or no index — the indexes matter more for future,
  larger files than for this specific dataset.
- **Storage efficiency:** SQLite's dynamic typing means nullable/absent
  columns cost little; the two JSON columns (`cluster_json`,
  `detection_ids_json`) are currently near-empty (`cluster_json`) or
  modest (13,596 total id occurrences) and not a storage concern at this
  scale.
- **Join complexity:** capped at two tables for every required query
  (Section 9) — a direct, measured consequence of the compact 10-table
  design, not an accident.
- **Expected bottlenecks:** none anticipated at this data volume. If the
  source file's scale grew by orders of magnitude, `fused_track_measurements`
  (highest row count of the child tables) and `cv_track_states`/`fused_track_states`
  (append-only history) would be the first candidates for partitioning or
  archival strategy — not a concern for the current file.

---

## 11. Unresolved risks (see also Sections 2 and 3)

- The ~81% CV-incorporation target is not reproduced by any evidence-
  supported definition (Section 2) — requires human/business clarification.
- The Drone-vs-Airplane duration question cannot currently be answered:
  the fused classification enum cannot represent those categories at all,
  and even CV's richer enum never uses them in this file (Section 3).
- `radar_detections.track_id`'s true meaning is unknown — CONFIRMED
  unrelated to every other track-identifier namespace in the file, but
  its own semantics were not otherwise recoverable from the schema.
- `capture_time_ns` population (on `cv_detections`, `cv_track_states`,
  `radar_detections`) is an ASSUMPTION based on 3 structural samples per
  topic (Stage 2), not a full-dataset scan — should be re-verified during
  ETL implementation before being relied upon as reliably populated.
- All findings in this document describe one sanitized recording session.
  Whether the always-empty fields, the 100%-unique detection ids, or the
  zero-overlap track-id namespaces would hold for a different file was
  not and cannot be tested here.
