-- =========================================================================
-- CUAS Sentry -- structural and referential validation queries
-- (Stage 6 implementation)
--
-- Read-only diagnostic queries. They modify nothing and are safe to run
-- at any time, including against an empty (freshly-initialized, no data
-- loaded yet) database. src/cuas_etl/database.py's validate_database()
-- runs the equivalent checks in Python and tests/test_schema.py asserts
-- on their results -- this file is the plain-SQL reference for the same
-- checks, runnable directly with the sqlite3 CLI:
--
--   sqlite3 data/output/sentry.db < sql/validation.sql
--
-- No BEGIN/COMMIT here -- every statement is read-only.
-- =========================================================================

-- -------------------------------------------------------------------------
-- 1. SQLite's built-in structural integrity check. On a healthy database
-- this returns exactly one row containing the text "ok". Any other
-- output describes a structural corruption problem.
-- -------------------------------------------------------------------------
PRAGMA integrity_check;

-- -------------------------------------------------------------------------
-- 2. Foreign-key consistency check. Returns one row per foreign-key
-- violation found (table, rowid, referenced table, FK index) -- an empty
-- result means every foreign key currently in the database is valid.
-- This check inspects existing data regardless of whether
-- PRAGMA foreign_keys was ON while that data was written, so it is a
-- meaningful check even against data loaded by a misconfigured caller.
-- -------------------------------------------------------------------------
PRAGMA foreign_key_check;

-- -------------------------------------------------------------------------
-- 3. Confirm every one of the 11 reviewed analytical tables exists.
-- (schema_version is deliberately excluded -- it is implementation-layer
-- metadata, not one of the 11 reviewed tables in docs/TABLE_GRAIN.md.)
-- Expected: 11 rows.
-- -------------------------------------------------------------------------
SELECT name
FROM sqlite_master
WHERE type = 'table'
  AND name IN (
    'source_messages',
    'cv_detections',
    'cv_tracks',
    'cv_track_states',
    'cv_track_class_distribution',
    'cv_detection_track_links',
    'radar_detections',
    'fused_tracks',
    'fused_track_states',
    'fused_track_measurements',
    'data_quality_issues'
  )
ORDER BY name;

-- -------------------------------------------------------------------------
-- 4. Confirm all reviewed views exist. Expected: 3 rows.
-- -------------------------------------------------------------------------
SELECT name
FROM sqlite_master
WHERE type = 'view'
  AND name IN ('v_cv_track_summary', 'v_fused_track_summary', 'v_fused_track_type_basis')
ORDER BY name;

-- -------------------------------------------------------------------------
-- 5. Confirm foreign-key enforcement is active on THIS connection.
-- Returns 1 if PRAGMA foreign_keys = ON has been set for the current
-- connection, 0 otherwise. This is a per-connection SQLite setting, so a
-- passing result here only describes the connection running this query,
-- not a database-wide property.
-- -------------------------------------------------------------------------
PRAGMA foreign_keys;

-- -------------------------------------------------------------------------
-- 6. Confirm the recorded schema version(s). Expected: at least one row
-- once src/cuas_etl/database.py's initialize_database() has run.
-- -------------------------------------------------------------------------
SELECT version, applied_at_utc, description
FROM schema_version
ORDER BY version;

-- -------------------------------------------------------------------------
-- 7. List every index actually present on the 11 reviewed tables
-- (including the automatic indexes SQLite creates for PRIMARY KEY and
-- UNIQUE constraints, which are not separately listed in sql/indexes.sql
-- but do exist in the database). Useful for confirming no unexpected or
-- duplicate index was created.
-- -------------------------------------------------------------------------
SELECT tbl_name, name AS index_name
FROM sqlite_master
WHERE type = 'index'
  AND tbl_name IN (
    'source_messages',
    'cv_detections',
    'cv_tracks',
    'cv_track_states',
    'cv_track_class_distribution',
    'cv_detection_track_links',
    'radar_detections',
    'fused_tracks',
    'fused_track_states',
    'fused_track_measurements',
    'data_quality_issues'
  )
ORDER BY tbl_name, index_name;
