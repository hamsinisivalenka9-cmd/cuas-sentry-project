"""Validates ad-hoc SQL submitted through the SQL Queries page's query
editor before it is ever handed to sqlite3.

This is defense-in-depth on top of (not a substitute for) the
dashboard's other read-only protections: every connection is already
opened via mode=ro + PRAGMA query_only = ON (dashboard/database.py),
which makes any actual write fail at the SQLite engine level
regardless of what this validator does or misses. This module exists
to give the user a clear, immediate error message before that point,
and to reject obviously unsafe input (multiple statements, a write
keyword hidden anywhere in the text, or a write keyword disguised
behind a comment) rather than relying on the database driver's default
behavior alone.

Explicitly does NOT rely only on checking the first word: forbidden
keywords are searched for anywhere in the comment-stripped statement,
and comments are stripped first specifically so a keyword or a
statement separator hidden inside a comment cannot be used to bypass
the first two checks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

ALLOWED_LEADING_KEYWORDS = ("SELECT", "WITH", "EXPLAIN", "PRAGMA")

FORBIDDEN_KEYWORDS = (
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "REPLACE", "ATTACH", "DETACH", "VACUUM",
)

_LINE_COMMENT = re.compile(r"--[^\n]*")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_KEYWORD_PATTERN = {kw: re.compile(rf"\b{kw}\b", re.IGNORECASE) for kw in FORBIDDEN_KEYWORDS}


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    cleaned_sql: str
    error: str | None = None


def _strip_comments(sql: str) -> str:
    without_block = _BLOCK_COMMENT.sub(" ", sql)
    without_line = _LINE_COMMENT.sub(" ", without_block)
    return without_line


def validate_read_only_sql(raw_sql: str) -> ValidationResult:
    """Returns a ValidationResult. Never raises -- callers should
    check .is_valid and show .error to the user rather than relying on
    an exception."""
    if not raw_sql or not raw_sql.strip():
        return ValidationResult(False, "", "Enter a SQL statement to run.")

    stripped = _strip_comments(raw_sql).strip()
    if not stripped:
        return ValidationResult(False, "", "The statement is empty once comments are removed.")

    # Split on ';' to detect multiple statements. A single trailing
    # semicolon (with only whitespace after it) is fine; anything else
    # after the first ';' means more than one statement was submitted.
    parts = [p for p in stripped.split(";")]
    non_empty_parts = [p for p in parts if p.strip()]
    if len(non_empty_parts) > 1:
        return ValidationResult(
            False, stripped,
            "Only one SQL statement is allowed per run. Remove the additional statement(s) after the first ';'.",
        )

    statement = non_empty_parts[0].strip() if non_empty_parts else ""
    if not statement:
        return ValidationResult(False, stripped, "The statement is empty once comments are removed.")

    first_word_match = re.match(r"[A-Za-z]+", statement)
    first_word = first_word_match.group(0).upper() if first_word_match else ""
    if first_word not in ALLOWED_LEADING_KEYWORDS:
        return ValidationResult(
            False, statement,
            f"Statement must begin with one of: {', '.join(ALLOWED_LEADING_KEYWORDS)}. "
            f"Found: {first_word or '(none)'!r}.",
        )

    # Defense-in-depth: search the entire statement, not only its
    # first word, for a forbidden keyword -- e.g. this catches an
    # attempt to hide a write inside a CTE name, a string literal
    # crafted to look like a comment, or any other position a naive
    # first-word-only check would miss.
    for keyword, pattern in _KEYWORD_PATTERN.items():
        if pattern.search(statement):
            return ValidationResult(
                False, statement,
                f"Statement contains the disallowed keyword '{keyword}'. "
                f"Only read-only statements are permitted "
                f"({', '.join(ALLOWED_LEADING_KEYWORDS)}).",
            )

    return ValidationResult(True, statement, None)
