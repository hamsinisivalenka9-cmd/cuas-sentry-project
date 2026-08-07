-- =========================================================================
-- CUAS Sentry -- SQLite schema (Stage 6 implementation)
--
-- Source of truth for every table, column, primary key, foreign key, and
-- UNIQUE constraint in this file: docs/DATABASE_DESIGN.md (Stage 4,
-- reviewed in Stage 5A per docs/SCHEMA_REVIEW.md). Nothing here redesigns
-- the reviewed schema -- this file is a direct SQL translation of it.
--
-- This file creates TABLES ONLY (11 reviewed analytical tables, plus one
-- small implementation-layer table, schema_version, that is not part of
-- the reviewed analytical schema -- see its own comment below).
-- Indexes live in sql/indexes.sql. Views live in sql/views.sql. This file
-- does not insert any data and does not implement ETL.
--
-- Idempotent: every statement uses IF NOT EXISTS, so running this file
-- against an already-initialized database is safe and makes no changes.
--
-- Foreign-key enforcement (PRAGMA foreign_keys = ON) is a per-connection
-- SQLite setting, not something a schema file can turn on for future
-- connections -- the caller (src/cuas_etl/database.py) sets it on every
-- connection it opens, before running this file.
-- =========================================================================

BEGIN TRANSACTION;

-- -------------------------------------------------------------------------
-- schema_version: implementation-layer metadata, NOT one of the 10
-- reviewed analytical tables in docs/TABLE_GRAIN.md. Records which schema
-- version(s) have been applied to this database file, so a caller can
-- confirm initialization happened and confidently re-run it without
-- guessing. One row is inserted per distinct version ever applied (see
-- src/cuas_etl/database.py); this table is never queried by analytical
-- SQL.
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_version (
    version         INTEGER NOT NULL PRIMARY KEY,
    applied_at_utc  TEXT NOT NULL,
    description     TEXT NOT NULL
);

-- -------------------------------------------------------------------------
-- 1. source_messages
-- Grain: one row = one raw MCAP message, from any of the four topics
-- (cv_detections, cv_tracks, radar_detections, track_states).
-- This is the envelope/provenance table every other table ultimately
-- traces back to via source_message_id, preserving log_time and
-- publish_time in nanoseconds (CLAUDE.md rule 5).
--
-- Primary key: source_message_id, a generated surrogate. Stage 3
-- (docs/KEY_ANALYSIS.md) tested every plausible natural/composite key
-- (topic+sequence, channel_id+sequence, each plus log_time) across the
-- full 57,266-message file and found none collision-free -- the best
-- natural combination reached only 52,890 of 57,266 distinct values.
-- `sequence` is preserved for provenance but is CONFIRMED degenerate
-- (collapses to 4 distinct values file-wide) and must never be treated
-- as unique or used for ordering.
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS source_messages (
    source_message_id  INTEGER NOT NULL PRIMARY KEY,
    channel_id          INTEGER NOT NULL,
    topic                TEXT NOT NULL,
    schema_id            INTEGER NOT NULL,
    sequence             INTEGER NOT NULL,
    log_time_ns          INTEGER NOT NULL,
    publish_time_ns      INTEGER NOT NULL
);

