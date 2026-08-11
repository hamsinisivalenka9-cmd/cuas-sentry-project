"""Tests for the Stage 8 Streamlit dashboard (dashboard/).

All tests are integration tests against a real, freshly-built database
(real data/input/sanitized.mcap, read-only). The dashboard is a
presentation layer over the already-tested Stage 7/7B analytical SQL
library -- these tests focus on: read-only access, query discovery,
parameter handling, database-safety guarantees, module import health,
and basic page-rendering smoke tests. They do not re-test the SQL
files' own correctness (tests/test_analytics_runner.py already does
that thoroughly) or re-litigate the ETL/schema (tests/test_schema.py,
tests/test_transform.py, etc.).
"""

from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from cuas_etl import database as etl_database
from cuas_etl import extract, load, transform

DASHBOARD_DIR = REPO_ROOT / "dashboard"
PAGES_DIR = DASHBOARD_DIR / "pages"


# ===========================================================================
# Fixtures: a real, freshly-built database file.
# ===========================================================================


@pytest.fixture(scope="module")
def real_db_path(tmp_path_factory) -> Path:
    db_path = tmp_path_factory.mktemp("stage8_dashboard") / "real.db"
    connection = etl_database.initialize_database(db_path)
    extracted = extract.extract_mcap()
    tables = transform.transform_all(extracted)
    load.load_phase1(connection, tables)
    load.load_phase2(connection, tables)
    connection.close()
    return db_path


def _dump_all_tables(db_path: Path) -> dict[str, list[tuple]]:
    connection = sqlite3.connect(str(db_path))
    dump: dict[str, list[tuple]] = {}
    for table_name in etl_database.REVIEWED_TABLES:
        if table_name == "data_quality_issues":
            columns = [r[1] for r in connection.execute("PRAGMA table_info(data_quality_issues)") if r[1] != "detected_at_utc"]
            select_list = ", ".join(f'"{c}"' for c in columns)
            rows = connection.execute(f"SELECT {select_list} FROM data_quality_issues ORDER BY rowid").fetchall()
        else:
            rows = connection.execute(f"SELECT * FROM {table_name} ORDER BY rowid").fetchall()
        dump[table_name] = [tuple(row) for row in rows]
    connection.close()
    return dump


# ===========================================================================
# 1. Database opens in read-only mode
# ===========================================================================


def test_database_opens_read_only(real_db_path):
    from dashboard import database

    connection = database.connect_read_only(real_db_path)
    try:
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("DELETE FROM cv_detections")
    finally:
        connection.close()


def test_database_not_found_raises_clear_error(tmp_path):
    from dashboard import database

    missing_path = tmp_path / "does_not_exist.db"
    with pytest.raises(database.DatabaseNotFoundError, match="build_database.py --rebuild"):
        database.connect_read_only(missing_path)


# ===========================================================================
# 2 & 3. Query discovery
# ===========================================================================


def test_discovery_finds_all_analytical_sql_files(real_db_path):
    from dashboard import sql_loader

    queries = sql_loader.discover_queries()
    names = {q.name for q in queries}
    new_query_names = names - {"fused_track_duration_by_type"}
    assert len(new_query_names) == 21  # Stage 7 (18) + Stage 7B (3)
    assert len(queries) == 22


def test_legacy_root_level_query_is_discoverable(real_db_path):
    from dashboard import sql_loader

    query = sql_loader.get_query("fused_track_duration_by_type")
    assert query.category == "general"
    assert query.path == REPO_ROOT / "queries" / "fused_track_duration_by_type.sql"


# ===========================================================================
# 4. SQL is loaded from disk, never duplicated in Python source
# ===========================================================================


_SQL_KEYWORD_PATTERN = re.compile(r"\b(SELECT|WITH)\b", re.IGNORECASE)


