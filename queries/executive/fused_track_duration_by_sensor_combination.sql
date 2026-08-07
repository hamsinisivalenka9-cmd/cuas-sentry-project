-- =========================================================================
-- Fused-track duration by exact sensor combination
--
-- Audience: Executive / Program Leadership
-- Question: Which exact combinations of contributing sensors (not just
--           "multi- vs. single-sensor") are associated with the
--           longest-lived fused tracks?
-- Decision supported: Sensor-pairing/coverage-overlap investment --
--                      if one specific combination (e.g. radar+camera
--                      vs. radar alone) systematically out- or
--                      under-performs, that is a more actionable
--                      finding than a single binary "more sensors is
--                      better/worse" conclusion.
-- Why it matters: queries/executive/multi_sensor_tracks_duration_comparison.sql
-- already showed multi-sensor tracks are, surprisingly, shorter-lived
-- on average than single-sensor tracks -- but that query collapses
-- every combination (radar+camera, radar+transponder, camera+
-- transponder, etc.) into one "multi-sensor" bucket. This query
-- resolves that finding to the exact combination level to see whether
-- the surprising result holds uniformly or is driven by one specific
-- pairing.
--
-- Tables involved: fused_track_measurements, fused_track_states,
--                   v_fused_track_summary (view)
-- Join path: fused_track_measurements -> fused_track_states (to learn
--            each track's full set of distinct contributing sensors)
--            -> v_fused_track_summary (to attach duration). Builds
--            directly on the same relationship
--            sensor_utilization_summary.sql and
--            multi_sensor_tracks_duration_comparison.sql use, but at a
--            finer grouping key (the exact sensor SET, not just a
--            count of how many sensors).
-- SQL technique: CTE with an explicit pre-sort before GROUP_CONCAT
--                (SQLite's GROUP_CONCAT has no native ORDER BY --
--                sorting in an intermediate CTE with no intervening
--                JOIN is the standard, reliable workaround, the same
--                technique queries/operational/object_class_changes_over_time.sql
--                uses) + INNER JOIN to an existing view
-- Grain: one row per distinct sensor combination observed in this file.
--
-- Why multiple datasets were required: no single table records "the
-- full set of sensors a track ever saw" -- that fact only exists by
-- aggregating fused_track_measurements per track, and duration only
-- exists on the state-history side. Combining them is what turns "how
-- many sensor types" into "which specific sensors, together."
--
-- Assumptions/limitations: a track's sensor combination reflects its
-- entire lifetime, not a single instant -- see
-- queries/operational/fused_track_history.sql for a specific track's
-- per-state sensor timeline. Combination labels are alphabetically
-- sorted and joined with "+" (e.g. "TOWER_SENSOR_CAMERA+TOWER_SENSOR_RADAR")
-- so the same combination always produces the same label regardless of
-- which sensor contributed first.
-- =========================================================================

WITH distinct_sensors_per_track AS (
    SELECT DISTINCT fts.fused_track_id, ftm.sensor_id_name
    FROM fused_track_measurements ftm
    JOIN fused_track_states fts ON fts.fused_track_state_id = ftm.fused_track_state_id
),
sorted_sensor_list AS (
    SELECT fused_track_id, sensor_id_name
    FROM distinct_sensors_per_track
    ORDER BY fused_track_id, sensor_id_name
),
sensor_combination AS (
    SELECT fused_track_id, GROUP_CONCAT(sensor_id_name, '+') AS sensor_combination
    FROM sorted_sensor_list
    GROUP BY fused_track_id
)
SELECT
    sc.sensor_combination,
    COUNT(*) AS track_count,
    ROUND(AVG(v.duration_seconds), 2) AS avg_duration_seconds,
    ROUND(MIN(v.duration_seconds), 2) AS min_duration_seconds,
    ROUND(MAX(v.duration_seconds), 2) AS max_duration_seconds
FROM sensor_combination sc
JOIN v_fused_track_summary v ON v.fused_track_id = sc.fused_track_id
GROUP BY sc.sensor_combination
ORDER BY avg_duration_seconds DESC;
