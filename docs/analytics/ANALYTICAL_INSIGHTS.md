# Analytical Insights — Stage 7 (+ Stage 7B gap-fill)

Stage 7B added 3 further queries after a deliberate gap review of the
Stage 7 library (`cv_detection_quality_vs_track_persistence.sql`,
`fused_track_duration_by_sensor_combination.sql`,
`fused_track_classification_stability_vs_measurement_support.sql`) —
see the end of the Executive and Operational sections below and the
updated Key Findings. No Stage 7 query was redesigned, renamed, or
replaced.

This document is the readable companion to `queries/`. For every
analytical query it records the business question, who asks it, what
decision it supports, the exact tables and join path involved, the
observed result against the current build of `data/output/sentry.db`,
a plain-English interpretation, and the assumptions/limitations that
apply. Run any query yourself with `python scripts/run_analytics.py
--query <name>` — see `docs/analytics/SQL_QUERY_GUIDE.md` for the full usage
guide.

**A note on why the join paths below stop where they do:** this
project's Stage 3 investigation (`docs/data/KEY_ANALYSIS.md`) directly
tested whether CV-track identity (`cv_tracks.track_id`, `uint64`) and
fused-track identity (`fused_tracks.fused_track_id`, `TEXT`) are the
same underlying real-world objects, and found **zero observed value
overlap** and incompatible protobuf types. That finding was reconfirmed
at every later stage (`docs/architecture/DATABASE_DESIGN.md` Section 6:
"Relationships explicitly NOT enforced"). Every query below that
traverses the CV side (`cv_detections → cv_detection_track_links →
cv_tracks → cv_track_states → cv_track_class_distribution`) or the
fused side (`fused_tracks → fused_track_states →
fused_track_measurements`) does so through real, FK-enforced
relationships. None of them cross from one side to the other — not
because that would be technically difficult, but because doing so
would assert a relationship this project's own evidence explicitly
rejected. Where a query needs to present both systems together (see
`longest_lived_tracks.sql`), it does so with an explicit `UNION ALL`
and a `track_type` label, never a join.

---

## Key Findings

1. **CV detection incorporation is 97.54%, not the assignment's ~81%
   target** — and this is not a bug. `docs/analytics/CHECKSUM_RESOLUTION.md`
   (consolidating three independent investigation rounds) tested every
   status-code, counter-delta, eligibility, and time-alignment
   interpretation available in the source data; all converge on the
   same figure. Anduril reviewed this finding and confirmed the
   interpretation is correct.

2. **The Drone/Airplane duration question is answered by *which
   sensor* contributed to a track, not by any object-classification
   field.** `proto.tower.TrackObjectClass` has no DRONE or AIRPLANE
   value at all (confirmed by protobuf descriptor enumeration).
   Classifying by transponder involvement instead gives Airplane a
   mean duration of 614.68s (target ~600s) and Drone a mean of 35.86s
   (target ~30s, honestly reported as +19.5% — the median, 30.26s, is
   closer but is not substituted for the mean).

3. **Multi-sensor tracks are, on average, *shorter-lived* than
   single-sensor tracks (69.92s vs. 255.75s)** — the opposite of the
   naive "more corroboration means more persistence" hypothesis. This
   is confounded by sensor type, not sensor count: the 9 multi-sensor
   tracks are exactly the camera+radar-visible tracks (short-range,
   brief engagements), while the 94 single-sensor tracks include both
   very brief radar-only blips and the very long transponder-only
   airplane tracks. See
   `queries/executive/multi_sensor_tracks_duration_comparison.sql`,
   confirmed and resolved to the exact-combination level by Stage 7B's
   `fused_track_duration_by_sensor_combination.sql` (finding #9 below)
   — **this file contains exactly 3 sensor combinations, never
   camera+transponder or radar+transponder**, so the "multi-sensor"
   bucket in this recording is entirely camera+radar, not a general
   multi-sensor effect.

4. **Image focus quality correlates strongly with CV incorporation
   rate**, from 99.89% (SHARP) down to 22.22% (BLURRY) — but this
   correlation was already tested and explicitly rejected as an
   explanation for the ~81% checksum gap (excluding blurry detections
   moves the overall rate *further* from 81%, not closer). It remains
   a genuine, useful operational/sensor-engineering finding on its own.

5. **18 of 103 persistent fused tracks change classification during
   their own lifetime** (exact match to `docs/architecture/SCHEMA_REVIEW.md` finding
   F6) — any downstream consumer that reports "the" class of a fused
   track needs to pick one of five documented resolution rules first;
   this project deliberately does not choose one.

6. **Every message in this recording has zero publish/log-time
   latency** (`max_publish_log_latency_ns = 0` across all 57,266
   messages) — either the recording tool set both fields identically,
   or this pipeline stage introduces no measurable delay. Either way,
   it means `publish_time_ns` and `log_time_ns` are interchangeable in
   this specific file, though that should not be assumed for a
   different recording.

7. **The Stage 6B source-fidelity correction is directly responsible
   for at least 3 of this stage's queries** (`cv_track_history.sql`'s
   classification-confidence join, `cv_focus_quality_vs_incorporation.sql`,
   and the underlying data behind `class_distribution_completeness_and_ordering.sql`)
   — none of these questions were answerable from the database before
   that correction added `cv_track_class_distribution` and the CV
   detection quality columns.

