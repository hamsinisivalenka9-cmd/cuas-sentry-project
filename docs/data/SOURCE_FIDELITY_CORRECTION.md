# Source-Fidelity Correction — Schema Version 2

## Issue found

The original database omitted three populated CV detection quality fields and
reduced each repeated CV track class distribution to a single selected
confidence. That lost alternative candidates, duplicate classifications, and
source order.

## Raw evidence

- `CVDetection.focus_quality`: enum, populated 1,911/1,911; raw values 1–5.
- `CVDetection.focus_score`: `google.protobuf.FloatValue`, populated
  1,911/1,911; range 0.00993645191192627–0.8966140747070312.
- `CVDetection.sharpness`: `google.protobuf.FloatValue`, populated
  1,911/1,911; range 0.10338592529296875–0.9900635480880737.
- `CVTrack.class_distribution[]`: four entries on every one of 9,496 track
  states, 37,984 entries total. Entries contain `classification` enum and
  protobuf-float `probability_score`; duplicate classifications occur and are
  meaningful source facts.

## Schema and ETL change

Four nullable columns were added to `cv_detections`: `focus_quality_raw`,
`focus_quality_name`, `focus_score`, and `sharpness`.

`cv_track_class_distribution` was added at one row per repeated entry per
`cv_track_states` parent. It uses a deterministic surrogate PK, an enforced FK
to the parent state, and `UNIQUE(cv_track_state_id, source_order)`. No
probability constraint was added because the descriptor declares no explicit
range validation.

Transformation copies wrapper values with presence checks, resolves enum names
from descriptors, retains duplicates, and records the zero-based protobuf
position. Loading remains parameterized, batched, transactional, and FK-safe.

## Scope boundary and follow-up items

This correction intentionally does not add `CVDetection.crop_edge_size` or
`mean_lc`, nor CV track focus fields, `unfiltered_class_name`, `update_uid`, or
`track_estimate`. Those populated omissions are documented follow-up work and
require separate approval. No existing grain, key, bridge, timestamp, or
checksum formula changed.

## Row counts and analytical impact

The new child table contains 37,984 rows, exactly four ordered entries for each
of 9,496 parent CV track states. All legacy table counts must remain unchanged.

The rebuilt database contains 37,984 child rows and 9,496 complete ordered
parent groups. Independent raw-MCAP comparison matched all 1,911 scalar rows
and all 37,984 repeated entries exactly. The full suite passed **193 tests**;
the validation runner passed **121 checks** with zero fatal failures and zero
warnings. `PRAGMA integrity_check` returned `ok`, `PRAGMA foreign_key_check`
returned no rows, and the source MD5 remained
`e32b641c93b84861d855b01a79ea09d0`.

Analytical results were unchanged: CV incorporation is 1,864/1,911 = 97.54%;
Drone mean duration is 35.86 seconds (51 tracks); Airplane mean duration is
614.68 seconds (36 tracks). Completeness improved, but the CV checksum
discrepancy was not resolved or forced.
