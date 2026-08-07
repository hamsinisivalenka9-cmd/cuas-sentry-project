-- =========================================================================
-- CV detection input quality vs. track persistence
--
-- Audience: Mission Operations Analyst / Sensor Engineer
-- Question: Do CV tracks fed by higher-quality/higher-confidence
--           detections persist longer than tracks fed by lower-quality
--           detections?
-- Decision supported: Whether investing in better camera focus/optics
--                      or detector confidence would improve not just
--                      *whether* a detection gets incorporated
--                      (queries/operational/cv_focus_quality_vs_incorporation.sql
--                      already answers that) but *how long the
--                      resulting track survives* -- a materially
--                      different, more operationally consequential
--                      question for sensor investment decisions.
-- Why it matters: this is the deepest cause-and-effect chain the CV
-- side of this schema can support -- detection-level input quality,
-- rolled up through the bridge table to track identity, joined against
-- track-level lifetime -- and no existing query in this library
-- connects those three facts together.
--
-- Tables involved: cv_detection_track_links, cv_detections,
--                   v_cv_track_summary (view over cv_track_states)
-- Join path: cv_detection_track_links -> cv_detections (to pull each
--            incorporated detection's own score/focus_quality) rolled
--            up per track_id, then -> v_cv_track_summary (to attach
--            that track's overall duration). Three genuinely distinct
--            facts -- which detections fed a track, how good those
--            detections were, and how long the track survived -- that
--            only exist as separate, joinable tables because the
--            schema keeps detection identity, the bridge relationship,
--            and track-state history at three separate grains.
-- SQL technique: CTE (per-track aggregation of joined detection
--                quality) + INNER JOIN to an existing view
-- Grain: one row per persistent CV track (all 17 -- small enough to
--        read directly rather than bucketing, since this file's CV
--        track population is not large enough for meaningful
--        statistical binning).
--
-- Why multiple datasets were required: cv_detections alone has no
-- notion of "which track," and cv_track_states/v_cv_track_summary
-- alone has no notion of detection-level quality -- cv_detection_
-- track_links is the only place these two facts can be joined, and
-- even that only works because it is a real, deduplicated bridge
-- table rather than a raw restatement history (which would
-- over-count the same detection once per track update that mentions it).
--
-- Assumptions/limitations: n=17 is small -- this is presented as a
-- direct, readable per-track comparison for visual inspection, not a
-- claim of statistical significance. avg_detection_score averages the
-- continuous score field (0.40-0.97 range in this file);
-- pct_sharp_or_better summarizes the categorical focus_quality field
-- as a single percentage for the same comparison. This is a
-- descriptive correlation, not a controlled experiment -- other
-- factors (object range, motion, recording conditions) are not held
-- constant.
-- =========================================================================

WITH detection_quality_per_track AS (
    SELECT
        l.track_id,
        COUNT(*) AS incorporated_detection_count,
        AVG(cd.score) AS avg_detection_score,
        SUM(
            CASE WHEN cd.focus_quality_name IN (
                'FOCUS_SEMANTIC_QUALITY_SHARP', 'FOCUS_SEMANTIC_QUALITY_MID_SHARP'
            ) THEN 1 ELSE 0 END
        ) AS sharp_or_better_count
    FROM cv_detection_track_links l
    JOIN cv_detections cd ON cd.detection_id = l.detection_id
    GROUP BY l.track_id
)
SELECT
    dq.track_id,
    dq.incorporated_detection_count,
    ROUND(dq.avg_detection_score, 3) AS avg_detection_score,
    ROUND(100.0 * dq.sharp_or_better_count / dq.incorporated_detection_count, 1) AS pct_sharp_or_better_focus,
    v.state_count AS track_state_count,
    ROUND(v.duration_seconds, 2) AS track_duration_seconds
FROM detection_quality_per_track dq
JOIN v_cv_track_summary v ON v.track_id = dq.track_id
ORDER BY track_duration_seconds DESC;
