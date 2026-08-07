-- =========================================================================
-- CUAS Sentry -- secondary indexes (Stage 6 implementation)
--
-- Source of truth: docs/DATABASE_DESIGN.md Section 5 ("Recommended
-- indexes" per table), as corrected by docs/SCHEMA_REVIEW.md finding F3.
-- Requires sql/schema.sql to have already been run (every index here
-- targets a table created there).
--
-- SQLite automatically creates an index to enforce every PRIMARY KEY and
-- UNIQUE constraint -- those are NOT repeated here. Per requirement,
-- indexes already covered by a UNIQUE constraint are omitted entirely
-- (see the two "removed as redundant" notes below, both corrections from
-- the Stage 5A schema review).
--
-- Idempotent: every statement uses IF NOT EXISTS.
-- =========================================================================

BEGIN TRANSACTION;

-- -------------------------------------------------------------------------
-- source_messages
-- -------------------------------------------------------------------------

-- Supports "message counts by topic" and any query filtering to one topic.
CREATE INDEX IF NOT EXISTS idx_source_messages_topic
    ON source_messages (topic);

-- Supports time-range queries and track-history-over-time joins that
-- filter or order by log_time_ns.
CREATE INDEX IF NOT EXISTS idx_source_messages_log_time
    ON source_messages (log_time_ns);

-- -------------------------------------------------------------------------
-- cv_detections
-- -------------------------------------------------------------------------

-- Supports joining a detection back to its source message.
-- (Note: detection_uid already has an automatic index from its UNIQUE
-- constraint in schema.sql -- not repeated here.)
CREATE INDEX IF NOT EXISTS idx_cv_detections_source_message
    ON cv_detections (source_message_id);

-- Supports classification-distribution / classification-filtered queries.
CREATE INDEX IF NOT EXISTS idx_cv_detections_object_class
    ON cv_detections (object_class_raw);

-- -------------------------------------------------------------------------
-- cv_tracks: no secondary indexes. A 17-row identity table needs none
-- beyond its automatic PRIMARY KEY index.
-- -------------------------------------------------------------------------

-- -------------------------------------------------------------------------
-- cv_track_states
-- -------------------------------------------------------------------------

-- Supports "track history over time" and joins back to cv_tracks.
CREATE INDEX IF NOT EXISTS idx_cv_track_states_track_id
    ON cv_track_states (track_id);

-- Supports the CV detection-incorporation query (docs/DATABASE_DESIGN.md
-- Section 2) computed directly from this raw provenance column.
CREATE INDEX IF NOT EXISTS idx_cv_track_states_last_assoc_det
    ON cv_track_states (last_associated_detection_id);

-- Supports classification-distribution queries (docs/SCHEMA_REVIEW.md
-- findings F5/F6).
CREATE INDEX IF NOT EXISTS idx_cv_track_states_object_class
    ON cv_track_states (object_class_raw);

-- Supports state -> complete ordered class-distribution lookup. The
-- UNIQUE constraint already covers this access path, so no redundant
-- explicit index is needed on (cv_track_state_id, source_order).

-- REMOVED AS REDUNDANT (docs/SCHEMA_REVIEW.md finding F3):
-- idx_cv_track_states_source_message(source_message_id) was proposed in
-- the original Stage 4 design but is fully covered by the automatic
-- index SQLite creates for UNIQUE(source_message_id, track_id) in
-- schema.sql -- by the leftmost-prefix rule for multi-column indexes,
-- that index already serves any query filtering on source_message_id
-- alone. Creating a second, single-column index on the same leftmost
-- column would cost extra write time and storage for zero additional
-- query capability.

-- -------------------------------------------------------------------------
-- cv_detection_track_links
-- -------------------------------------------------------------------------

-- Supports reverse lookups ("which detections fed this track"). The
-- forward direction (detection_id -> track_id) is already served by the
-- table's composite PRIMARY KEY (detection_id, track_id), whose
-- automatic index has detection_id as its leftmost column -- not
-- repeated here.
CREATE INDEX IF NOT EXISTS idx_cv_detection_track_links_track
    ON cv_detection_track_links (track_id);

-- -------------------------------------------------------------------------
-- radar_detections
-- -------------------------------------------------------------------------

-- Supports joining a radar detection back to its source message.
CREATE INDEX IF NOT EXISTS idx_radar_detections_source_message
    ON radar_detections (source_message_id);

-- Supports radar-side grouping by track_id, despite track_id not being
-- FK-enforced (Stage 3: rejected cross-topic relationship) -- this is
-- still a useful grouping key within radar_detections alone.
CREATE INDEX IF NOT EXISTS idx_radar_detections_track_id
    ON radar_detections (track_id);

-- -------------------------------------------------------------------------
-- fused_tracks: no secondary indexes. A 103-row identity table needs none
-- beyond its automatic PRIMARY KEY index.
-- -------------------------------------------------------------------------

-- -------------------------------------------------------------------------
-- fused_track_states
-- -------------------------------------------------------------------------

-- Supports time-range queries and the v_fused_track_summary view's
-- MIN/MAX(log_time_ns) aggregation.
CREATE INDEX IF NOT EXISTS idx_fused_track_states_log_time
    ON fused_track_states (log_time_ns);

-- Supports joining a fused-track state back to its source message.
CREATE INDEX IF NOT EXISTS idx_fused_track_states_source_message
    ON fused_track_states (source_message_id);

-- Supports classification-distribution and classification-semantics
-- analysis (docs/SCHEMA_REVIEW.md findings F5/F6).
CREATE INDEX IF NOT EXISTS idx_fused_track_states_object_class
    ON fused_track_states (object_class_raw);

-- REMOVED AS REDUNDANT (docs/SCHEMA_REVIEW.md finding F3):
-- idx_fused_track_states_fused_track_id(fused_track_id) was proposed in
-- the original Stage 4 design but is fully covered by the automatic
-- index SQLite creates for UNIQUE(fused_track_id, log_time_ns) in
-- schema.sql, for the same leftmost-prefix reason as cv_track_states
-- above.

-- -------------------------------------------------------------------------
-- fused_track_measurements
-- -------------------------------------------------------------------------

-- Supports joining measurements back to their fused-track state.
CREATE INDEX IF NOT EXISTS idx_fused_track_measurements_state
    ON fused_track_measurements (fused_track_state_id);

-- Supports the "sensor contribution to fused tracks" required
-- analytical query (GROUP BY sensor_id_raw).
CREATE INDEX IF NOT EXISTS idx_fused_track_measurements_sensor
    ON fused_track_measurements (sensor_id_raw);

-- -------------------------------------------------------------------------
-- data_quality_issues
-- -------------------------------------------------------------------------

-- Supports filtering/grouping data-quality reports by issue type.
CREATE INDEX IF NOT EXISTS idx_data_quality_issues_type
    ON data_quality_issues (issue_type);

-- Supports filtering data-quality reports to a specific affected table.
CREATE INDEX IF NOT EXISTS idx_data_quality_issues_table
    ON data_quality_issues (related_table);

COMMIT;
