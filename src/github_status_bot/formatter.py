"""Formats VerdictResult into a Slack reply string."""

from __future__ import annotations

from github_status_bot.verdict import VerdictResult

_SEVERITY_LABELS: dict[str, str] = {
    "minor": "Degraded",
    "major": "Major Outage",
    "critical": "Critical Outage",
}


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


def format_reply(verdict: VerdictResult, service_name: str, status_page_url: str) -> str:
    source = f"<{status_page_url}|{service_name}'s status page>"

    if verdict.has_fetch_error:
        return (
            f"Couldn't check {service_name}'s status right now — the status API didn't respond. "
            "Try again in a moment."
        )

    if not verdict.is_down:
        return f"{service_name} appears to be *up*... for NOW.\n\nSource: {source}"

    lines = [f"{service_name} is *down* because AI DevOps is a blight on our land.", ""]

    if len(verdict.affected_components) == 1:
        lines.append(f"Affected Area: {verdict.affected_components[0]}")
    elif len(verdict.affected_components) > 1:
        lines.append("Affected Areas:")
        lines.extend(f"• {name}" for name in verdict.affected_components)

    severity = _SEVERITY_LABELS.get(verdict.indicator, verdict.indicator.title())
    lines.append(f"Severity: {severity}")

    if verdict.duration_seconds is not None:
        lines.append(f"Time Down: {_format_duration(verdict.duration_seconds)}")

    lines.extend(["", f"Source: {source}"])

    return "\n".join(lines)


def format_summary_line(verdict: VerdictResult, service_name: str) -> str:
    if verdict.has_fetch_error:
        return f"*{service_name}*: unknown (couldn't reach status API)"
    if not verdict.is_down:
        return f"*{service_name}*: up"
    severity = _SEVERITY_LABELS.get(verdict.indicator, verdict.indicator.title())
    parts = [f"*{service_name}*: down — {severity}"]
    if verdict.duration_seconds is not None:
        parts.append(_format_duration(verdict.duration_seconds))
    return ", ".join(parts)


def format_summary_reply(lines: list[str], bot_name: str) -> str:
    hint = f"Tag with a service name for more detail, e.g. `@{bot_name} github`"
    return "\n".join([*lines, "", hint])
