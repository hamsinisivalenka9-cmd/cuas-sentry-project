-- =========================================================================
-- Zero-duration or single-state tracks
--
-- Audience: Data Engineer / Mission Operations Analyst
-- Question: Which persistent tracks (CV or fused) were only ever
--           observed in a single state, or otherwise have a
--           degenerate (zero-second) duration -- i.e. candidates for
--           left/right-censoring at the edges of the recording, or a
--           track that briefly flickered into existence and never
--           restated?
-- Decision supported: Whether these specific tracks should be excluded
--                      from any average-duration analysis (they can
--                      skew a mean toward zero) or flagged for
--                      engineering review as possible tracker
--                      false-positives.
-- Why it matters: docs/CHECKSUM_RESOLUTION.md's Drone/Airplane duration
-- investigation explicitly tested and rejected excluding these tracks
-- as an eligibility filter (it moved the result further from the
-- target, not closer) -- this query exists so that decision is
-- re-checkable against the current data rather than only asserted in a
-- document.
--
-- Tables involved: v_cv_track_summary, v_fused_track_summary (views)
-- Join path: none -- UNION ALL of two independent view queries (see
--            longest_lived_tracks.sql for why CV and fused tracks are
--            never joined to each other in this project).
-- SQL technique: UNION ALL with a WHERE filter on each branch
-- Grain: one row per track meeting the condition (state_count = 1 OR
--        duration_seconds = 0 -- for a single-state track these are
--        the same condition, since MAX(log_time_ns) - MIN(log_time_ns)
--        is trivially 0 when there is only one row to begin with).
--
-- Assumptions/limitations: a zero/single-state track is not
-- automatically an error -- it may be a genuine, brief real-world
-- observation, or a track whose lifetime was truncated by the
-- recording's own start/end boundary (left/right-censoring). This
-- query surfaces the candidates; distinguishing "real but brief" from
-- "censored by recording boundary" requires checking each track's
-- log_time_ns against the overall recording span (see
-- queries/executive/recording_overview.sql) or the individual sensor
-- history in queries/operational/{cv,fused}_track_history.sql.
-- =========================================================================

SELECT
    'cv_track' AS track_type,
    CAST(track_id AS TEXT) AS track_id,
    state_count,
    ROUND(duration_seconds, 3) AS duration_seconds
FROM v_cv_track_summary
WHERE state_count = 1 OR duration_seconds = 0

UNION ALL

SELECT
    'fused_track',
    fused_track_id,
    state_count,
    ROUND(duration_seconds, 3)
FROM v_fused_track_summary
WHERE state_count = 1 OR duration_seconds = 0

ORDER BY track_type, track_id;
