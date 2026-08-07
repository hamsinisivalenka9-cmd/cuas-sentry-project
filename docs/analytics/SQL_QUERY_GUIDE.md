# SQL Query Guide

A practical guide to exploring `data/output/sentry.db` directly and to
running the Stage 7 analytical layer under `queries/`.

## Opening the database

```
sqlite3 data/output/sentry.db
```

This drops you into SQLite's interactive shell, pointed at the built
database. Nothing you type here can accidentally corrupt the source
MCAP file — `sqlite3` only ever touches the `.db` file you opened.

## Listing tables

```sql
.tables
```

Shows every table and view. As of schema version 2 that's 11 reviewed
analytical tables (`source_messages`, `cv_detections`, `cv_tracks`,
`cv_track_states`, `cv_track_class_distribution`,
`cv_detection_track_links`, `radar_detections`, `fused_tracks`,
`fused_track_states`, `fused_track_measurements`,
`data_quality_issues`), one implementation-metadata table
(`schema_version`), and 3 views (`v_cv_track_summary`,
`v_fused_track_summary`, `v_fused_track_type_basis`).

## Listing views

```sql
SELECT name FROM sqlite_master WHERE type = 'view';
```

Or just look at the `.tables` output above — SQLite lists views
alongside tables there without distinguishing them; the query above
filters to views only.

## Inspecting a table's or view's schema

```sql
.schema cv_detections
.schema v_fused_track_type_basis
```

Prints the exact `CREATE TABLE`/`CREATE VIEW` statement, including
every column, type, and constraint.

## Running an individual SQL file

Any file under `queries/` is a plain, complete SQL statement — pipe it
straight into `sqlite3`:

```
sqlite3 data/output/sentry.db < queries/executive/cv_incorporation_summary.sql
```

Add `-header -column` for readable aligned output:

```
sqlite3 -header -column data/output/sentry.db < queries/executive/recording_overview.sql
```

For a **parameterized** query (one whose SQL contains a `:name`
placeholder — currently `cv_track_history.sql` and
`fused_track_history.sql`), bind the parameter first with `.param set`:

```
sqlite3 data/output/sentry.db
.param set :track_id 81754
.read queries/operational/cv_track_history.sql
```

```
sqlite3 data/output/sentry.db
.param set :fused_track_id '25295F49158-7aa000016009'
.read queries/operational/fused_track_history.sql
```

(Note the quotes around the fused track id — it's a `TEXT` value, not
an integer, so it needs to be quoted in `.param set` exactly as it
would in any SQL string literal.)

## Using `scripts/run_analytics.py`

The recommended way to run these queries day to day — it discovers
every `.sql` file under `queries/` automatically, opens the database
**read-only** (a query that tried to write would fail at the SQLite
layer, not just by convention), and prints readable column-aligned
output.

```
# See every available query, grouped by audience category:
python scripts/run_analytics.py --list

# Run one query by its filename (without .sql):
python scripts/run_analytics.py --query cv_incorporation_summary

# Run every query in one category:
python scripts/run_analytics.py --category executive
python scripts/run_analytics.py --category operational
python scripts/run_analytics.py --category technical

# Run everything (the two parameterized queries will report a clean
# "requires parameter" error and a nonzero exit code if you don't
# supply --param — this is expected, not a bug):
python scripts/run_analytics.py --all

# Run a parameterized query:
python scripts/run_analytics.py --query cv_track_history --param track_id=81754
python scripts/run_analytics.py --query fused_track_history --param fused_track_id=25295F49158-7aa000016009

# Point at a different database file:
python scripts/run_analytics.py --list --db-path /path/to/other.db
```

Categories map directly to `queries/`' subdirectories:
`executive`, `operational`, `technical` — plus `general`, an automatic
category for any `.sql` file placed directly under `queries/` itself
rather than in one of the three subdirectories (currently just the
pre-existing `queries/fused_track_duration_by_type.sql`, kept in place
since existing tests and `docs/analytics/CHECKSUM_RESOLUTION.md` reference its
exact path).