8. **Zero relational-integrity violations found anywhere.** Every
   technical query in this stage — row-count reconciliation, duplicate
   check, enum consistency (16 column pairs), class-distribution
   completeness (9,496 parent states), and source-message-to-child
   reconciliation (4 tables) — returns a clean result. The Stage 6/6B
   database is structurally sound.

9. **(Stage 7B) There are exactly 3 sensor combinations in this file, and
   they cleanly separate into 3 distinct populations**, not a smooth
   multi-vs-single gradient: `TOWER_SENSOR_TRANSPONDER` alone (n=36, mean
   614.68s), `TOWER_SENSOR_CAMERA+TOWER_SENSOR_RADAR` (n=9, mean 69.92s),
   and `TOWER_SENSOR_RADAR` alone (n=58, mean 32.96s). See
   `queries/executive/fused_track_duration_by_sensor_combination.sql`.

10. **(Stage 7B) CV detection quality shows a visible, if imperfect,
    relationship with track duration.** The two shortest CV tracks
    (`82403`, 5.87s; `82990`, 4.5s) also have the two lowest average
    detection scores (0.467, 0.456) and 0% sharp-or-better focus
    detections — while the four longest tracks all have ≥92%
    sharp-or-better focus. The relationship isn't perfectly monotonic
    (track `82808`, 31.53s, has only 41.1% sharp detections yet
    persisted longer than several higher-quality tracks), so this is
    reported as a visible pattern at the extremes, not a strict rule.
    See `queries/operational/cv_detection_quality_vs_track_persistence.sql`.

11. **(Stage 7B) Classification-unstable fused tracks are not
    under-measured relative to their own (shorter) lifetimes — if
    anything they see slightly *more* sensor diversity.** The 18
    classification-unstable tracks average 78.5 measurements and 1.22
    distinct sensor types over 53.47s, versus 124.5 measurements and
    1.06 sensor types over 278.91s for the 85 stable tracks. Raw
    measurement count is lower for unstable tracks, but that's
    substantially explained by their much shorter duration, not sparser
    per-track sensor coverage — the naive "instability = poor sensor
    support" hypothesis is not supported by this data. See
    `queries/operational/fused_track_classification_stability_vs_measurement_support.sql`.

---

## Executive Findings

### `queries/executive/recording_overview.sql`

1. **Business question:** What does this recording cover, end to end?
2. **Audience:** Executive / Program Leadership
3. **Operational decision supported:** Whether the recording's scope
   and pipeline timing are sufficient to trust downstream analytics.
4. **Why it matters:** every other query implicitly assumes this
   recording is complete and its clocks are trustworthy — this checks
   that assumption directly.
5. **Tables involved:** `source_messages`
6. **Join path:** single table
7. **Returned grain:** one row
8. **SQL techniques used:** aggregation (MIN/MAX/COUNT)
9. **Observed result:** 57,266 messages, 4 topics, 1,199.97-second span
   (2026-08-06 recording), 0ns max publish/log latency.
10. **Plain-English interpretation:** the recording is a continuous,
    ~20-minute capture across all four expected sensor topics, with no
    measurable publish-pipeline delay.
11. **Assumptions/limitations:** relies on `log_time_ns`/`publish_time_ns`
    being genuinely nanoseconds (confirmed, CLAUDE.md rule 5).
12. **Why the normalized schema helps:** `source_messages` is the one
    table every other table traces back to — this query would be
    identical in a denormalized design, which is exactly why it's
    intentionally simple here.

### `queries/executive/cv_incorporation_summary.sql`

1. **Business question:** What percentage of CV detections were
   incorporated into a persistent CV track?
2. **Audience:** Executive / Program Leadership
3. **Operational decision supported:** Whether the CV pipeline's
   headline effectiveness metric should be reported as-is.
4. **Why it matters:** one of the two checksum questions this project
   was explicitly asked to answer.
5. **Tables involved:** `cv_detections`, `cv_detection_track_links`
6. **Join path:** `cv_detections → cv_detection_track_links`
7. **Returned grain:** one row
8. **SQL techniques used:** correlated scalar subqueries
9. **Observed result:** 1,864 / 1,911 = **97.54%**
10. **Plain-English interpretation:** almost every detection the camera
    system produced ended up linked to a persistent track — a high
    yield, though not matching the assignment's stated ~81% target.
11. **Assumptions/limitations:** this figure is fixed and protected —
    see `docs/analytics/CHECKSUM_RESOLUTION.md` for the full investigation and
    Anduril's confirmation that no further work is needed here.
12. **Why the normalized schema helps:** without `cv_detection_track_links`
    as its own deduplicated bridge table, this percentage would require
    re-deriving the deduplication logic inline in every query that
    needs it, risking a different (and silently wrong) answer each time.

### `queries/executive/cv_detection_to_track_funnel.sql`

1. **Business question:** Of everything the camera detected, how much
   became a persistent tracked object, and how concentrated is that
   outcome?
2. **Audience:** Executive / Program Leadership
3. **Operational decision supported:** Whether camera coverage should
   be expanded, tuned, or left as-is.
4. **Why it matters:** a single percentage hides *how* it's
   distributed — this shows the same detections narrowing through each
   stage of the CV pipeline's own grain.
