-- =========================================================================
-- Sensor utilization summary
--
-- Audience: Executive / Program Leadership
-- Question: Which sensor modalities (radar, camera, transponder, ...)
--           contributed how much of the fusion system's measurement
--           volume, and to how many distinct tracked objects?
-- Decision supported: Sensor investment/maintenance prioritization --
--                      a sensor contributing to few measurements or few
--                      distinct tracks may be under-utilized,
--                      mis-configured, or covering a smaller share of
--                      the operating envelope than the others.
-- Why it matters: this is also the same field
-- (fused_track_measurements.sensor_id_name) the Drone/Airplane
-- checksum classification is built on
-- (docs/CHECKSUM_RESOLUTION.md) -- TOWER_SENSOR_TRANSPONDER's row here
-- is the exact population used as the Airplane group in
-- queries/fused_track_duration_by_type.sql.
--
-- Tables involved: fused_track_measurements, fused_track_states
-- Join path: fused_track_measurements -> fused_track_states (each
--            measurement traces back to the fused-track state it
--            contributed to, which in turn identifies which persistent
--            fused_track_id it belongs to). This relationship is what
--            lets a per-measurement fact (which sensor) be rolled up to
--            a per-track fact (how many distinct tracks this sensor
--            touched) -- impossible without the two grains being kept
--            separate.
-- SQL technique: INNER JOIN + GROUP BY with a COUNT(DISTINCT ...)
-- Grain: one row per distinct sensor_id_name observed in this file.
--
-- Assumptions/limitations: sensor_id_name is resolved from the
-- protobuf enum proto.tower.SensorId at load time (never hand-mapped).
-- "Contributed to N distinct tracks" counts a track once regardless of
-- how many measurements that sensor gave it.
-- =========================================================================

SELECT
    ftm.sensor_id_name,
    COUNT(*) AS measurement_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM fused_track_measurements), 2) AS pct_of_total_measurements,
    COUNT(DISTINCT fts.fused_track_id) AS distinct_fused_tracks_contributed_to
FROM fused_track_measurements ftm
JOIN fused_track_states fts ON fts.fused_track_state_id = ftm.fused_track_state_id
GROUP BY ftm.sensor_id_name
ORDER BY measurement_count DESC;
