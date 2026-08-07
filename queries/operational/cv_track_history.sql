-- =========================================================================
-- CV track history with classification confidence
--
-- Audience: Mission Operations Analyst
-- Question: What is the complete state-by-state history of one
--           specific CV track, including which object class the
--           tracker's own candidate-classification model considered
--           most likely at each restatement?
-- Decision supported: Whether a specific track's classification was
--                      stable and confident throughout its life, or
--                      wavered -- directly informs how much an analyst
--                      should trust that track's final label when
--                      making an identification call.
-- Why it matters: cv_track_states.object_class_name alone shows what
-- the tracker *selected*; joining in cv_track_class_distribution shows
-- *how confident* that selection was and what the alternative
-- candidates were at that instant -- a selection can look identical
-- across two states while the underlying confidence differs sharply.
--
-- Tables involved: cv_track_states, cv_track_class_distribution
-- Join path: cv_track_states -> cv_track_class_distribution (one state
--            has exactly 4 class-distribution entries; this query picks
--            the highest-probability one per state via a window
--            function, rather than requiring the caller to know that
--            grain detail). This join is only possible because the
--            source-fidelity correction (docs/SOURCE_FIDELITY_
--            CORRECTION.md) preserved the full repeated
--            class_distribution[] structure in its own child table
--            instead of collapsing it to one selected value.
-- SQL technique: CTE + window function (ROW_NUMBER, to pick the
--                top-probability class per state) + LEFT JOIN
-- Grain: one row per state restatement of the given track, in time
--        order.
--
-- PARAMETERIZED QUERY -- requires :track_id (an integer from
-- cv_tracks.track_id; see `SELECT track_id FROM cv_tracks;` for real
-- values in this file). Run via:
--   python scripts/run_analytics.py --query cv_track_history --param track_id=81754
--
-- Assumptions/limitations: log_time_ns is the row's own timestamp
-- (confirmed nanoseconds); last_associated_detection_id is raw
-- provenance, not FK-enforced (docs/SCHEMA_REVIEW.md finding F1) -- a
-- handful of historical values may reference a detection_id that no
-- longer resolves in cv_detections (4 known cases file-wide, logged in
-- data_quality_issues). Ties in top-probability class are broken by
-- source_order (the original protobuf repeated-field position).
-- =========================================================================

WITH top_class_per_state AS (
    SELECT
        cv_track_state_id,
        class_name AS top_predicted_class,
        probability_score AS top_predicted_class_probability,
        ROW_NUMBER() OVER (
            PARTITION BY cv_track_state_id
            ORDER BY probability_score DESC, source_order ASC
        ) AS rnk
    FROM cv_track_class_distribution
)
SELECT
    cts.cv_track_state_id,
    cts.log_time_ns,
    cts.track_age,
    cts.status_name,
    cts.status_code_name,
    cts.object_class_name AS selected_object_class,
    tc.top_predicted_class,
    tc.top_predicted_class_probability,
    cts.last_associated_detection_id,
    cts.num_detection_associations,
    cts.score
FROM cv_track_states cts
LEFT JOIN top_class_per_state tc ON tc.cv_track_state_id = cts.cv_track_state_id AND tc.rnk = 1
WHERE cts.track_id = :track_id
ORDER BY cts.log_time_ns;