-- -------------------------------------------------------------------------
-- 2. cv_detections
-- Grain: one row = one individual CV (camera) detection event.
-- Source: cv_detections topic, CVDetectionFrame.detections[].
--
-- Primary key: detection_id itself (a genuine CONFIRMED natural key --
-- Stage 3 found it 100% unique across all 1,911 detections in the file).
-- No surrogate is added on top; rule 7 says use keys only when justified,
-- and a clean natural key removes the justification for a surrogate.
-- detection_uid is also 100% unique and kept as a UNIQUE column for
-- provenance, not as the PK, since detection_id is the message's native
-- numeric identity.
--
-- FOREIGN KEY (source_message_id): every detection traces back to the
-- exact raw MCAP message it was decoded from.
--
-- parent_object_detection_id is a candidate self-reference
-- (CVDetection.parent_object_detection_id) that Stage 3 confirmed has
-- ZERO populated occurrences in this file and only a "weak_heuristic"
-- relationship verdict -- it is intentionally NOT declared as a foreign
-- key (docs/DATABASE_DESIGN.md Section 6). Enforcing it would encode a
-- relationship the evidence does not support.
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cv_detections (
    detection_id                 INTEGER NOT NULL PRIMARY KEY,
    detection_uid                 TEXT NOT NULL,
    source_message_id             INTEGER NOT NULL,
    capture_time_ns                INTEGER,
    class_name                     TEXT,
    object_class_raw               INTEGER,
    object_class_name              TEXT,
    bbox_left                      REAL,
    bbox_top                       REAL,
    bbox_right                     REAL,
    bbox_bottom                    REAL,
    score                          REAL,
    semantic_confidence_raw        INTEGER,
    semantic_confidence_name       TEXT,
    focus_quality_raw              INTEGER,
    focus_quality_name             TEXT,
    focus_score                    REAL,
    sharpness                      REAL,
    detector_index                 INTEGER,
    disposition_raw                INTEGER,
    disposition_name               TEXT,
    motion_state_raw               INTEGER,
    motion_state_name              TEXT,
    -- Candidate self-reference, intentionally NOT a foreign key -- see
    -- table comment above (0 populated occurrences, Stage 3).
    parent_object_detection_id     INTEGER,
    UNIQUE (detection_uid),
    FOREIGN KEY (source_message_id) REFERENCES source_messages (source_message_id)
);

-- -------------------------------------------------------------------------
-- 3. cv_tracks
-- Grain: one row = one persistent CV track identity -- the real-world
-- tracked object itself, not any single observation of it.
-- Source: derived from the DISTINCT values of
-- CVTrackFrame.tracks[].track_id (not a 1:1 protobuf structure).
--
-- Primary key: track_id, a CONFIRMED natural key at this grain (17
-- distinct values, Stage 3) FOR THIS FILE -- this uniqueness is a
-- property of the observed data, not a constraint the protobuf schema
-- itself enforces (docs/SCHEMA_REVIEW.md finding F8).
--
-- This table has no foreign keys (it is the root of the CV persistent-
-- entity relationships) and is referenced by cv_track_states and
-- cv_detection_track_links.
--
-- Deliberately holds ONLY the identity column -- first/last-observed
-- timestamps and duration are derived via the view v_cv_track_summary
-- (sql/views.sql), not stored here, so they can never go stale.
--
-- LOADING ORDER NOTE: this table must be fully populated by a complete
-- upfront scan of the source file before any cv_track_states row is
-- inserted (docs/SCHEMA_REVIEW.md finding F2) -- see
-- docs/DATABASE_DESIGN.md Section 5.12. This is an ETL concern, not a
-- schema concern, and is documented here for traceability only.
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cv_tracks (
    track_id  INTEGER NOT NULL PRIMARY KEY
);

