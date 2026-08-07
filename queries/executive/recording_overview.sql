-- =========================================================================
-- Recording overview
--
-- Audience: Executive / Program Leadership
-- Question: What does this recording cover, end to end -- how many raw
--           messages, across how many topics, over what wall-clock
--           span, and how much publish latency did the pipeline add?
-- Decision supported: Whether the recording's scope and pipeline timing
--                      are sufficient to trust downstream analytics
--                      before presenting them further.
-- Why it matters: Every other query in this analytical layer implicitly
--                  assumes this recording is complete and its clocks
--                  are trustworthy -- this is the query that actually
--                  checks that assumption.
--
-- Tables involved: source_messages
-- Join path: single table (this is a foundational context query, not a
--            pipeline-traversal one -- see cv_detection_to_track_funnel.sql
--            and multi_sensor_tracks_duration_comparison.sql for the
--            relationship-driven executive insights).
-- SQL technique: aggregation (MIN/MAX/COUNT)
-- Grain: one row (a single summary).
--
-- Assumptions/limitations: log_time_ns and publish_time_ns are both
-- confirmed nanoseconds since epoch (CLAUDE.md rule 5), so no unit
-- conversion is applied. max_publish_log_latency_ns being 0 in this
-- recording (an observed, not assumed, fact) means publish_time and
-- log_time are identical for every message here -- worth confirming
-- again if this pipeline is ever pointed at a different recording.
-- =========================================================================

SELECT
    COUNT(*) AS total_messages,
    COUNT(DISTINCT topic) AS distinct_topics,
    MIN(log_time_ns) AS recording_start_log_time_ns,
    MAX(log_time_ns) AS recording_end_log_time_ns,
    ROUND((MAX(log_time_ns) - MIN(log_time_ns)) / 1e9, 2) AS recording_duration_seconds,
    MAX(publish_time_ns - log_time_ns) AS max_publish_log_latency_ns
FROM source_messages;
