-- =========================================================================
-- Class-distribution completeness and ordering check
--
-- Audience: Data Engineer
-- Question: Does every cv_track_states row have exactly the 4 class-
--           distribution entries the source protobuf always carries,
--           with a contiguous, gap-free, duplicate-free source_order
--           (0..3)?
-- Decision supported: Whether the Stage 6B source-fidelity correction's
--                      child table (cv_track_class_distribution) can be
--                      trusted to have preserved every repeated
--                      protobuf entry in its original order, before it
--                      is used by queries/operational/cv_track_history.sql.
-- Why it matters: this is the grain guarantee the child table's own
-- design depends on (docs/SOURCE_FIDELITY_CORRECTION.md) -- if it ever
-- fails, every query joining against this table needs to be revisited.
--
-- Tables involved: cv_track_class_distribution
-- Join path: single table (self-aggregation, checking each parent
--            cv_track_state_id's own child-row group).
-- SQL technique: GROUP BY + multi-condition WHERE on the aggregated
--                counts
-- Grain: one row per cv_track_state_id that FAILS the check --
--        HEALTHY RESULT IS ZERO ROWS (all 9,496 parent states pass).
--
-- Assumptions/limitations: "exactly 4" is an observed, CONFIRMED
-- full-dataset fact about this specific recording (every
-- CVTrack.class_distribution[] in this file has exactly 4 entries), not
-- a protobuf-enforced guarantee -- a different recording could
-- legitimately have a different count per state, in which case this
-- query's row_count != 4 branch would need revisiting, not just its
-- comparison value.
-- =========================================================================

WITH per_state AS (
    SELECT
        cv_track_state_id,
        COUNT(*) AS row_count,
        MIN(source_order) AS min_order,
        MAX(source_order) AS max_order,
        COUNT(DISTINCT source_order) AS distinct_order_count
    FROM cv_track_class_distribution
    GROUP BY cv_track_state_id
)
SELECT
    cv_track_state_id,
    row_count,
    min_order,
    max_order,
    distinct_order_count
FROM per_state
WHERE row_count != 4
   OR min_order != 0
   OR max_order != 3
   OR distinct_order_count != 4;
