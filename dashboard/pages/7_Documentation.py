"""Documentation page.

A plain index of the project's design and analysis documents. This
page reads no data from the database -- it only lists file paths that
exist in this repository (verified against the files on disk when this
page was written) so a reader can open them in an editor or terminal.
No file is fetched, rendered, or linked as a live URL from here.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st

from dashboard.components.sidebar import render_sidebar
from dashboard.constants import LAYOUT, PAGE_ICON

st.set_page_config(page_title="Documentation", page_icon=PAGE_ICON, layout=LAYOUT)
render_sidebar()

st.title("Documentation")
st.markdown(
    "An index of this project's design and analysis documents, grouped by topic. Paths are "
    "relative to the repository root -- open them in an editor or with `cat`/a Markdown "
    "viewer; this page does not render their content."
)


def _doc_section(title: str, docs: list[tuple[str, str]]) -> None:
    st.subheader(title)
    for path, description in docs:
        st.markdown(f"`{path}` -- {description}")


st.markdown("---")
_doc_section(
    "Getting started",
    [
        ("START_HERE.md", "Step-by-step replication instructions: setup, build, validate, run the dashboard, run tests."),
        ("README.md", "Concise project overview and dashboard summary."),
        ("DESIGN.md", "Concise architecture and design-decision overview -- what the project does, the data model, the ETL flow, and trade-offs."),
    ],
)

st.markdown("---")
_doc_section(
    "Database design",
    [
        ("docs/architecture/DATABASE_DESIGN.md", "The SQLite schema design: tables, grain, keys, and rationale."),
        ("docs/architecture/TABLE_GRAIN.md", "Quick-reference table of each table's grain, primary key, and row count."),
        ("docs/architecture/NORMALIZATION_DECISIONS.md", "Explains each normalization choice (child tables, bridge tables, repeated fields)."),
        ("docs/architecture/ERD.md", "Entity-relationship diagram and foreign-key relationships."),
        ("docs/architecture/SCHEMA_REVIEW.md", "An adversarial review of the initial schema design and the changes it produced."),
        ("docs/data/DATA_DICTIONARY.md", "Plain-language description of every table and column in the database."),
    ],
)

st.markdown("---")
_doc_section(
    "Data inspection and cleaning",
    [
        ("docs/data/MCAP_INSPECTION.md", "Read-only structural inspection of the source MCAP file's topics and message shapes."),
        ("docs/data/KEY_ANALYSIS.md", "Identifier and relationship analysis used to justify primary/foreign key decisions."),
        ("docs/data/DATA_CLEANING.md", "Every cleaning, normalization, or exclusion rule actually implemented in the ETL, with evidence."),
    ],
)

st.markdown("---")
_doc_section(
    "Analytics and the two headline checks",
    [
        ("docs/analytics/ANALYTICAL_INSIGHTS.md", "The full analytical query library: business question, tables, join path, and grain for each query."),
        ("docs/analytics/SQL_QUERY_GUIDE.md", "A practical guide to running the analytical queries and exploring the database directly with sqlite3."),
        ("docs/analytics/CHECKSUM_RESOLUTION.md", "The single canonical investigation, root cause, approval, and implementation record for the CV-incorporation and Drone/Airplane duration checks."),
        ("docs/data/SOURCE_FIDELITY_CORRECTION.md", "A correction record for a source-fidelity issue found during analysis."),
    ],
)

st.markdown("---")
_doc_section(
    "Dashboard",
    [
        ("docs/dashboard/DASHBOARD_GUIDE.md", "Dashboard architecture, page descriptions, caching, and read-only guarantees."),
    ],
)

st.markdown("---")
_doc_section(
    "Project instructions and AI usage",
    [
        ("CLAUDE.md", "The project's governing objective, critical rules, and expected analytical checks (used to direct AI-assisted work in this repository)."),
        ("AGENTS.md", "An equivalent copy of the project instructions for AI agents/tools that read AGENTS.md instead of CLAUDE.md."),
        ("docs/project/AI_USAGE.md", "Disclosure of how an AI coding assistant was used to build this project, and what the submitter verified personally."),
    ],
)

st.markdown("---")
_doc_section(
    "Submission audit",
    [
        ("docs/project/FINAL_SUBMISSION_AUDIT.md", "Final submission-quality audit: deliverables verified, test/validation results, Docker and clean-room verification, and archive contents."),
    ],
)

st.markdown("---")
_doc_section(
    "Stage summaries",
    [
        ("docs/stages/STAGE_01_SUMMARY.txt", "Stage 1 -- environment and prerequisite verification."),
        ("docs/stages/STAGE_02_SUMMARY.txt", "Stage 2 -- read-only MCAP structural inspection."),
        ("docs/stages/STAGE_03_SUMMARY.txt", "Stage 3 -- identifier, message-grain, and relationship (key) analysis."),
        ("docs/stages/STAGE_04_SUMMARY.txt", "Stage 4 -- database schema design."),
        ("docs/stages/STAGE_05A_SUMMARY.txt", "Stage 5A -- skeptical schema review."),
        ("docs/stages/STAGE_05B_SUMMARY.txt", "Stage 5B -- schema revisions following the review."),
        ("docs/stages/STAGE_06_SUMMARY.txt", "Stage 6 -- ETL pipeline and database build."),
        ("docs/stages/STAGE_07_SUMMARY.txt", "Stage 7 -- analytical SQL query library."),
        ("docs/stages/STAGE_08_SUMMARY.txt", "Stage 8 -- Streamlit dashboard build."),
        ("docs/stages/STAGE_09_UI_AND_NAVIGATION_SUMMARY.txt", "Stage 9 -- UI cleanup, navigation restructuring, and this SQL Queries page."),
    ],
)
