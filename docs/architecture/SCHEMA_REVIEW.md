# Schema Review — Skeptical Senior Data-Engineering Pass

Stage 5A deliverable. This is an adversarial review of the Stage 4 design
(`docs/architecture/DATABASE_DESIGN.md`, `docs/architecture/TABLE_GRAIN.md`,
`docs/architecture/NORMALIZATION_DECISIONS.md`, `docs/architecture/ERD.md`), performed before any
`schema.sql`, database, ETL, or view is implemented. No file was changed
before this review was written; corrections are applied afterward, only
where a finding below justifies one.

## Methodology and new evidence gathered

Every finding below is evidence-based. Where Stage 2/3/4's existing
evidence did not already settle a question, a fresh, read-only,
full-dataset query was run directly against `data/input/sanitized.mcap`
during this review (never Stage 2's 3-sample structural observation) and
is cited by its result. New evidence gathered in this review, not present
in any prior document:

1. `cv_tracks.tracks[].class_distribution` — population and value
   distribution (previously omitted from the schema, never measured).
2. `track_states.object_class_external` — population (previously omitted,
   never measured).
3. `track_states.object_class_confidence` — population and range
   (previously not analyzed in Stage 2/3 at all).
4. Per-track history of `track_states.object_class` — whether it actually
   changes within one persistent track's lifetime.
5. `radar_detections` value ranges for `range`, `azimuth`, `elevation`,
   `range_rate`, `snr`, `filter_type`, `estimated_width_meters`,
   `is_marked`, and frame-level `capture_time` population — full dataset,
   not samples.
6. `cv_detections`/`cv_tracks` frame-level `capture_time` population —
   full dataset (previously an ASSUMPTION based on 3 Stage 2 samples).
7. `track_states.track_status` value distribution — full dataset
   (previously an ASSUMPTION).
8. Signed 64-bit integer headroom for the observed nanosecond timestamp
   range (arithmetic check, not a data query).

Findings are labeled with exactly one of five categories, per instruction:

- **CONFIRMED DEFECT** — the design as written will misbehave or is
  factually wrong.
- **DESIGN IMPROVEMENT** — the design works, but evidence supports a
  better version.
- **DOCUMENTATION AMBIGUITY** — the design is fine, but the document does
  not say so clearly enough, risking a future implementer getting it
  wrong.
- **PERFORMANCE OPTIMIZATION** — correctness is unaffected; efficiency or
  clarity is.
- **UNRESOLVED QUESTION** — no schema change fixes this; it is a real
  limit of the data or the assignment's own ambiguity, recorded so it is
  not silently dropped.

---

## Findings

### F1 — `cv_track_states.last_associated_detection_id` FK status is implicit, not stated

- **Severity:** major
- **Category:** DOCUMENTATION AMBIGUITY
- **Affected:** `docs/architecture/DATABASE_DESIGN.md`, table `cv_track_states`
- **Problem:** the design's "Foreign keys" bullet for `cv_track_states`
  lists only `source_message_id` and `track_id`, and separately states
  `parent_object_track_id` is explicitly unenforced. It never explicitly
  says `last_associated_detection_id` is *also* not FK-enforced — a
  reader has to infer this by noticing it's absent from the FK list.
- **Why risky:** `last_associated_detection_id` *looks* exactly like a
  foreign key (an id column pointing at another table's PK). An
  implementer skimming the table spec, not the full prose, could
  reasonably add `REFERENCES cv_detections(detection_id)` to this column
  "for completeness" — which would then fail to load on exactly the 4
  rows the design already knows are orphaned (see F-evidence below),
  breaking the append-only load for reasons the implementer would have to
  rediscover from scratch.
- **Evidence:** `docs/data/KEY_ANALYSIS.md` / `data/output/key_analysis.json`,
  `detection_track_relationship.orphaned_references = 4`; Stage 4's own
  `docs/architecture/DATABASE_DESIGN.md` Section 5.5 cleaning rule already handles this
  correctly for `cv_detection_track_links`, but never states the parallel
  requirement for the raw column on `cv_track_states`.
- **Correction:** add an explicit sentence to `cv_track_states`'
  specification: "`last_associated_detection_id` is intentionally **not**
  FK-enforced on this table (unlike `cv_detection_track_links`, where the
  4 orphaned values are filtered out before insertion) — enforcing it
  here would reject 4 otherwise-valid track-state rows."
- **Effect:** documentation-only change. No column, key, or constraint
  changes. Prevents a real future ETL bug.

### F2 — Loading order does not state the two-phase requirement `PRAGMA foreign_keys = ON` creates

- **Severity:** major
- **Category:** CONFIRMED DEFECT (in the *documentation's* completeness,
  not the schema's correctness — the schema itself is fine; a naive
  implementation of "load in the stated numeric order, one message at a
  time" is not)
- **Affected:** `docs/architecture/DATABASE_DESIGN.md`, tables `cv_tracks`,
  `cv_track_states`, `fused_tracks`, `fused_track_states`
- **Problem:** `cv_tracks` and `fused_tracks` are populated from the
  *distinct values* observed across `cv_track_states`'/`fused_track_states`'
  own source data (`docs/architecture/DATABASE_DESIGN.md` Sections 5.3, 5.7) — they are
  not decoded from a separate protobuf structure. The design lists a
  numeric loading order (`cv_tracks` = 3rd, `cv_track_states` = 4th) but
  never states that this requires the *entire* `cv_tracks` topic to be
  scanned for distinct `track_id` values, and every row inserted into
  `cv_tracks`, **before any** `cv_track_states` row is inserted — not
  "process messages in file order, track by track."
- **Why risky:** a natural, single-pass streaming implementation — decode
  each `cv_tracks` message, insert its tracks into `cv_track_states` as
  they're seen — will insert a `cv_track_states` row referencing a
  `track_id` on its *first* appearance, before that `track_id` has been
  inserted into `cv_tracks`. With `PRAGMA foreign_keys = ON` (CLAUDE.md
  rule 8), this insert fails immediately. This is exactly the kind of
  loading-order problem the review was asked to test for (#4, #24).
- **Evidence:** `docs/data/KEY_ANALYSIS.md`, "Persistent entity vs. update
  analysis" — `cv_tracks.tracks.track_id` is derived, not native; 17
  distinct values, each appearing across many messages (up to 1,676
  times), confirming the identity table cannot be known until (at least)
  a full scan of that topic's `track_id` values has happened.
- **Correction (concrete, per instruction — not "disable foreign
  keys"):** a **two-phase load**, tested conceptually below in "Loading
  order test," Section 3:
  - **Phase 1:** load `source_messages` (all 4 topics, one full pass);
    then, from the same pass's decoded `cv_tracks`/`track_states` data
    already held in memory or re-read once, insert every distinct
    `track_id` into `cv_tracks` and every distinct `track_id2` into
    `fused_tracks`.
  - **Phase 2:** with both identity tables fully populated, load
    `cv_detections`, `cv_track_states`, `cv_detection_track_links`,
    `radar_detections`, `fused_track_states`, `fused_track_measurements`,
    `data_quality_issues`, in that order, each safely able to FK against
    an already-complete parent table.
  - This works with `PRAGMA foreign_keys = ON` at all times — no
    deferred-constraint transaction tricks are required, though `PRAGMA
    defer_foreign_keys = ON` (scoped to a single transaction) is noted as
    a valid *alternative* for an implementer who prefers single-pass
    streaming over two explicit phases; it is not the primary
    recommendation, per instruction not to default to relaxing
    enforcement.
- **Effect:** ETL: this is now a concrete, two-phase algorithm instead of
  an implicit ordering claim — directly actionable for Stage 5/6. SQL
  simplicity: unaffected (this is purely a load-time concern). Maintainability:
  significantly improved — the next engineer does not have to rediscover
  this constraint by hitting the FK failure themselves.

### F3 — Two indexes are redundant with existing UNIQUE constraints

- **Severity:** minor
- **Category:** PERFORMANCE OPTIMIZATION
- **Affected:** `docs/architecture/DATABASE_DESIGN.md`, tables `cv_track_states`,
  `fused_track_states`
- **Problem:** `cv_track_states` declares both `UNIQUE(source_message_id,
  track_id)` and a separate `idx_cv_track_states_source_message(source_message_id)`.
  `fused_track_states` declares both `UNIQUE(fused_track_id, log_time_ns)`
  and a separate `idx_fused_track_states_fused_track_id(fused_track_id)`.
- **Why risky:** not a correctness issue, but a maintenance and storage
  cost with zero benefit. SQLite automatically creates an index to
  enforce a `UNIQUE` constraint, and by the standard leftmost-prefix rule
  for multi-column indexes, that automatic index is already fully usable
  for any query filtering on just the *first* column of the constraint
  (`source_message_id` alone; `fused_track_id` alone). The separately
  declared single-column index duplicates that coverage exactly.
- **Evidence:** this is a property of how SQLite (and relational indexes
  generally) resolve multi-column indexes, not something the source data
  can confirm or refute — a reasoning-based finding, not a data-query
  finding. (By contrast, `idx_cv_track_states_track_id(track_id)` is
  **not** redundant: `track_id` is the *second* column of the `UNIQUE`
  pair, so a query filtering on `track_id` alone cannot use that
  composite index's leftmost prefix and genuinely needs its own index —
  this one is correctly kept.)
- **Correction:** remove `idx_cv_track_states_source_message` and
  `idx_fused_track_states_fused_track_id` from the recommended-indexes
  list in both tables' specifications.
- **Effect:** ETL: two fewer indexes to create and maintain during bulk
  load. SQL simplicity: none. Maintainability: one less place for the
  index list to drift out of sync with the constraint list.

### F4 — Radar `azimuth`/`elevation` units were never verified; `range`/`range_rate`/`snr` are confirmed always empty in this file

- **Severity:** major
- **Category:** DESIGN IMPROVEMENT + DOCUMENTATION AMBIGUITY (units), plus
  an UNRESOLVED QUESTION (radar's actual analytical usefulness)
- **Affected:** `docs/architecture/DATABASE_DESIGN.md`, table `radar_detections`
- **Problem / evidence, checked fresh in this review (full dataset,
  2,929 radar detections):**
  - `azimuth`: observed range **[0.0376, 6.2788]** — matches `[0, 2π]`
    (2π ≈ 6.2832) almost exactly. This is strong empirical evidence
    `azimuth` is in **radians**, not degrees.
  - `elevation`: observed range **[0.0066, 0.1975]** — a narrow band
    consistent with radians (≈0.38° to ≈11.3°); as degrees, this range
    would be an implausibly narrow near-zero elevation band for every
    single detection in the file.
  - `range`: **always exactly 0.0** across all 2,929 detections.
  - `range_rate`: **never populated** (`HasField` false for all 2,929).
  - `snr`: **never populated**.
  - `filter_type`: always raw `0` (`FILTER_TYPE_UNKNOWN`).
  - `estimated_width_meters`: never populated.
  - `is_marked`: always `false`.
  - Frame-level `capture_time`: populated in all 2,902 `radar_detections`
    messages (upgraded from unchecked to CONFIRMED).
  - (Previously confirmed in Stage 4: `object_type_class`, `object_class`,
    `radar_type`, `cluster` are also always constant/empty.)
- **Why risky:** two distinct risks. First, storing an unlabeled `azimuth`/
  `elevation` column invites a future analyst or query author to assume
  degrees (the more common convention in ad hoc reporting) and silently
  compute wrong geometry. Second, and more importantly: **once `range`,
  `range_rate`, `snr`, `filter_type`, `estimated_width_meters`, `is_marked`,
  `object_type_class`, `object_class`, and `radar_type` are all removed
  from consideration as always-empty, the only genuinely populated,
  analytically useful fields left on `radar_detections` are `azimuth`,
  `elevation`, `track_id`, and `capture_time_ns`.** The "radar analysis"
  required query (`docs/architecture/DATABASE_DESIGN.md` Section 9, item 5's sibling
  requirement) is far more constrained by this dataset than the full
  column list in the current design implies.
- **Correction:**
  1. Rename `azimuth` → `azimuth_rad`, `elevation` → `elevation_rad` (the
     value is already flattened from a wrapped `DoubleValue`, so this is
     a rename only, no structural change), and state the empirical basis
     for "radians" directly in the column note rather than leaving it
     implicit.
  2. Add explicit CONFIRMED-empty annotations (not a structural change —
     these columns are already nullable, consistent with rule 12) to
     `range`, `range_rate`, `snr`, `filter_type`, `estimated_width_meters`,
     `is_marked`, matching the documentation style already used for
     `disposition`, `track_quality`, etc.
  3. Add a prominent note to Section 9's radar-analysis discussion: in
     this file, radar analysis is effectively limited to azimuth/elevation
     geometry and `track_id`-based grouping — recorded as an UNRESOLVED
     QUESTION about this dataset's actual radar analytical scope, not a
     schema defect.
- **Effect:** ETL: none (no column added/removed, only renamed/annotated).
  SQL simplicity: unaffected. Maintainability: prevents a real,
  plausible unit-confusion bug; sets accurate expectations for what radar
  analysis can and cannot show with this file.

### F5 — `class_distribution` and `object_class_confidence` were never measured before being designed around; both change the classification picture

- **Severity:** major
- **Category:** DESIGN IMPROVEMENT (confirmed by fresh full-dataset
  evidence, not previously gathered in Stage 2/3/4)
- **Affected:** `docs/architecture/DATABASE_DESIGN.md`, `docs/architecture/NORMALIZATION_DECISIONS.md`,
  tables `cv_track_states`, `fused_track_states`
- **Problem:** the original design omitted `cv_tracks.tracks[].class_distribution`
  (repeated, per-candidate-class probability scores) and never
  investigated `track_states.object_class_confidence` (a plain scalar,
  not repeated) at all — it is simply absent from the original column
  list. Given the project's already-unresolved Drone/Airplane question,
  omitting a confidence/alternative-classification signal without first
  checking whether it contains relevant information was a genuine gap in
  the original review rigor, not just a compact-design trade-off.
- **Evidence, checked fresh in this review:**
  - `class_distribution` **is populated**: all 9,496 `cv_track_states`
    rows have exactly 4 entries each. The classification values that
    actually appear are only `OBJECT_CLASSIFICATION_BIRD` (raw 11),
    `OBJECT_CLASSIFICATION_AIR_VEHICLE` (raw 21), and
    `OBJECT_CLASSIFICATION_UNKNOWN` (raw 50) — confirmed via direct
    enum reflection, not memory. **DRONE and AIRPLANE never appear**,
    even as a low-probability alternative candidate. Sample scores: the
    top candidate (`AIR_VEHICLE`) typically carries ~0.92–0.93
    probability; the alternates carry ~0.004–0.008. This *reinforces*
    Section 3's existing conclusion (no Drone/Airplane signal exists in
    this file's CV data) with stronger evidence than before — it is not
    a reversal.
  - `object_class_confidence` (on `track_states`, the *fused* side) **is
    populated in all 11,630 rows**, ranging from ~0.50 to 1.0, and was
    never included as a column in the original design at all.
  - `track_states.object_class_external` (the repeated,
    timestamped classification-history field) is **confirmed always
    empty** (length 0 in all 11,630 rows) — this *confirms* the original
    omission was safe, no reversal needed here.
- **Why this matters:** a per-row confidence score sitting directly next
  to a classification the project has already flagged as ambiguous
  (Section 3) is exactly the kind of supporting evidence an analyst would
  reach for first when investigating that ambiguity — omitting it without
  even checking its population was a real gap.
- **Correction:**
  1. Add `object_class_confidence REAL NULLABLE` to `fused_track_states`
     (a plain scalar column, zero normalization cost, confirmed 100%
     populated).
  2. Add `object_class_confidence REAL NULLABLE` to `cv_track_states`,
     derived at ETL time as the `probability_score` of the
     `class_distribution` entry whose `classification` matches the row's
     own `object_class_raw` (a simple lookup within the already-decoded
     repeated field — no new table, no JSON, no full-fidelity storage of
     the other 3 candidates).
  3. **Retain** the decision not to store the full `class_distribution`
     array (the other 3 candidates and their scores) as a table or JSON
     column — confirmed, with fresh evidence, that none of the
     alternative candidates are ever Drone/Airplane, so the marginal
     value of keeping the full distribution is low relative to the
     compact-design goal. Document this explicitly as a re-affirmed,
     evidence-checked decision, not an unexamined one.
- **Effect:** ETL: one additional simple lookup per `cv_track_states` row
  (no new join, no new table); one additional pass-through scalar per
  `fused_track_states` row. SQL simplicity: improved for any future
  confidence-filtered query (e.g. "only count high-confidence
  classifications"). Maintainability: the schema now visibly reflects
  that a real, checked confidence signal exists and was consciously
  included or excluded, not silently missed.

### F6 — Fused-track classification genuinely changes within a track's own history — Section 9's "duration by class" query is more complex than stated

- **Severity:** critical (for the accuracy of Section 9's claim and for
  the still-unresolved Drone/Airplane question); the underlying
  UNRESOLVED QUESTION itself is not fixable by a schema change
- **Category:** DOCUMENTATION AMBIGUITY (Section 9's oversimplification)
  wrapping a genuine UNRESOLVED QUESTION (which classification semantic
  to use)
- **Affected:** `docs/architecture/DATABASE_DESIGN.md` Section 9 (analytics review,
  query #2) and Section 5.11 (`v_fused_track_summary`)
- **Problem:** Section 9 originally described "fused-track duration by
  class" as answerable via "`v_fused_track_summary` joined to
  `fused_track_states.object_class_raw`/`_name` — one view, one table,
  `GROUP BY`." This understates the problem: `object_class` is recorded
  **per state row**, not per persistent track, so "the" class of a track
  is not a given fact — it must be *resolved* from potentially many,
  sometimes conflicting, observations before any `GROUP BY class` is
  meaningful.
- **Evidence, checked fresh in this review:** of the 103 persistent fused
  tracks, **18 (17.5%) show more than one distinct `object_class` value
  across their own state history.** Inspecting the actual sequences shows
  two genuinely different patterns, not one: some are clearly single-frame
  noise (e.g. one track: 183 states of `BIRD`, a single `UNKNOWN_AIR_VEHICLE`
  state, then back to `BIRD`) — but others are real, sustained transitions
  (e.g. one track: 37 consecutive states of `UNKNOWN_AIR_VEHICLE` followed
  by 63 consecutive states of `AIR_VEHICLE`, no flapping). A single
  "pick one class per track" rule cannot correctly handle both patterns
  with the same logic.
- **Why this matters:** this is not just a documentation nit — it means
  the schema and its recommended view, as originally written, would
  produce a *silently arbitrary* answer to "duration by class" depending
  on incidental implementation choices (which `GROUP BY` happens to run
  first), without ever surfacing that arbitrariness to whoever reads the
  result.
- **Correction:** do **not** pick a semantic in the schema design (per
  explicit instruction). Instead:
  1. Rewrite Section 9's query #2 description to state plainly that
     resolving "the" class per track is an unresolved modeling decision,
     not a solved `GROUP BY`.
  2. Add a new, explicit comparison of classification semantics (below,
     Section 4 of this review) to `docs/architecture/DATABASE_DESIGN.md`, so whoever
     makes this decision later has the real trade-offs and real evidence
     in front of them, not a blank slate.
  3. `v_fused_track_summary` remains as specified (identity, first/last
     timestamp, duration, row count) — it deliberately still does **not**
     attempt to resolve a class, consistent with the original Section 3
     caveat, now with stronger justification for why that restraint is
     correct.
- **Effect:** ETL: none yet — this remains a documentation/analysis
  change, not a schema change, until a semantic is chosen. SQL simplicity:
  the *honest* complexity of this query is now visible instead of hidden;
  whichever semantic is eventually chosen will need to be implemented as
  its own resolved-class lookup (a small table or a query-time CTE), not
  assumed away. Maintainability: prevents a future engineer from shipping
  a silently-arbitrary "duration by class" report.

### F7 — Nanosecond timestamps stored as `INTEGER`: confirmed safe, not just assumed

- **Severity:** informational
- **Category:** CONFIRMED (no defect found; upgrading a previously
  implicit assumption to an explicit, checked fact)
- **Affected:** `docs/architecture/DATABASE_DESIGN.md`, all timestamp columns
- **Evidence:** SQLite's `INTEGER` storage class is a signed 64-bit
  integer, maximum `9,223,372,036,854,775,807`. The observed
  `log_time_ns` range in this file is `1,761,244,500,011,495,000` to
  `1,761,245,699,980,848,000` — about **5.24×** smaller than the 64-bit
  maximum. There is no precision loss, and no overflow risk for this
  timestamp format at any date before roughly the year 2262 (when
  nanosecond-since-epoch values would approach the 64-bit signed limit).
- **Correction:** none required. Add one sentence to
  `docs/architecture/DATABASE_DESIGN.md` stating this was explicitly checked (not
  assumed), for the reader's confidence.
- **Effect:** none — confirms an already-correct decision with evidence
  instead of assumption.

### F8 — Natural-key uniqueness is data-observed for this one file, not protobuf-guaranteed

- **Severity:** informational (cannot be resolved by a schema change)
- **Category:** UNRESOLVED QUESTION
- **Affected:** `docs/architecture/DATABASE_DESIGN.md`, tables `cv_detections`,
  `cv_tracks`, `fused_tracks`
- **Problem:** `detection_id`'s 100% uniqueness, `track_id`'s stable
  persistent-entity behavior, and `fused_track_id`'s same behavior, are
  all facts about *this one 57,266-message recording*, established by
  Stage 3's full-dataset scan — not properties the `.proto` schema itself
  guarantees (nothing in the protobuf definitions marks these fields as
  unique). A longer deployment, a different recording session, or a
  restarted tracker process could, in principle, reuse an id.
- **Why this matters, but is not fixable here:** this is exactly why
  `docs/architecture/DATABASE_DESIGN.md` already frames these as CONFIRMED-for-this-file
  rather than universally guaranteed — this finding does not change the
  chosen primary keys (they remain the best-supported choice available),
  it strengthens the existing caveat so a future reader does not mistake
  "confirmed in this file" for "guaranteed by the schema."
- **Correction:** strengthen the existing caveat language in Sections 5.2,
  5.3, 5.7 to explicitly state "this is a property of the observed data
  in this file, not a constraint the protobuf schema enforces" — no key
  decision changes.
- **Effect:** documentation-only. No structural change. Sets correct
  expectations for anyone loading a *different* MCAP file through this
  same schema later.

### F9 — No circular dependencies, no hidden unjustified cross-topic joins, no unproven CHECK constraints, no giant mixed-concern tables

- **Severity:** informational
- **Category:** CONFIRMED (explicitly checked, nothing found — recorded
  so the review demonstrably covered these checklist items rather than
  silently skipping them)
- **Checked:**
  - **Circular dependencies (#4):** the 9 FK relationships form a strict
    DAG (`source_messages` → 4 tables; `cv_tracks`/`cv_detections` →
    `cv_detection_track_links`; `fused_tracks` → `fused_track_states` →
    `fused_track_measurements`). No cycle exists. The only ordering
    subtlety is the two-phase requirement in F2, which is a *data*
    dependency, not a *schema-level* circular FK.
  - **Unjustified cross-topic joins (#12):** every cross-topic
    relationship the design proposes (`cv_detections` ↔ `cv_tracks`) is
    the one Stage 3 confirmed; every one Stage 3 rejected
    (`radar_detections.track_id` against anything;
    `parent_object_track_id`/`parent_object_detection_id`) is correctly
    left unenforced. No new unjustified join was found.
  - **CHECK constraints (#23):** the only `CHECK` in the design
    (`data_quality_issues.severity IN ('info','warning','error')`)
    constrains an ETL-internal vocabulary this project defines itself,
    not an assumption about source-data ranges — no unproven CHECK exists.
  - **Giant tables mixing unrelated concerns (#16):** the widest table,
    `fused_track_states`, holds only attributes that are genuinely facts
    about one state row (position, classification, disposition, quality,
    timestamps) — no unrelated concern (e.g. sensor-measurement detail,
    which correctly lives in `fused_track_measurements`) is mixed in.
- **Effect:** none — confirms these areas of the design pass a skeptical
  check.

---

## 1. Explicit re-check of the 10-table model

| Table | Grain still accurate? | New issues this review | Verdict |
|---|---|---|---|
| `source_messages` | Yes | none | Retained as-is |
| `cv_detections` | Yes | F8 (caveat strengthened) | Retained as-is |
| `cv_tracks` | Yes | F2 (loading order), F8 (caveat) | Retained; loading-order note added |
| `cv_track_states` | Yes | F1, F2, F3, F5 | Retained; FK-status note, index fix, `object_class_confidence` column added |
| `cv_detection_track_links` | Yes | none new (grain re-affirmed correct) | Retained as-is |
| `radar_detections` | Yes | F4 | Retained; columns renamed/annotated, no structural change |
| `fused_tracks` | Yes | F2, F8 (caveat) | Retained; loading-order note added |
| `fused_track_states` | Yes | F2, F3, F5, F6 | Retained; index fix, `object_class_confidence` column added, Section 9 corrected |
| `fused_track_measurements` | Yes | none new (JSON decision re-affirmed) | Retained as-is |
| `data_quality_issues` | Yes | none | Retained as-is |

No table is added, removed, merged, or split by this review. The 10-table
model holds up under skeptical review — every issue found is a
refinement (a missing column, a missing sentence, a redundant index), not
a structural flaw.

## 2. Explicit re-check of the 14 named decisions

| Decision | Verdict | Basis |
|---|---|---|
| `cv_detections.detection_id` as natural PK | **Retained** | Still the only 100%-unique field found (Stage 3); caveat strengthened (F8) |
| `cv_tracks.track_id` as persistent-entity PK | **Retained** | Confirmed stable, zero within-message duplicates (Stage 2); caveat strengthened (F8) |
| `UNIQUE(source_message_id, track_id)` for `cv_track_states` | **Retained** | Confirmed collision-free (Stage 2); redundant *secondary index* removed (F3), constraint itself unchanged |
| `fused_track_id` as fused persistent-track identity | **Retained** | Confirmed 103 distinct, clean state-history behavior (Stage 3) |
| `UNIQUE(fused_track_id, log_time_ns)` supporting constraint | **Retained** | Confirmed collision-free (Stage 3); redundant *secondary index* removed (F3), constraint itself unchanged |
| Detection-track bridge-table grain | **Retained** | Still the Stage-3-recommended grain; re-emphasize it does not resolve the 81% question (unchanged from Stage 4) |
| `source_message_id` as generated surrogate key | **Retained** | Still the only collision-free option across the whole file (Stage 3); loading-order implication now made explicit (F2) |
| Non-enforcement of radar/CV/fused `track_id` cross-topic relationships | **Retained** | Re-checked (F9) — no new evidence found supporting enforcement |
| Nullable handling for the 4 orphaned detection references | **Retained**, clarified | Bridge-table behavior unchanged; explicit statement added that the raw column is *also* unenforced, for the same reason (F1) |
| `detection_ids_json` in `fused_track_measurements` | **Retained** | No new evidence found that changes the Issue-4 trade-off from Stage 4 |
| `cluster_json` in `radar_detections` | **Retained** | Re-confirmed still always empty; no id field exists regardless (unchanged from Stage 4) |
| Raw enum value plus resolved enum name | **Retained** | Pattern held up under review; directly enabled this review's own enum-reflection checks (F4, F5) |
| Duration derived with views rather than stored | **Retained** | Still correct; F6 adds that the *fused* view should not attempt class resolution either |
| Nanosecond timestamps stored as `INTEGER` | **Retained**, confirmed | Upgraded from assumed-safe to arithmetically confirmed safe (F7) |

**Zero of the 14 named decisions were reversed.** Three (`cv_track_states`'
FK list, the two supporting-constraint index pairs, `v_fused_track_summary`'s
scope) received clarifying or corrective refinements. This is the expected
outcome of a healthy review — not every finding should force a structural
change, and this review did not manufacture structural changes to appear
more thorough.

## 3. Loading-order test, `PRAGMA foreign_keys = ON`

Walking the 10-table load in the originally-stated numeric order
(1 → 10), with foreign-key enforcement active throughout, exactly as
CLAUDE.md rule 8 requires:

1. `source_messages` — no FKs, loads freely.
2. `cv_detections` — FK to `source_messages` (already loaded). OK.
3. `cv_tracks` — no FKs. **But its 17 rows must be fully known before
   step 4** — see F2. If step 3 is implemented as "scan the entire
   `cv_tracks` topic once, insert every distinct `track_id`," this step
   is safe and complete before step 4 begins.
4. `cv_track_states` — FKs to `source_messages` (loaded, step 1) and
   `cv_tracks` (loaded completely, step 3, **only if step 3 was a full
   scan, not incremental**). Safe under the two-phase strategy in F2;
   **fails under naive single-pass streaming**, confirmed by this test.
5. `cv_detection_track_links` — FKs to `cv_detections` (step 2) and
   `cv_tracks` (step 3). Safe once both are complete. The 4 orphaned rows
   are filtered before insertion (Stage 4 rule, re-confirmed F1) — no FK
   failure.
6. `radar_detections` — FK to `source_messages` only. Safe, independent
   of steps 2–5.
7. `fused_tracks` — no FKs, but same full-scan requirement as step 3
   (F2).
8. `fused_track_states` — FKs to `source_messages` and `fused_tracks`
   (must be complete first, same reasoning as step 4).
9. `fused_track_measurements` — FK to `fused_track_states` (step 8,
   complete). Safe.
10. `data_quality_issues` — no enforced FKs (F9 confirms
    `related_table`/`related_id` are intentionally loose). Safe, and
    logically depends on validation having run against 1–9.

**Result: the design is loadable end-to-end with `PRAGMA foreign_keys = ON`
at every step, with zero constraint relaxation, provided steps 3 and 7 are
implemented as complete, upfront scans (the two-phase strategy, F2) rather
than incremental discovery during steps 4/8.** This is the one genuine
loading-order risk this review found, and it is fully resolved by F2's
correction without disabling any enforcement.

## 4. Fused-track classification semantics — comparison, not a choice

Per instruction, this section defines and compares the plausible
semantics for "the" classification of a persistent fused track, without
selecting one. **None of these semantics changes the underlying blocker:
the `proto.tower.TrackObjectClass` enum used by `fused_track_states.object_class`
has no DRONE or AIRPLANE value at all (Stage 4, Section 3, re-confirmed
unchanged by this review) — every option below still cannot answer
CLAUDE.md's Drone/Airplane question. This comparison is about the
*general* problem of resolving one class per track for classes the enum
*can* represent, evaluated using this file's real AIR_VEHICLE/
UNKNOWN_AIR_VEHICLE/BIRD data as the concrete test case.**

Real evidence used for this comparison (F6): of 103 persistent fused
tracks, 18 (17.5%) show more than one distinct `object_class` across
their history; inspection shows both single-frame noise blips and real,
sustained transitions among them; `object_class_confidence` (F5) is a
real, fully-populated per-row field (~0.50–1.0) usable by any
confidence-based option below.

| Semantic | Definition | Strength | Weakness (using this file's real tracks) |
|---|---|---|---|
| **Class at first observation** | `object_class` of the row with `MIN(log_time_ns)` for that track | Simple, deterministic, no aggregation logic needed | For the 37-then-63-state track (F6 example), reports `UNKNOWN_AIR_VEHICLE` even though the track spent the *majority* of its life as `AIR_VEHICLE` — not representative |
| **Class at last observation** | `object_class` of the row with `MAX(log_time_ns)` for that track | Simple; often preferred operationally (most information accumulated) | For a track whose classification degrades right before loss (a plausible failure mode, not directly observed but not ruled out either), "last" could be the *least* reliable point, not the most |
| **Most frequent class (mode)** | `object_class` with the most state rows for that track | Robust to single-frame noise (correctly handles the 183/1/1 BIRD-blip-BIRD track) | For a near-even split like 37/63, picks one arbitrarily with no regard to confidence; ties need an explicit tiebreak rule not yet defined |
| **Highest-confidence class** | `object_class` of the row with `MAX(object_class_confidence)` for that track | Uses a real, evidenced per-row signal (F5) the source system itself reports about its own certainty; now genuinely implementable given F5's finding that this field is fully populated | A single confidence spike does not necessarily represent the class the track was observed as *most of the time*; not yet checked whether high-confidence rows correlate with the "real" transitions or the noise blips |
| **Class-interval splitting** | Do not resolve to one class per track at all; split each track's state history into contiguous same-class runs, each becoming its own duration interval | Most faithful to the data — does not discard the fact that 17.5% of tracks genuinely change class; directly supported by the run-length evidence in F6 | Changes the *meaning* of "average fused-track duration by class" from "per persistent track" to "per classified interval," which may not match what CLAUDE.md's phrasing ("average fused-track duration for Drone objects") intends; a track could contribute multiple, shorter intervals instead of one |

**No option is selected.** All five remain equally valid candidates
pending a business-rule decision this project's evidence cannot make on
its own — consistent with the explicit instruction not to choose one
without source or assignment justification for doing so. Whichever is
chosen later, it does not need a new stored column beyond
`object_class_confidence` (F5, now added) — it needs a query-time or
view-time resolution rule, decided by a human, not invented here.

---

## 5. Unresolved issues carried forward (explicitly not re-litigated toward a target)

- **CV detection incorporation is approximately 97.8%–99.9%, not
  approximately 81%.** Re-examined in this review for any evidence that
  would change this conclusion (F5's class_distribution investigation, F6's
  classification investigation) — none found. This remains an open
  question requiring human/business-rule clarification, not a schema
  defect and not something this review manufactured a fix for.
- **Drone/Airplane duration is not currently supported by the observed
  fused classification schema or data.** This review's fresh evidence
  (F5) *strengthens* this conclusion rather than weakening it: even the
  richer, multi-candidate `class_distribution` signal on the CV side never
  assigns any probability to DRONE or AIRPLANE in this file, and the
  fused-side enum cannot represent those categories at all, regardless of
  which classification-resolution semantic (Section 4) is eventually
  chosen.
- **Radar analytical scope is narrower than the original column list
  implied** (F4, new finding this review) — recorded as its own
  unresolved question about this dataset's actual radar-analysis
  potential, not a schema defect, since every affected column is already
  nullable per the existing sanitized-field handling pattern.

## 6. Summary of corrections applied after this review

1. `cv_track_states`: explicit "not FK-enforced" statement for
   `last_associated_detection_id` (F1); `object_class_confidence` column
   added (F5); `idx_cv_track_states_source_message` removed as redundant
   (F3); `idx_cv_track_states_object_class` added (supports F5/F6
   follow-up analysis).
2. `fused_track_states`: `object_class_confidence` column added (F5);
   `idx_fused_track_states_fused_track_id` removed as redundant (F3);
   `idx_fused_track_states_object_class` added.
3. `radar_detections`: `azimuth`→`azimuth_rad`, `elevation`→`elevation_rad`
   renamed with empirical unit basis stated; CONFIRMED-empty annotations
   added to `range`, `range_rate`, `snr`, `filter_type`,
   `estimated_width_meters`, `is_marked` (F4).
4. `cv_tracks`, `fused_tracks`: explicit two-phase loading-order note
   added (F2); natural-key uniqueness caveat strengthened (F8).
5. `docs/architecture/DATABASE_DESIGN.md` Section 9: query #2 ("duration by class")
   rewritten to state the resolution problem honestly and point to the
   new classification-semantics comparison (F6, Section 4 above).
6. `docs/architecture/DATABASE_DESIGN.md`: new "ETL loading order" subsection with the
   concrete two-phase strategy (F2/Section 3 above); new sentence
   confirming 64-bit nanosecond timestamp safety (F7).
7. `docs/architecture/NORMALIZATION_DECISIONS.md`: `class_distribution` and
   `object_class_confidence` entries added to the structure inventory,
   reflecting the now-checked (not assumed) decision to add one derived
   scalar and continue omitting the full repeated array.
8. `docs/architecture/TABLE_GRAIN.md`, `docs/architecture/ERD.md`: updated to reflect the two new
   columns and the renamed radar columns; no grain, PK, or FK statement
   changes (none were needed).

No table was added, removed, merged, or split. No primary key, foreign
key, or UNIQUE constraint was reversed. No analytical answer was forced
toward the assignment's expected checks.
