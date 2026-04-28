"""Formats VerdictResult into a Slack reply string."""

from __future__ import annotations

from github_status_bot.verdict import VerdictResult


def _format_duration(seconds: int) -> str:
    if seconds < 60:
        return "less than a minute"
    minutes = seconds // 60
    if minutes < 60:
        return f"~{minutes}m"
    hours = minutes // 60
    remaining_minutes = minutes % 60
    if remaining_minutes == 0:
        return f"~{hours}h"
    return f"~{hours}h {remaining_minutes}m"


def format_reply(verdict: VerdictResult) -> str:
    if verdict.has_fetch_error:
        return (
            "Couldn't check GitHub's status right now — the status API didn't respond. "
            "Try again in a moment."
        )

    if not verdict.is_down:
        return (
            "GitHub appears to be *up*. "
            "Source: GitHub's official status page (all systems operational)."
        )

    detail = f"indicator: {verdict.indicator}"
    if verdict.duration_seconds is not None:
        detail += f", {_format_duration(verdict.duration_seconds)}"

    return f"GitHub appears to be *down*. Source: GitHub's official status page ({detail})."
