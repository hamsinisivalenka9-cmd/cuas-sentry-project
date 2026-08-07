-- =========================================================================
-- Source-message-to-child-row reconciliation
--
-- Audience: Data Engineer
-- Question: Does every child row that claims to trace back to a raw
--           MCAP message (via source_message_id) actually resolve to a
--           real source_messages row?
-- Decision supported: Whether the provenance chain this entire schema
--                      is built around (every analytical fact traces
--                      back to the exact raw message it came from --
--                      docs/DATABASE_DESIGN.md Section 5.1) can be
--                      trusted, independent of whatever FOREIGN KEY
--                      declarations happen to be in sql/schema.sql.
-- Why it matters: this is the query that most directly demonstrates
-- why source_messages exists as its own table at all -- every one of
-- these four child tables could theoretically have skipped the
-- indirection and stored log_time_ns/topic directly, but doing so
-- would have made exactly this kind of cross-table provenance check
-- impossible to express as a simple join.
--
-- Tables involved: source_messages, cv_detections, cv_track_states,
--                   radar_detections, fused_track_states
-- Join path: source_messages <- cv_detections (LEFT JOIN, looking for
--            unresolved rows on the child side), and independently the
--            same pattern for cv_track_states, radar_detections, and
--            fused_track_states -- the four tables with a direct
--            source_message_id foreign key.
-- SQL technique: four independent LEFT JOIN ... WHERE ... IS NULL
--                checks (the standard SQL idiom for "does the parent
--                exist"), unioned into one result
-- Grain: one row per checked child table -- HEALTHY RESULT IS
--        orphaned_rows = 0 IN EVERY ROW.
--
-- Assumptions/limitations: source_message_id is already a real,
-- enforced FOREIGN KEY on all four of these tables (PRAGMA foreign_keys
-- = ON throughout this project, CLAUDE.md rule 8), so this check is
-- expected to always pass -- it exists as an independent, from-scratch
-- verification that does not merely trust the constraint declaration,
-- the same defense-in-depth philosophy as duplicate_relationship_check.sql.
-- cv_detection_track_links and fused_track_measurements are
-- deliberately not included here: neither has its own
-- source_message_id column (they trace provenance indirectly, through
-- their parent state/detection row instead).
-- =========================================================================

SELECT 'cv_detections' AS table_name, COUNT(*) AS orphaned_rows
FROM cv_detections cd
LEFT JOIN source_messages sm ON sm.source_message_id = cd.source_message_id
WHERE sm.source_message_id IS NULL

UNION ALL

SELECT 'cv_track_states', COUNT(*)
FROM cv_track_states cts
LEFT JOIN source_messages sm ON sm.source_message_id = cts.source_message_id
WHERE sm.source_message_id IS NULL

UNION ALL

SELECT 'radar_detections', COUNT(*)
FROM radar_detections rd
LEFT JOIN source_messages sm ON sm.source_message_id = rd.source_message_id
WHERE sm.source_message_id IS NULL

UNION ALL

SELECT 'fused_track_states', COUNT(*)
FROM fused_track_states fts
LEFT JOIN source_messages sm ON sm.source_message_id = fts.source_message_id
WHERE sm.source_message_id IS NULL;
