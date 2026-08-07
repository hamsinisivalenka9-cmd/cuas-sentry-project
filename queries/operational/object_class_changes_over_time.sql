-- =========================================================================
-- Fused tracks that changed classification over their own lifetime
--
-- Audience: Mission Operations Analyst
-- Question: Which fused tracks were classified differently at
--           different points in their own history, and what did their
--           classification sequence look like?
-- Decision supported: Flagging specific tracks whose "final" or
--                      "current" classification should not be treated
--                      as settled -- an analyst reviewing one of these
--                      tracks should check its full history
--                      (queries/operational/fused_track_history.sql)
--                      before reporting a single class with confidence.
-- Why it matters: docs/SCHEMA_REVIEW.md finding F6 CONFIRMED 18 of 103
-- persistent fused tracks genuinely change object_class within their
-- own state history -- this query is the direct, queryable answer to
-- "which 18," not just the aggregate count.
--
-- Tables involved: fused_track_states
-- Join path: single table, compared against itself over time via a
--            window function (LAG) -- included here as an operational
--            query rather than a technical one because the audience is
--            a mission analyst deciding whether to trust a
--            classification, not an engineer checking pipeline health.
-- SQL technique: window function (LAG, to compare each state's class
--                against the immediately preceding state for the same
--                track) + GROUP_CONCAT to show the full sequence
-- Grain: one row per fused track that changed classification at least
--        once (a strict subset of the 103 persistent fused tracks).
--
-- Assumptions/limitations: this reports the raw sequence of selected
-- object_class_name values in log_time_ns order -- it does not attempt
-- to resolve which classification is "correct" for the track (that
-- remains an explicit, human-decided step per
-- docs/DATABASE_DESIGN.md Section 3 / docs/SCHEMA_REVIEW.md Section 4,
-- which define and compare five possible resolution semantics without
-- selecting one).
-- =========================================================================

WITH ordered_states AS (
    SELECT
        fused_track_id,
        log_time_ns,
        object_class_name,
        LAG(object_class_name) OVER (
            PARTITION BY fused_track_id ORDER BY log_time_ns
        ) AS previous_object_class_name
    FROM fused_track_states
),
changed_tracks AS (
    SELECT DISTINCT fused_track_id
    FROM ordered_states
    WHERE previous_object_class_name IS NOT NULL
      AND object_class_name != previous_object_class_name
),
-- GROUP_CONCAT has no native ORDER BY clause in SQLite -- the
-- documented, reliable workaround is to pre-sort in a subquery with no
-- intervening JOIN, since GROUP BY over an already-ordered scan
-- preserves that order into the aggregate.
sorted_for_concat AS (
    SELECT fused_track_id, object_class_name
    FROM fused_track_states
    WHERE fused_track_id IN (SELECT fused_track_id FROM changed_tracks)
    ORDER BY fused_track_id, log_time_ns
)
SELECT
    fused_track_id,
    COUNT(*) AS state_count,
    COUNT(DISTINCT object_class_name) AS distinct_classes_observed,
    GROUP_CONCAT(object_class_name, ' -> ') AS class_sequence_in_time_order
FROM sorted_for_concat
GROUP BY fused_track_id
ORDER BY distinct_classes_observed DESC, fused_track_id;
