-- =========================================================================
-- Multi-sensor fusion coverage vs. track persistence
--
-- Audience: Executive / Program Leadership
-- Question: Do fused tracks confirmed by more than one sensor modality
--           persist longer than tracks seen by only one sensor?
-- Decision supported: Whether investment in multi-sensor fusion
--                      coverage (e.g. ensuring radar and camera fields
--                      of view overlap) measurably improves tracking
--                      outcomes -- directly informs sensor placement
--                      and coverage-overlap investment decisions.
-- Why it matters: this is a genuine cause-and-effect question (sensor
-- diversity -> track persistence) that cannot be answered from any
-- single table -- it requires knowing, per track, both how many
-- distinct sensors ever fed it AND how long it lasted.
--
-- Tables involved: fused_track_measurements, fused_track_states,
--                   v_fused_track_summary (view)
-- Join path: fused_track_measurements -> fused_track_states (to learn
--            which fused_track_id each measurement belongs to and how
--            many distinct sensor_id_name values that track ever saw)
--            -> v_fused_track_summary (to attach that track's overall
--            duration_seconds). Three logically distinct facts --
--            per-measurement sensor identity, per-track sensor
--            diversity, and per-track duration -- combined into one
--            answer.
-- SQL technique: CTE (per-track sensor diversity) + INNER JOIN to an
--                existing view, then GROUP BY on a derived category
-- Grain: one row per sensor-diversity group ("multi-sensor" vs.
--        "single-sensor").
--
-- Assumptions/limitations: "multi-sensor" here means at least 2
-- distinct sensor_id_name values across the track's entire lifetime,
-- not necessarily concurrent coverage at any single instant -- see
-- queries/operational/fused_track_history.sql for a specific track's
-- exact per-state sensor timeline if simultaneity matters for a given
-- track. This descriptive comparison does not control for other
-- confounding factors (object type, range, etc.).
-- =========================================================================

WITH sensor_diversity AS (
    SELECT
        fts.fused_track_id,
        COUNT(DISTINCT ftm.sensor_id_name) AS distinct_sensor_types
    FROM fused_track_measurements ftm
    JOIN fused_track_states fts ON fts.fused_track_state_id = ftm.fused_track_state_id
    GROUP BY fts.fused_track_id
)
SELECT
    CASE WHEN sd.distinct_sensor_types > 1 THEN 'multi-sensor' ELSE 'single-sensor' END AS sensor_diversity_group,
    COUNT(*) AS track_count,
    ROUND(AVG(v.duration_seconds), 2) AS avg_duration_seconds,
    ROUND(MIN(v.duration_seconds), 2) AS min_duration_seconds,
    ROUND(MAX(v.duration_seconds), 2) AS max_duration_seconds
FROM sensor_diversity sd
JOIN v_fused_track_summary v ON v.fused_track_id = sd.fused_track_id
GROUP BY sensor_diversity_group
ORDER BY sensor_diversity_group;
