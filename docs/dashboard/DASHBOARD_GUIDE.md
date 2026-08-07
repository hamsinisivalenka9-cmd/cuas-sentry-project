# Dashboard Guide — Stage 8 (page structure and naming updated in Stage 9)

## Purpose

A Streamlit analytics console that visualizes and lets users explore
the completed CUAS Sentry pipeline: `data/input/sanitized.mcap` →
Python ETL → `data/output/sentry.db` (SQLite) → the reusable
`sql/`/`queries/` analytical layer. It is a **read-only presentation
layer** — it adds no new analytical logic; every number shown anywhere
in the dashboard is the direct output of an existing, already-tested
`.sql` file.

## Pages (Stage 9 naming)

Pages are organized by data domain, not by audience, so each page's
purpose is unambiguous from its name:

- **Overview** — system-wide counts and the two headline checksum results.
- **CV Detections** — individual camera detections and incorporation into tracks.
- **CV Tracks** — persistent camera-tracked objects and their state history.
- **Fused Tracks** — persistent fused (tower) tracked objects, sensor
  contributions, and classification stability.
- **Data Quality** — pipeline health and relational-integrity checks.
- **SQL Queries** — run the approved analytical queries or write and run
  your own read-only SQL.
- **Documentation** — an index of the project's design and analysis documents.

