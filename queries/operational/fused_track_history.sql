-- =========================================================================
-- Fused track history with contributing sensors
--
-- Audience: Mission Operations Analyst
-- Question: What is the complete state-by-state history of one
--           specific fused (tower) track, including which sensors
--           contributed to each individual state update?
-- Decision supported: Whether a specific track's fused position/
--                      classification at a given moment should be
--                      trusted at high confidence (multiple
--                      corroborating sensors) or treated cautiously
--                      (single sensor, or a gap in coverage).
-- Why it matters: fused_track_states alone shows *what* the fusion
-- system concluded at each update; joining in fused_track_measurements
-- shows *why* -- which sensor(s) fed that specific conclusion, not just
-- the track as a whole.
--
-- Tables involved: fused_track_states, fused_track_measurements
-- Join path: fused_track_states -> fused_track_measurements (one state
--            can have zero, one, or several contributing measurements;
--            this query aggregates them per state with GROUP_CONCAT
--            rather than fanning the result out to one row per
--            measurement, since the analyst wants "what happened at
--            this instant," not a separate measurement-level table).
-- SQL technique: LEFT JOIN + GROUP BY with GROUP_CONCAT(DISTINCT ...)
-- Grain: one row per state update of the given track, in time order.
--
-- PARAMETERIZED QUERY -- requires :fused_track_id (a text value from
-- fused_tracks.fused_track_id; see
-- `SELECT fused_track_id FROM fused_tracks;` for real values in this
-- file). Run via:
--   python scripts/run_analytics.py --query fused_track_history --param fused_track_id=25295F49158-7aa000016009
--
-- Assumptions/limitations: object_class_name uses proto.tower.
-- TrackObjectClass, which has no DRONE/AIRPLANE value
-- (docs/CHECKSUM_RESOLUTION.md) -- for the Drone/Airplane inference,
-- see queries/fused_track_duration_by_type.sql instead, which uses
-- sensor provenance (visible directly in this query's
-- contributing_sensors column), not this object_class_name column. A
-- LEFT JOIN is used deliberately: a state with zero measurements is a
-- meaningful, visible fact (contributing_sensors = NULL,
-- measurement_count = 0), not a row to silently drop.
-- =========================================================================

SELECT
    fts.fused_track_state_id,
    fts.log_time_ns,
    fts.object_class_name,
    fts.disposition_name,
    fts.track_status_name,
    fts.object_class_confidence,
    fts.lla_lat,
    fts.lla_lon,
    fts.lla_alt,
    GROUP_CONCAT(DISTINCT ftm.sensor_id_name) AS contributing_sensors,
    COUNT(ftm.fused_track_measurement_id) AS measurement_count
FROM fused_track_states fts
LEFT JOIN fused_track_measurements ftm ON ftm.fused_track_state_id = fts.fused_track_state_id
WHERE fts.fused_track_id = :fused_track_id
GROUP BY fts.fused_track_state_id
ORDER BY fts.log_time_ns;
