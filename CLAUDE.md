# CUAS Sentry MCAP Data Engineering Project

## Objective

Build a local Python ETL pipeline that reads protobuf-encoded messages from
data/input/sanitized.mcap and persists them in a relational SQLite database at
data/output/sentry.db.

The database must support simple analytical SQL queries across:

- cv_detections
- cv_tracks
- radar_detections
- track_states

## Critical rules

1. Never modify, delete, rename, move, or overwrite the source MCAP file.
2. Never commit the MCAP file or generated SQLite database.
3. Do not invent protobuf field names.
4. Inspect the actual MCAP schemas and decoded messages before designing tables.
5. Preserve the original MCAP log_time and publish_time in nanoseconds.
6. Explicitly define the grain of every table.
7. Use primary keys and foreign keys only when justified by the source data.
8. Enable SQLite foreign-key enforcement with PRAGMA foreign_keys = ON.
9. Use parameterized SQL queries.
10. Use transactions and batched inserts.
11. The pipeline must be idempotent or safely rebuild the database.
12. Do not silently discard repeated or nested protobuf data.
13. Put repeated nested structures in child or bridge tables.
14. Do not hardcode the expected analytical answers.
15. Add tests for transformations, schema integrity, and analytical queries.
16. Explain all significant assumptions in docs/DESIGN.md.
17. Do not begin the dashboard or Docker work until the SQLite pipeline works.
18. Before making major changes, provide a plan.
19. After making changes, list all files changed and commands used.
20. Use beginner-readable Python with type hints and clear function names.

## Expected analytical checks

The data model should make these questions simple to answer:

1. What percentage of CV detections were incorporated into CV tracks?
2. What is the average fused-track duration for Drone objects compared with
   Airplane objects?

The expected approximate answers are provided only as validation targets:

- CV incorporation: approximately 81%
- Drone average duration: approximately 30 seconds
- Airplane average duration: approximately 600 seconds

These answers must be computed from the source data and must never be embedded
as constants in transformation code.

## Code quality

Before considering work complete, run:

- pytest
- Python compilation checks
- SQLite integrity checks
- foreign-key checks