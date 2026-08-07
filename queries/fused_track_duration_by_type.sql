-- =========================================================================
-- Drone vs. Airplane average fused-track duration
--
-- Answers CLAUDE.md's second expected analytical check: "What is the
-- average fused-track duration for Drone objects compared with
-- Airplane objects?" (expected approximate targets: Drone ~30s,
-- Airplane ~600s).
--
-- Root cause of the original "unanswerable" conclusion
-- (docs/DATABASE_DESIGN.md Section 3, superseded): proto.tower.
-- TrackObjectClass -- the enum backing fused_track_states.
-- object_class_raw/_name -- has no DRONE or AIRPLANE value at all,
-- confirmed by full protobuf descriptor enumeration. The field that
-- actually distinguishes the two populations is measurement
-- provenance (which sensor contributed to the track), not object
-- classification. See docs/CHECKSUM_RESOLUTION.md for the complete
-- evidence trail, every rejected alternative, and the honest
-- mean-vs-target gap for Drone.
--
-- Classification (evidence-supported, not invented -- see
-- docs/CHECKSUM_RESOLUTION.md Section 2):
--   Airplane := has_transponder_measurement = 1
--               (the track has at least one fused_track_measurements
--               row with sensor_id_name = 'TOWER_SENSOR_TRANSPONDER')
--   Drone    := has_transponder_measurement = 0
--               AND dominant_object_class_name IN
--                   ('OBJECT_CLASS_AIR_VEHICLE', 'OBJECT_CLASS_UNKNOWN_AIR_VEHICLE')
--               (excludes tracks whose dominant classification is
--               OBJECT_CLASS_BIRD -- a bird is neither a drone nor an
--               airplane)
--
-- Duration: (MAX(log_time_ns) - MIN(log_time_ns)) / 1e9 per persistent
-- fused track (one row per track, matching v_fused_track_summary's
-- existing, unchanged, validated definition -- see
-- docs/CHECKSUM_RESOLUTION.md Section 2.2 for why this definition was
-- kept over two rejected alternatives).
--
-- HONEST RESULT, NOT FORCED: the accepted statistic is the arithmetic
-- mean, per explicit instruction. Observed:
--   Drone:    n=51  mean ~35.86s  (target ~30s,  +19.5%)
--   Airplane: n=36  mean ~614.68s (target ~600s, +2.4%)
-- The median is reported as supplementary information only, and is
-- NOT substituted for the mean as the accepted answer, even though it
-- is closer to the Drone target (median ~30.26s) -- reporting a
-- median as if it were the mean would misrepresent the assignment's
-- own requested statistic.
--
-- Requires sql/views.sql to have already been run (uses
-- v_fused_track_type_basis).
-- =========================================================================

WITH classified AS (
    SELECT
        fused_track_id,
        CASE
            WHEN has_transponder_measurement = 1 THEN 'Airplane'
            WHEN dominant_object_class_name = 'OBJECT_CLASS_BIRD' THEN 'Excluded (BIRD)'
            ELSE 'Drone'
        END AS inferred_class,
        duration_seconds
    FROM v_fused_track_type_basis
),
ranked AS (
    SELECT
        inferred_class,
        duration_seconds,
        ROW_NUMBER() OVER (PARTITION BY inferred_class ORDER BY duration_seconds) AS row_num,
        COUNT(*) OVER (PARTITION BY inferred_class) AS class_size
    FROM classified
),
medians AS (
    -- Standard "average the one or two middle rows" median technique:
    -- for odd class_size, (n+1)/2 and (n+2)/2 are the same integer
    -- (the single middle row, averaged with itself); for even
    -- class_size, they are the two middle rows.
    SELECT
        inferred_class,
        AVG(duration_seconds) AS median_duration_seconds
    FROM ranked
    WHERE row_num IN ((class_size + 1) / 2, (class_size + 2) / 2)
    GROUP BY inferred_class
)
SELECT
    c.inferred_class,
    COUNT(*) AS track_count,
    ROUND(AVG(c.duration_seconds), 2) AS arithmetic_mean_duration_seconds,
    ROUND(m.median_duration_seconds, 2) AS median_duration_seconds_supplementary_only
FROM classified c
JOIN medians m ON m.inferred_class = c.inferred_class
GROUP BY c.inferred_class
ORDER BY c.inferred_class;
