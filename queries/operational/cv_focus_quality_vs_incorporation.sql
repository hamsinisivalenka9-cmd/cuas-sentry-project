-- =========================================================================
-- CV focus quality vs. incorporation rate
--
-- Audience: Mission Operations Analyst / Sensor Engineer
-- Question: Does a CV detection's image focus quality correlate with
--           whether it ends up incorporated into a track?
-- Decision supported: Whether investing in better camera focus/optics,
--                      or filtering out blurry detections before they
--                      reach the tracker, would materially improve
--                      tracking yield -- directly informs sensor
--                      engineering priorities.
-- Why it matters: this is a direct test of a "cause -> effect"
-- hypothesis (image quality -> successful tracking) using a field
-- (focus_quality_name) only available since the Stage 6B source-
-- fidelity correction -- without that correction, this question could
-- not have been asked from this database at all.
--
-- Tables involved: cv_detections, cv_detection_track_links
-- Join path: cv_detections -> cv_detection_track_links (LEFT JOIN, so a
--            detection that was never incorporated still appears in
--            the denominator with a NULL match -- the same bridge-table
--            relationship cv_incorporation_summary.sql uses in
--            aggregate, applied here per focus-quality bucket instead).
-- SQL technique: LEFT JOIN + GROUP BY
-- Grain: one row per distinct focus_quality_name value.
--
-- Assumptions/limitations: this is a descriptive correlation, not a
-- causal claim, and it is NOT part of the CV-incorporation checksum
-- investigation -- docs/CHECKSUM_RESOLUTION.md already tested and
-- rejected focus_quality as an eligibility filter for that question
-- (excluding low-focus-quality detections moves the overall percentage
-- further from, not closer to, the ~81% target). This query exists to
-- surface the correlation itself as an operational insight, independent
-- of that closed investigation.
-- =========================================================================

SELECT
    cd.focus_quality_name,
    COUNT(*) AS total_detections,
    COUNT(l.detection_id) AS incorporated_detections,
    ROUND(100.0 * COUNT(l.detection_id) / COUNT(*), 2) AS incorporation_pct
FROM cv_detections cd
LEFT JOIN cv_detection_track_links l ON l.detection_id = cd.detection_id
GROUP BY cd.focus_quality_name
ORDER BY incorporation_pct DESC;
