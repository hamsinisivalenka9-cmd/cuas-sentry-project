# Entity-Relationship Diagram

Stage 4 deliverable, updated in Stage 5A (`docs/architecture/SCHEMA_REVIEW.md`): two
columns added (`cv_track_states.object_class_confidence`,
`fused_track_states.object_class_confidence`), two radar columns renamed
(`azimuth`→`azimuth_rad`, `elevation`→`elevation_rad`) for unit clarity.
No table, primary key, foreign key, or relationship line changed. Companion
diagram to `docs/architecture/DATABASE_DESIGN.md` (full specification) and
`docs/architecture/TABLE_GRAIN.md` (grain reference). Table names, primary keys, and
foreign keys below are copied exactly from `docs/architecture/DATABASE_DESIGN.md`
Section 5 — see that document for full column lists, nullability,
indexes, and the reasoning behind every relationship (including the ones
deliberately **not** drawn here).

```mermaid
erDiagram
    source_messages {
        INTEGER source_message_id PK
        INTEGER channel_id
        TEXT topic
        INTEGER schema_id
        INTEGER sequence
        INTEGER log_time_ns
        INTEGER publish_time_ns
    }

    cv_detections {
        INTEGER detection_id PK
        TEXT detection_uid UK
        INTEGER source_message_id FK
        INTEGER parent_object_detection_id "unenforced self-ref"
    }

    cv_tracks {
        INTEGER track_id PK
    }

    cv_track_states {
        INTEGER cv_track_state_id PK
        INTEGER source_message_id FK
        INTEGER track_id FK
        INTEGER last_associated_detection_id "raw provenance, NOT FK - see note"
        INTEGER num_detection_associations
        REAL object_class_confidence "added Stage 5A, F5"
        INTEGER parent_object_track_id "unenforced self-ref"
    }
    cv_track_class_distribution {
        INTEGER cv_track_class_distribution_id PK
        INTEGER cv_track_state_id FK
        INTEGER class_raw
        TEXT class_name
        REAL probability_score
        INTEGER source_order
    }

    cv_detection_track_links {
        INTEGER detection_id PK_FK
        INTEGER track_id PK_FK
        INTEGER first_observed_log_time_ns
    }

    radar_detections {
        INTEGER radar_detection_id PK
        INTEGER source_message_id FK
        REAL azimuth_rad "renamed Stage 5A, F4 - confirmed radians"
        REAL elevation_rad "renamed Stage 5A, F4 - confirmed radians"
        TEXT track_id "not FK - rejected namespace, Stage 3"
        TEXT cluster_json "not a self-FK - no id field exists"
    }

    fused_tracks {
        TEXT fused_track_id PK
        INTEGER legacy_track_id
    }

    fused_track_states {
        INTEGER fused_track_state_id PK
        INTEGER source_message_id FK
        TEXT fused_track_id FK
        INTEGER log_time_ns
        INTEGER object_class_raw "no DRONE/AIRPLANE value exists"
        REAL object_class_confidence "added Stage 5A, F5"
    }

    fused_track_measurements {
        INTEGER fused_track_measurement_id PK
        INTEGER fused_track_state_id FK
        TEXT detection_ids_json "JSON, not a bridge table"
    }

    data_quality_issues {
        INTEGER issue_id PK
        TEXT issue_type
        TEXT severity
        TEXT related_table "loose reference, not FK"
        TEXT related_id "loose reference, not FK"
    }

    source_messages ||--o{ cv_detections : "one message, many detections"
    source_messages ||--o{ cv_track_states : "one message, many track-states"
    source_messages ||--o{ radar_detections : "one message, many detections"
    source_messages ||--o{ fused_track_states : "one message, one state (1:1 in practice)"

    cv_tracks ||--o{ cv_track_states : "one track, many restatements"
    cv_track_states ||--|{ cv_track_class_distribution : "one state, ordered class candidates"
    cv_tracks ||--o{ cv_detection_track_links : "one track, many linked detections"
    cv_detections ||--o{ cv_detection_track_links : "one detection, at most one link (Section below)"

    fused_tracks ||--o{ fused_track_states : "one track, many state updates"
    fused_track_states ||--o{ fused_track_measurements : "one state, many measurements"
```

