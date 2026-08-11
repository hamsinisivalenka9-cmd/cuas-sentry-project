"""Data Quality page.

Audience: anyone checking pipeline health and relational integrity
before trusting the numbers on the other pages. Shows live SQLite
integrity diagnostics plus the six technical queries covering row
counts, duplicate relationships, enum consistency, class-distribution
completeness, and orphan checks.

The "Run validation" button subprocess-invokes the existing,
already-proven-read-only scripts/run_validation.py unchanged -- it
never reimplements any validation logic here. PRAGMA integrity_check
and PRAGMA foreign_key_check are both inherently read-only diagnostics
and are run directly (not via subprocess) since they cannot modify the
database.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st

from dashboard import database, formatting, sql_loader
from dashboard.components.query_details import query_source_expander
from dashboard.components.sidebar import render_sidebar
from dashboard.components.status import status_banner, zero_rows_is_healthy
from dashboard.components.tables import render_table
from dashboard.constants import DEFAULT_DB_PATH, LAYOUT, PAGE_ICON, RUN_VALIDATION_PATH
from dashboard.query_catalog import entry_for_name

st.set_page_config(page_title="Data Quality", page_icon=PAGE_ICON, layout=LAYOUT)
render_sidebar()


@st.cache_data(show_spinner=False)
def _run(name: str, params_tuple: tuple = (), db_mtime: float = 0.0):
    return sql_loader.run_query(name, dict(params_tuple))


_db_mtime = DEFAULT_DB_PATH.stat().st_mtime if DEFAULT_DB_PATH.exists() else 0.0

st.title("Data Quality")
st.markdown(
    "Pipeline health and relational integrity: live SQLite diagnostics plus the six "
    "technical queries over `data_quality_issues` and the core tables. Use this page to "
    "confirm the database can be trusted before relying on any other page's numbers."
)

# ---------------------------------------------------------------------
# Database metadata
# ---------------------------------------------------------------------
st.subheader("Database metadata")
metadata = database.get_database_metadata(DEFAULT_DB_PATH)
checksum = database.compute_source_mcap_checksum()
cols = st.columns(4)
cols[0].metric("Schema version", metadata.schema_version)
cols[1].metric("Tables", metadata.table_count, help="11 analytical tables plus schema_version (schema metadata).")
cols[2].metric("Views", metadata.view_count)
cols[3].metric("Analytical queries", len(sql_loader.discover_queries()))
cols = st.columns(4)
cols[0].metric("Database size", formatting.format_bytes(metadata.size_bytes))
cols[1].metric("SQLite version", metadata.sqlite_version)
cols[2].metric("Source MCAP MD5", f"{checksum[:12]}..." if checksum else "not found")
cols[3].metric("Database path", str(metadata.db_path.name))

st.markdown("---")

# ---------------------------------------------------------------------
# Integrity status
# ---------------------------------------------------------------------
st.subheader("Integrity status")
st.caption("PRAGMA integrity_check and PRAGMA foreign_key_check, run live against the database on every page load.")
integrity = database.run_integrity_checks(DEFAULT_DB_PATH)
col_a, col_b = st.columns(2)
with col_a:
    status_banner(
        integrity.integrity_check_ok,
        "PRAGMA integrity_check: ok",
        f"PRAGMA integrity_check reported issues: {integrity.integrity_check_detail}",
    )
with col_b:
    status_banner(
        len(integrity.foreign_key_violations) == 0,
        "PRAGMA foreign_key_check: no violations",
        f"PRAGMA foreign_key_check found {len(integrity.foreign_key_violations)} violation(s)",
    )

with st.expander("Run full validation suite (scripts/run_validation.py)"):
    st.caption(
        "Subprocess-invokes the existing, unchanged, already-proven-read-only "
        "scripts/run_validation.py -- no validation logic is reimplemented here."
    )
    if st.button("Run validation now"):
        with st.spinner("Running scripts/run_validation.py --skip-rederivation ..."):
            result = subprocess.run(
                [sys.executable, str(RUN_VALIDATION_PATH), "--skip-rederivation"],
                capture_output=True, text=True, cwd=REPO_ROOT,
            )
        if result.returncode == 0:
            st.success("Validation passed.")
        else:
            st.warning(f"Validation exited with code {result.returncode}.")
        st.code(result.stdout or "(no stdout)", language="text")
        if result.stderr:
            st.code(result.stderr, language="text")
    else:
        st.caption("Or run from a terminal: python scripts/run_validation.py")

st.markdown("---")

# ---------------------------------------------------------------------
# Technical query sections
# ---------------------------------------------------------------------
st.subheader("Table row-count reconciliation")
st.caption("Row counts for every reviewed analytical table -- the fastest way to catch a partial or corrupted load.")
row_counts = _run("table_row_count_reconciliation", db_mtime=_db_mtime)
render_table(row_counts, key="dq_row_counts")
query_source_expander(entry_for_name("table_row_count_reconciliation"))

st.subheader("Duplicate relationship check")
st.caption("Healthy result is zero rows: no (detection, track) pairing should be duplicated in cv_detection_track_links.")
duplicates = _run("duplicate_relationship_check", db_mtime=_db_mtime)
zero_rows_is_healthy(len(duplicates), "No duplicate (detection, track) pairings found.", "Duplicate pairings found")
render_table(duplicates, key="dq_duplicates")
query_source_expander(entry_for_name("duplicate_relationship_check"))

st.subheader("Enum raw/name consistency")
st.caption("Checks that every raw enum value and its decoded name column agree, across 16 enum column pairs.")
enum_consistency = _run("enum_raw_name_consistency", db_mtime=_db_mtime)
all_zero = bool((enum_consistency["inconsistent_rows"] == 0).all()) if not enum_consistency.empty else True
status_banner(all_zero, "All 16 checked enum column pairs are consistent.", "Some enum column pairs show inconsistencies")
render_table(enum_consistency, key="dq_enum_consistency")
query_source_expander(entry_for_name("enum_raw_name_consistency"))

st.subheader("Class-distribution completeness and ordering")
st.caption("Healthy result is zero rows: every cv_track_states row should have exactly 4 well-ordered class-distribution entries.")
class_dist = _run("class_distribution_completeness_and_ordering", db_mtime=_db_mtime)
zero_rows_is_healthy(
    len(class_dist),
    "Every cv_track_states row has exactly 4 well-ordered class-distribution entries.",
    "Some cv_track_states rows have incomplete/misordered class distributions",
)
render_table(class_dist, key="dq_class_dist")
query_source_expander(entry_for_name("class_distribution_completeness_and_ordering"))

st.subheader("Source-message child reconciliation")
st.caption("Checks that every child row (detections, states, etc.) traces back to a real source_messages row.")
child_reconciliation = _run("source_message_child_reconciliation", db_mtime=_db_mtime)
all_zero = bool((child_reconciliation["orphaned_rows"] == 0).all()) if not child_reconciliation.empty else True
status_banner(all_zero, "Every child row traces back to a real source message.", "Some child rows reference a missing source message")
render_table(child_reconciliation, key="dq_child_reconciliation")
query_source_expander(entry_for_name("source_message_child_reconciliation"))

st.subheader("Zero-duration or single-state tracks")
st.caption("Informational, not pass/fail -- see the query's own documented caveats before treating any row as an error.")
zero_duration = _run("zero_duration_or_single_state_tracks", db_mtime=_db_mtime)
render_table(zero_duration, key="dq_zero_duration")
query_source_expander(entry_for_name("zero_duration_or_single_state_tracks"))

st.markdown("---")

# ---------------------------------------------------------------------
# Data-quality issue summary (ETL-generated audit log)
# ---------------------------------------------------------------------
st.subheader("Data-quality issue summary")
st.caption("Findings the ETL pipeline itself recorded and chose not to silently discard, grouped by type and severity.")
issues = _run("data_quality_issue_summary", db_mtime=_db_mtime)
render_table(issues, key="dq_issues")
query_source_expander(entry_for_name("data_quality_issue_summary"))

with st.expander("What does orphaned_detection_reference mean?"):
    st.markdown(
        "**What caused it:** a `cv_track_states` row references a detection via "
        "`last_associated_detection_id`, but no matching row exists in `cv_detections` "
        "for that id. 4 such references exist in the source recording.\n\n"
        "**Why a warning, not a fatal error:** `cv_detection_track_links.detection_id` "
        "is a real, enforced foreign key (`PRAGMA foreign_keys = ON`). Inserting these 4 "
        "pairs would violate it, so the ETL logs them here instead of failing the whole "
        "load over 4 dangling references out of 1,911 detections and 9,496 track-state "
        "restatements.\n\n"
        "**What happened to the rows:** nothing was silently dropped (CLAUDE.md rule 12). "
        "The underlying `cv_track_states` row is kept as-is, with its original "
        "`last_associated_detection_id` value intact. Only the *derived bridge row* in "
        "`cv_detection_track_links` is omitted for that one pairing -- and the omission "
        "itself is recorded as one of these 4 warning rows, with the exact `detection_id`/"
        "`track_id` preserved in the finding.\n\n"
        "**Why it doesn't invalidate the analytical results:** this affects at most 4 of "
        "the 1,864 CV detection-to-track associations (0.2%) -- everywhere else in this "
        "dashboard, `cv_detection_track_links` is exactly the reconciled table these 4 "
        "exclusions were built for, so downstream numbers already reflect this decision "
        "rather than being silently wrong. `scripts/run_validation.py`'s "
        "`orphan_reference_reconciliation` check independently re-derives the same count "
        "of 4 from the raw data on every validation run. Full detail: "
        "`docs/data/DATA_CLEANING.md`, Section 6."
    )
