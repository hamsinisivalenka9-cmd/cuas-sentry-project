"""Tests for the Stage 7 analytical SQL layer: every .sql file under
queries/ and the scripts/run_analytics.py runner that executes them.

All tests here are integration tests against a real, freshly-built
database (real data/input/sanitized.mcap, read-only source). Stage 7 is
purely a read layer over the already-tested Stage 6/6B pipeline, so
there is nothing meaningful to unit-test with synthetic fixtures beyond
what tests/test_checksum_queries.py already covers for
queries/fused_track_duration_by_type.sql specifically.

scripts/ has no __init__.py (it is a collection of standalone
entry-point scripts, not an importable package -- consistent with the
rest of this project), so run_analytics.py is imported here via
importlib from its file path.
"""

from __future__ import annotations

import importlib.util
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
QUERIES_DIR = REPO_ROOT / "queries"
RUN_ANALYTICS_PATH = REPO_ROOT / "scripts" / "run_analytics.py"

sys.path.insert(0, str(REPO_ROOT / "src"))
from cuas_etl import database, extract, load, transform  # noqa: E402


def _load_run_analytics_module():
    spec = importlib.util.spec_from_file_location("run_analytics", RUN_ANALYTICS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_analytics = _load_run_analytics_module()


# ===========================================================================
# Fixtures: a real, freshly-built database file (not just a connection --
# the read-only runner needs an actual file path to open via a URI).
# ===========================================================================


@pytest.fixture(scope="module")
def real_db_path(tmp_path_factory) -> Path:
    db_path = tmp_path_factory.mktemp("stage7_analytics") / "real.db"
    connection = database.initialize_database(db_path)
    extracted = extract.extract_mcap()
    tables = transform.transform_all(extracted)
    load.load_phase1(connection, tables)
    load.load_phase2(connection, tables)
    connection.close()
    return db_path


@pytest.fixture(scope="module")
def real_connection(real_db_path: Path) -> sqlite3.Connection:
    connection = database.get_connection(real_db_path)
    yield connection
    connection.close()


def _dump_all_tables(connection: sqlite3.Connection) -> dict[str, list[tuple]]:
    dump: dict[str, list[tuple]] = {}
    for table_name in database.REVIEWED_TABLES:
        if table_name == "data_quality_issues":
            columns = [
                r[1] for r in connection.execute("PRAGMA table_info(data_quality_issues)")
                if r[1] != "detected_at_utc"
            ]
            select_list = ", ".join(f'"{c}"' for c in columns)
            rows = connection.execute(f"SELECT {select_list} FROM data_quality_issues ORDER BY rowid").fetchall()
        else:
            rows = connection.execute(f"SELECT * FROM {table_name} ORDER BY rowid").fetchall()
        dump[table_name] = [tuple(row) for row in rows]
    return dump


# ===========================================================================
# Discovery
# ===========================================================================


def test_discovery_finds_at_least_fifteen_new_queries():
    queries = run_analytics.discover_queries()
    new_queries = [q for q in queries if q.name != "fused_track_duration_by_type"]
    # 18 from Stage 7 + 3 from Stage 7B's cross-dataset gap-fill.
    assert len(new_queries) >= 15
    assert len(new_queries) <= 21


def test_discovery_includes_the_preexisting_general_query():
    queries = run_analytics.discover_queries()
    names = {q.name for q in queries}
    assert "fused_track_duration_by_type" in names
    general = next(q for q in queries if q.name == "fused_track_duration_by_type")
    assert general.category == "general"
    assert general.path == QUERIES_DIR / "fused_track_duration_by_type.sql"


def test_every_query_declares_a_category_in_executive_operational_technical_or_general():
    queries = run_analytics.discover_queries()
    categories = {q.category for q in queries}
    assert categories <= {"executive", "operational", "technical", "general"}
    assert categories >= {"executive", "operational", "technical"}


# ===========================================================================
# Every query parses and runs against a freshly rebuilt database
# ===========================================================================


PARAM_VALUES = {
    "track_id": None,  # filled in by the fixture below
    "fused_track_id": None,
}


@pytest.fixture(scope="module")
def sample_param_values(real_connection: sqlite3.Connection) -> dict[str, object]:
    track_id = real_connection.execute("SELECT track_id FROM cv_tracks LIMIT 1").fetchone()[0]
    fused_track_id = real_connection.execute("SELECT fused_track_id FROM fused_tracks LIMIT 1").fetchone()[0]
    return {"track_id": track_id, "fused_track_id": fused_track_id}


def test_every_query_executes_without_error(real_connection: sqlite3.Connection, sample_param_values):
    queries = run_analytics.discover_queries()
    for query in queries:
        bind_params = {name: sample_param_values[name] for name in query.required_params}
        try:
            cursor = real_connection.execute(query.sql, bind_params)
            cursor.fetchall()
        except sqlite3.Error as exc:
            pytest.fail(f"{query.category}/{query.name} failed to execute: {exc}")


def test_every_query_has_named_result_columns(real_connection: sqlite3.Connection, sample_param_values):
    queries = run_analytics.discover_queries()
    for query in queries:
        bind_params = {name: sample_param_values[name] for name in query.required_params}
        cursor = real_connection.execute(query.sql, bind_params)
        cursor.fetchall()
        assert cursor.description, f"{query.category}/{query.name} returned no column descriptions"
        column_names = [d[0] for d in cursor.description]
        assert all(column_names), f"{query.category}/{query.name} has an unnamed column"


# ===========================================================================
# Grain checks (spot-checked where the expected grain is a fixed, known
# number, not the full dataset's worth of assertions)
# ===========================================================================


def test_recording_overview_returns_exactly_one_row(real_connection):
    sql = (QUERIES_DIR / "executive" / "recording_overview.sql").read_text()
    rows = real_connection.execute(sql).fetchall()
    assert len(rows) == 1


def test_cv_detection_to_track_funnel_returns_exactly_one_row(real_connection):
    sql = (QUERIES_DIR / "executive" / "cv_detection_to_track_funnel.sql").read_text()
    rows = real_connection.execute(sql).fetchall()
    assert len(rows) == 1
    total, incorporated, tracks_receiving, total_tracks, _avg = rows[0]
    assert total == 1911
    assert incorporated == 1864
    assert tracks_receiving == total_tracks == 17


def test_multi_sensor_duration_comparison_returns_two_groups(real_connection):
    sql = (QUERIES_DIR / "executive" / "multi_sensor_tracks_duration_comparison.sql").read_text()
    rows = real_connection.execute(sql).fetchall()
    groups = {row[0] for row in rows}
    assert groups == {"multi-sensor", "single-sensor"}
    counts = {row[0]: row[1] for row in rows}
    assert counts["multi-sensor"] + counts["single-sensor"] == 103


def test_table_row_count_reconciliation_returns_one_row_per_reviewed_table(real_connection):
    sql = (QUERIES_DIR / "technical" / "table_row_count_reconciliation.sql").read_text()
    rows = real_connection.execute(sql).fetchall()
    assert len(rows) == len(database.REVIEWED_TABLES) == 11


def test_class_distribution_completeness_check_returns_zero_rows(real_connection):
    # Healthy result: every one of the 9,496 cv_track_states rows has
    # exactly 4 well-ordered class_distribution entries.
    sql = (QUERIES_DIR / "technical" / "class_distribution_completeness_and_ordering.sql").read_text()
    rows = real_connection.execute(sql).fetchall()
    assert rows == []


def test_duplicate_relationship_check_returns_zero_rows(real_connection):
    sql = (QUERIES_DIR / "technical" / "duplicate_relationship_check.sql").read_text()
    rows = real_connection.execute(sql).fetchall()
    assert rows == []


def test_enum_consistency_check_shows_zero_inconsistencies_in_every_category(real_connection):
    sql = (QUERIES_DIR / "technical" / "enum_raw_name_consistency.sql").read_text()
    rows = real_connection.execute(sql).fetchall()
    assert len(rows) == 16  # one row per checked column pair
    assert all(inconsistent_count == 0 for _column_pair, inconsistent_count in rows)


def test_source_message_child_reconciliation_shows_zero_orphans_in_every_table(real_connection):
    sql = (QUERIES_DIR / "technical" / "source_message_child_reconciliation.sql").read_text()
    rows = real_connection.execute(sql).fetchall()
    assert len(rows) == 4
    assert all(orphaned_rows == 0 for _table_name, orphaned_rows in rows)


def test_object_class_changes_over_time_matches_schema_review_finding_f6(real_connection):
    # docs/SCHEMA_REVIEW.md finding F6: exactly 18 of 103 persistent
    # fused tracks genuinely change object_class within their own
    # state history.
    sql = (QUERIES_DIR / "operational" / "object_class_changes_over_time.sql").read_text()
    rows = real_connection.execute(sql).fetchall()
    assert len(rows) == 18
    for fused_track_id, state_count, distinct_classes, sequence in rows:
        assert distinct_classes >= 2
        assert state_count >= 2
        assert sequence.count("->") == state_count - 1  # every state represented, in order


def test_longest_lived_tracks_returns_up_to_ten_of_each_type(real_connection):
    sql = (QUERIES_DIR / "operational" / "longest_lived_tracks.sql").read_text()
    rows = real_connection.execute(sql).fetchall()
    cv_rows = [r for r in rows if r[0] == "cv_track"]
    fused_rows = [r for r in rows if r[0] == "fused_track"]
    assert len(cv_rows) == 10  # only 17 exist total, so 10 is the LIMIT, not the population
    assert len(fused_rows) == 10


# ---------------------------------------------------------------------------
# Stage 7B: cross-dataset gap-fill queries
# ---------------------------------------------------------------------------


def test_cv_detection_quality_vs_track_persistence_covers_every_cv_track(real_connection):
    sql = (QUERIES_DIR / "operational" / "cv_detection_quality_vs_track_persistence.sql").read_text()
    rows = real_connection.execute(sql).fetchall()
    assert len(rows) == 17  # every persistent CV track, none dropped
    for track_id, det_count, avg_score, pct_sharp, state_count, duration in rows:
        assert det_count > 0  # every CV track received at least one incorporated detection (Stage 3)
        assert 0.0 <= avg_score <= 1.0
        assert 0.0 <= pct_sharp <= 100.0


def test_fused_track_duration_by_sensor_combination_covers_every_fused_track(real_connection):
    sql = (QUERIES_DIR / "executive" / "fused_track_duration_by_sensor_combination.sql").read_text()
    rows = real_connection.execute(sql).fetchall()
    total_tracks = sum(row[1] for row in rows)  # track_count column
    assert total_tracks == 103
    # No combination label should contain the same sensor twice, and
    # every label should be alphabetically sorted (deterministic
    # regardless of which sensor contributed first).
    for combination, *_rest in rows:
        parts = combination.split("+")
        assert parts == sorted(parts)
        assert len(parts) == len(set(parts))


def test_fused_track_classification_stability_matches_schema_review_f6(real_connection):
    sql = (
        QUERIES_DIR / "operational" / "fused_track_classification_stability_vs_measurement_support.sql"
    ).read_text()
    rows = dict((row[0], row) for row in real_connection.execute(sql).fetchall())
    assert set(rows.keys()) == {"stable", "unstable"}
    assert rows["unstable"][1] == 18  # matches docs/SCHEMA_REVIEW.md finding F6
    assert rows["stable"][1] == 103 - 18


# ===========================================================================
# Parameterized queries
# ===========================================================================


def test_cv_track_history_returns_rows_for_a_real_track(real_connection, sample_param_values):
    sql = (QUERIES_DIR / "operational" / "cv_track_history.sql").read_text()
    rows = real_connection.execute(sql, {"track_id": sample_param_values["track_id"]}).fetchall()
    assert len(rows) > 0
    log_times = [row[1] for row in rows]
    assert log_times == sorted(log_times)  # ORDER BY log_time_ns honored


def test_fused_track_history_returns_rows_for_a_real_track(real_connection, sample_param_values):
    sql = (QUERIES_DIR / "operational" / "fused_track_history.sql").read_text()
    rows = real_connection.execute(sql, {"fused_track_id": sample_param_values["fused_track_id"]}).fetchall()
    assert len(rows) > 0


def test_cv_track_history_returns_nothing_for_a_nonexistent_track(real_connection):
    sql = (QUERIES_DIR / "operational" / "cv_track_history.sql").read_text()
    rows = real_connection.execute(sql, {"track_id": 999_999_999}).fetchall()
    assert rows == []


# ===========================================================================
# No query mutates the database
# ===========================================================================


def test_running_every_query_does_not_change_any_table_contents(real_db_path: Path, sample_param_values):
    connection = database.get_connection(real_db_path)
    before = _dump_all_tables(connection)

    for query in run_analytics.discover_queries():
        bind_params = {name: sample_param_values[name] for name in query.required_params}
        connection.execute(query.sql, bind_params).fetchall()

    after = _dump_all_tables(connection)
    connection.close()
    assert before == after


def test_read_only_connection_rejects_a_write(real_db_path: Path):
    connection = run_analytics.connect_read_only(real_db_path)
    try:
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("DELETE FROM cv_detections")
    finally:
        connection.close()

    # And confirm nothing was in fact deleted, via a normal connection.
    check_connection = database.get_connection(real_db_path)
    count = check_connection.execute("SELECT COUNT(*) FROM cv_detections").fetchone()[0]
    check_connection.close()
    assert count == 1911


# ===========================================================================
# Independent cross-checks of key numerical results
# ===========================================================================


def test_cv_incorporation_summary_matches_independent_recount(real_connection):
    sql = (QUERIES_DIR / "executive" / "cv_incorporation_summary.sql").read_text()
    total, incorporated, pct = real_connection.execute(sql).fetchone()

    independent_total = real_connection.execute("SELECT COUNT(*) FROM cv_detections").fetchone()[0]
    independent_incorporated = real_connection.execute(
        "SELECT COUNT(DISTINCT detection_id) FROM cv_detection_track_links"
    ).fetchone()[0]

    assert total == independent_total == 1911
    assert incorporated == independent_incorporated == 1864
    assert pct == round(100.0 * independent_incorporated / independent_total, 2)
    assert pct == 97.54  # regression guard on the documented, unforced figure


def test_sensor_utilization_summary_measurement_counts_sum_to_total(real_connection):
    sql = (QUERIES_DIR / "executive" / "sensor_utilization_summary.sql").read_text()
    rows = real_connection.execute(sql).fetchall()
    total_from_query = sum(row[1] for row in rows)  # measurement_count column
    independent_total = real_connection.execute("SELECT COUNT(*) FROM fused_track_measurements").fetchone()[0]
    assert total_from_query == independent_total == 11992


def test_sensor_combination_query_matches_independent_python_reimplementation(real_connection):
    # Independently recompute each track's sensor set and duration in
    # plain Python (no GROUP_CONCAT, no SQL window functions) and
    # confirm the query's grouped averages match -- a defense against a
    # subtle bug in the pre-sort-then-concat technique specifically.
    rows = real_connection.execute(
        "SELECT fts.fused_track_id, ftm.sensor_id_name "
        "FROM fused_track_measurements ftm "
        "JOIN fused_track_states fts ON fts.fused_track_state_id = ftm.fused_track_state_id"
    ).fetchall()
    sensors_by_track: dict[str, set[str]] = {}
    for fused_track_id, sensor_name in rows:
        sensors_by_track.setdefault(fused_track_id, set()).add(sensor_name)

    durations = dict(
        real_connection.execute("SELECT fused_track_id, duration_seconds FROM v_fused_track_summary").fetchall()
    )

    from collections import defaultdict

    grouped: dict[str, list[float]] = defaultdict(list)
    for track_id, sensors in sensors_by_track.items():
        label = "+".join(sorted(sensors))
        grouped[label].append(durations[track_id])

    sql = (QUERIES_DIR / "executive" / "fused_track_duration_by_sensor_combination.sql").read_text()
    query_results = {
        row[0]: (row[1], row[2]) for row in real_connection.execute(sql).fetchall()
    }  # combination -> (track_count, avg_duration)

    assert set(query_results.keys()) == set(grouped.keys())
    for label, values in grouped.items():
        expected_count = len(values)
        expected_avg = round(sum(values) / len(values), 2)
        actual_count, actual_avg = query_results[label]
        assert actual_count == expected_count
        assert actual_avg == expected_avg


def test_table_row_count_reconciliation_matches_independent_counts(real_connection):
    sql = (QUERIES_DIR / "technical" / "table_row_count_reconciliation.sql").read_text()
    results = dict(real_connection.execute(sql).fetchall())
    for table_name in database.REVIEWED_TABLES:
        independent_count = real_connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        assert results[table_name] == independent_count


# ===========================================================================
# No query file hardcodes a final answer in place of a computed
# expression (static check, not a full SQL parser -- see limitations
# noted inline)
# ===========================================================================

# Numbers that appear as literal comparison/assignment targets outside a
# comment would be suspicious -- e.g. "WHERE incorporation_pct = 81" or
# "SELECT 97.54 AS incorporation_percentage" instead of a computed
# expression. This is a narrow, deliberately conservative heuristic: it
# only flags a bare number immediately after =, <, >, or SELECT at the
# start of a non-comment line, not every occurrence of these digits
# (which would also flag legitimate things like LIMIT 10 or a
# sensor_id_raw = 6 lookup, which the code below explicitly permits by
# only checking a maintained "known checksum target" list rather than
# an unbounded rejection list).
SUSPICIOUS_LITERAL_PATTERN = re.compile(r"(?:=|SELECT)\s*(81(\.\d+)?|97\.54|30(\.\d+)?|35\.86|600(\.\d+)?|614\.68)\b")


def _non_comment_sql(sql_text: str) -> str:
    return "\n".join(line for line in sql_text.splitlines() if not line.strip().startswith("--"))


def test_no_query_file_hardcodes_a_checksum_answer():
    for query in run_analytics.discover_queries():
        body = _non_comment_sql(query.sql)
        match = SUSPICIOUS_LITERAL_PATTERN.search(body)
        assert match is None, (
            f"{query.path} appears to hardcode a checksum-target literal "
            f"({match.group(0)!r} outside a comment) instead of computing it"
        )


# ===========================================================================
# CLI smoke tests (subprocess, exercising scripts/run_analytics.py as a
# real command line, not just its importable functions)
# ===========================================================================


def test_cli_list_exits_zero_and_shows_every_category(real_db_path: Path):
    result = subprocess.run(
        [sys.executable, str(RUN_ANALYTICS_PATH), "--list", "--db-path", str(real_db_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    for category in ("executive", "operational", "technical", "general"):
        assert f"[{category}]" in result.stdout


def test_cli_query_by_name_exits_zero(real_db_path: Path):
    result = subprocess.run(
        [
            sys.executable, str(RUN_ANALYTICS_PATH),
            "--query", "cv_incorporation_summary",
            "--db-path", str(real_db_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "97.54" in result.stdout


def test_cli_category_exits_zero(real_db_path: Path):
    result = subprocess.run(
        [
            sys.executable, str(RUN_ANALYTICS_PATH),
            "--category", "technical",
            "--db-path", str(real_db_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_cli_missing_parameter_exits_nonzero(real_db_path: Path):
    result = subprocess.run(
        [
            sys.executable, str(RUN_ANALYTICS_PATH),
            "--query", "cv_track_history",
            "--db-path", str(real_db_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "requires parameter" in result.stderr


def test_cli_unknown_query_name_exits_nonzero(real_db_path: Path):
    result = subprocess.run(
        [
            sys.executable, str(RUN_ANALYTICS_PATH),
            "--query", "not_a_real_query",
            "--db-path", str(real_db_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0


def test_cli_does_not_modify_the_database_file(real_db_path: Path):
    before_mtime = real_db_path.stat().st_mtime_ns
    result = subprocess.run(
        [sys.executable, str(RUN_ANALYTICS_PATH), "--all", "--db-path", str(real_db_path)],
        capture_output=True,
        text=True,
    )
    # exit code 1 is expected here: --all attempts the two parameterized
    # queries with no --param supplied, which correctly fail closed.
    assert result.returncode in (0, 1)
    after_mtime = real_db_path.stat().st_mtime_ns
    assert before_mtime == after_mtime