def test_no_dashboard_module_embeds_analytical_sql():
    # Every .py file under dashboard/ must not contain a domain
    # analytical SELECT/WITH statement -- all analytical SQL must come
    # from queries/*.sql on disk, not a Python string. Two files carry
    # narrow, explicitly-approved exceptions, each checked separately
    # below rather than being silently skipped entirely:
    #   - sql_loader.py: 2 tiny identity-list lookups (no JOIN/GROUP BY,
    #     checked by test_sql_loader_lookup_queries_are_non_analytical)
    #   - database.py: 3 pure SQLite-catalog introspection queries
    #     (sqlite_master, schema_version) -- structural metadata, not
    #     CUAS domain logic; checked by
    #     test_database_module_sql_is_pure_catalog_introspection
    #   - pages/6_SQL_Queries.py: the SQL Queries page's named-example
    #     dict for its ad-hoc query editor (Stage 9) -- small, simple,
    #     non-formal-library SELECT/WITH statements for categories not
    #     covered by an existing queries/*.sql file (e.g. radar
    #     observations, classification counts); checked by
    #     test_sql_queries_page_example_queries_are_read_only_and_valid
    allowed_exceptions = {
        DASHBOARD_DIR / "sql_loader.py",
        DASHBOARD_DIR / "database.py",
        PAGES_DIR / "6_SQL_Queries.py",
    }
    for py_file in DASHBOARD_DIR.rglob("*.py"):
        if py_file in allowed_exceptions:
            continue
        text = py_file.read_text()
        # Strip comments/docstrings-ish lines that merely *mention* SQL
        # keywords in prose (e.g. "SELECT/WITH statement" above) by
        # only flagging matches that look like actual embedded SQL:
        # a keyword immediately followed by a plausible SQL fragment on
        # the same or next line inside a string literal.
        code_lines = [
            line for line in text.splitlines()
            if not line.strip().startswith("#") and '"""' not in line
        ]
        suspicious = [
            line for line in code_lines
            if re.search(r'["\'].*\b(SELECT|WITH)\b.*(FROM|AS)\b', line, re.IGNORECASE)
        ]
        assert not suspicious, f"{py_file} appears to embed SQL directly: {suspicious}"


def test_database_module_sql_is_pure_catalog_introspection():
    # The narrow exception granted to dashboard/database.py above: its
    # only 3 embedded SQL statements must all target sqlite_master or
    # schema_version (SQLite/project structural metadata), never a
    # CUAS domain table (cv_detections, fused_tracks, etc.).
    text = (DASHBOARD_DIR / "database.py").read_text()
    embedded_statements = re.findall(r'"(SELECT[^"]+)"', text)
    assert len(embedded_statements) == 3
    for statement in embedded_statements:
        assert "sqlite_master" in statement or "schema_version" in statement, (
            f"dashboard/database.py contains a SQL statement outside its approved "
            f"catalog-introspection exception: {statement!r}"
        )


def test_sql_queries_page_example_queries_are_read_only_and_valid():
    # The narrow exception granted to pages/6_SQL_Queries.py above: every
    # named example must itself pass the same read-only validator the
    # page applies to user-submitted SQL -- these are prefill text, not
    # a bypass of the read-only guarantee.
    import ast

    from dashboard.sql_validator import validate_read_only_sql

    text = (PAGES_DIR / "6_SQL_Queries.py").read_text()
    match = re.search(r"_EXAMPLE_QUERIES: dict\[str, str\] = (\{.*?\n\})\n", text, re.DOTALL)
    assert match, "Could not locate _EXAMPLE_QUERIES dict in 6_SQL_Queries.py"
    examples = ast.literal_eval(match.group(1))
    assert len(examples) >= 8
    for name, sql in examples.items():
        result = validate_read_only_sql(sql)
        assert result.is_valid, f"named example {name!r} is not read-only-valid: {result.error}"


