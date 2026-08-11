"""Static constants shared across the dashboard.

No analytical logic lives here -- only paths, labels, and display
configuration. See docs/DASHBOARD_GUIDE.md for the read-only
architecture this dashboard follows.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
QUERIES_DIR = REPO_ROOT / "queries"
DEFAULT_DB_PATH = REPO_ROOT / "data" / "output" / "sentry.db"
DEFAULT_MCAP_PATH = REPO_ROOT / "data" / "input" / "sanitized.mcap"
RUN_ANALYTICS_PATH = REPO_ROOT / "scripts" / "run_analytics.py"
RUN_VALIDATION_PATH = REPO_ROOT / "scripts" / "run_validation.py"

# Categories in the fixed display order used throughout the dashboard
# (matches queries/executive, queries/operational, queries/technical,
# plus "general" for the one pre-existing root-level file --
# queries/fused_track_duration_by_type.sql -- preserved in its
# original location per explicit instruction, never moved).
CATEGORY_ORDER: tuple[str, ...] = ("executive", "operational", "technical", "general")

CATEGORY_LABELS: dict[str, str] = {
    "executive": "Executive / Leadership",
    "operational": "Operations / Mission Analyst",
    "technical": "Technical / Data Quality",
    "general": "General",
}

# Protected checksum figures (docs/CHECKSUM_RESOLUTION.md). The
# dashboard never computes these in Python -- it only ever displays
# what the corresponding SQL query returns. These constants exist
# solely to label the documented caveats in the UI, not to override or
# recompute anything.
CV_INCORPORATION_TARGET_PCT = "~81% (assignment target -- not reproduced from source data; this dataset computes 97.54%, see docs/analytics/CHECKSUM_RESOLUTION.md)"
DRONE_DURATION_TARGET = "~30 seconds (target)"
AIRPLANE_DURATION_TARGET = "~600 seconds (target)"

# Streamlit page config, shared by every page. No emoji/pictograph
# icon -- plain browser tab title only, consistent with the rest of
# the UI's understated, non-decorative style.
PAGE_ICON = None
LAYOUT = "wide"

# Default row limit for ad-hoc queries on the SQL Queries page (not
# applied to the fixed analytical queries under queries/, which return
# a bounded, already-known result size).
DEFAULT_QUERY_ROW_LIMIT = 1000

# Plotly color palette -- kept small and consistent, no decorative
# gradients or 3D effects.
COLOR_PRIMARY = "#1f77b4"
COLOR_SECONDARY = "#ff7f0e"
COLOR_NEUTRAL = "#7f7f7f"
COLOR_GOOD = "#2ca02c"
COLOR_WARN = "#d62728"