-- -------------------------------------------------------------------------
-- 4. cv_track_states
-- Grain: one row = one CV track's state as restated within one
-- cv_tracks batch message -- i.e. one track's appearance in one frame.
-- This is explicitly NOT the persistent track (that's cv_tracks, 17
-- rows) -- it is every restatement of that track across every frame it
-- appeared in (9,496 rows).
-- Source: cv_tracks topic, CVTrackFrame.tracks[].
--
-- Primary key: cv_track_state_id, a surrogate. The natural composite
-- (source_message_id, track_id) is CONFIRMED collision-free in this file
-- (Stage 2: zero within-message duplicate track_id values), but per
-- Stage 3's own general guidance a surrogate is the safer choice, so a
-- future file that violates this composite uniqueness fails a catchable
-- UNIQUE constraint rather than being un-insertable at the PK level.
--
-- FOREIGN KEY (source_message_id): traces this state back to its raw
-- message. FOREIGN KEY (track_id): ties this state to its persistent
-- track identity in cv_tracks.
--
-- last_associated_detection_id is raw provenance (the value
-- cv_detection_track_links is derived from) and is INTENTIONALLY NOT a
-- foreign key here (docs/SCHEMA_REVIEW.md finding F1): Stage 3 confirmed
-- 4 of its observed values reference a detection_id that does not exist
-- in cv_detections. cv_detection_track_links filters those 4 out before
-- insertion; this raw column must accept all observed values, including
-- the orphans, or 4 otherwise-valid track-state rows would be rejected.
--
-- parent_object_track_id is a candidate self-reference to cv_tracks that
-- Stage 3 rated only "weak_heuristic" with ZERO populated occurrences in
-- this file -- intentionally NOT a foreign key (Section 6 of the design).
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cv_track_states (
    cv_track_state_id              INTEGER NOT NULL PRIMARY KEY,
    source_message_id               INTEGER NOT NULL,
    track_id                        INTEGER NOT NULL,
    log_time_ns                     INTEGER NOT NULL,
    track_age                       INTEGER,
    status_raw                      INTEGER,
    status_name                     TEXT,
    status_code_raw                 INTEGER,
    status_code_name                TEXT,
    object_class_raw                INTEGER,
    object_class_name               TEXT,
    class_name                      TEXT,
    bbox_left                       REAL,
    bbox_top                        REAL,
    bbox_right                      REAL,
    bbox_bottom                     REAL,
    -- Raw provenance only -- NOT FK-enforced, see table comment above
    -- (docs/SCHEMA_REVIEW.md finding F1; 4 known orphaned values).
    last_associated_detection_id    INTEGER,
    num_detection_associations      INTEGER,
    object_class_confidence         REAL,
    score                           REAL,
    disposition_raw                 INTEGER,
    disposition_name                TEXT,
    motion_state_raw                INTEGER,
    motion_state_name               TEXT,
    is_manual                       INTEGER,
    -- Candidate self-reference, intentionally NOT a foreign key -- see
    -- table comment above (weak_heuristic, 0 populated, Stage 3).
    parent_object_track_id          INTEGER,
    capture_time_ns                 INTEGER,
    UNIQUE (source_message_id, track_id),
    FOREIGN KEY (source_message_id) REFERENCES source_messages (source_message_id),
    FOREIGN KEY (track_id) REFERENCES cv_tracks (track_id)
);

-- One row per CVTrack.class_distribution[] entry for one CV track state.
-- source_order is the zero-based protobuf repeated-field position; it
-- deliberately preserves both ordering and duplicate classifications.
CREATE TABLE IF NOT EXISTS cv_track_class_distribution (
    cv_track_class_distribution_id  INTEGER NOT NULL PRIMARY KEY,
    cv_track_state_id                INTEGER NOT NULL,
    class_raw                        INTEGER NOT NULL,
    class_name                       TEXT,
    probability_score                REAL NOT NULL,
    source_order                     INTEGER NOT NULL,
    UNIQUE (cv_track_state_id, source_order),
    FOREIGN KEY (cv_track_state_id) REFERENCES cv_track_states (cv_track_state_id)
);

