# AI / Code-Assistant Usage Disclosure

## Summary

This project was built with substantial assistance from an AI coding
assistant (Claude Code, Anthropic). I (Hamsini Sivalenka) directed the
work throughout, reviewed every change, ran and inspected the actual
output of the pipeline, tests, and dashboard, and made the final
decisions on design, data interpretation, and what shipped. I did not
write every line by hand, and I am not claiming otherwise — but I am
responsible for the resulting implementation and its correctness.

## How the assistant was used

- **Governing instructions.** `CLAUDE.md` (and its `AGENTS.md`
  duplicate, for tools that read that filename instead) contains the
  project's objective and 20 critical rules that I wrote to direct the
  assistant's work — things like "never modify the source MCAP file,"
  "do not invent protobuf field names," "do not hardcode expected
  analytical answers," and "add tests for transformations, schema
  integrity, and analytical queries." These rules were enforced across
  the whole project, not just suggested once.
- **Staged development.** The project was built in stages (MCAP
  inspection → key/relationship analysis → schema design → schema
  review → ETL implementation → analytical SQL → dashboard → Docker
  packaging → this final submission audit), each recorded under
  `docs/stages/`. The assistant proposed designs and implementations
  at each stage; I reviewed, asked for revisions, and approved before
  moving on.
- **Code generation and review.** The assistant wrote most of the
  Python (`src/`, `scripts/`, `dashboard/`), SQL (`sql/`, `queries/`),
  and tests (`tests/`) under my direction, iterating in response to
  real output — actual MCAP structure, actual query results, actual
  test failures — rather than working from assumptions.
- **Analytical results were not hand-picked.** The two headline
  analytical checks (CV-detection incorporation rate; Drone vs.
  Airplane average fused-track duration) are computed by SQL against
  the decoded data, not embedded as constants. Where the computed
  results differed from the assignment's approximate targets, that
  discrepancy was investigated and documented rather than adjusted to
  match — see `docs/analytics/CHECKSUM_RESOLUTION.md`.
- **Documentation.** Most of the design and analysis documents under
  `docs/`, and this repository's `README.md`/`START_HERE.md`, were
  drafted by the assistant and edited/reviewed by me for accuracy
  against the actual code and data.

## What I verified myself

- Ran the ETL pipeline against the real source file and inspected the
  resulting database.
- Ran the full test suite and the SQLite integrity/foreign-key checks.
- Ran the analytical queries and read their actual output before it
  was written into any document.
- Ran the dashboard locally and in Docker and clicked through its
  pages.
- Reviewed the schema, ETL logic, and SQL for correctness against the
  source protobuf schemas, not just against the assistant's own
  explanation of them.

## Responsibility

I am the submitter of this project and take responsibility for its
correctness, its design decisions, and any errors it may still
contain, regardless of which parts were AI-assisted.
