"""Tests for dashboard/sql_validator.py -- the read-only SQL check used
by the SQL Queries page's ad-hoc query editor.

This is a pure-function unit test suite (no database, no Streamlit) --
it formalizes the 24 cases exercised ad hoc while building the
validator, covering valid statements, forbidden keywords, multi-
statement rejection, and comment-obscured bypass attempts.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.sql_validator import FORBIDDEN_KEYWORDS, validate_read_only_sql


def test_empty_input_rejected():
    assert not validate_read_only_sql("").is_valid
    assert not validate_read_only_sql("   ").is_valid


def test_comment_only_input_rejected():
    result = validate_read_only_sql("-- just a comment\n/* another */")
    assert not result.is_valid


def test_valid_select_accepted():
    result = validate_read_only_sql("SELECT * FROM cv_tracks")
    assert result.is_valid
    assert result.cleaned_sql == "SELECT * FROM cv_tracks"


def test_valid_with_accepted():
    result = validate_read_only_sql("WITH t AS (SELECT 1) SELECT * FROM t")
    assert result.is_valid


def test_valid_explain_accepted():
    assert validate_read_only_sql("EXPLAIN SELECT * FROM cv_tracks").is_valid


def test_valid_pragma_accepted():
    assert validate_read_only_sql("PRAGMA table_info(cv_tracks)").is_valid


def test_lowercase_leading_keyword_accepted():
    assert validate_read_only_sql("select * from cv_tracks").is_valid


def test_trailing_semicolon_accepted():
    result = validate_read_only_sql("SELECT * FROM cv_tracks;")
    assert result.is_valid
    assert result.cleaned_sql == "SELECT * FROM cv_tracks"


def test_disallowed_leading_keyword_rejected():
    result = validate_read_only_sql("EXEC something")
    assert not result.is_valid
    assert "must begin with" in result.error


def test_all_forbidden_keywords_rejected_even_with_select_prefix():
    # Confirms the validator does NOT rely only on the first word:
    # each of these begins with SELECT-shaped text but contains a
    # forbidden keyword later in the statement.
    templates = {
        "INSERT": "SELECT 1 WHERE 1 IN (SELECT INSERT FROM x)",
        "UPDATE": "SELECT * FROM cv_tracks WHERE track_id = (SELECT UPDATE FROM x)",
        "DELETE": "SELECT * FROM cv_tracks; DELETE FROM cv_tracks",  # also multi-statement
        "DROP": "SELECT 1; DROP TABLE cv_tracks",
        "ALTER": "SELECT 1; ALTER TABLE cv_tracks ADD COLUMN x",
        "CREATE": "SELECT 1; CREATE TABLE evil (x INT)",
        "REPLACE": "SELECT 1; REPLACE INTO cv_tracks VALUES (1)",
        "ATTACH": "SELECT 1; ATTACH DATABASE 'x' AS y",
        "DETACH": "SELECT 1; DETACH DATABASE y",
        "VACUUM": "SELECT 1; VACUUM",
    }
    for keyword, sql in templates.items():
        result = validate_read_only_sql(sql)
        assert not result.is_valid, f"{keyword} statement was incorrectly accepted: {sql!r}"


def test_forbidden_keyword_mid_single_statement_rejected():
    result = validate_read_only_sql("SELECT DROP_COUNT FROM (SELECT 1 AS x) WHERE x IN (SELECT 1 WHERE 'DROP' = 'DROP')")
    assert not result.is_valid
    assert "DROP" in result.error


def test_multiple_statements_rejected():
    result = validate_read_only_sql("SELECT 1; SELECT 2;")
    assert not result.is_valid
    assert "one SQL statement" in result.error


def test_multiple_statements_hidden_by_comment_rejected():
    # A comment between two statements must not hide the second
    # statement or its semicolon from the multi-statement check.
    result = validate_read_only_sql("SELECT 1; -- comment\nDROP TABLE cv_tracks;")
    assert not result.is_valid


def test_forbidden_keyword_hidden_inside_line_comment_is_stripped_and_harmless():
    # The forbidden word only ever appears inside a stripped comment,
    # and the remaining single statement is a plain, valid SELECT --
    # this must be accepted, since the comment text itself never
    # reaches SQLite.
    result = validate_read_only_sql("SELECT 1 -- DROP TABLE cv_tracks\n")
    assert result.is_valid
    assert "DROP" not in result.cleaned_sql


def test_forbidden_keyword_hidden_inside_block_comment_is_stripped_and_harmless():
    result = validate_read_only_sql("SELECT /* DROP TABLE cv_tracks */ 1")
    assert result.is_valid


def test_semicolon_hidden_inside_comment_does_not_bypass_multi_statement_check():
    # A semicolon that only exists inside a comment must not be
    # treated as a real statement separator by the comment-stripping
    # step, but the surrounding statement must still be evaluated
    # correctly as a single statement.
    result = validate_read_only_sql("SELECT 1 -- ; DROP TABLE cv_tracks")
    assert result.is_valid


def test_forbidden_keyword_as_substring_of_identifier_is_still_rejected():
    # Documented trade-off: a forbidden keyword is rejected anywhere it
    # appears as a whole word, even inside what could be a string
    # literal or identifier -- this validator intentionally favors
    # over-rejection over risking a missed bypass.
    result = validate_read_only_sql("SELECT 'DROP' AS label")
    assert not result.is_valid


def test_all_forbidden_keywords_present_in_constant():
    expected = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "REPLACE", "ATTACH", "DETACH", "VACUUM"}
    assert set(FORBIDDEN_KEYWORDS) == expected