-- -------------------------------------------------------------------------
-- 5. cv_detection_track_links
-- Grain: one row = one DISTINCT (detection, track) pairing ever observed
-- -- deduplicated across every track update that restates the same
-- association. This is a derived bridge table (many-to-many between
-- cv_detections and cv_tracks), not a direct 1:1 protobuf structure.
-- Source: derived from cv_tracks.tracks[].track_id paired with
-- cv_tracks.tracks[].last_associated_detection_id, deduplicated by ETL.
--
-- Primary key: composite (detection_id, track_id). Nothing else in the
-- schema needs to reference an individual link row, so a surrogate key
-- would add overhead with no benefit -- the composite PK IS the natural
-- key here, and also serves as the table's only UNIQUE constraint.
--
-- FOREIGN KEY (detection_id) -> cv_detections, FOREIGN KEY (track_id) ->
-- cv_tracks: both real, enforced relationships. Because these ARE
-- enforced, the ETL cleaning rule (docs/DATABASE_DESIGN.md Section 5.5)
-- excludes the 4 CONFIRMED orphaned references (a last_associated_
-- detection_id with no matching cv_detections row) from this table
-- before insertion, recording them in data_quality_issues instead of
-- silently discarding them or breaking referential integrity.
--
-- IMPORTANT CAVEAT (not a constraint, a documentation note): this
-- table's row count is NOT validated as "the" answer to CLAUDE.md's
-- ~81% CV-incorporation question -- see docs/DATABASE_DESIGN.md
-- Section 2 (unresolved discrepancy; observed data supports ~97.8%-
-- 99.9%, not ~81%).
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cv_detection_track_links (
    detection_id                  INTEGER NOT NULL,
    track_id                       INTEGER NOT NULL,
    first_observed_log_time_ns     INTEGER,
    PRIMARY KEY (detection_id, track_id),
    FOREIGN KEY (detection_id) REFERENCES cv_detections (detection_id),
    FOREIGN KEY (track_id) REFERENCES cv_tracks (track_id)
);

-- -------------------------------------------------------------------------
-- 6. radar_detections
-- Grain: one row = one individual radar detection reading, including any
-- cluster-grouped sub-detections (preserved as compact JSON on the same
-- row, not as separate linked rows -- see cluster_json below).
-- Source: radar_detections topic, RadarFrame.detections[].
--
-- Primary key: radar_detection_id, a surrogate. CONFIRMED --
-- RadarDetection has no identifier field of any kind on the protobuf
-- message itself, so no natural key is possible.
--
-- FOREIGN KEY (source_message_id): traces this reading back to its raw
-- message.
--
-- track_id is a raw string, deliberately NOT a foreign key to anything.
-- Stage 3 CONFIRMED zero observed value overlap between this field and
-- every CV/fused track_id-family field, including the one pairing with
-- matching protobuf types -- these are different, unrelated identifier
-- namespaces despite the shared field name (docs/DATABASE_DESIGN.md
-- Section 6). Joining on this column would be an unjustified,
-- name-based assumption the evidence explicitly rejects.
--
-- cluster_json preserves RadarDetection.cluster[] (a self-referential
-- repeated field). No self-referencing foreign key is created: the
-- field is CONFIRMED always empty in this file, and RadarDetection has
-- no identifier field to build a stable self-reference from even if it
-- were populated.
--
-- Several columns (range, range_rate, snr, filter_type,
-- estimated_width_meters, is_marked, object_type_class, object_class)
-- are CONFIRMED constant or empty across every row in this file
-- (docs/DATABASE_DESIGN.md Section 5.6 / docs/SCHEMA_REVIEW.md finding
-- F4) -- kept nullable per CLAUDE.md rule 12 rather than dropped, since
-- a future recording could populate them. azimuth_rad/elevation_rad were
-- renamed from azimuth/elevation and CONFIRMED to be in radians (not
-- degrees) from their observed value ranges (Schema Review finding F4).
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS radar_detections (
    radar_detection_id            INTEGER NOT NULL PRIMARY KEY,
    source_message_id              INTEGER NOT NULL,
    capture_time_ns                 INTEGER,
    "range"                         REAL,
    azimuth_rad                     REAL,
    elevation_rad                   REAL,
    range_rate                      REAL,
    return_strength                 REAL,
    snr                             REAL,
    -- Deliberately NOT a foreign key -- see table comment above
    -- (Stage 3: zero overlap with every other track_id-family field).
    track_id                        TEXT,
    object_type_class_raw           INTEGER,
    object_type_class_name          TEXT,
    object_class_raw                INTEGER,
    object_class_name               TEXT,
    filter_type_raw                 INTEGER,
    filter_type_name                TEXT,
    azimuth_sigma                   REAL,
    elevation_sigma                 REAL,
    range_sigma                     REAL,
    range_rate_sigma                REAL,
    estimated_width_meters          REAL,
    is_marked                       INTEGER,
    cluster_json                    TEXT,
    FOREIGN KEY (source_message_id) REFERENCES source_messages (source_message_id)
);