5. **Tables involved:** `cv_detections`, `cv_detection_track_links`, `cv_tracks`
6. **Join path:** `cv_detections → cv_detection_track_links → cv_tracks`
7. **Returned grain:** one row
8. **SQL techniques used:** correlated scalar subqueries at three grains
9. **Observed result:** 1,911 total detections → 1,864 incorporated →
   17 tracks receiving detections → 17 total persistent tracks →
   **109.6 incorporated detections per track on average**.
10. **Plain-English interpretation:** all 17 persistent CV tracks
    received detections (none is an empty "ghost" identity), and each
    track was re-confirmed by over 100 detections on average — a small
    number of persistent, heavily-observed objects, not many
    fleeting ones.
11. **Assumptions/limitations:** the average is only meaningful because
    every one of the 17 tracks did receive at least one detection
    (CONFIRMED, Stage 3) — the two denominators (17 and 17) happen to
    coincide in this file.
12. **Why the normalized schema helps:** this three-stage funnel is a
    single, cheap query specifically because `cv_detections`,
    `cv_detection_track_links`, and `cv_tracks` are three separate
    tables at three separate, well-defined grains — a denormalized
    table would have already picked one grain and lost the other two.

### `queries/executive/sensor_utilization_summary.sql`

1. **Business question:** Which sensor modalities contributed how much
   measurement volume, and to how many distinct tracked objects?
2. **Audience:** Executive / Program Leadership
3. **Operational decision supported:** Sensor investment/maintenance
   prioritization.
4. **Why it matters:** this is the same field the Drone/Airplane
   checksum classification is built on.
5. **Tables involved:** `fused_track_measurements`, `fused_track_states`
6. **Join path:** `fused_track_measurements → fused_track_states`
7. **Returned grain:** one row per sensor type
8. **SQL techniques used:** INNER JOIN + GROUP BY + COUNT(DISTINCT ...)
9. **Observed result:**

    | sensor | measurements | % of total | distinct tracks |
    |---|---|---|---|
    | TOWER_SENSOR_TRANSPONDER | 7,653 | 63.82% | 36 |
    | TOWER_SENSOR_RADAR | 2,735 | 22.81% | 67 |
    | TOWER_SENSOR_CAMERA | 1,604 | 13.38% | 9 |

10. **Plain-English interpretation:** transponder contacts dominate
    measurement *volume* (each transponder-tracked object generates
    many measurements over its long lifetime) but touch the fewest
    distinct tracks; radar covers the most distinct objects; camera
    covers the fewest objects and the least volume — consistent with
    camera being a short-range, close-confirmation sensor.
11. **Assumptions/limitations:** "contributed to N distinct tracks"
    counts a track once regardless of measurement count.
12. **Why the normalized schema helps:** `fused_track_measurements`
    exists at exactly the right grain (one row per measurement) to
    answer both "how much volume" and "how many distinct tracks" from
    the same table without duplicating track-level data once per
    measurement.

### `queries/executive/multi_sensor_tracks_duration_comparison.sql`

1. **Business question:** Do fused tracks confirmed by more than one
   sensor persist longer than single-sensor tracks?
2. **Audience:** Executive / Program Leadership
3. **Operational decision supported:** Whether investment in
   multi-sensor coverage overlap measurably improves tracking outcomes.
4. **Why it matters:** a genuine cause-and-effect question that
   requires combining per-track sensor diversity with per-track duration.
5. **Tables involved:** `fused_track_measurements`, `fused_track_states`, `v_fused_track_summary`
6. **Join path:** `fused_track_measurements → fused_track_states → v_fused_track_summary`
7. **Returned grain:** one row per sensor-diversity group
8. **SQL techniques used:** CTE + INNER JOIN to an existing view + GROUP BY
9. **Observed result:** multi-sensor: n=9, mean 69.92s (range 42.06–97.37s);
   single-sensor: n=94, mean 255.75s (range 0.0–1118.78s).
10. **Plain-English interpretation:** **the naive hypothesis is wrong**
    — multi-sensor tracks are shorter, not longer, on average. This is
    explained by Key Finding #3: the multi-sensor group is exactly the
    camera-visible (short-range) tracks, while the single-sensor group
    is a wide mix of very brief radar blips *and* the longest-lived
    transponder tracks in the whole file.
11. **Assumptions/limitations:** "multi-sensor" means ≥2 distinct
    sensors across the track's *entire* lifetime, not necessarily
    concurrent coverage; this comparison does not control for object
    type or range.
12. **Why the normalized schema helps:** this cause-effect question is
    a 3-table join precisely because sensor identity, track identity,
    and track duration are three separate facts at three separate
    grains in this schema — exactly the design this stage exists to
    demonstrate the value of.

### `queries/executive/fused_track_duration_by_sensor_combination.sql` (Stage 7B)

1. **Business question:** Which exact combinations of contributing
   sensors are associated with the longest-lived fused tracks?
2. **Audience:** Executive / Program Leadership
3. **Operational decision supported:** Sensor-pairing/coverage-overlap
   investment — whether one specific combination systematically out- or
   under-performs is more actionable than a single binary conclusion.