---

## Reading this diagram

- **PK** = primary key. **FK** = foreign key. **UK** = unique key
  (non-primary). **PK_FK** = part of a composite primary key that is also
  a foreign key (`cv_detection_track_links`).
- Quoted labels on some columns and relationships call out places where
  the obvious ER interpretation would be wrong — read them before
  assuming a line means "enforced foreign key."
- `data_quality_issues` has **no relationship lines** to any other table.
  This is deliberate: its `related_table`/`related_id` columns are a
  loose, polymorphic reference (they can point to rows in *different*
  tables depending on `issue_type`) and are intentionally not a real
  foreign key — see `docs/architecture/DATABASE_DESIGN.md` Section 5.10.
- `cv_track_states.last_associated_detection_id` has **no relationship
  line** to `cv_detections`, deliberately (`docs/architecture/SCHEMA_REVIEW.md`
  finding F1) — only the deduplicated `cv_detection_track_links` bridge
  table enforces that relationship, after filtering the 4 confirmed
  orphaned values; enforcing it on this raw column too would reject 4
  otherwise-valid rows.
- The `cv_tracks ||--o{ cv_track_states` and `fused_tracks ||--o{
  fused_track_states` lines both carry a loading-order implication not
  visible in the diagram itself: both parent tables must be **fully**
  populated by an upfront scan before any child row referencing them is
  inserted — see `docs/architecture/DATABASE_DESIGN.md` Section 5.12
  (`docs/architecture/SCHEMA_REVIEW.md` finding F2).

## Cardinalities, stated precisely

| Relationship | Cardinality | Note |
|---|---|---|
| `source_messages` → `cv_detections` | 1 : many | one batch message contains many detections |
| `source_messages` → `cv_track_states` | 1 : many | one batch message contains many track restatements |
| `source_messages` → `radar_detections` | 1 : many | one batch message contains many radar readings |
| `source_messages` → `fused_track_states` | 1 : many (0 or 1 in practice) | `track_states` is confirmed *not* batched (Stage 2) — every real message produces exactly one state row, but the FK's cardinality is drawn as 1:many for schema consistency across all four topics sharing one envelope table |
| `cv_tracks` → `cv_track_states` | 1 : many | a persistent track (17 total) is restated across up to 1,676 state rows |
| `cv_tracks` → `cv_detection_track_links` | 1 : many | a track can be linked to many distinct detections |
| `cv_detections` → `cv_detection_track_links` | 1 : 0 or 1 (observed) | CONFIRMED (Stage 3/4): zero detections in this file are linked to more than one distinct track — see the note below |
| `fused_tracks` → `fused_track_states` | 1 : many | a persistent fused track (103 total) receives up to 521 state updates |
| `fused_track_states` → `fused_track_measurements` | 1 : many | one state update can have several contributing sensor measurements |

**On the `cv_detections` ↔ `cv_detection_track_links` cardinality:** the
schema's foreign key allows a detection to appear in more than one link
row (a real many-to-many is representable), but the *observed data*
(Stage 3, re-confirmed Stage 4) shows every one of the 1,868 linked
detections maps to exactly one track — zero conflicts. The Mermaid diagram
draws the general `||--o{` form because the schema does not forbid
multiple links; it is not literally `||--o|` (one-to-zero-or-one), which
would over-claim a constraint the data merely happens to satisfy so far.
See `docs/architecture/DATABASE_DESIGN.md` Section 5.5.

## Relationships deliberately NOT drawn

These candidate relationships were investigated in Stage 3 and/or Stage 4
and explicitly **not** enforced — see `docs/architecture/DATABASE_DESIGN.md` Section 6
for the full evidence behind each:

- `cv_track_states.parent_object_track_id` → `cv_tracks.track_id`
  (weak_heuristic, 0 populated in this file)
- `cv_detections.parent_object_detection_id` → `cv_detections.detection_id`
  (0 populated occurrences)
- `radar_detections` cluster self-reference (always empty; no id field
  exists to reference even if populated)
- `radar_detections.track_id` ↔ `cv_tracks.track_id` /
  `fused_tracks.fused_track_id` (zero observed value overlap in every
  tested pairing, including the one pairing with matching protobuf types)
