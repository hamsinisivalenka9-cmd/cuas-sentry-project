# CUAS Sentry Data Engineering Assessment

A local Python ETL pipeline that turns a raw counter-UAS (drone
detection) sensor recording into a queryable SQLite database, a
library of analytical SQL, and a small interactive dashboard. It reads
protobuf-encoded sensor messages from an MCAP file, models them
relationally, and answers real analytical questions about the
recording with SQL — nothing hardcoded, everything traceable back to
the source file.

## Architecture

```
sanitized.mcap  →  Python ETL  →  SQLite  →  SQL Analytics  →  Streamlit Dashboard
```

The pipeline decodes protobuf messages from `data/input/sanitized.mcap`
(camera, radar, and a multi-sensor fusion tower), loads them into a
normalized relational schema, validates the load against the source
file, and exposes the result through a SQL query library and a
read-only dashboard. See [DESIGN.md](DESIGN.md) for the full
explanation.

## Quick Start

**Option A — Local Python**

```bash
python scripts/build_database.py --rebuild
python scripts/run_validation.py
python scripts/run_analytics.py --category executive
streamlit run dashboard/app.py
```

**Option B — Docker** (no local Python install needed)

```bash
docker compose up --build
```

Both open the dashboard at **http://localhost:8501**. The generated
database always ends up at **`data/output/sentry.db`** — the Docker
container writes to that same host path via a bind mount.

## Run the tests

```bash
pytest
```

## Run the SQL

```bash
python scripts/run_analytics.py --list             # see every query
python scripts/run_analytics.py --category executive
sqlite3 data/output/sentry.db                       # or open it directly
```

## Documentation

- **[START_HERE.md](START_HERE.md)** — the complete step-by-step setup,
  build, and validation guide.
- **[DESIGN.md](DESIGN.md)** — architecture, data model, and design
  decisions.
- **[docs/data/DATA_DICTIONARY.md](docs/data/DATA_DICTIONARY.md)** —
  column-level reference for every table.
- **[docs/project/AI_USAGE.md](docs/project/AI_USAGE.md)** — AI/code-assistant
  usage disclosure.
