# CUAS Sentry Data Engineering Assessment

A local Python ETL pipeline that turns a raw counter-UAS (drone
detection) sensor recording into a queryable SQLite database, a
library of analytical SQL, and an interactive dashboard. Built as a
data engineering assessment: read protobuf-encoded sensor messages
from an MCAP file, model them relationally, and answer real analytical
questions about the recording with SQL — nothing hardcoded, everything
traceable back to the source file.

*Start with [START_HERE.md](START_HERE.md)** for the
complete step-by-step setup, build, and validation guide. This README
is a concise project overview.

## Project Overview

```
MCAP file  →  Python ETL  →  SQLite  →  SQL Analytics  →  Streamlit Dashboard
```

The pipeline decodes protobuf messages from `data/input/sanitized.mcap`
(three independent sensor systems: camera, radar, and a multi-sensor
fusion tower), loads them into a normalized relational schema at
`data/output/sentry.db`, validates the load against the source file,
and exposes the result through a reusable SQL query library and a
read-only Streamlit dashboard.

## Features

- Decodes protobuf messages directly from MCAP — no intermediate format
- Loads a normalized, 11-table SQLite schema with enforced foreign keys
- Validates source fidelity: structural counts, checksums, and a full
  re-derivation pass against the raw file
- Preserves protobuf provenance (nanosecond timestamps, raw + resolved
  enum values, every repeated/nested field) — nothing silently dropped
- Ships 22 analytical SQL queries answering real questions about the
  recording, plus 3 reusable views
- Includes an interactive, read-only Streamlit dashboard (7 pages,
  including a SQL query editor)
- Covered by 274 automated tests (ETL, schema, validation, analytics,
  dashboard)

**Analytical insights.** The two headline questions this project
answers directly from the data:

- **CV detection incorporation:** 97.54% of camera detections were
  incorporated into a persistent track. Using multiple independent SQL implementations and direct protobuf relationship validation, this project consistently computes that 1,864 of 1,911 CV detections (97.54%) were incorporated into one or more persistent CV tracks in the provided sanitized.mcap dataset.
- **Fused-track duration by class:** Drone-classified tracks average
  ~36 seconds; Airplane-classified tracks average ~615 seconds
  (classified by sensor provenance, not an object-classification
  field — see `docs/analytics/CHECKSUM_RESOLUTION.md`).

**Technologies:** Python 3.12, `mcap`/`mcap-protobuf-support`/`protobuf`
for decoding, SQLite (standard library `sqlite3`), pytest, and
Streamlit + Plotly + pandas for the dashboard.

## Repository Structure

| Path | Contents |
|---|---|
| `data/` | Source MCAP file (`input/`) and generated database (`output/`) — neither committed to Git. |
| `src/` | The ETL pipeline and MCAP inspection helpers. |
| `queries/` | The 22-file analytical SQL library, grouped by audience. |
| `sql/` | Core schema, indexes, views, and validation SQL. |
| `dashboard/` | The read-only Streamlit dashboard. |
| `tests/` | The full pytest suite. |
| `scripts/` | Command-line entry points (build, validate, run analytics). |
| `docs/` | Design documents, analysis reports, and stage summaries. |

## Documentation

**[START_HERE.md](START_HERE.md)** is the complete operational guide —
setup, build, validate, run analytics, launch the dashboard, open the
database, troubleshoot. Design and analysis documents are organized
under `docs/architecture/`, `docs/data/`, `docs/analytics/`, and
`docs/dashboard/`, and are also indexed on the dashboard's
**Documentation** page.

## Quick Start

```bash
python scripts/build_database.py --rebuild
python scripts/run_validation.py
python scripts/run_analytics.py --category executive
streamlit run dashboard/app.py
```

- **Dashboard:** http://localhost:8501
- **SQLite database:** `data/output/sentry.db`

Open the database with `sqlite3`, [DBeaver](https://dbeaver.io/), [DB
Browser for SQLite](https://sqlitebrowser.org/), or any SQLite-compatible
client. See [START_HERE.md](START_HERE.md) for detailed commands,
prerequisites, and both database-client walkthroughs.
