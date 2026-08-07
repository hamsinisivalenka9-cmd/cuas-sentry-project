-- =========================================================================
-- Longest-lived tracks (CV and fused, side by side)
--
-- Audience: Mission Operations Analyst
-- Question: Which CV tracks and which fused tracks were followed the
--           longest, and how many state updates did each receive?
-- Decision supported: Identifying the specific tracks most worth a
--                      manual review (a long-lived track represents
--                      the most sustained engagement in the recording
--                      and is the highest-value candidate for a
--                      detailed history review via
--                      queries/operational/{cv,fused}_track_history.sql).
-- Why it matters: pairs the two independent tracking systems' top
-- performers side by side for a single at-a-glance operational read,
-- while keeping them explicitly labeled as separate systems -- see the
-- limitation note below on why they are not, and cannot be, joined to
-- each other.
--
-- Tables involved: v_cv_track_summary, v_fused_track_summary (views)
-- Join path: none -- deliberately a UNION ALL of two independent
--            single-table view queries, not a join. CV track identity
--            and fused track identity are CONFIRMED unrelated
--            identifier namespaces with zero observed value overlap
--            and incompatible protobuf types (uint64 vs. string) --
--            docs/KEY_ANALYSIS.md tested this exact join and rejected
--            it. Presenting these two systems' top tracks side by side
--            is useful; pretending they are joinable would misrepresent
--            evidence this project already gathered and confirmed.
-- SQL technique: UNION ALL of two independently ordered/limited
--                subqueries
-- Grain: one row per track, top 10 from each system (20 rows total).
--
-- Assumptions/limitations: only 17 persistent CV tracks exist in this
-- file in total, so the CV "top 10" already covers most of that
-- population; the fused side has 103, so its top 10 is a smaller slice
-- of a larger population -- direct numeric comparison between the two
-- track_type groups' duration values is not meaningful (different
-- systems, different sensors, different definitions of "engagement").
-- =========================================================================

SELECT * FROM (
    SELECT
        'cv_track' AS track_type,
        CAST(track_id AS TEXT) AS track_id,
        state_count,
        ROUND(duration_seconds, 2) AS duration_seconds
    FROM v_cv_track_summary
    ORDER BY duration_seconds DESC
    LIMIT 10
)

UNION ALL

SELECT * FROM (
    SELECT
        'fused_track' AS track_type,
        fused_track_id AS track_id,
        state_count,
        ROUND(duration_seconds, 2) AS duration_seconds
    FROM v_fused_track_summary
    ORDER BY duration_seconds DESC
    LIMIT 10
)

ORDER BY track_type, duration_seconds DESC;
