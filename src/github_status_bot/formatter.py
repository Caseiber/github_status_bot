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

    if verdict.indicator == "minor":
        lines = [f"{service_name} is *struggling* — some services are degraded.", ""]
    else:
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


def format_recovery_alert(service_name: str, status_page_url: str) -> str:
    source = f"<{status_page_url}|{service_name}'s status page>"
    return f"{service_name} is back *up*.\n\nSource: {source}"


def format_unknown_service_reply(token: str, available_names: list[str]) -> str:
    bullets = "\n".join(f"• {name}" for name in available_names)
    return (
        f"Sorry, I don't have *{token}* saved as a service to check :(\n\n"
        f"You can check:\n{bullets}\n\n"
        "or ask Caroline to add it!"
    )

