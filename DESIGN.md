# Design Overview

## What this project does

This project turns a raw sensor recording into something you can
actually query and explore. In plain terms, it:

- reads `data/input/sanitized.mcap`, a recording of counter-UAS
  (drone-detection) sensor messages
- decodes the protobuf messages inside it (camera detections, camera
  tracks, radar detections, and a multi-sensor "fused" tower track)
- transforms those messages into a clean, relational shape
- stores the result in a single SQLite database file
- validates that nothing was lost or corrupted along the way
- lets anyone answer real questions about the recording using plain
  SQL
- shows the same results in a small read-only Streamlit dashboard

## Architecture

```
sanitized.mcap
    |
    v
MCAP + Protobuf Reader   (src/cuas_etl/extract.py)
    |
    v
Transform / Normalize    (src/cuas_etl/transform.py)
    |
    v
SQLite Database          (data/output/sentry.db)
    |
    +--> SQL Queries       (queries/, scripts/run_analytics.py)
    +--> Validation / Tests (scripts/run_validation.py, tests/)
    +--> Streamlit Dashboard (dashboard/)
```

- **MCAP + Protobuf Reader** opens the recording and decodes each
  message using its protobuf schema — nothing is guessed or
  hand-parsed.
- **Transform / Normalize** turns decoded messages into rows for each
  table, resolving IDs, timestamps, and repeated/nested fields.
- **SQLite Database** is the single source of truth after loading —
  everything downstream reads from this one file.
- **SQL Queries / Validation & Tests / Dashboard** all read the same
  database independently; none of them re-derives data on their own.

## Why these technologies

**Python** — simple and well-supported for MCAP/protobuf processing;
the `mcap` and `mcap-protobuf-support` libraries do the decoding work
directly.

**SQLite** — a single-file relational database. No server to install
or manage, easy to hand to another engineer, and more than capable for
a recording of this size.

**pytest** — straightforward, widely known automated testing, used to
check the ETL, the schema, and the analytical queries.

**Streamlit** — a lightweight way to turn existing SQL results into a
browsable interface without building a separate frontend.

**Docker** — lets someone else run the exact same pipeline without
installing Python or any dependency themselves.

## Data model

The schema is split into several tables instead of one giant table
because the source data actually has different *grains* — different
things update at different rates and for different reasons:

- **detections** are individual sensor sightings — one row per camera
  frame or radar sweep that spotted something.
- **tracks** are persistent identities — a track exists once, even
  though many detections and updates belong to it over time.
- **track states** are updates to those identities over time — a
  track's position, classification, or status as of a given moment.
- **detection-track links** represent associations — which
  detections were actually incorporated into which track.
- **fused measurements** represent individual sensor contributions —
  which sensor (camera, radar, transponder) fed into a given fused
  track update.
- **source_messages** preserves provenance — every row traces back to
  the exact raw MCAP message (topic, timestamp, sequence) it came
  from.

Keeping these separate means a track's history isn't duplicated across
every detection, a detection isn't lost if it was never incorporated
into a track, and every derived row can always be traced back to the
raw message it came from. Column-by-column detail is in
[docs/data/DATA_DICTIONARY.md](docs/data/DATA_DICTIONARY.md).

## ETL flow

1. Read MCAP messages from `data/input/sanitized.mcap`.
2. Decode each one using its protobuf schema.
3. Capture source-message metadata (topic, timestamps, sequence) for
   every message, so every derived row can be traced back to it.
4. Create persistent track identities (CV tracks, fused tracks) first.
5. Load detections, track states, detection-track links, and fused
   measurements, which all reference those identities.
6. Record any data-quality issues found along the way (for example, a
   detection that was referenced but never actually loaded).
7. Validate the finished database.

Identities are loaded before the rows that depend on them so foreign
keys are always valid — nothing is inserted that points at a row that
doesn't exist yet.

## Analytical queries

Common analysis is available as plain SQL files under `queries/`, plus
a few reusable views, so nobody has to hand-write joins to answer a
routine question. They cover things like:

- CV detection incorporation (how many detections became tracks)
- CV track duration and history
- fused track duration, by sensor combination and by object type
- sensor utilization and contribution (including radar)
- data-quality summaries

Run them with `scripts/run_analytics.py` — see START_HERE.md for exact
commands. The two sample analytical questions from the assignment (CV
incorporation rate; Drone vs. Airplane average fused-track duration)
are answered directly from this data — the actual computed results,
the methodology, and the documented explanation for why they differ
from the assignment's approximate targets are in
[docs/analytics/CHECKSUM_RESOLUTION.md](docs/analytics/CHECKSUM_RESOLUTION.md).

## Testing and validation

- 274 automated tests (`pytest`), covering the ETL, the schema, the
  analytical queries, and the dashboard.
- `PRAGMA integrity_check` and `PRAGMA foreign_key_check` on the built
  database.
- A full pipeline validation pass (`scripts/run_validation.py`) —
  structural row counts, relational integrity, enum consistency, and a
  re-derivation of key results directly from the raw MCAP file, to
  confirm the database matches the source.

## Trade-offs

**SQLite vs. DuckDB** — SQLite was chosen for simplicity and
portability: it's a single file, needs no setup, and every engineer
already knows how to query it.

**Normalization vs. simplicity** — nested/repeated protobuf data was
split into child tables wherever a real relationship existed (tracks,
states, links, measurements), rather than flattened or dropped. Views
exist specifically so that everyday analyst SQL doesn't need to
re-derive those joins each time.

**Dashboard** — intentionally lightweight. The SQL and the data model
are the actual deliverable here; the dashboard is a thin, read-only
window onto them, not a product in its own right.

## Known limitations

- The CV-incorporation result (97.54%) does not match the assignment's
  ~81% approximate target. This was investigated; no alternative
  definition of "incorporated" reproduces ~81% against this specific
  source file. See `docs/analytics/CHECKSUM_RESOLUTION.md`.
- Drone/Airplane classification is inferred from sensor provenance
  (whether a fused track ever incorporated a transponder measurement),
  not a native object-class field — the source protobuf schema has no
  `DRONE`/`AIRPLANE` enum value.
- No linter or type-checker is configured; `pytest` is the only
  automated check.

## How to extend it

- **Another MCAP topic** — add a decoder call in
  `src/cuas_etl/extract.py`, a transform step in
  `src/cuas_etl/transform.py`, and a table in `sql/schema.sql`.
- **Another sensor type** — follow the same pattern as radar: a
  detections table keyed to `source_messages`, plus any
  fused-measurement rows that reference it.
- **Another relational table** — add it to `sql/schema.sql` with an
  explicit grain and foreign keys back to `source_messages` or the
  relevant track table, then load it in `src/cuas_etl/load.py` after
  the identity tables it depends on.
- **Another analytical query** — add a `.sql` file under the
  appropriate `queries/` subfolder; `scripts/run_analytics.py` and the
  dashboard's SQL Queries page both discover query files automatically.
