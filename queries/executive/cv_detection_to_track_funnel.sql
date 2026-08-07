-- =========================================================================
-- CV detection-to-track funnel
--
-- Audience: Executive / Program Leadership
-- Question: Of everything the camera detected, how much became a
--           persistent tracked object, and how concentrated is that
--           outcome across the tracks that exist?
-- Decision supported: Whether camera coverage should be expanded,
--                      tuned, or left as-is -- a low
--                      detections-per-track ratio suggests either
--                      excellent 1:1 tracking or a tracker that never
--                      consolidates repeat sightings; a high ratio
--                      suggests a small number of persistent, heavily
--                      re-observed objects.
-- Why it matters: a single incorporation percentage
-- (cv_incorporation_summary.sql) hides *how* that percentage is
-- distributed -- this funnel shows the same detections narrowing down
-- through each stage of the CV pipeline's own data model.
--
-- Tables involved: cv_detections, cv_detection_track_links, cv_tracks
-- Join path: cv_detections -> cv_detection_track_links -> cv_tracks
--            (the full CV-side identity chain: raw detection event ->
--            deduplicated detection/track association -> persistent
--            track identity). This chain only exists because the
--            schema keeps these three grains in three separate tables
--            (rule 6, docs/DATABASE_DESIGN.md Section 4) -- a single
--            flat table would have to pick one grain and either
--            duplicate or discard the others.
-- SQL technique: correlated scalar subqueries at three distinct grains
-- Grain: one row (a single funnel summary).
--
-- Assumptions/limitations: "avg_detections_per_track" divides
-- incorporated detections by *tracks that received at least one*, not
-- by all 17 persistent tracks -- every one of the 17 CV tracks in this
-- file did receive at least one detection (CONFIRMED, Stage 3), so the
-- two denominators happen to coincide here, but this is a Stage 3
-- fact, not a query guarantee.
-- =========================================================================

SELECT
    (SELECT COUNT(*) FROM cv_detections) AS total_detections,
    (SELECT COUNT(DISTINCT detection_id) FROM cv_detection_track_links) AS incorporated_detections,
    (SELECT COUNT(DISTINCT track_id) FROM cv_detection_track_links) AS tracks_receiving_detections,
    (SELECT COUNT(*) FROM cv_tracks) AS total_persistent_tracks,
    ROUND(
        CAST((SELECT COUNT(DISTINCT detection_id) FROM cv_detection_track_links) AS REAL)
        / (SELECT COUNT(DISTINCT track_id) FROM cv_detection_track_links),
        1
    ) AS avg_incorporated_detections_per_track;
