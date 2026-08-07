"""Independent, read-only verification of both checksum questions,
computed directly from a fresh decode of data/input/sanitized.mcap.

Does NOT import or call anything from src/cuas_etl/transform.py or
src/cuas_etl/load.py -- only src/cuas_etl/extract.py is used, and only
for its read-only MCAP decode (iterating messages, no field mapping or
aggregation logic is reused). All aggregation/classification logic
below is independently re-implemented so this script can serve as a
cross-check against the production sentry.db, not a re-run of it.

Produces:
  (A) CV incorporation percentage (best-supported definition)
  (B) Drone vs. Airplane average fused-track duration, classified by
      whether a fused track ever received a TOWER_SENSOR_TRANSPONDER
      measurement (sensor_id raw value 6).

Never writes to data/output/sentry.db or data/input/sanitized.mcap.
"""
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, "src")
from cuas_etl.extract import extract_mcap  # noqa: E402 (read-only decode only)

print("Decoding data/input/sanitized.mcap (read-only)...")
data = extract_mcap()
print("Decoded:", data.topic_counts())

# ---------------------------------------------------------------------
# (A) CV incorporation
# ---------------------------------------------------------------------
print("\n" + "=" * 70)
print("(A) CV DETECTION INCORPORATION")
print("=" * 70)

all_detection_ids = set()
for msg in data.cv_detections:
    for d in msg.decoded.detections:
        all_detection_ids.add(d.detection_id)

incorporated_pairs = set()
for msg in data.cv_tracks:
    for t in msg.decoded.tracks:
        det_id = t.last_associated_detection_id
        if det_id != 0:
            incorporated_pairs.add((det_id, t.track_id))

incorporated_detection_ids = {d for d, _ in incorporated_pairs}
valid_incorporated = incorporated_detection_ids & all_detection_ids
orphaned = incorporated_detection_ids - all_detection_ids

denominator = len(all_detection_ids)
numerator = len(valid_incorporated)
print(f"Total distinct cv_detections.detection_id: {denominator}")
print(f"Distinct detection_id ever referenced as last_associated_detection_id: {len(incorporated_detection_ids)}")
print(f"  ...of which valid (exist in cv_detections): {numerator}")
print(f"  ...of which orphaned (no matching cv_detections row): {len(orphaned)}")
print(f"Incorporation percentage (valid / total): {100.0 * numerator / denominator:.2f}%")

# cross-check against sentry.db
import sqlite3
conn = sqlite3.connect("data/output/sentry.db")
db_num, db_den = conn.execute(
    "SELECT (SELECT COUNT(DISTINCT detection_id) FROM cv_detection_track_links), "
    "(SELECT COUNT(*) FROM cv_detections)"
).fetchone()
print(f"\nsentry.db comparison: numerator={db_num}, denominator={db_den}, "
      f"pct={100.0*db_num/db_den:.2f}%  (match: {db_num == numerator and db_den == denominator})")

# ---------------------------------------------------------------------
# (B) Drone vs Airplane duration, classified by transponder involvement
# ---------------------------------------------------------------------
print("\n" + "=" * 70)
print("(B) DRONE vs AIRPLANE FUSED-TRACK DURATION")
print("=" * 70)

TOWER_SENSOR_TRANSPONDER = 6

log_times_by_track = defaultdict(list)
transponder_tracks = set()
for msg in data.track_states:
    st = msg.decoded
    fid = st.track_id2
    log_times_by_track[fid].append(msg.envelope.log_time_ns)
    for m in st.measurements:
        if m.sensor_id == TOWER_SENSOR_TRANSPONDER:
            transponder_tracks.add(fid)

airplane_durations = []
drone_durations = []
for fid, times in log_times_by_track.items():
    duration_s = (max(times) - min(times)) / 1e9
    if fid in transponder_tracks:
        airplane_durations.append(duration_s)
    else:
        drone_durations.append(duration_s)

print(f"Total distinct fused tracks (track_id2): {len(log_times_by_track)}")
print(f"  Airplane candidates (ever has a TOWER_SENSOR_TRANSPONDER measurement): n={len(airplane_durations)}")
print(f"    mean={sum(airplane_durations)/len(airplane_durations):.2f}s  "
      f"median={statistics.median(airplane_durations):.2f}s")
print(f"  Drone candidates (no transponder measurement ever): n={len(drone_durations)}")
print(f"    mean={sum(drone_durations)/len(drone_durations):.2f}s  "
      f"median={statistics.median(drone_durations):.2f}s")

print(f"\nExpected targets: Drone ~30s, Airplane ~600s")
print(f"Observed:         Drone {statistics.median(drone_durations):.1f}s (median), "
      f"Airplane {statistics.median(airplane_durations):.1f}s (median)")

conn.close()
print("\nDONE. No files were written or modified by this script.")
