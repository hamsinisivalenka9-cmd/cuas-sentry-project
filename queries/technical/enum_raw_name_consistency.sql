-- =========================================================================
-- Enum raw/name consistency check
--
-- Audience: Data Engineer
-- Question: For every column pair that stores a raw protobuf enum
--           integer alongside its resolved name, is a populated raw
--           value ever paired with a NULL name (i.e. an unrecognized
--           enum value that silently lost its label)?
-- Decision supported: Whether every *_name column in this database can
--                      be trusted as a faithful resolution of its *_raw
--                      counterpart before any query (including several
--                      in this analytical layer) groups or filters by
--                      the resolved name instead of the raw integer.
-- Why it matters: transform.py's resolve_enum_name() is a single
-- generic function reused across every enum in this schema (never a
-- hand-maintained per-field mapping) -- this check independently
-- verifies that generic mechanism actually worked everywhere it was
-- used, not just in the one or two places most commonly queried.
--
-- Tables involved: cv_detections, cv_track_states,
--                   cv_track_class_distribution, radar_detections,
--                   fused_track_states, fused_track_measurements
-- Join path: none -- 16 independent single-table checks, unioned (see
--            table_row_count_reconciliation.sql for why independent
--            per-column checks are preferred over a join here).
-- SQL technique: UNION ALL of independent conditional COUNT(*)
--                statements, wrapped in a subquery so the whole result
--                set can be ordered together
-- Grain: one row per checked column pair, always returned (not
--        filtered to failures only) so every category's health is
--        visible at a glance -- HEALTHY RESULT IS inconsistent_rows = 0
--        IN EVERY ROW.
--
-- Assumptions/limitations: this checks only "raw populated but name
-- NULL" (an unresolved enum value). The inverse -- name populated but
-- raw NULL -- cannot happen given how resolve_enum_name() is called
-- (name is always derived FROM raw, never independently), so it is not
-- checked here. See src/cuas_etl/validation.py's
-- check_enum_raw_name_consistency() for the automated equivalent that
-- also runs at build time.
-- =========================================================================

SELECT * FROM (
    SELECT 'cv_detections.object_class' AS column_pair, COUNT(*) AS inconsistent_rows
    FROM cv_detections WHERE object_class_raw IS NOT NULL AND object_class_name IS NULL

    UNION ALL
    SELECT 'cv_detections.semantic_confidence', COUNT(*)
    FROM cv_detections WHERE semantic_confidence_raw IS NOT NULL AND semantic_confidence_name IS NULL

    UNION ALL
    SELECT 'cv_detections.focus_quality', COUNT(*)
    FROM cv_detections WHERE focus_quality_raw IS NOT NULL AND focus_quality_name IS NULL

    UNION ALL
    SELECT 'cv_detections.disposition', COUNT(*)
    FROM cv_detections WHERE disposition_raw IS NOT NULL AND disposition_name IS NULL

    UNION ALL
    SELECT 'cv_detections.motion_state', COUNT(*)
    FROM cv_detections WHERE motion_state_raw IS NOT NULL AND motion_state_name IS NULL

    UNION ALL
    SELECT 'cv_track_states.status', COUNT(*)
    FROM cv_track_states WHERE status_raw IS NOT NULL AND status_name IS NULL

    UNION ALL
    SELECT 'cv_track_states.status_code', COUNT(*)
    FROM cv_track_states WHERE status_code_raw IS NOT NULL AND status_code_name IS NULL

    UNION ALL
    SELECT 'cv_track_states.object_class', COUNT(*)
    FROM cv_track_states WHERE object_class_raw IS NOT NULL AND object_class_name IS NULL

    UNION ALL
    SELECT 'cv_track_class_distribution.class', COUNT(*)
    FROM cv_track_class_distribution WHERE class_raw IS NOT NULL AND class_name IS NULL

    UNION ALL
    SELECT 'radar_detections.object_type_class', COUNT(*)
    FROM radar_detections WHERE object_type_class_raw IS NOT NULL AND object_type_class_name IS NULL

    UNION ALL
    SELECT 'radar_detections.object_class', COUNT(*)
    FROM radar_detections WHERE object_class_raw IS NOT NULL AND object_class_name IS NULL

    UNION ALL
    SELECT 'radar_detections.filter_type', COUNT(*)
    FROM radar_detections WHERE filter_type_raw IS NOT NULL AND filter_type_name IS NULL

    UNION ALL
    SELECT 'fused_track_states.object_class', COUNT(*)
    FROM fused_track_states WHERE object_class_raw IS NOT NULL AND object_class_name IS NULL

    UNION ALL
    SELECT 'fused_track_states.disposition', COUNT(*)
    FROM fused_track_states WHERE disposition_raw IS NOT NULL AND disposition_name IS NULL

    UNION ALL
    SELECT 'fused_track_states.track_status', COUNT(*)
    FROM fused_track_states WHERE track_status_raw IS NOT NULL AND track_status_name IS NULL

    UNION ALL
    SELECT 'fused_track_measurements.sensor_id', COUNT(*)
    FROM fused_track_measurements WHERE sensor_id_raw IS NOT NULL AND sensor_id_name IS NULL
)
ORDER BY inconsistent_rows DESC, column_pair;
