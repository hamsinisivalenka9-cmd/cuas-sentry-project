-- =========================================================================
-- CUAS Sentry -- analytical views (Stage 6 implementation)
--
-- Source of truth: docs/DATABASE_DESIGN.md Section 5.11 ("Recommended
-- views"). v_cv_track_summary and v_fused_track_summary are the two
-- views the original reviewed design called for. v_fused_track_type_basis
-- was added in Stage 6B (docs/CHECKSUM_RESOLUTION.md) once the Drone/
-- Airplane checksum was resolved via a sensor-provenance signal
-- (fused_track_measurements.sensor_id_name) that was already loaded by
-- the existing ETL -- no schema or ETL change was required, only this
-- view. See docs/CHECKSUM_RESOLUTION.md for the full evidence trail.
--
-- Requires sql/schema.sql to have already been run.
--
-- WHY VIEWS INSTEAD OF STORED COLUMNS: per explicit design instruction,
-- first_observed_log_time, last_observed_log_time, and duration are NOT
-- stored as columns on cv_tracks or fused_tracks. A stored duration
-- column would be a fact computed at load time that could silently go
-- stale the moment new state rows are appended (cv_track_states and
-- fused_track_states are both append-only history tables that keep
-- growing). A view recomputes from the current state rows on every
-- query, so the derived fact can never become inconsistent with its
-- source.
--
-- Idempotent: CREATE VIEW IF NOT EXISTS.
-- =========================================================================

BEGIN TRANSACTION;

-- -------------------------------------------------------------------------
-- v_cv_track_summary
-- One row per persistent CV track (cv_tracks.track_id), with its first
-- and last observed timestamps, how many state rows it has, and its
-- duration in seconds -- all derived live from cv_track_states.
--
-- Deliberately does NOT resolve or include an object classification for
-- the track -- see the note on v_fused_track_summary below, and
-- docs/DATABASE_DESIGN.md Section 3.
-- -------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_cv_track_summary AS
SELECT
    track_id,
    MIN(log_time_ns) AS first_observed_log_time_ns,
    MAX(log_time_ns) AS last_observed_log_time_ns,
    COUNT(*) AS state_count,
    (MAX(log_time_ns) - MIN(log_time_ns)) / 1e9 AS duration_seconds
FROM cv_track_states
GROUP BY track_id;

-- -------------------------------------------------------------------------
-- v_fused_track_summary
-- One row per persistent fused track (fused_tracks.fused_track_id), with
-- its first and last observed timestamps, how many state rows it has,
-- and its duration in seconds -- all derived live from
-- fused_track_states.
--
-- IMPORTANT: this view deliberately does NOT attempt to resolve "the"
-- object classification for a track. docs/SCHEMA_REVIEW.md finding F6
-- CONFIRMED that 18 of 103 persistent fused tracks genuinely change
-- object_class within their own state history, and defined five
-- possible resolution semantics (class at first observation, class at
-- last observation, most frequent class, highest-confidence class, or
-- class-interval splitting) WITHOUT selecting one -- neither the source
-- evidence nor the assignment's wording justifies choosing one over the
-- others. Answering CLAUDE.md's "average fused-track duration by class"
-- question therefore requires an additional, explicit, human-decided
-- resolution step on top of this view, not a plain GROUP BY on
-- object_class_raw. This view intentionally stops short of making that
-- decision. It also does not, and cannot, resolve the separate,
-- independent Drone/Airplane question (docs/DATABASE_DESIGN.md Section
-- 3): proto.tower.TrackObjectClass (the enum object_class_raw/_name
-- store) has no DRONE or AIRPLANE value at all.
-- -------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_fused_track_summary AS
SELECT
    fused_track_id,
    MIN(log_time_ns) AS first_observed_log_time_ns,
    MAX(log_time_ns) AS last_observed_log_time_ns,
    COUNT(*) AS state_count,
    (MAX(log_time_ns) - MIN(log_time_ns)) / 1e9 AS duration_seconds
FROM fused_track_states
GROUP BY fused_track_id;

-- -------------------------------------------------------------------------
-- v_fused_track_type_basis
-- One row per persistent fused track, providing the raw ingredients
-- needed to classify it as a Drone/Airplane checksum candidate --
-- NOT the classification itself (that logic lives in
-- queries/fused_track_duration_by_type.sql, kept out of this view so
-- the eligibility rule can be revised without touching the schema).
--
-- Columns:
--   fused_track_id               -- the persistent track identity
--   has_transponder_measurement  -- 1 if ANY fused_track_measurements
--                                    row for this track has
--                                    sensor_id_name =
--                                    'TOWER_SENSOR_TRANSPONDER', else 0
--   dominant_object_class_name   -- the object_class_name that appears
--                                    on the most fused_track_states
--                                    rows for this track (a simple
--                                    mode/plurality vote across that
--                                    track's own state history, NOT a
--                                    stored column -- ties broken
--                                    alphabetically for determinism)
--   duration_seconds             -- (MAX(log_time_ns) -
--                                    MIN(log_time_ns)) / 1e9, identical
--                                    definition to v_fused_track_summary
--
-- EVIDENCE (docs/CHECKSUM_RESOLUTION.md Section 2): proto.tower.
-- TrackObjectClass (object_class_raw/_name) has no DRONE or AIRPLANE
-- value at all -- confirmed by full protobuf descriptor enumeration,
-- not just observed data. The field that actually separates the two
-- populations close to the ~30s/~600s checksum targets is measurement
-- provenance: proto.tower.SensorId's TOWER_SENSOR_TRANSPONDER value,
-- already loaded (unchanged) as fused_track_measurements.sensor_id_name
-- by the existing ETL. This view adds no new extraction -- it only
-- exposes a grouping already possible against columns that were
-- already correctly populated.
--
-- "Dominant object class" exists so a consuming query can exclude
-- OBJECT_CLASS_BIRD-dominant tracks (a bird is neither a drone nor an
-- airplane) without repeating the mode-selection window function in
-- every query that needs it.
-- -------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_fused_track_type_basis AS
WITH class_counts AS (
    SELECT
        fused_track_id,
        object_class_name,
        COUNT(*) AS state_count,
        ROW_NUMBER() OVER (
            PARTITION BY fused_track_id
            ORDER BY COUNT(*) DESC, object_class_name ASC
        ) AS class_rank
    FROM fused_track_states
    GROUP BY fused_track_id, object_class_name
),
dominant_class AS (
    SELECT fused_track_id, object_class_name AS dominant_object_class_name
    FROM class_counts
    WHERE class_rank = 1
),
transponder_flag AS (
    SELECT
        fts.fused_track_id,
        MAX(CASE WHEN ftm.sensor_id_name = 'TOWER_SENSOR_TRANSPONDER' THEN 1 ELSE 0 END)
            AS has_transponder_measurement
    FROM fused_track_states fts
    JOIN fused_track_measurements ftm ON ftm.fused_track_state_id = fts.fused_track_state_id
    GROUP BY fts.fused_track_id
),
durations AS (
    SELECT
        fused_track_id,
        (MAX(log_time_ns) - MIN(log_time_ns)) / 1e9 AS duration_seconds
    FROM fused_track_states
    GROUP BY fused_track_id
)
SELECT
    d.fused_track_id,
    COALESCE(t.has_transponder_measurement, 0) AS has_transponder_measurement,
    dc.dominant_object_class_name,
    d.duration_seconds
FROM durations d
JOIN dominant_class dc ON dc.fused_track_id = d.fused_track_id
LEFT JOIN transponder_flag t ON t.fused_track_id = d.fused_track_id;

COMMIT;
