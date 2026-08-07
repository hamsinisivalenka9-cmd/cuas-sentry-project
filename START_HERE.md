# Start Here

The complete operational guide for this project — setup through
troubleshooting. For a short project overview, see
[README.md](README.md).

## Quick Start (30 seconds)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/build_database.py --rebuild
python scripts/run_validation.py
python scripts/run_analytics.py --category executive

streamlit run dashboard/app.py
```

Open the dashboard: **http://localhost:8501**

That's the whole project running end to end. Everything below explains
each step in more detail, plus how to explore the database and
evaluate the results.

| Approximate time |
Approximate execution times on a modern laptop


## 1. Project overview

This project turns a raw counter-UAS (drone-detection) sensor
recording into a fully queryable, validated relational database —
**everything runs locally**, with no external services or cloud
dependencies. A Python ETL pipeline reads protobuf-encoded sensor
messages from `data/input/sanitized.mcap` and transforms them into a
normalized SQLite database at `data/output/sentry.db`.

```
data/input/sanitized.mcap (protobuf/MCAP)
    -> Python ETL (src/cuas_etl/)
    -> data/output/sentry.db (SQLite)
    -> validated (scripts/run_validation.py)
    -> queried (sqlite3, DBeaver, queries/*.sql, scripts/run_analytics.py)
    -> visualized (Streamlit dashboard, dashboard/app.py)
```

A few things worth knowing up front:

- **The ETL is the only step that touches the raw MCAP file.** It
  transforms the recording once into the normalized SQLite database.
- **SQLite is the analytical backend.** Every number, chart, and KPI
  anywhere in this project — from a raw `sqlite3` query to a dashboard
  page — is computed by SQL running directly against it.
- **All analytical SQL executes against SQLite**, via the query
  library under `queries/` or the dashboard — both read the same
  database.
- **The dashboard is a read-only presentation layer.** It visualizes
  the results of existing SQL queries. It never reads the MCAP file
  directly, and it contains no analytical logic of its own.

The full design/analysis document set is indexed on the dashboard's
**Documentation** page.

## 2. Repository layout

```
cuas-sentry-project/
├── data/
├── src/
├── sql/
├── queries/
├── dashboard/
├── tests/
├── docs/
└── scripts/
```

- `data/` — Source MCAP file and generated SQLite database (neither committed to Git).
- `src/` — The ETL pipeline and MCAP inspection helpers.
- `sql/` — Core schema, indexes, views, and validation SQL.
- `queries/` — The 22-file analytical SQL query library.
- `dashboard/` — The read-only Streamlit dashboard.
- `tests/` — The full pytest suite.
- `docs/` — Design documents, analysis reports, and stage summaries.
- `scripts/` — Command-line entry points (build, validate, run analytics).

See [README.md](README.md#repository-structure) for a one-line summary
of the same layout.

## 3. Prerequisites

- Python 3.12 (developed and tested with 3.12.6)
- Git
- Docker is **not** required — this project runs entirely with local
  Python. (Docker support is planned for a later stage; there is
  nothing to install or run for it today.)

## 4. Clone and set up

```bash
git clone <this repository>
cd cuas-sentry-project

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Place the source recording at `data/input/sanitized.mcap`. It is
**not committed to Git** (`.gitignore` excludes `data/input/*`, keeping
only `.gitkeep`) — CLAUDE.md rule 2 forbids committing the source MCAP
file. You must place `sanitized.mcap` at that exact path yourself
before continuing; no script fetches or generates it.

## 5. Build the database

```bash
python scripts/build_database.py --rebuild
```

Reads the source MCAP file, builds the schema, and loads all 11
tables. Safe to re-run: `--rebuild` deletes and rebuilds from scratch.
Running the same command **without** `--rebuild` against an
already-built database validates the existing data and exits cleanly
instead of reloading it.

## 6. Validate the database

```bash
python scripts/run_validation.py
```

Runs every validation check (structural row counts, relational
integrity, enum consistency, source-MCAP checksum, and a full
re-derivation pass against the raw file) without modifying anything.
Exits 0 and prints `PASS` for every check on success. Add
`--skip-rederivation` for a faster, pure-SQL-only pass.

## 7. Run analytics

The same SQL files are used by both the command-line analytics runner and the Streamlit dashboard, ensuring a single source of analytical truth.

**How this works:** all analytical calculations live in SQL, under
`queries/`. `scripts/run_analytics.py` only discovers, executes,
validates, and formats those queries' results — it never recomputes
or overrides a value in Python. The dashboard (Section 8) reads from
this exact same query library.

The 22-file analytical query library lives under `queries/`, grouped
into `executive/`, `operational/`, `technical/`, plus one root-level
file. Run it through `scripts/run_analytics.py`:

```bash
# List every discovered query
python scripts/run_analytics.py --list

# Run every query in one category
python scripts/run_analytics.py --category executive
python scripts/run_analytics.py --category technical

# Run a single named query
python scripts/run_analytics.py --query cv_incorporation_summary

# Run a query that requires a parameter
python scripts/run_analytics.py --category operational --param track_id=81754 --param fused_track_id=25295F49158-7aa000015874

# Run every query at once (the two operational queries that require a
# track_id/fused_track_id will report an expected "requires parameter"
# error and the command will exit 1 -- this is normal; run them
# individually with --param as shown above to see their output)
python scripts/run_analytics.py --all
```

Each result set printed is one query's own output: a header
(`=== category/query_name ===`), the query's documented business
question, and a formatted result table.

## 8. Launch the dashboard

```bash
streamlit run dashboard/app.py
```

Opens at **http://localhost:8501** (only while this command is
running locally — there is no hosted deployment). Use the page
navigator in the sidebar:

| Page | Shows |
|---|---|
| Overview | System-wide counts and the two headline checksum results. |
| CV Detections | Individual camera detections and incorporation into tracks. |
| CV Tracks | Persistent camera-tracked objects, with a track-history drill-down. |
| Fused Tracks | Persistent fused (tower) tracked objects, sensor contributions, classification stability. |
| Data Quality | Live integrity checks, database metadata, and a "Run validation" button. |
| SQL Queries | Run any of the 22 approved queries, or write and run your own read-only SQL. |
| Documentation | Index of the project's design and analysis documents. |

## 9. Open the SQLite database

The generated database lives at `data/output/sentry.db` (not
committed to Git — `.gitignore` excludes `*.db` everywhere) and can be
explored using any SQLite-compatible client. The two recommended
options are `sqlite3` and DBeaver — both connect to the same file:

- **sqlite3** — a lightweight command-line client, installed on most
  systems already.
- **DBeaver** — a graphical database browser and SQL editor.

### Method 1 — sqlite3

```bash
# Open an interactive shell
sqlite3 data/output/sentry.db

# List tables / views
sqlite3 data/output/sentry.db ".tables"
sqlite3 data/output/sentry.db "SELECT name FROM sqlite_master WHERE type='view';"

# View one table's schema
sqlite3 data/output/sentry.db ".schema cv_detections"

# Run a query directly
sqlite3 data/output/sentry.db "SELECT COUNT(*) FROM cv_detections;"

# Run SQLite's built-in integrity checks
sqlite3 data/output/sentry.db "PRAGMA integrity_check;"
sqlite3 data/output/sentry.db "PRAGMA foreign_key_check;"

# Exit the interactive shell
.quit
```

### Method 2 — DBeaver

1. **New Database Connection** → choose **SQLite**.
2. Browse to `data/output/sentry.db` (build it first — see Section 5).
   DBeaver may prompt to download the SQLite JDBC driver on first
   connection; allow it.
3. **Finish**, then expand the connection in the Database Navigator to
   browse all 11 tables and 3 views.
4. To run a query: open a SQL Editor on this connection, then either
   paste SQL from any file under `queries/`, or open a `.sql` file
   directly and execute it (`Ctrl+Enter` / `Cmd+Enter`).

Any other SQLite-compatible client (e.g. DB Browser for SQLite) works
the same way — point it at `data/output/sentry.db`.

## 10. Run tests

```bash
# All tests
pytest

# Schema tests only
pytest tests/test_schema.py

# ETL tests only
pytest tests/test_extract.py tests/test_transform.py tests/test_load.py tests/test_etl_integration.py

# Analytical-query tests only
pytest tests/test_analytics_runner.py tests/test_checksum_queries.py

# Dashboard and SQL-validator tests only
pytest tests/test_dashboard.py tests/test_sql_validator.py
```

No lint or type-check tool (ruff, mypy, flake8) is currently
configured in this project — `pytest` is the only automated check.

## 11. Common troubleshooting

| Symptom | Fix |
|---|---|
| `FileNotFoundError` / "MCAP file not found" | Place `sanitized.mcap` at `data/input/sanitized.mcap` (see Section 4). |
| Dashboard shows "No database found" | Run `python scripts/build_database.py --rebuild` first. |
| `sqlite3`/DBeaver shows an empty or missing-table database | The build didn't complete — rerun `python scripts/build_database.py --rebuild` and check its output for errors. |
| "Address already in use" / port 8501 busy | Another Streamlit process is already running — stop it, or run `streamlit run dashboard/app.py --server.port 8502`. |
| `ModuleNotFoundError` for a package | Activate the virtual environment (`source .venv/bin/activate`) and run `pip install -r requirements.txt`. |
| Permission errors writing to `data/output/` | Confirm the directory exists and is writable: `mkdir -p data/output`. |
| `PRAGMA foreign_key_check` reports violations | Rebuild from scratch: `python scripts/build_database.py --rebuild` — a partial or interrupted build is the most common cause. |
| Dashboard started before the database finished building | Wait for `python scripts/build_database.py --rebuild` to exit 0, then start (or refresh) the dashboard. |

## 12. Expected outputs

- ✓ **SQLite database generated** — `data/output/sentry.db` (11 tables, 3 views)
- ✓ **Validation passes** — `python scripts/run_validation.py` exits 0, prints `PASS` for every check
- ✓ **All tests pass** — `pytest` reports 274/274 passing
- ✓ **Dashboard launches successfully** — every page loads at http://localhost:8501 without error
- ✓ **Executive analytics execute successfully** — `python scripts/run_analytics.py --category executive` returns results for every query

Two headline analytical checks (see `docs/analytics/CHECKSUM_RESOLUTION.md`
for the full evidence trail):

- ✓ **CV incorporation** — computed from `cv_incorporation_summary.sql`: **97.54%** (not the assignment's ~81% target; the interpretation was reviewed and confirmed correct)
- ✓ **Drone/Airplane average fused-track duration** — computed from `fused_track_duration_by_type.sql`: **Drone ~35.86s** (target ~30s), **Airplane ~614.68s** (target ~600s), classified by sensor provenance, not an object-classification field

These are the actual outputs this pipeline currently produces, not
values embedded as constants anywhere in the ETL or query code.

## 13. Suggested Evaluation Workflow

1. Read this document (START_HERE.md).
2. Run the ETL: `python scripts/build_database.py --rebuild`.
3. Run validation: `python scripts/run_validation.py`.
4. Run sample SQL: `python scripts/run_analytics.py --category executive`.
5. Open the dashboard: `streamlit run dashboard/app.py`, then visit http://localhost:8501.
6. Run tests: `pytest`.
7. Read the design documentation: start with `docs/architecture/DATABASE_DESIGN.md`, `docs/architecture/TABLE_GRAIN.md`, and `docs/analytics/ANALYTICAL_INSIGHTS.md`, or browse the full index on the dashboard's Documentation page.
