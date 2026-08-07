-- =========================================================================
-- Table row-count reconciliation
--
-- Audience: Data Engineer
-- Question: Do every table's row counts match the documented, approved
--           grain (docs/DATABASE_DESIGN.md, docs/TABLE_GRAIN.md)?
-- Decision supported: Whether the currently-loaded database can be
--                      trusted as a faithful, complete load of the
--                      source file before running any analytical query
--                      against it.
-- Why it matters: this is the single fastest way to catch a partial or
-- corrupted load before it silently produces misleading analytics
-- downstream.
--
-- Tables involved: every reviewed analytical table
-- Join path: none -- deliberately single-table counts per row, unioned
--            (a validation summary is exactly the case where simple,
--            independent per-table checks are more trustworthy than a
--            clever join that could itself hide a bug).
-- SQL technique: UNION ALL of independent COUNT(*) statements
-- Grain: one row per table.
--
-- Assumptions/limitations: this reports counts only -- it does not
-- itself assert what the "correct" count should be (that comparison is
-- what src/cuas_etl/validation.py's check_structural_row_counts()
-- already automates against EXPECTED_STRUCTURAL_ROW_COUNTS at build
-- time; this query is the human-readable, ad-hoc equivalent for
-- spot-checking without re-running the full validation suite).
-- =========================================================================

SELECT 'source_messages' AS table_name, COUNT(*) AS row_count FROM source_messages
UNION ALL SELECT 'cv_detections', COUNT(*) FROM cv_detections
UNION ALL SELECT 'cv_tracks', COUNT(*) FROM cv_tracks
UNION ALL SELECT 'cv_track_states', COUNT(*) FROM cv_track_states
UNION ALL SELECT 'cv_track_class_distribution', COUNT(*) FROM cv_track_class_distribution
UNION ALL SELECT 'cv_detection_track_links', COUNT(*) FROM cv_detection_track_links
UNION ALL SELECT 'radar_detections', COUNT(*) FROM radar_detections
UNION ALL SELECT 'fused_tracks', COUNT(*) FROM fused_tracks
UNION ALL SELECT 'fused_track_states', COUNT(*) FROM fused_track_states
UNION ALL SELECT 'fused_track_measurements', COUNT(*) FROM fused_track_measurements
UNION ALL SELECT 'data_quality_issues', COUNT(*) FROM data_quality_issues;