-- -------------------------------------------------------------------------
-- 7. fused_tracks
-- Grain: one row = one persistent fused-track identity -- the
-- tower/fusion system's tracked object, independent of how many state
-- updates it received.
-- Source: track_states topic, derived from the DISTINCT values of
-- TrackState.track_id2 (the CONFIRMED-active string identifier; paired
-- 1:1 in this file with the legacy TrackState.track_id, uint64).
--
-- Primary key: fused_track_id (= track_id2), a CONFIRMED natural key at
-- this grain (103 distinct values, Stage 3) FOR THIS FILE -- as with
-- cv_tracks.track_id, this uniqueness is a property of the observed
-- data, not protobuf-enforced (docs/SCHEMA_REVIEW.md finding F8).
--
-- legacy_track_id is the paired legacy uint64 identifier, kept as a
-- plain provenance column (not UNIQUE -- its 1:1 pairing was observed
-- but not stress-tested the way fused_track_id was). It was NOT chosen
-- as the primary key because Stage 2 found the numeric "legacy" half of
-- this kind of field pair is generally the less-trustworthy one project-
-- wide (e.g. asset_id vs asset_id2).
--
-- This table has no foreign keys and is referenced by fused_track_states.
-- Deliberately holds ONLY identity + one stable provenance attribute --
-- first/last-observed timestamps and duration are derived via the view
-- v_fused_track_summary (sql/views.sql), not stored here.
--
-- LOADING ORDER NOTE: same complete-upfront-scan requirement as
-- cv_tracks (docs/SCHEMA_REVIEW.md finding F2) -- an ETL concern,
-- documented here for traceability only.
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fused_tracks (
    fused_track_id   TEXT NOT NULL PRIMARY KEY,
    legacy_track_id   INTEGER
);

-- -------------------------------------------------------------------------
-- 8. fused_track_states
-- Grain: one row = one fused-track state/update -- exactly one
-- track_states MCAP message. Unlike the CV topics, track_states is
-- CONFIRMED not batched (Stage 2), so this table maps one-to-one with
-- the raw messages on that topic (11,630 rows).
-- Source: track_states topic, the whole proto.tower.TrackState message.
--
-- Primary key: fused_track_state_id, a surrogate -- same reasoning as
-- cv_track_states: (fused_track_id, log_time_ns) is CONFIRMED
-- collision-free in this file, but a surrogate is the safer general
-- choice per Stage 3's own guidance.
--
-- FOREIGN KEY (source_message_id): traces this state back to its raw
-- message. FOREIGN KEY (fused_track_id): ties this state to its
-- persistent fused-track identity in fused_tracks.
--
-- object_class_raw/object_class_name use proto.tower.TrackObjectClass,
-- which CONFIRMED has no DRONE or AIRPLANE value at all
-- (docs/DATABASE_DESIGN.md Section 3) -- stored exactly as observed,
-- never mapped to an invented category.
--
-- object_class_confidence (docs/SCHEMA_REVIEW.md finding F5) is a native
-- protobuf field, CONFIRMED populated on all 11,630 rows -- added
-- directly from the schema review's investigation into the still-
-- unresolved classification question.
--
-- parent_track_id is CONFIRMED always empty across every row in this
-- file -- kept nullable per rule 12, not a foreign key (no evidence of a
-- real relationship to test).
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fused_track_states (
    fused_track_state_id           INTEGER NOT NULL PRIMARY KEY,
    source_message_id               INTEGER NOT NULL,
    fused_track_id                  TEXT NOT NULL,
    log_time_ns                     INTEGER NOT NULL,
    create_timestamp_ns             INTEGER,
    last_measurement_timestamp_ns   INTEGER,
    lla_lat                         REAL,
    lla_lon                         REAL,
    lla_alt                         REAL,
    track_quality                   INTEGER,
    object_class_raw                INTEGER,
    object_class_name               TEXT,
    disposition_raw                 INTEGER,
    disposition_name                TEXT,
    track_status_raw                INTEGER,
    track_status_name               TEXT,
    parent_track_id                 TEXT,
    object_class_confidence         REAL,
    UNIQUE (fused_track_id, log_time_ns),
    FOREIGN KEY (source_message_id) REFERENCES source_messages (source_message_id),
    FOREIGN KEY (fused_track_id) REFERENCES fused_tracks (fused_track_id)
);

