"""Formats VerdictResult into a Slack reply string."""

from __future__ import annotations

from github_status_bot.verdict import VerdictResult

_SEVERITY_LABELS: dict[str, str] = {
    "minor": "Degraded",
    "major": "Major Outage",
    "critical": "Critical Outage",
}

_SOURCE = "<https://www.githubstatus.com|GitHub's status page>"


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
        return f"GitHub appears to be *up*... for NOW.\n\nSource: {_SOURCE}"

    lines = ["GitHub is *down* because AI DevOps is a blight on our land.", ""]

    if len(verdict.affected_components) == 1:
        lines.append(f"Affected Area: {verdict.affected_components[0]}")
    elif len(verdict.affected_components) > 1:
        lines.append("Affected Areas:")
        lines.extend(f"• {name}" for name in verdict.affected_components)

    severity = _SEVERITY_LABELS.get(verdict.indicator, verdict.indicator.title())
    lines.append(f"Severity: {severity}")

    if verdict.duration_seconds is not None:
        lines.append(f"Time Down: {_format_duration(verdict.duration_seconds)}")

    lines.extend(["", f"Source: {_SOURCE}"])

    return "\n".join(lines)
