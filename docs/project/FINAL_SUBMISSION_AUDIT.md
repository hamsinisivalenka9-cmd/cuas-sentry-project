# Final Submission Audit

**Audit date:** 2026-08-08
**Submitter:** Hamsini Sivalenka

## Final project status

**READY TO SUBMIT.** The pipeline builds, validates, and answers both
required analytical questions from source data; the full test suite,
integrity checks, and a clean-room Docker run all pass; the submission
archive excludes all source/generated/sensitive files and was itself
extracted and re-run independently to confirm it is complete.

## Deliverables verified

| Deliverable | Status | Where |
|---|---|---|
| MCAP → SQLite ETL pipeline | Present, working | `src/cuas_etl/`, `scripts/build_database.py` |
| Relational SQLite schema (12 tables — 11 analytical + `schema_version`, 3 views) | Present | `sql/schema.sql`, `sql/views.sql` |
| Primary/foreign keys, `PRAGMA foreign_keys = ON` | Present, enforced | `sql/schema.sql`, `src/cuas_etl/database.py` |
| Analytical SQL (22 queries) | Present, all discoverable/runnable | `queries/`, `scripts/run_analytics.py` |
| Automated tests | Present, 274/274 passing | `tests/` |
| Data validation | Present, 121/121 checks passing | `scripts/run_validation.py` |
| README | Present, verified against repo | `README.md` |
| Setup/execution documentation | Present, verified against repo | `START_HERE.md` |
| Architecture/design documentation | Present | `docs/architecture/`, `docs/data/`, `docs/analytics/` |
| AI/code-assistant usage documentation | **Added during this audit** — was missing | `docs/project/AI_USAGE.md` |
| Docker support | Present, clean-room verified | `Dockerfile`, `docker-compose.yml`, `scripts/docker-entrypoint.sh` |
| Streamlit dashboard (7 pages) | Present, all pages verified reachable | `dashboard/` |

## Tests passed

`pytest` (local): **274 passed, 0 failed, 0 skipped** (37.3s).
`pytest` (from a fresh extraction of the final ZIP, fresh venv, real
MCAP copy, freshly built database): **274 passed, 0 failed, 0 skipped**
(43.7s) — identical result, confirming the archive is self-sufficient.

## Integrity-check result

`PRAGMA integrity_check` → `ok`.

## Foreign-key-check result

`PRAGMA foreign_key_check` → no violations (empty result set).

Both were run directly via `sqlite3`, via `scripts/run_validation.py`
(as part of its 121-check report), and independently inside the
clean-room Docker container — all three agree.

## Docker verification result

**Passed.** A clean-room copy of the repository (rsync of the working
tree, excluding `.git`/`.venv`/caches/generated data, plus a copy of
`sanitized.mcap`) was built and run in an isolated directory outside
the working repo:

- Image built successfully (`docker compose up --build`).
- Container correctly detected the missing database and ran the ETL
  from scratch: all 11 tables loaded with the expected row counts;
  `Overall validation: PASSED`.
- `PRAGMA integrity_check` / `PRAGMA foreign_key_check` inside the
  container both passed.
- Streamlit started and `http://localhost:8501` responded `200`, with
  `/_stcore/health` reporting `ok`.
- Three representative dashboard routes (Overview, CV Detections,
  Fused Tracks) all returned `200`.
- Both headline analytical queries, run inside the container against
  the container-built database, returned the same results as the
  local run.
- Source MCAP MD5 on the host was confirmed unchanged after the run.
- The clean-room stack was stopped cleanly (`docker compose down`);
  the working repository's own container was stopped before this test
  (to free the fixed container name/port) and restarted afterward,
  confirmed reachable again.
- Separately, `docker build` was re-run directly from the **extracted
  submission ZIP** (Phase 12 below) and also succeeded.

## Dashboard verification result

All 7 pages verified present and, during the clean-room Docker run,
reachable via HTTP: Overview, CV Detections, CV Tracks, Fused Tracks,
Data Quality, SQL Queries, Documentation. `http://localhost:8501` is
only reachable while the dashboard (local or Docker) is running —
documented in `START_HERE.md` Section 9.

## Analytical-query verification (actual results from this dataset)

Run via `scripts/run_analytics.py`, locally, inside the clean-room
Docker container, and from the extracted ZIP — all identical:

| Question | Assignment target | Actual result (this dataset) |
|---|---|---|
| CV detection incorporation | ~81% | **97.54%** (1,864 / 1,911) |
| Drone avg. fused-track duration | ~30s | **~35.86s** (n=51) |
| Airplane avg. fused-track duration | ~600s | **~614.68s** (n=36) |

