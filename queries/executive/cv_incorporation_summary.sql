-- =========================================================================
-- CV detection incorporation summary
--
-- Audience: Executive / Program Leadership
-- Question: What percentage of CV detections were incorporated into a
--           persistent CV track?
-- Decision supported: Whether the CV tracking pipeline's core
--                      effectiveness metric should be reported as-is,
--                      or whether it requires further engineering
--                      investigation before being presented externally.
-- Why it matters: this is one of the two headline checksum questions
-- this project was explicitly asked to answer (see
-- docs/CHECKSUM_RESOLUTION.md) -- it demonstrates whether raw sensor
-- output actually becomes a usable, persistent tracked object.
--
-- Tables involved: cv_detections, cv_detection_track_links
-- Join path: cv_detections -> cv_detection_track_links (the bridge
--            table that resolves the many-to-many relationship between
--            individual detection events and the persistent tracks
--            they were associated with -- this relationship could not
--            be expressed at all in a single denormalized table without
--            either duplicating every detection once per track update
--            that restated it, or collapsing the many-to-many
--            association down to a single value and losing it).
-- SQL technique: correlated scalar subqueries (numerator/denominator
--                each computed independently, then combined)
-- Grain: one row (a single summary statistic).
--
-- Numerator: COUNT(DISTINCT detection_id) in cv_detection_track_links --
-- every cv_detections row that appears at least once as a deduplicated
-- (detection, track) pairing derived from CVTrack.last_associated_
-- detection_id.
-- Denominator: COUNT(*) in cv_detections -- every individual
-- CVDetectionFrame.detections[] element in the source file.
--
-- THIS QUERY IS UNCHANGED FROM THE STAGE 6/6B EVIDENCE-SUPPORTED
-- CALCULATION -- do not alter it to chase the assignment's ~81%
-- target. Anduril reviewed the clarification request that accompanied
-- this figure and confirmed the interpretation is correct and no
-- further investigation is needed (see docs/CHECKSUM_RESOLUTION.md
-- Part B/C for the full exhaustive search that preceded that
-- clarification). The observed result is 97.54%, not ~81%; this is
-- reported as the evidence-supported fact, not adjusted to match.
-- =========================================================================

SELECT
    (SELECT COUNT(*) FROM cv_detections) AS total_cv_detections,
    (SELECT COUNT(DISTINCT detection_id) FROM cv_detection_track_links) AS incorporated_cv_detections,
    ROUND(
        100.0 * (SELECT COUNT(DISTINCT detection_id) FROM cv_detection_track_links)
        / (SELECT COUNT(*) FROM cv_detections),
        2
    ) AS incorporation_percentage;
