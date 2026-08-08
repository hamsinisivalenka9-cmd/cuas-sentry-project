# Start Here

The complete operational guide for this project — setup through
troubleshooting. For a short project overview, see
[README.md](README.md).

There are two ways to run this project. Pick one:

## Quick Start — Option A: Local Python (30 seconds)

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

## Quick Start — Option B: Docker (no Python install needed)

```bash
docker compose up --build
```

Open the dashboard: **http://localhost:8501**. Full walkthrough,
including what's happening under the hood, in Section 5.

Either option gets the whole project running end to end. Everything
below explains each step in more detail, plus how to explore the
database and evaluate the results.

| Task | Approximate time |
|---|---|
| Build database | ~2–5 seconds |
| Validation | ~1–2 seconds |
| Executive analytics | <1 second |
| Launch dashboard | ~3–5 seconds |
| Docker image build (first time only) | ~1–3 minutes |

*Approximate, on a modern laptop with a warm pip/Docker cache where
applicable.*

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

Pick a track:

- **Local Python** — Python 3.12 (developed and tested with 3.12.6) and Git.
- **Docker** — [Docker Desktop](https://www.docker.com/products/docker-desktop/)
  (includes Docker Compose) and Git. No local Python install needed —
  see Section 5.

Either way, you'll need Git to clone the repository.

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

If you're using **Docker**, skip ahead to Section 5 — it replaces
Sections 6–9 below (you don't need a Python virtual environment).

## 5. Docker

Docker packages this exact, unmodified application (same ETL, same
SQLite database, same SQL, same dashboard) so it can run without
installing Python or any dependency locally. If you're following the
local Python path instead, skip to Section 6.

**New to Docker? Four terms, explained once:**

| Term | What it means |
|---|---|
| **Dockerfile** | Defines how the project image is built (base Python version, dependencies, code, startup command). |
| **Docker image** | A packaged snapshot containing Python, all dependencies, and the project code — built once from the Dockerfile. |
| **Docker container** | A running instance of that image — the actual live process serving the dashboard. |
| **docker-compose.yml** | Defines how the container is started: which ports are exposed, and which local folder (`data/`) is mounted in. |

### Setup

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and make sure it's running.
2. Place the source recording at `data/input/sanitized.mcap` (same
   requirement as Section 4 — not committed to Git).
3. From the repository root:

   ```bash
   docker compose up --build
   ```

4. Open **http://localhost:8501**.
5. Stop with:

   ```bash
   docker compose down
   ```

### What happens on startup

`docker compose up --build` builds the image (first time only —
later runs reuse cached layers unless `requirements.txt` changed),
then starts one container that:

1. Checks that `data/input/sanitized.mcap` exists (bind-mounted from
   the host). If it's missing, the container exits immediately with a
   clear error telling you where to place it — it does not hide the
   failure or start the dashboard against a missing source file.
2. Runs the exact same `scripts/build_database.py` used by the local
   Python workflow, unmodified — it builds `data/output/sentry.db` if
   missing, or just validates it (without rebuilding) if it already
   exists.
3. Starts the same `streamlit run dashboard/app.py`, bound to
   `0.0.0.0:8501` inside the container and published to
   `localhost:8501` on the host.

### Where the database ends up

`docker-compose.yml` mounts `./data` on the host to `/app/data` inside
the container (`volumes: - ./data:/app/data`), so `data/output/sentry.db`
is written to the exact same host path the local Python workflow
already uses. You can open it with `sqlite3` or DBeaver (Section 10)
at any time, whether it was built locally or inside the container. The
source MCAP file and any generated database are excluded via
`.dockerignore` and are never copied into the image itself — they only
ever exist in the host-mounted `data/` folder.

### Rebuilding

- Code changed? `docker compose up --build` — only rebuilds the image
  layers that changed.
- Want to force a full data rebuild inside the container? Delete
  `data/output/sentry.db` on the host, then run `docker compose up --build`
  again — startup will detect the missing database and rebuild it
  from `data/input/sanitized.mcap`, the same as a fresh first run.

## 6. Build the database

```bash
python scripts/build_database.py --rebuild
```

Reads the source MCAP file, builds the schema, and loads all 11
tables. Safe to re-run: `--rebuild` deletes and rebuilds from scratch.
Running the same command **without** `--rebuild` against an
already-built database validates the existing data and exits cleanly
instead of reloading it.

## 7. Validate the database

```bash
python scripts/run_validation.py
```

Runs every validation check (structural row counts, relational
integrity, enum consistency, source-MCAP checksum, and a full
re-derivation pass against the raw file) without modifying anything.
Exits 0 and prints `PASS` for every check on success. Add
`--skip-rederivation` for a faster, pure-SQL-only pass.

## 8. Run analytics

**How this works:** all analytical calculations live in SQL, under
`queries/`. `scripts/run_analytics.py` only discovers, executes,
validates, and formats those queries' results — it never recomputes
or overrides a value in Python. The dashboard (Section 9) reads from
this exact same query library, so command-line runs and the dashboard
always agree.

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

## 9. Launch the dashboard

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

To stop the dashboard, go back to the terminal it's running in and
press **Ctrl+C**. (For Docker, use `docker compose down` instead — see
Section 5.)

## 10. Open the SQLite database

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
2. Browse to `data/output/sentry.db` (build it first — see Section 6).
   DBeaver may prompt to download the SQLite JDBC driver on first
   connection; allow it.
3. **Finish**, then expand the connection in the Database Navigator to
   browse all 11 tables and 3 views.
4. To run a query: open a SQL Editor on this connection, then either
   paste SQL from any file under `queries/`, or open a `.sql` file
   directly and execute it (`Ctrl+Enter` / `Cmd+Enter`).

Any other SQLite-compatible client (e.g. DB Browser for SQLite) works
the same way — point it at `data/output/sentry.db`.

## 11. Run tests

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

## 12. Common troubleshooting

| Symptom | Fix |
|---|---|
| `FileNotFoundError` / "MCAP file not found" | Place `sanitized.mcap` at `data/input/sanitized.mcap` (Section 4, or Section 5 for Docker). |
| Dashboard shows "No database found" | Run `python scripts/build_database.py --rebuild` first. |
| `sqlite3`/DBeaver shows an empty or missing-table database | The build didn't complete — rerun `python scripts/build_database.py --rebuild` and check its output for errors. |
| "Address already in use" / port 8501 busy | Another Streamlit process (local or Docker) is already using it — stop it, run `streamlit run dashboard/app.py --server.port 8502`, or change the host port in `docker-compose.yml`'s `ports:` mapping. |
| `ModuleNotFoundError` for a package | Activate the virtual environment (`source .venv/bin/activate`) and run `pip install -r requirements.txt`. |
| Permission errors writing to `data/output/` | Confirm the directory exists and is writable: `mkdir -p data/output`. |
| `PRAGMA foreign_key_check` reports violations | Rebuild from scratch: `python scripts/build_database.py --rebuild` — a partial or interrupted build is the most common cause. |
| Dashboard started before the database finished building | Wait for `python scripts/build_database.py --rebuild` to exit 0, then start (or refresh) the dashboard. |
| `docker compose up` hangs, or fails to connect to the daemon | Docker Desktop isn't running — start it and wait until it's fully up, then retry. |
| Docker container exits immediately with an MCAP-not-found error | Confirm `sanitized.mcap` is at `data/input/sanitized.mcap` on the host, and that you're running `docker compose up` from the repository root (the `./data:/app/data` bind mount is relative to it). |
| "port is already allocated" from Docker | Another process is already using port 8501 — stop it, or edit the `ports:` mapping in `docker-compose.yml`. |

## 13. Expected outputs

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

## 14. Suggested Evaluation Workflow

1. Read this document (START_HERE.md).
2. Run the ETL: `python scripts/build_database.py --rebuild`.
3. Run validation: `python scripts/run_validation.py`.
4. Run sample SQL: `python scripts/run_analytics.py --category executive`.
5. Open the dashboard: `streamlit run dashboard/app.py`, then visit http://localhost:8501.
6. Run tests: `pytest`.
7. Read the design documentation: start with [`DESIGN.md`](DESIGN.md) for a concise overview, then `docs/architecture/DATABASE_DESIGN.md`, `docs/architecture/TABLE_GRAIN.md`, and `docs/analytics/ANALYTICAL_INSIGHTS.md` for detail, or browse the full index on the dashboard's Documentation page.
8. Read `docs/project/AI_USAGE.md` for the AI/code-assistant usage disclosure.

(Prefer Docker? `docker compose up --build` covers steps 2–5 in one
command — see Section 5.)