No algorithm or data was adjusted to move these figures toward the
assignment's approximate targets. The full investigation — methodology,
root cause of the CV-incorporation gap, the sensor-provenance basis for
Drone/Airplane classification (there is no `DRONE`/`AIRPLANE` value in
`proto.tower.TrackObjectClass`), and the review/approval record — is in
`docs/analytics/CHECKSUM_RESOLUTION.md`. That document explicitly
distinguishes the assignment's approximate target, the value this
implementation actually computes, the methodology used to compute it,
and known limitations/ambiguity in the source data.

## Clean-room verification

See "Docker verification result" and "Test the ZIP itself" above/below
— both a clean-room copy of the working tree and the final ZIP itself
were built, run, and validated in isolated temporary directories,
independent of the working repository.

## Test the ZIP itself

The final `Hamsini_Sivalenka.zip` was extracted into a new temporary
directory and treated as an independent copy:

- No excluded data present: `find` for `*.mcap`/`*.db`/`*.sqlite*`/
  `.git`/`.venv` in the extracted tree returned nothing.
- A fresh virtual environment was created and dependencies installed
  from `requirements.txt`.
- `pytest --collect-only` discovered all 274 tests with no import
  errors.
- A temporary copy of `sanitized.mcap` was placed at the documented
  path (`data/input/sanitized.mcap`); `build_database.py --rebuild`,
  `run_validation.py`, both analytical queries, and the full `pytest`
  suite were run against it — all passed, with results identical to
  the working repository.
- `docker build` was run directly from the extracted directory and
  succeeded.
- The temporary extraction directory, its venv, its MCAP copy, and the
  Docker images built from it were deleted afterward. **The source
  `sanitized.mcap` was not added back into the ZIP** — it was only
  ever copied into the separate, disposable extraction directory.

## Files intentionally excluded from the archive

`sanitized.mcap`, `data/output/*` (generated `sentry.db` and any other
generated artifacts, e.g. `mcap_schema_report.json`, `key_analysis.json`),
`.git/`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`,
`.ruff_cache/`, `*.pyc`, `.DS_Store`, `.claude/` (local tool settings,
not a project deliverable). No `.env`/credential/secret/API-key files
exist in this repository (verified by search).

## Known limitations

- The CV-incorporation checksum (97.54%) does not match the
  assignment's ~81% approximate target. This was investigated
  exhaustively; no alternative, evidence-supported definition of
  "incorporated" was found that reproduces ~81% against this specific
  source file. See `docs/analytics/CHECKSUM_RESOLUTION.md` Phase 1A
  for the full evidence trail, including the possibility that the
  assignment's target was computed against a different (larger, less
  sanitized) source recording.
- Drone/Airplane classification is derived from sensor provenance
  (whether a fused track ever incorporated a transponder-sourced
  measurement), not a direct object-classification field, because the
  source protobuf schema (`proto.tower.TrackObjectClass`) has no
  `DRONE` or `AIRPLANE` enum value. This is documented, not hidden.
- No lint/type-check tool (ruff, mypy, flake8) is configured; `pytest`
  is the only automated check, as noted in `START_HERE.md`.

## Final archive

- **Name:** `Hamsini_Sivalenka.zip`
- **Path:** `/Users/hamsinisivalenka/Downloads/cuas-sentry-project/Hamsini_Sivalenka.zip`
- **Size:** 434,341 bytes (~424 KB)
- **`sanitized.mcap` inside the archive:** **Confirmed absent** (`unzip -l` search returned no match)
- **`sentry.db` inside the archive:** **Confirmed absent** (`unzip -l` search for `*.db`/`*.sqlite*` returned no match)

## Changes made during this audit

- `START_HERE.md` — added "how to stop the dashboard" (Ctrl+C) and a
  link to the new AI usage disclosure in the evaluation workflow.
- `README.md` — added a direct link to the AI usage disclosure.
- `docs/project/AI_USAGE.md` — **new file**, the AI/code-assistant
  usage disclosure required by the assignment (was missing entirely).
- `dashboard/pages/7_Documentation.py` — added `docs/project/AI_USAGE.md`
  to the "Project instructions and AI usage" index section.
- `scripts/build_database.py` — corrected a stale end-of-build console
  note that said the CV-incorporation checksum "remains unresolved"
  and pointed at an outdated doc path (`docs/CHECKSUM_RESOLUTION.md`).
  The investigation was in fact completed and reviewed in an earlier
  stage; the note now states the actual computed figures and points to
  the current path, `docs/analytics/CHECKSUM_RESOLUTION.md`. No
  analytical logic, schema, or query changed — this was a print-string
  correction only, caught during the clean-room Docker verification
  when the stale note appeared in the container's startup log.
- `Hamsini_Sivalenka.zip` — **new file**, the final submission archive.
- `docs/project/FINAL_SUBMISSION_AUDIT.md` — this document.

No schema, ETL logic, analytical query, or dashboard functionality was
changed.