def test_sql_queries_page_example_queries_execute(real_db_path):
    # Every named example must actually run successfully against a real
    # database, applying the same SELECT/WITH-only LIMIT wrapping the
    # page itself applies.
    import ast

    from dashboard import database
    from dashboard.constants import DEFAULT_QUERY_ROW_LIMIT
    from dashboard.sql_validator import validate_read_only_sql

    text = (PAGES_DIR / "6_SQL_Queries.py").read_text()
    match = re.search(r"_EXAMPLE_QUERIES: dict\[str, str\] = (\{.*?\n\})\n", text, re.DOTALL)
    examples = ast.literal_eval(match.group(1))

    connection = database.connect_read_only(real_db_path)
    try:
        for name, sql in examples.items():
            result = validate_read_only_sql(sql)
            statement = result.cleaned_sql.rstrip(";")
            first_word = statement.split(None, 1)[0].upper()
            if first_word in ("SELECT", "WITH"):
                statement = f"SELECT * FROM ({statement}) LIMIT {DEFAULT_QUERY_ROW_LIMIT}"
            cursor = connection.execute(statement)
            rows = cursor.fetchall()
            assert rows, f"named example {name!r} returned no rows against the real database"
    finally:
        connection.close()


def test_sql_loader_lookup_queries_are_non_analytical():
    # The two approved exceptions must remain simple, unfiltered,
    # unjoined identity-column listings -- not a stand-in for real
    # analytical logic.
    from dashboard import sql_loader

    assert "JOIN" not in sql_loader._TRACK_ID_LIST_SQL.upper()
    assert "JOIN" not in sql_loader._FUSED_TRACK_ID_LIST_SQL.upper()
    assert "GROUP BY" not in sql_loader._TRACK_ID_LIST_SQL.upper()
    assert "GROUP BY" not in sql_loader._FUSED_TRACK_ID_LIST_SQL.upper()


# ===========================================================================
# 5, 6, 7. Queries execute by category
# ===========================================================================


def test_executive_queries_execute(real_db_path):
    from dashboard import sql_loader

    for query in sql_loader.discover_queries():
        if query.category != "executive":
            continue
        df = sql_loader.run_query(query.name, db_path=real_db_path)
        assert df is not None


def test_operational_queries_execute_with_valid_parameters(real_db_path):
    from dashboard import sql_loader

    track_id = sql_loader.list_cv_track_ids(real_db_path)[0]
    fused_track_id = sql_loader.list_fused_track_ids(real_db_path)[0]
    for query in sql_loader.discover_queries():
        if query.category != "operational":
            continue
        params = {}
        if "track_id" in query.required_params:
            params["track_id"] = track_id
        if "fused_track_id" in query.required_params:
            params["fused_track_id"] = fused_track_id
        df = sql_loader.run_query(query.name, params, db_path=real_db_path)
        assert df is not None


def test_technical_queries_execute(real_db_path):
    from dashboard import sql_loader

    for query in sql_loader.discover_queries():
        if query.category != "technical":
            continue
        df = sql_loader.run_query(query.name, db_path=real_db_path)
        assert df is not None


def test_general_legacy_query_executes(real_db_path):
    from dashboard import sql_loader

    df = sql_loader.run_query("fused_track_duration_by_type", db_path=real_db_path)
    assert set(df["inferred_class"]) == {"Airplane", "Drone", "Excluded (BIRD)"}


# ===========================================================================
# 8, 9. Invalid input handling
# ===========================================================================


def test_invalid_query_name_rejected(real_db_path):
    from dashboard import sql_loader

    with pytest.raises(sql_loader.QueryNotFoundError):
        sql_loader.run_query("not_a_real_query", db_path=real_db_path)


def test_missing_parameter_produces_clear_error(real_db_path):
    from dashboard import sql_loader

    with pytest.raises(sql_loader.MissingParameterError, match="track_id"):
        sql_loader.run_query("cv_track_history", db_path=real_db_path)


def test_unexpected_parameter_rejected(real_db_path):
    from dashboard import sql_loader

    with pytest.raises(sql_loader.UnexpectedParameterError):
        sql_loader.run_query("cv_incorporation_summary", {"bogus_param": 1}, db_path=real_db_path)