No "Radar" page exists: no query in the current library performs
radar-specific analysis (`radar_detections`' own row count already
appears on the Data Quality page's row-count reconciliation), so a
standalone Radar tab would have no real functionality behind it.

## Architecture

```
data/input/sanitized.mcap
    -> Python ETL (src/cuas_etl/)
    -> data/output/sentry.db  (SQLite)
    -> reusable SQL queries and views (sql/, queries/)
    -> dashboard/  (Streamlit, read-only)
```

Execution flow for every chart/table/KPI:

```
Streamlit page (dashboard/pages/*.py)
    -> dashboard/sql_loader.py  (discovers + executes the .sql file)
    -> queries/<category>/<name>.sql  (the actual analytical SQL, on disk)
    -> read-only SQLite connection (mode=ro + PRAGMA query_only)
    -> pandas.DataFrame
    -> dashboard/charts.py or dashboard/components/tables.py  (presentation only)
```

`dashboard/sql_loader.py` does not re-implement query discovery: it
imports `scripts/run_analytics.py`'s `QueryFile`/`discover_queries`/
`connect_read_only` directly (via `importlib`, the file has no
`__init__.py`), so the CLI runner and the dashboard always agree on
what queries exist and how to run them safely.

## Directory structure

```
dashboard/
    app.py                 # entry point: streamlit run dashboard/app.py
    database.py             # read-only connection, DB metadata, integrity checks
    sql_loader.py            # query discovery + execution -> DataFrame
    query_catalog.py          # presentation metadata (chart type, page placement)
    charts.py                  # generic Plotly chart builders (no query-specific logic)
    formatting.py                # number/percentage/status formatting
    constants.py                  # paths, labels, color palette
    sql_validator.py         # read-only SQL check for the SQL Queries page's ad-hoc editor
    components/
        __init__.py
        metrics.py                  # KPI card row
        tables.py                     # DataFrame table + CSV download
        status.py                      # pass/fail/warning banners
        query_details.py                # "source query" expander (SQL + metadata)
        sidebar.py                       # shared sidebar (added during implementation --
                                          # see "Deviations from the original file list" below)
    pages/
        1_Overview.py
        2_CV_Detections.py
        3_CV_Tracks.py
        4_Fused_Tracks.py
        5_Data_Quality.py
        6_SQL_Queries.py
        7_Documentation.py
```

### Deviations from the original file list

Two small additions were made during implementation, beyond the
originally proposed structure:

- `dashboard/__init__.py` and `dashboard/components/__init__.py` —
  required for `dashboard.*` imports to resolve as a proper Python
  package (needed by both `pytest` and `streamlit run`).
- `dashboard/components/sidebar.py` — Streamlit's multipage model runs
  each `pages/*.py` file as an independent script; the sidebar (project
  overview, database status, navigation) needed to live somewhere every
  page could import without re-triggering `app.py`'s own
  `st.set_page_config()` call. This is the smallest addition that keeps
  the sidebar consistent across all 8 scripts.

No analytical SQL logic was added anywhere — both additions are pure
UI/import plumbing.

## Dependencies

Added to `requirements.txt`: `streamlit==1.61.1`, `pandas==3.0.5`,
`plotly==6.9.0`. No ORM, no SQLAlchemy — the standard library `sqlite3`
module is sufficient and is all that's used.

## Database requirements

The dashboard reads `data/output/sentry.db`. If it doesn't exist, every
page shows a clear message with the exact build command rather than
attempting to build it automatically:

```
python scripts/build_database.py --rebuild
```

## Launch instructions

```bash
source .venv/bin/activate   # or your environment of choice
pip install -r requirements.txt
python scripts/build_database.py --rebuild   # if sentry.db doesn't exist yet
streamlit run dashboard/app.py
```

Streamlit will open the app in your browser (default `http://localhost:8501`)
and automatically discover the 7 pages under `dashboard/pages/`.

## Page descriptions

### Overview

KPI row (source messages, CV detections, persistent CV/fused tracks,
radar detections, CV incorporation %, Drone/Airplane mean duration,
data-quality issue count, recording duration) -> CV detection-to-track
funnel -> **Drone vs. Airplane duration** (the protected checksum
result, arithmetic mean primary, median supplementary, full caveat
text preserved) -> data-quality issue summary -> Key Findings
(narrative, sourced from `docs/analytics/ANALYTICAL_INSIGHTS.md`).

### CV Detections

CV incorporation summary (detail) -> detection-to-track funnel
(detail) -> focus quality vs. incorporation.

### CV Tracks

Longest-lived CV tracks -> CV track history (drill-down: table +
classification-confidence line chart) -> CV detection quality vs.
track persistence.

### Fused Tracks

Duration by inferred class (detail) -> longest-lived fused tracks ->
fused track history (drill-down: table + line chart, contributing
sensors shown) -> sensor contributions per fused track -> sensor
utilization summary -> classification changes over time ->
classification stability vs. measurement support -> multi-sensor vs.
single-sensor duration comparison -> duration by exact sensor
combination. A prominent callout states that CV and fused tracks are
never joined by ID (Stage 3 evidence).

### Data Quality

Database metadata (path, size, schema version, table/view/query
counts, SQLite version, live-computed source MCAP checksum) ->
integrity status (live `PRAGMA integrity_check` / `PRAGMA
foreign_key_check`, both read-only) -> optional "Run validation" button
(subprocess-invokes the unchanged `scripts/run_validation.py`) -> all 6
technical queries, each with a pass/fail status banner plus its table
-> data-quality issue summary.

### SQL Queries

Two sections on one page:

1. **Approved queries** — category filter -> query picker -> business
   question, SQL source, audience, parameters (only for the 2 queries
   that have real parameters) -> Run -> results table -> CSV download.
   Only executes the 22 approved files already on disk; never accepts
   arbitrary SQL text or a filesystem path.
2. **Query editor** — a free-text SQL box for read-only ad-hoc queries,
   with 8 named examples that prefill it. Every submission is checked
   by `dashboard/sql_validator.py` (single statement, must start with
   SELECT/WITH/EXPLAIN/PRAGMA, no forbidden write keyword anywhere in
   the statement including inside a comment) before execution, and
   results are capped at `DEFAULT_QUERY_ROW_LIMIT` (1,000) rows.

### Documentation

A plain index of file paths to the project's design and analysis
documents, grouped by topic. Reads no data from the database.

## Query-to-component mapping

See `docs/analytics/ANALYTICAL_INSIGHTS.md` for the full per-query business
detail, and `dashboard/query_catalog.py` for the machine-readable
mapping of each query to its recommended visualization(s) and home
page(s).

## Parameter handling

Only `cv_track_history.sql` (`:track_id`) and `fused_track_history.sql`
(`:fused_track_id`) accept parameters anywhere in the current query
library. `dashboard/sql_loader.run_query()`:

- Rejects an unknown query name (`QueryNotFoundError`).
- Rejects a missing required parameter (`MissingParameterError`).
- Rejects an unexpected parameter the query doesn't declare
  (`UnexpectedParameterError`).
- Never concatenates a value into SQL text — every parameter is passed
  through `sqlite3`'s native parameter binding.

The CV Tracks, Fused Tracks, and SQL Queries pages populate their track-ID
dropdowns from two small, non-analytical, hardcoded lookup queries in
`sql_loader.py` (`SELECT track_id FROM cv_tracks ORDER BY track_id` and
the `fused_tracks` equivalent) — these contain no joins or aggregation
and exist solely to give the dropdown real values; they are not a
substitute for, or duplicate of, any analytical query.

## Caching

- `st.cache_resource` — SQL catalog discovery (file list/metadata),
  invalidated by the sidebar's "Reload SQL catalog" button.
- `st.cache_data` — individual query results, keyed on
  `(query_name, params, db_file_mtime)`. Rebuilding the database
  changes its mtime, which automatically invalidates stale cached
  results; the sidebar's "Refresh cached results" button clears the
  cache manually as well.
- No long-lived writable connection is ever held — every query opens a
  short-lived, read-only connection and closes it immediately after
  fetching results.

## Read-only guarantees

- Every connection is opened via
  `sqlite3.connect(f"file:{path}?mode=ro", uri=True)` plus
  `PRAGMA query_only = ON` (`dashboard/database.py::connect_read_only`,
  reusing `scripts/run_analytics.py`'s already-proven implementation).
  A write attempt through this connection fails at the SQLite layer
  (`sqlite3.OperationalError: attempt to write a readonly database`),
  not merely by convention — verified directly in
  `tests/test_dashboard.py::test_database_opens_read_only`.
- `PRAGMA integrity_check` and `PRAGMA foreign_key_check` (Technical
  page) are inherently read-only diagnostics.
- The "Run validation" button subprocess-invokes
  `scripts/run_validation.py` unchanged — it does not reimplement any
  validation logic in the dashboard.
- `tests/test_dashboard.py` includes a full before/after table-content
  diff proving that running every query in the library leaves the
  database byte-for-byte unchanged.

## How to add an existing query to the dashboard

1. Add an entry to `_DASHBOARD_METADATA` in `dashboard/query_catalog.py`:
   the query name, its recommended `visualizations` list, and its
   `pages` list.
2. In the relevant `dashboard/pages/*.py` file, call
   `sql_loader.run_query("your_query_name")`, pass the resulting
   DataFrame to a `dashboard/charts.py` builder or
   `dashboard/components/tables.py::render_table`, and add
   `query_source_expander(entry_for_name("your_query_name"))`
   beneath it.

Do not write new analytical SQL inline in a page file — if a new
question needs new SQL, it belongs under `queries/`, following the
existing header-comment convention (`-- Audience:`, `-- Question:`,
etc.) so `sql_loader`/`query_catalog` can describe it automatically.

## How to add a new chart type

Add a new builder function to `dashboard/charts.py` that accepts a
DataFrame and column names (never a query name or SQL) and returns a
`plotly.graph_objects.Figure`. Keep it generic — it should not know
which query produced its input.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| "No database found" error on every page | `data/output/sentry.db` doesn't exist | `python scripts/build_database.py --rebuild` |
| A page shows stale numbers after a rebuild | Cached query results | Click "Refresh cached results" in the sidebar, or restart the app |
| `QueryNotFoundError` on the SQL Queries page | Shouldn't happen via the UI (closed dropdown) — only possible by calling `sql_loader.run_query()` directly with a typo | Check `sql_loader.discover_queries()` for valid names |
| A chart shows "—" for a KPI | The underlying query returned an empty/unexpected result | Open the query's source expander beneath the chart and re-run it on the SQL Queries page to inspect |
| `streamlit run` fails with an import error | Repo root not on `sys.path` | Every page/app.py file inserts `REPO_ROOT` at the top before any `dashboard.*` import — confirm you're running `streamlit run dashboard/app.py` from the repo root |
