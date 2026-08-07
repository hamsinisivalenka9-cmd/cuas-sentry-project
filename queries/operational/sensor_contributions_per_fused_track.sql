-- =========================================================================
-- Sensor contributions per fused track
--
-- Audience: Mission Operations Analyst
-- Question: For each fused track, which sensors contributed
--           measurements, how many each, and how many distinct sensor
--           modalities were involved (i.e. which tracks were confirmed
--           by more than one kind of sensor)?
-- Decision supported: Identifying which specific tracks have
--                      multi-sensor corroboration (higher confidence
--                      for mission reporting) versus single-sensor-only
--                      tracks (may warrant secondary confirmation
--                      before acting on them).
-- Why it matters: this is the track-level detail behind the
-- executive-level aggregate in
-- queries/executive/multi_sensor_tracks_duration_comparison.sql --
-- that query answers "does multi-sensor coverage matter, on average,"
-- this one answers "which specific tracks does it apply to."
--
-- Tables involved: fused_track_measurements, fused_track_states
-- Join path: fused_track_measurements -> fused_track_states (per-
--            measurement sensor identity rolled up to per-track sensor
--            diversity, the same relationship
--            sensor_utilization_summary.sql uses at the fleet-wide
--            level instead of per-track).
-- SQL technique: CTE (per-track-per-sensor aggregation) + a second CTE
--                (per-track sensor-type count) + INNER JOIN
-- Grain: one row per (fused_track_id, sensor_id_name) pair.
--
-- Assumptions/limitations: "contributed a measurement" does not by
-- itself imply the sensors' data was fused simultaneously -- a track
-- with both RADAR and TRANSPONDER rows may have transitioned from one
-- sensor's coverage to the other's over time, not necessarily been
-- seen by both at once. Cross-reference with
-- queries/operational/fused_track_history.sql for a specific track's
-- exact timeline if that distinction matters.
-- =========================================================================

WITH per_track_sensor AS (
    SELECT
        fts.fused_track_id,
        ftm.sensor_id_name,
        COUNT(*) AS measurement_count
    FROM fused_track_measurements ftm
    JOIN fused_track_states fts ON fts.fused_track_state_id = ftm.fused_track_state_id
    GROUP BY fts.fused_track_id, ftm.sensor_id_name
),
sensor_diversity AS (
    SELECT fused_track_id, COUNT(*) AS distinct_sensor_types
    FROM per_track_sensor
    GROUP BY fused_track_id
)
SELECT
    p.fused_track_id,
    p.sensor_id_name,
    p.measurement_count,
    d.distinct_sensor_types
FROM per_track_sensor p
JOIN sensor_diversity d ON d.fused_track_id = p.fused_track_id
ORDER BY d.distinct_sensor_types DESC, p.fused_track_id, p.measurement_count DESC;
