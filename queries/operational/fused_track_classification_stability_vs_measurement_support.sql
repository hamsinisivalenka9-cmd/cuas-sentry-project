-- =========================================================================
-- Fused-track classification stability vs. measurement support
--
-- Audience: Mission Operations Analyst / Data Engineer
-- Question: Do fused tracks whose classification changed during their
--           own lifetime receive less sensor/measurement support
--           (fewer measurements, fewer distinct sensor types) than
--           tracks whose classification stayed stable?
-- Decision supported: Whether classification instability is an
--                      engineering symptom of under-observed tracks
--                      (fixable by improving sensor coverage/dwell
--                      time) or an independent phenomenon -- directly
--                      informs whether more sensor investment would be
--                      expected to reduce classification churn.
-- Why it matters: queries/operational/object_class_changes_over_time.sql
-- already identified exactly which 18 of 103 fused tracks are
-- classification-unstable (an exact match to docs/SCHEMA_REVIEW.md
-- finding F6), but reports that fact in isolation. This query is the
-- cause-and-effect follow-up: does that instability correlate with a
-- measurable, explainable factor, or does it look no different from
-- the stable population?
--
-- Tables involved: fused_track_states, fused_track_measurements,
--                   v_fused_track_summary (view)
-- Join path: fused_track_states compared against itself over time (the
--            same LAG-based technique
--            object_class_changes_over_time.sql uses, to flag each
--            track stable/unstable), then fused_track_measurements ->
--            fused_track_states rolled up per track (the same
--            relationship sensor_contributions_per_fused_track.sql
--            uses, for measurement count and sensor diversity), then
--            joined to v_fused_track_summary for duration -- combining
--            three previously-separate analytical facts (classification
--            history, measurement support, and duration) into one
--            comparison that none of the existing queries make.
-- SQL technique: window function (LAG) for stability detection + CTE
--                for per-track measurement/sensor aggregation + LEFT
--                JOIN (to classify every track as stable by default,
--                unstable only if found in the unstable set) + INNER
--                JOIN to an existing view
-- Grain: one row per stability group ("stable" vs. "unstable").
--
-- Why multiple datasets were required: classification stability is a
-- fact about fused_track_states' own history; measurement support is a
-- fact about fused_track_measurements; duration is a fact
-- v_fused_track_summary already derives from fused_track_states. None
-- of these three facts lives in one table, and the question only makes
-- sense once all three are combined per track.
--
-- Assumptions/limitations: n=18 (unstable) vs. n=85 (stable) --
-- reported as observed group averages, not a significance-tested
-- claim. "Measurement support" here means lifetime totals, not
-- support density (measurements per second) -- a longer-lived track
-- will naturally accumulate more raw measurements even at the same
-- underlying rate, so this comparison should be read alongside
-- avg_duration_seconds in the same row, not in isolation.
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
unstable_tracks AS (
    SELECT DISTINCT fused_track_id
    FROM ordered_states
    WHERE previous_object_class_name IS NOT NULL
      AND object_class_name != previous_object_class_name
),
measurement_support AS (
    SELECT
        fts.fused_track_id,
        COUNT(*) AS measurement_count,
        COUNT(DISTINCT ftm.sensor_id_name) AS distinct_sensor_types
    FROM fused_track_measurements ftm
    JOIN fused_track_states fts ON fts.fused_track_state_id = ftm.fused_track_state_id
    GROUP BY fts.fused_track_id
)
SELECT
    CASE WHEN ut.fused_track_id IS NOT NULL THEN 'unstable' ELSE 'stable' END AS classification_stability,
    COUNT(*) AS track_count,
    ROUND(AVG(ms.measurement_count), 1) AS avg_measurement_count,
    ROUND(AVG(ms.distinct_sensor_types), 2) AS avg_distinct_sensor_types,
    ROUND(AVG(v.duration_seconds), 2) AS avg_duration_seconds
FROM v_fused_track_summary v
JOIN measurement_support ms ON ms.fused_track_id = v.fused_track_id
LEFT JOIN unstable_tracks ut ON ut.fused_track_id = v.fused_track_id
GROUP BY classification_stability
ORDER BY classification_stability;