4. **Why it matters:** resolves `multi_sensor_tracks_duration_comparison.sql`'s
   binary multi-/single-sensor split to the exact combination level, to
   check whether that finding holds uniformly or is driven by one pairing.
5. **Tables involved:** `fused_track_measurements`, `fused_track_states`, `v_fused_track_summary`
6. **Join path:** `fused_track_measurements → fused_track_states → v_fused_track_summary`
7. **Returned grain:** one row per distinct sensor combination
8. **SQL techniques used:** CTE with an explicit pre-sort before
   `GROUP_CONCAT` (SQLite has no native `ORDER BY` inside that
   aggregate) + INNER JOIN to an existing view
9. **Observed result:**

    | combination | tracks | avg duration | min | max |
    |---|---|---|---|---|
    | TOWER_SENSOR_TRANSPONDER | 36 | 614.68s | 35.82s | 1118.78s |
    | TOWER_SENSOR_CAMERA+TOWER_SENSOR_RADAR | 9 | 69.92s | 42.06s | 97.37s |
    | TOWER_SENSOR_RADAR | 58 | 32.96s | 0.0s | 169.75s |

10. **Plain-English interpretation:** only 3 combinations exist in this
    recording — no track was ever seen by camera+transponder or
    radar+transponder. This resolves Key Finding #3's "surprising"
    result: it isn't that more sensors hurts persistence in general, it's
    that the *only* multi-sensor population here (camera+radar) happens
    to be short-range engagements, while the *only* long-duration
    population (transponder-only) never overlaps with camera coverage
    at all in this file.
11. **Assumptions/limitations:** a track's combination reflects its
    entire lifetime, not concurrent coverage at one instant. Labels are
    alphabetically sorted so the same combination always produces the
    same string regardless of which sensor contributed first.
12. **Why the normalized schema helps:** no single table records "the
    full set of sensors a track ever saw" — this fact only exists by
    aggregating `fused_track_measurements` per track, then joining to
    duration, which is derived from a separate table entirely.

### `queries/executive/data_quality_issue_summary.sql`

1. **Business question:** How many data-quality findings did the ETL
   pipeline generate, and how severe?
2. **Audience:** Executive / Program Leadership
3. **Operational decision supported:** Whether the database can be
   trusted for downstream reporting as-is.
4. **Why it matters:** the pipeline's own explicit statement of what it
   found and chose not to silently discard.
5. **Tables involved:** `data_quality_issues`
6. **Join path:** single table (deliberately — this table has no FKs by
   design, docs/architecture/DATABASE_DESIGN.md Section 5.10)
7. **Returned grain:** one row per (issue_type, severity)
8. **SQL techniques used:** GROUP BY + COUNT
9. **Observed result:** `orphaned_detection_reference` / `warning` — 4
   rows.