## Safely modifying query parameters

Every parameterized query documents its required parameter(s) in its
own header comment (look for a `PARAMETERIZED QUERY --` line). To find
a real, valid value to substitute:

```sql
SELECT track_id FROM cv_tracks;          -- for :track_id
SELECT fused_track_id FROM fused_tracks; -- for :fused_track_id
```

Do not edit a `.sql` file to hardcode a specific id in place of the
`:name` placeholder if you plan to commit that change — that turns a
reusable query into a one-off. If you need a permanent "history for
track X" report, save the *output*, not a modified copy of the query.

## Important timestamp units

- `log_time_ns` and `publish_time_ns` (on `source_messages`, and
  denormalized onto every state table) are **nanoseconds since epoch**
  — confirmed directly, no conversion needed (CLAUDE.md rule 5).
- `capture_time_ns` (on `cv_detections`, `cv_track_states`,
  `radar_detections`) is also nanoseconds — converted at load time from
  a nested protobuf `Timestamp` (`seconds * 1e9 + nanos`).
- `create_timestamp_ns`, `last_measurement_timestamp_ns` (on
  `fused_track_states`) and `measurement_timestamp_ns` (on
  `fused_track_measurements`) are nanoseconds **in the database**, but
  the *source* protobuf fields are microseconds — a real unit bug found
  and fixed during Stage 6 (`docs/stages/STAGE_06_SUMMARY.txt`). If you ever
  add a new column from one of these same source fields, remember the
  ×1000 conversion; do not assume a plain `int64` timestamp field is
  automatically nanoseconds just because a sibling field is.
- To convert any `*_ns` column to seconds in a query: `column / 1e9`.
  Use `1e9` (a float literal), not `1000000000` — SQLite integer
  division would silently truncate instead of giving you a fractional
  second.

## Important table grains

Grain (what one row means) is documented in the header comment of every
table in `sql/schema.sql` and summarized in `docs/data/DATA_DICTIONARY.md`.
The two distinctions that most often trip up a new query author:

- **Identity vs. history.** `cv_tracks` (17 rows) and `fused_tracks`
  (103 rows) are *persistent identities* — one row per real-world
  tracked object. `cv_track_states` (9,496 rows) and
  `fused_track_states` (11,630 rows) are *history* — one row per
  restatement/update of that object. Never assume `COUNT(*)` on a
  states table tells you how many distinct objects exist — use
  `COUNT(DISTINCT track_id)` or the corresponding identity table
  instead.
- **CV and fused are unrelated identifier namespaces.** Do not join
  `cv_tracks`/`cv_track_states` to `fused_tracks`/`fused_track_states`
  on any track-id-shaped column — this was tested directly
  (`docs/data/KEY_ANALYSIS.md`) and found to have zero value overlap and
  incompatible types. See the note at the top of
  `docs/analytics/ANALYTICAL_INSIGHTS.md` for the full explanation.

## `sql/` vs. `queries/`

- **`sql/`** contains database-*definition* SQL: `schema.sql` (tables),
  `indexes.sql`, `views.sql`, `validation.sql`. These files are run by
  `src/cuas_etl/database.py` to build the database's structure. They
  never contain analytical questions, only structure and integrity
  checks.
- **`queries/`** contains reusable, read-only *analytical* SQL — the
  questions this database exists to answer. Organized into
  `executive/`, `operational/`, `technical/` by intended audience, plus
  one pre-existing file directly in `queries/` (see "Using
  scripts/run_analytics.py" above). Nothing under `queries/` is ever
  run automatically during a database build — you run these yourself,
  on demand, against an already-built database.
- **`scripts/`** contains Python programs that *execute or automate*
  work: `build_database.py` (runs the `sql/` files and loads data),
  `run_validation.py` (runs `sql/validation.sql` plus Python-side
  checks), and `run_analytics.py` (runs the `queries/` files).