-- -------------------------------------------------------------------------
-- 9. fused_track_measurements
-- Grain: one row = one sensor measurement contributing to one
-- fused-track state.
-- Source: track_states topic, TrackState.measurements[]
-- (proto.tower.MeasurementAssociation).
--
-- Primary key: fused_track_measurement_id, a surrogate. CONFIRMED --
-- MeasurementAssociation has no identifier field of its own, and
-- asset_id2 alone is not unique per state (many measurements can share
-- the same sensor within one state).
--
-- FOREIGN KEY (fused_track_state_id): ties each measurement to the
-- fused-track state row it contributed to.
--
-- detection_ids_json preserves TrackState.measurements[].detection_ids[]
-- (a repeated string field, 2 levels of nesting deep) as compact JSON
-- rather than an 11th bridge table (docs/DATABASE_DESIGN.md Section 5.9,
-- "Issue 4" decision) -- none of the 6 required analytical queries need
-- a relational join on these ids. The legacy numeric asset_id is
-- deliberately omitted as a column entirely (CONFIRMED always empty,
-- Stage 2) -- unlike fused_tracks.legacy_track_id, this is high-volume,
-- per-row noise rather than a central entity-identity attribute.
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fused_track_measurements (
    fused_track_measurement_id  INTEGER NOT NULL PRIMARY KEY,
    fused_track_state_id         INTEGER NOT NULL,
    measurement_timestamp_ns     INTEGER,
    asset_id2                    TEXT,
    sensor_id_raw                 INTEGER,
    sensor_id_name                TEXT,
    frame_counter                 INTEGER,
    sensor_index                  INTEGER,
    detection_ids_json            TEXT,
    FOREIGN KEY (fused_track_state_id) REFERENCES fused_track_states (fused_track_state_id)
);

-- -------------------------------------------------------------------------
-- 10. data_quality_issues
-- Grain: one row = one detected data-quality finding, generated by ETL
-- validation logic -- NOT sourced from any protobuf field.
-- Source: none (ETL-generated); references evidence from Stage 2/3/4/5A
-- (for example, the 4 CONFIRMED orphaned detection references excluded
-- from cv_detection_track_links -- see that table's comment above).
--
-- Primary key: issue_id, a surrogate. Issues are ETL-generated events,
-- not entities with an inherent identity, so no natural key exists.
--
-- Deliberately has NO foreign keys. related_table/related_id are a
-- loose, polymorphic reference (they may point to rows in different
-- tables depending on issue_type) and cannot be a single real foreign
-- key without over-constraining the design
-- (docs/DATABASE_DESIGN.md Section 5.10).
--
-- CHECK (severity IN (...)): the only CHECK constraint in this schema.
-- It constrains an ETL-internal vocabulary this project defines itself
-- (not an assumption about source-data ranges), so it is justified
-- differently than a source-data CHECK would need to be.
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_quality_issues (
    issue_id          INTEGER NOT NULL PRIMARY KEY,
    issue_type         TEXT NOT NULL,
    severity            TEXT NOT NULL,
    related_table        TEXT,
    related_id            TEXT,
    description           TEXT NOT NULL,
    detected_at_utc        TEXT NOT NULL,
    CHECK (severity IN ('info', 'warning', 'error'))
);

COMMIT;