# ===========================================================================
# 10, 11. Query execution cannot modify the database
# ===========================================================================


def test_running_every_query_does_not_modify_database(real_db_path):
    from dashboard import sql_loader

    before = _dump_all_tables(real_db_path)

    track_id = sql_loader.list_cv_track_ids(real_db_path)[0]
    fused_track_id = sql_loader.list_fused_track_ids(real_db_path)[0]
    for query in sql_loader.discover_queries():
        params = {}
        if "track_id" in query.required_params:
            params["track_id"] = track_id
        if "fused_track_id" in query.required_params:
            params["fused_track_id"] = fused_track_id
        sql_loader.run_query(query.name, params, db_path=real_db_path)

    after = _dump_all_tables(real_db_path)
    assert before == after


def test_database_row_count_fingerprint_unchanged_after_dashboard_queries(real_db_path):
    from dashboard import sql_loader

    def fingerprint():
        connection = sqlite3.connect(str(real_db_path))
        counts = {
            t: connection.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in etl_database.REVIEWED_TABLES
        }
        connection.close()
        return counts

    before = fingerprint()
    for query in sql_loader.discover_queries():
        if query.required_params:
            continue
        sql_loader.run_query(query.name, db_path=real_db_path)
    after = fingerprint()
    assert before == after


# ===========================================================================
# 12. Query result columns match dashboard component expectations
# ===========================================================================


def test_result_columns_match_pages_expectations(real_db_path):
    from dashboard import sql_loader

    expectations = {
        "recording_overview": {"total_messages", "recording_duration_seconds"},
        "cv_incorporation_summary": {"total_cv_detections", "incorporation_percentage"},
        "cv_detection_to_track_funnel": {"total_detections", "incorporated_detections", "total_persistent_tracks"},
        "table_row_count_reconciliation": {"table_name", "row_count"},
        "fused_track_duration_by_type": {"inferred_class", "arithmetic_mean_duration_seconds", "median_duration_seconds_supplementary_only"},
        "sensor_utilization_summary": {"sensor_id_name", "measurement_count"},
        "multi_sensor_tracks_duration_comparison": {"sensor_diversity_group", "avg_duration_seconds", "min_duration_seconds", "max_duration_seconds"},
        "fused_track_duration_by_sensor_combination": {"sensor_combination", "avg_duration_seconds"},
        "data_quality_issue_summary": {"issue_type", "severity", "issue_count"},
        "longest_lived_tracks": {"track_type", "track_id", "duration_seconds"},
        "cv_focus_quality_vs_incorporation": {"focus_quality_name", "incorporation_pct"},
        "cv_detection_quality_vs_track_persistence": {"avg_detection_score", "track_duration_seconds", "track_id", "pct_sharp_or_better_focus"},
        "fused_track_classification_stability_vs_measurement_support": {"classification_stability", "avg_measurement_count"},
        "object_class_changes_over_time": {"class_sequence_in_time_order"},
        "sensor_contributions_per_fused_track": set(),
        "duplicate_relationship_check": set(),
        "enum_raw_name_consistency": {"inconsistent_rows"},
        "class_distribution_completeness_and_ordering": set(),
        "source_message_child_reconciliation": {"orphaned_rows"},
        "zero_duration_or_single_state_tracks": set(),
    }
    for name, required_columns in expectations.items():
        df = sql_loader.run_query(name, db_path=real_db_path)
        assert required_columns <= set(df.columns), f"{name} missing expected columns: {required_columns - set(df.columns)}"

    # Parameterized ones checked separately with a real id.
    track_id = sql_loader.list_cv_track_ids(real_db_path)[0]
    fused_track_id = sql_loader.list_fused_track_ids(real_db_path)[0]
    cv_history = sql_loader.run_query("cv_track_history", {"track_id": track_id}, db_path=real_db_path)
    assert {"log_time_ns", "top_predicted_class_probability"} <= set(cv_history.columns)
    fused_history = sql_loader.run_query("fused_track_history", {"fused_track_id": fused_track_id}, db_path=real_db_path)
    assert {"log_time_ns", "object_class_confidence", "contributing_sensors"} <= set(fused_history.columns)