10. **Plain-English interpretation:** the only data-quality finding in
    this entire recording is the 4 known orphaned detection references
    (a `last_associated_detection_id` pointing at a `detection_id` that
    doesn't exist) — already excluded from `cv_detection_track_links`
    and logged here instead of silently dropped.
11. **Assumptions/limitations:** this table only grows as new cleaning
    rules are implemented — not a complete inventory of every possible
    concern (see `docs/data/DATA_CLEANING.md`).
12. **Why the normalized schema helps:** a single audit-log table lets
    every cleaning rule across every other table report findings in one
    place, instead of each table needing its own ad hoc "issues" column.

---

## Operational Findings

### `queries/operational/cv_track_history.sql` (parameterized: `:track_id`)

1. **Business question:** What is the complete state-by-state history
   of one specific CV track, including which class the tracker's own
   candidate-classification model considered most likely at each
   restatement?
2. **Audience:** Mission Operations Analyst
3. **Operational decision supported:** Whether a specific track's
   classification was stable and confident throughout its life.
4. **Why it matters:** the *selected* class alone hides *how confident*
   that selection was — a selection can look identical across two
   states while the underlying confidence differs sharply.
5. **Tables involved:** `cv_track_states`, `cv_track_class_distribution`
6. **Join path:** `cv_track_states → cv_track_class_distribution`
7. **Returned grain:** one row per state restatement, time-ordered
8. **SQL techniques used:** CTE + window function (ROW_NUMBER) + LEFT JOIN
9. **Observed result (track_id=81754):** first state (log_time
   1761244500011495000): `status=ACTIVE`, `selected_object_class=AIR_VEHICLE`,
   `top_predicted_class=AIR_VEHICLE` at 0.928 probability — 1,207
   total states for this track (its longest CV track in the file).
10. **Plain-English interpretation:** this track's tracker-selected
    class and its own top-probability candidate agree from the very
    first state, at high confidence (~93%) — a clean, unambiguous
    classification throughout.
11. **Assumptions/limitations:** `last_associated_detection_id` is raw
    provenance, not FK-enforced — 4 historical values file-wide
    reference a `detection_id` that no longer resolves (logged in
    `data_quality_issues`). Probability ties are broken by
    `source_order`.
12. **Why the normalized schema helps:** this join is only possible
    because Stage 6B preserved the full repeated `class_distribution[]`
    structure in its own child table instead of collapsing it to one
    selected value — a denormalized table could not have offered this
    without either 4x row duplication per state or discarding the
    other 3 candidates entirely.

### `queries/operational/fused_track_history.sql` (parameterized: `:fused_track_id`)

1. **Business question:** What is the complete state-by-state history
   of one specific fused track, including which sensors contributed to
   each individual state?
2. **Audience:** Mission Operations Analyst
3. **Operational decision supported:** Whether a specific track's
   position/classification at a given moment should be trusted at high
   confidence or treated cautiously.
4. **Why it matters:** shows *why* the fusion system reached each
   conclusion, not just *what* it concluded.
5. **Tables involved:** `fused_track_states`, `fused_track_measurements`
6. **Join path:** `fused_track_states → fused_track_measurements`
7. **Returned grain:** one row per state update, time-ordered
8. **SQL techniques used:** LEFT JOIN + GROUP BY + GROUP_CONCAT(DISTINCT ...)
9. **Observed result (fused_track_id=25295F49158-7aa000016009):** first
   state (log_time 1761244501902726000): `object_class=AIR_VEHICLE`,
   `disposition=ASSUMED_FRIENDLY`, `track_status=MATURE`,
   `contributing_sensors=TOWER_SENSOR_TRANSPONDER`, 1 measurement.
10. **Plain-English interpretation:** this track was fed exclusively by
    the transponder sensor from its very first recorded state, already
    at MATURE status — consistent with a cooperative, easily-confirmed
    contact.
11. **Assumptions/limitations:** `object_class_name` cannot show
    Drone/Airplane (see `docs/analytics/CHECKSUM_RESOLUTION.md`) — use
    `contributing_sensors` for that inference instead. A LEFT JOIN is
    used deliberately so a state with zero measurements is a visible
    fact, not a silently dropped row.
12. **Why the normalized schema helps:** `fused_track_measurements`
    being its own table at its own grain is exactly what makes "which
    sensor, at which specific instant" answerable — collapsing
    measurements into the state row would force picking one sensor per
    state and losing the others.

### `queries/operational/sensor_contributions_per_fused_track.sql`

1. **Business question:** For each fused track, which sensors
   contributed, how many measurements each, and how many distinct
   modalities were involved?
2. **Audience:** Mission Operations Analyst
3. **Operational decision supported:** Identifying which specific
   tracks have multi-sensor corroboration versus single-sensor-only.
4. **Why it matters:** the track-level detail behind the executive
   aggregate in `multi_sensor_tracks_duration_comparison.sql`.
5. **Tables involved:** `fused_track_measurements`, `fused_track_states`
6. **Join path:** `fused_track_measurements → fused_track_states`
7. **Returned grain:** one row per (fused_track_id, sensor_id_name) pair
8. **SQL techniques used:** two CTEs (per-track-per-sensor, then
   per-track diversity) + INNER JOIN
9. **Observed result:** 112 rows total; e.g. track
   `25295F49158-7aa000016023`: CAMERA 237 measurements, RADAR 121
   measurements, 2 distinct sensor types.
10. **Plain-English interpretation:** the 9 multi-sensor tracks each
    show exactly 2 rows (camera + radar); the 94 single-sensor tracks
    each show exactly 1 — confirming the 9/94 split used by the
    executive comparison query.
11. **Assumptions/limitations:** "contributed a measurement" does not
    imply simultaneous coverage.
12. **Why the normalized schema helps:** same relationship as
    `sensor_utilization_summary.sql`, applied per-track instead of
    fleet-wide — one join, two different grains of insight.

### `queries/operational/object_class_changes_over_time.sql`

1. **Business question:** Which fused tracks were classified
   differently at different points in their own history?
2. **Audience:** Mission Operations Analyst
3. **Operational decision supported:** Flagging specific tracks whose
   "current" classification should not be treated as settled.
4. **Why it matters:** the direct, queryable answer to
   `docs/architecture/SCHEMA_REVIEW.md` finding F6's aggregate count.
5. **Tables involved:** `fused_track_states`
6. **Join path:** single table, compared against itself over time
7. **Returned grain:** one row per track that changed classification
   at least once
8. **SQL techniques used:** window function (LAG) + pre-sorted CTE +
   GROUP_CONCAT
9. **Observed result:** **exactly 18 rows** — an exact match to
   Schema Review finding F6. Example: track `25295F49158-7aa000016054`
   (17 states): `BIRD → BIRD → BIRD → BIRD → UNKNOWN_AIR_VEHICLE → ...`
10. **Plain-English interpretation:** these 18 tracks are the ones an
    analyst must not trust a single "final" classification for without
    reviewing the sequence — most transitions are between
    `UNKNOWN_AIR_VEHICLE` and a more specific class as the fusion
    system gathers more evidence, not random flip-flopping.
11. **Assumptions/limitations:** reports the raw sequence — does not
    resolve "the" correct class (5 documented resolution semantics
    exist, none selected, per Schema Review Section 4).
12. **Why the normalized schema helps:** `fused_track_states` being an
    append-only history table (not overwritten in place) is exactly
    what makes this self-comparison possible at all — a design that
    stored only the "current" class per track could never answer this
    question.

### `queries/operational/cv_focus_quality_vs_incorporation.sql`

1. **Business question:** Does CV detection image focus quality
   correlate with incorporation into a track?
2. **Audience:** Mission Operations Analyst / Sensor Engineer
3. **Operational decision supported:** Whether investing in better
   camera focus/optics would improve tracking yield.
4. **Why it matters:** a direct cause-effect test using a field only
   available since Stage 6B.
5. **Tables involved:** `cv_detections`, `cv_detection_track_links`
6. **Join path:** `cv_detections → cv_detection_track_links`
7. **Returned grain:** one row per focus-quality value
8. **SQL techniques used:** LEFT JOIN + GROUP BY
9. **Observed result:**

    | focus quality | total | incorporated | rate |
    |---|---|---|---|
    | SHARP | 951 | 950 | 99.89% |
    | MID_SHARP | 682 | 677 | 99.27% |
    | MID | 198 | 191 | 96.46% |
    | MID_BLURRY | 71 | 44 | 61.97% |
    | BLURRY | 9 | 2 | 22.22% |

10. **Plain-English interpretation:** a strong, monotonic correlation —
    blurry detections are far less likely to be tracked. This is a
    genuine sensor-engineering finding, separate from (and already
    ruled out as an explanation for) the CV-incorporation checksum gap.
11. **Assumptions/limitations:** descriptive correlation, not a causal
    claim; already tested and rejected as a checksum eligibility filter.
12. **Why the normalized schema helps:** only possible because Stage 6B
    added `focus_quality_name` to `cv_detections` instead of discarding
    it — this query is a direct demonstration of that correction's value.

### `queries/operational/longest_lived_tracks.sql`

1. **Business question:** Which CV tracks and which fused tracks were
   followed the longest?
2. **Audience:** Mission Operations Analyst
3. **Operational decision supported:** Identifying the highest-value
   candidates for a detailed manual history review.
4. **Why it matters:** pairs both systems' top performers for one
   at-a-glance read.
5. **Tables involved:** `v_cv_track_summary`, `v_fused_track_summary`
6. **Join path:** none — deliberate `UNION ALL`, not a join (see the
   note at the top of this document on why CV and fused sides are never
   joined)
7. **Returned grain:** top 10 from each system (20 rows)
8. **SQL techniques used:** UNION ALL of two ordered/limited subqueries
9. **Observed result:** longest CV track: `83006`, 1,676 states, 57.8s.
   Longest fused track: `25295F49158-7aa000015976`, 521 states, 1,118.78s.
10. **Plain-English interpretation:** the longest-lived fused track
    (1,118.78s ≈ 18.6 minutes) is almost the entire 1,199.97-second
    recording — likely present from near the start to near the end.
11. **Assumptions/limitations:** the two `track_type` groups' duration
    values are not directly comparable (different systems, different
    sensors).
12. **Why the normalized schema helps:** `v_cv_track_summary` and
    `v_fused_track_summary` already encapsulate the "duration per
    persistent track" computation — this query reuses both without
    redefining that logic a third time.

### `queries/operational/cv_detection_quality_vs_track_persistence.sql` (Stage 7B)

1. **Business question:** Do CV tracks fed by higher-quality/higher-
   confidence detections persist longer than tracks fed by lower-quality
   detections?
2. **Audience:** Mission Operations Analyst / Sensor Engineer
3. **Operational decision supported:** Whether better camera focus/optics
   would improve not just *whether* a detection gets incorporated
   (`cv_focus_quality_vs_incorporation.sql` already answers that) but
   *how long the resulting track survives*.
4. **Why it matters:** the deepest cause-and-effect chain the CV side of
   this schema supports, and no existing query connected these three
   facts together.
5. **Tables involved:** `cv_detection_track_links`, `cv_detections`, `v_cv_track_summary`
6. **Join path:** `cv_detection_track_links → cv_detections`, rolled up
   per `track_id`, then `→ v_cv_track_summary`
7. **Returned grain:** one row per persistent CV track (all 17)
8. **SQL techniques used:** CTE (per-track aggregation of joined
   detection quality) + INNER JOIN to an existing view
9. **Observed result:** the two shortest tracks (`82403`, 5.87s;
   `82990`, 4.5s) have the lowest average detection scores (0.467,
   0.456) and 0% sharp-or-better focus; the four longest tracks all
   have ≥92% sharp-or-better focus. Not perfectly monotonic — track
   `82808` (31.53s) has only 41.1% sharp detections but still outlasts
   several higher-quality tracks.
10. **Plain-English interpretation:** poor detection quality is visibly
    associated with the shortest-lived tracks at the extremes, but is
    not a strict predictor across the full population — other factors
    clearly also matter.
11. **Assumptions/limitations:** n=17 is small — presented as a direct,
    readable per-track comparison for visual inspection, not a
    statistical-significance claim. Descriptive correlation only; range,
    motion, and recording conditions are not held constant.
12. **Why the normalized schema helps:** `cv_detections` alone has no
    notion of "which track"; `cv_track_states`/`v_cv_track_summary`
    alone has no notion of detection-level quality — `cv_detection_
    track_links` is the only place, as a real deduplicated bridge table,
    these two facts can be joined without over-counting a detection once
    per track restatement that mentions it.

### `queries/operational/fused_track_classification_stability_vs_measurement_support.sql` (Stage 7B)

1. **Business question:** Do fused tracks whose classification changed
   during their lifetime receive less sensor/measurement support than
   tracks whose classification stayed stable?
2. **Audience:** Mission Operations Analyst / Data Engineer
3. **Operational decision supported:** Whether classification
   instability is an engineering symptom fixable by improving sensor
   coverage/dwell time, or an independent phenomenon.
4. **Why it matters:** `object_class_changes_over_time.sql` identifies
   *which* 18 tracks are unstable but reports that fact in isolation —
   this is the cause-and-effect follow-up.
5. **Tables involved:** `fused_track_states`, `fused_track_measurements`, `v_fused_track_summary`
6. **Join path:** `fused_track_states` compared against itself over time
   (LAG, to flag stable/unstable) + `fused_track_measurements →
   fused_track_states` rolled up per track (measurement/sensor count) +
   `→ v_fused_track_summary` (duration)
7. **Returned grain:** one row per stability group ("stable"/"unstable")
8. **SQL techniques used:** window function (LAG) + CTE for per-track
   aggregation + LEFT JOIN (to default every track to "stable" unless
   found unstable) + INNER JOIN to an existing view
9. **Observed result:**

    | group | tracks | avg measurements | avg distinct sensors | avg duration |
    |---|---|---|---|---|
    | stable | 85 | 124.5 | 1.06 | 278.91s |
    | unstable | 18 | 78.5 | 1.22 | 53.47s |

10. **Plain-English interpretation:** unstable tracks are not
    under-measured in a per-track-lifetime sense — they in fact average
    slightly *more* distinct sensor types (1.22 vs. 1.06). Their lower
    raw measurement count is substantially explained by their much
    shorter duration (53s vs. 279s), not by sparser sensor coverage.
    **The naive "instability = poor sensor support" hypothesis is not
    supported by this data.**
11. **Assumptions/limitations:** n=18 vs. n=85 — observed group averages,
    not significance-tested. "Measurement support" here is a lifetime
    total, confounded by duration — read alongside `avg_duration_seconds`
    in the same row, not in isolation.
12. **Why the normalized schema helps:** classification stability
    (`fused_track_states`), measurement support (`fused_track_
    measurements`), and duration (derived from `fused_track_states` via
    an existing view) are three facts that live in genuinely separate
    tables/derivations — this question only becomes answerable once all
    three are combined per track.

---

## Technical / Data-Quality Findings

### `queries/technical/table_row_count_reconciliation.sql`

1. **Business question:** Do all table row counts match the documented
   grain?
2. **Audience:** Data Engineer
3. **Operational decision supported:** Whether the loaded database can
   be trusted as a complete load before running any analysis.
4. **Why it matters:** the fastest way to catch a partial/corrupted load.
5. **Tables involved:** all 11 reviewed tables
6. **Join path:** none (independent counts, unioned)
7. **Returned grain:** one row per table
8. **SQL techniques used:** UNION ALL
9. **Observed result:** all 11 tables present with their documented
   counts (57,266 / 1,911 / 17 / 9,496 / 37,984 / 1,864 / 2,929 / 103 /
   11,630 / 11,992 / 4).
10. **Plain-English interpretation:** the database is a complete,
    correctly-graded load.
11. **Assumptions/limitations:** reports counts only, does not itself
    assert correctness (that's `validation.py`'s job at build time).
12. **Why the normalized schema helps:** N/A — this is intentionally a
    simple validation query; see Key Findings for why that's
    appropriate here.

### `queries/technical/duplicate_relationship_check.sql`

1. **Business question:** Does the CV bridge table contain any
   duplicate pairing?
2. **Audience:** Data Engineer
3. **Operational decision supported:** Whether
   `cv_incorporation_summary.sql` can be trusted not to double-count.
4. **Why it matters:** a duplicate here would silently inflate every
   incorporation figure.
5. **Tables involved:** `cv_detection_track_links`
6. **Join path:** single table (self-comparison)
7. **Returned grain:** one row per duplicate found — healthy = 0 rows
8. **SQL techniques used:** GROUP BY + HAVING
9. **Observed result:** 0 rows.
10. **Plain-English interpretation:** no duplicates exist.
11. **Assumptions/limitations:** the PK already prevents this at the
    SQL level — this is a from-scratch, defense-in-depth recheck.
12. **Why the normalized schema helps:** N/A — validation query.

### `queries/technical/class_distribution_completeness_and_ordering.sql`

1. **Business question:** Does every `cv_track_states` row have exactly
   4 well-ordered class-distribution entries?
2. **Audience:** Data Engineer
3. **Operational decision supported:** Whether the Stage 6B child table
   can be trusted before `cv_track_history.sql` joins against it.
4. **Why it matters:** the grain guarantee the child table's design
   depends on.
5. **Tables involved:** `cv_track_class_distribution`
6. **Join path:** single table (self-aggregation)
7. **Returned grain:** one row per failing parent state — healthy = 0 rows
8. **SQL techniques used:** GROUP BY + multi-condition WHERE
9. **Observed result:** 0 rows (all 9,496 parent states pass).
10. **Plain-English interpretation:** the source-fidelity correction's
    core guarantee holds for every single row.
11. **Assumptions/limitations:** "exactly 4" is an observed fact of
    this file, not a protobuf guarantee.
12. **Why the normalized schema helps:** N/A — validation query.

### `queries/technical/enum_raw_name_consistency.sql`

1. **Business question:** Is any populated raw enum value ever paired
   with a NULL resolved name?
2. **Audience:** Data Engineer
3. **Operational decision supported:** Whether every `*_name` column
   can be trusted before any query groups/filters by it.
4. **Why it matters:** independently verifies the one generic
   enum-resolution mechanism worked everywhere it was used.
5. **Tables involved:** 6 tables, 16 column pairs
6. **Join path:** none (16 independent checks, unioned)
7. **Returned grain:** one row per checked pair, always shown
8. **SQL techniques used:** UNION ALL wrapped in a subquery for ordering
9. **Observed result:** all 16 pairs show `inconsistent_rows = 0`.
10. **Plain-English interpretation:** every enum in the database was
    correctly resolved from its protobuf descriptor.
11. **Assumptions/limitations:** only checks raw-populated/name-NULL,
    not the (impossible-by-construction) inverse.
12. **Why the normalized schema helps:** N/A — validation query.

### `queries/technical/source_message_child_reconciliation.sql`

1. **Business question:** Does every child row's `source_message_id`
   actually resolve to a real `source_messages` row?
2. **Audience:** Data Engineer
3. **Operational decision supported:** Whether the provenance chain
   this entire schema is built around can be trusted, independent of
   whatever FK declarations exist.
4. **Why it matters:** demonstrates why `source_messages` exists as its
   own table at all.
5. **Tables involved:** `source_messages`, `cv_detections`,
   `cv_track_states`, `radar_detections`, `fused_track_states`
6. **Join path:** `source_messages ← {cv_detections, cv_track_states,
   radar_detections, fused_track_states}` (four independent LEFT JOINs)
7. **Returned grain:** one row per checked child table — healthy = 0
8. **SQL techniques used:** LEFT JOIN ... WHERE ... IS NULL (×4), unioned
9. **Observed result:** all 4 tables show `orphaned_rows = 0`.
10. **Plain-English interpretation:** every analytical fact in this
    database traces back to a real raw message — full provenance intact.
11. **Assumptions/limitations:** FKs already enforce this; independent
    recheck. `cv_detection_track_links` and `fused_track_measurements`
    are excluded (no `source_message_id` column of their own).
12. **Why the normalized schema helps:** this cross-table check is
    literally impossible to express meaningfully without
    `source_messages` being its own table — it's the query that most
    directly justifies that design choice.

### `queries/technical/zero_duration_or_single_state_tracks.sql`

1. **Business question:** Which tracks were only ever observed in a
   single state, or have zero duration?
2. **Audience:** Data Engineer / Mission Operations Analyst
3. **Operational decision supported:** Whether these tracks should be
   excluded from average-duration analysis or flagged for review.
4. **Why it matters:** `docs/analytics/CHECKSUM_RESOLUTION.md` explicitly tested
   and rejected excluding these from the Drone/Airplane calculation —
   this makes that decision re-checkable against current data.
5. **Tables involved:** `v_cv_track_summary`, `v_fused_track_summary`
6. **Join path:** none — `UNION ALL`
7. **Returned grain:** one row per qualifying track
8. **SQL techniques used:** UNION ALL with per-branch WHERE
9. **Observed result:** 6 fused tracks (0 CV tracks) — all 6 are
   `OBJECT_CLASS_UNKNOWN_AIR_VEHICLE`-dominant, single-state, 0.0s
   duration.
10. **Plain-English interpretation:** a small number of fused tracks
    (6 of 103) were only ever seen once — plausibly brief,
    low-confidence contacts the fusion system never re-acquired.
11. **Assumptions/limitations:** not automatically an error — could be
    genuine brief sightings or recording-boundary censoring.
12. **Why the normalized schema helps:** N/A — validation-adjacent query.

---

## Future work — additional query ideas not implemented

Per the approved Stage 7 scope (~15–18 queries, quality over quantity)
and Stage 7B's 3-query limit, these ideas were not implemented. They
remain reasonable candidates for a future stage:

- Radar detections ranked by signal strength/range (most radar fields
  in this file are confirmed constant/empty — see `docs/architecture/DATABASE_DESIGN.md`
  Section 5.6 — so this query's value in *this* recording is limited,
  but it would be a natural addition against a recording where those
  fields vary). `radar_detections` remains analytically isolated in
  this library: Stage 3 (`docs/data/KEY_ANALYSIS.md`) confirmed its
  `track_id` field has zero value overlap with every other track-id-
  family field, so no join from `radar_detections` to any track
  identity is possible without asserting a relationship the evidence
  rejects.
- CV track-state density/persistence over time-bucketed windows.
- A dedicated "detections associated multiple times" query — partially
  covered by `cv_detection_to_track_funnel.sql`'s
  `avg_incorporated_detections_per_track`, but not broken out per
  detection.
- Missing-value rate summary across every nullable column (a broader,
  more mechanical version of the enum-consistency check).
- Fused-track duration broken down by dominant object class alone
  (independent of sensor combination) — considered during Stage 7B's
  gap review and deliberately not added: `v_fused_track_type_basis`
  already exposes `dominant_object_class_name` alongside
  `duration_seconds`, so this would be close enough to a single-view
  `GROUP BY` to read as a cosmetic variant of existing coverage rather
  than a genuinely new insight, per the "avoid slight variations of
  existing aggregations" instruction.
