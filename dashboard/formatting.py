"""Presentation-only formatting helpers.

Everything here formats an already-computed value for display -- it
never derives a new analytical fact. Percentages, means, counts, and
comparisons all come from SQL; this module only decides how many
decimal places, what units suffix, and what color/icon to show.
"""

from __future__ import annotations


def format_count(value: int | float | None) -> str:
    if value is None:
        return "—"
    return f"{int(value):,}"


def format_percentage(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "—"
    return f"{value:.{decimals}f}%"


def format_seconds(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "—"
    return f"{value:,.{decimals}f}s"


def format_bytes(size_bytes: int | None) -> str:
    if size_bytes is None:
        return "—"
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def format_ns_as_seconds(value_ns: int | float | None, decimals: int = 2) -> str:
    if value_ns is None:
        return "—"
    return f"{value_ns / 1e9:,.{decimals}f}s"


def status_word(is_healthy: bool) -> str:
    return "OK" if is_healthy else "ATTENTION"


def status_label(is_healthy: bool, healthy_text: str = "Healthy", unhealthy_text: str = "Needs review") -> str:
    return f"[{status_word(is_healthy)}] {healthy_text if is_healthy else unhealthy_text}"