# ===========================================================================
# 13. Dashboard modules import successfully
# ===========================================================================
#
# CUAS_Sentry.py and pages/*.py contain top-level Streamlit calls
# (st.set_page_config, render_sidebar(), etc.) that require an active
# Streamlit ScriptRunContext to execute correctly -- a bare `import`
# outside that context (as a plain pytest test would do) is not a
# meaningful test for them; streamlit.testing.v1.AppTest (used below,
# requirement 14) is the correct, supported way to verify those files.
# The non-UI library modules below have no such requirement and are
# safe to import directly.


def test_core_library_modules_import_successfully():
    import dashboard.constants  # noqa: F401
    import dashboard.database  # noqa: F401
    import dashboard.sql_loader  # noqa: F401
    import dashboard.query_catalog  # noqa: F401
    import dashboard.formatting  # noqa: F401
    import dashboard.charts  # noqa: F401
    import dashboard.components.metrics  # noqa: F401
    import dashboard.components.tables  # noqa: F401
    import dashboard.components.status  # noqa: F401
    import dashboard.components.query_details  # noqa: F401
    import dashboard.components.sidebar  # noqa: F401


# ===========================================================================
# 14. Basic page-rendering smoke tests
# ===========================================================================
#
# These run against whatever is currently built at data/output/sentry.db
# (each page reads dashboard.constants.DEFAULT_DB_PATH internally, the
# same way a real user launching `streamlit run dashboard/CUAS_Sentry.py`
# would) rather than the isolated per-test fixture database used
# elsewhere in this file -- AppTest exercises the actual page scripts
# as Streamlit would run them, which is the point of this check.
# Requires data/output/sentry.db to exist (skipped otherwise).

pytestmark_requires_real_db = pytest.mark.skipif(
    not (REPO_ROOT / "data" / "output" / "sentry.db").exists(),
    reason="data/output/sentry.db not built -- run scripts/build_database.py --rebuild first",
)


@pytestmark_requires_real_db
@pytest.mark.parametrize(
    "script_path",
    [
        DASHBOARD_DIR / "CUAS_Sentry.py",
        PAGES_DIR / "1_Overview.py",
        PAGES_DIR / "2_CV_Detections.py",
        PAGES_DIR / "3_CV_Tracks.py",
        PAGES_DIR / "4_Fused_Tracks.py",
        PAGES_DIR / "5_Data_Quality.py",
        PAGES_DIR / "6_SQL_Queries.py",
        PAGES_DIR / "7_Documentation.py",
    ],
    ids=["cuas_sentry_entry", "overview", "cv_detections", "cv_tracks", "fused_tracks", "data_quality", "sql_queries", "documentation"],
)
def test_page_renders_without_exception(script_path):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(script_path))
    at.run(timeout=60)
    assert not at.exception, f"{script_path.name} raised: {[str(e) for e in at.exception]}"


# ===========================================================================
# 15. CSV export
# ===========================================================================


def test_csv_export_matches_current_result_without_modifying_database(real_db_path):
    from dashboard import sql_loader

    before = _dump_all_tables(real_db_path)

    df = sql_loader.run_query("cv_incorporation_summary", db_path=real_db_path)
    csv_text = df.to_csv(index=False)

    assert "total_cv_detections" in csv_text
    assert "incorporation_percentage" in csv_text
    assert "97.54" in csv_text

    # Round-trip: the CSV text reflects exactly the DataFrame that was
    # already fetched -- no second query, no mutation.
    import io

    import pandas as pd

    round_tripped = pd.read_csv(io.StringIO(csv_text))
    pd.testing.assert_frame_equal(round_tripped, df)

    after = _dump_all_tables(real_db_path)
    assert before == after
