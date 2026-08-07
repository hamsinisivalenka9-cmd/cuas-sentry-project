-- =========================================================================
-- Duplicate relationship check
--
-- Audience: Data Engineer
-- Question: Does the CV detection<->track bridge table contain any
--           duplicate (detection_id, track_id) pairing?
-- Decision supported: Whether cv_detection_track_links (and therefore
--                      queries/executive/cv_incorporation_summary.sql)
--                      can be trusted not to be double-counting a
--                      pairing.
-- Why it matters: a duplicate here would silently inflate every
-- incorporation-percentage figure this project reports.
--
-- Tables involved: cv_detection_track_links
-- Join path: single table (self-comparison via GROUP BY/HAVING).
-- SQL technique: GROUP BY + HAVING COUNT(*) > 1
-- Grain: one row per duplicate pair found -- HEALTHY RESULT IS ZERO
--        ROWS.
--
-- Assumptions/limitations: cv_detection_track_links' composite PRIMARY
-- KEY (detection_id, track_id) already makes a true SQL-level duplicate
-- impossible; this query independently re-derives the same check from
-- first principles as a defense-in-depth verification that does not
-- merely trust the constraint was correctly declared -- see
-- tests/test_checksum_queries.py and tests/test_schema.py for the
-- equivalent automated checks.
-- =========================================================================

SELECT
    detection_id,
    track_id,
    COUNT(*) AS occurrence_count
FROM cv_detection_track_links
GROUP BY detection_id, track_id
HAVING COUNT(*) > 1;
