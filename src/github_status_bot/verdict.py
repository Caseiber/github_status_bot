"""Derives a human-readable verdict from a GitHubStatusResponse."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from github_status_bot.github_status import Incident, ServiceStatusResponse

_DOWN_INDICATORS = {"minor", "major", "critical"}
_NON_OPERATIONAL_STATUSES = {"degraded_performance", "partial_outage", "major_outage"}


@dataclass(frozen=True)
class VerdictResult:
    is_down: bool
    indicator: str
    duration_seconds: int | None
    has_fetch_error: bool
    affected_components: tuple[str, ...]


def _active_incidents(incidents: list[Incident]) -> list[Incident]:
    return [i for i in incidents if i.resolved_at is None]


def _earliest_started_at(incidents: list[Incident]) -> datetime | None:
    timestamps = [i.started_at for i in incidents if i.started_at is not None]
    return min(timestamps) if timestamps else None


def compute_verdict(
    status_response: ServiceStatusResponse,
    ignored_components: frozenset[str] = frozenset(),
) -> VerdictResult:
    if status_response.fetch_error:
        return VerdictResult(
            is_down=False,
            indicator=status_response.indicator,
            duration_seconds=None,
            has_fetch_error=True,
            affected_components=(),
        )

    active = _active_incidents(status_response.incidents)
    is_down = status_response.indicator in _DOWN_INDICATORS or bool(active)

    duration_seconds: int | None = None
    if is_down:
        earliest = _earliest_started_at(active)
        if earliest is not None:
            duration_seconds = int((datetime.now(UTC) - earliest).total_seconds())

    affected_components = tuple(
        c.name for c in status_response.components
        if c.status in _NON_OPERATIONAL_STATUSES and c.name not in ignored_components
    )

    return VerdictResult(
        is_down=is_down,
        indicator=status_response.indicator,
        duration_seconds=duration_seconds,
        has_fetch_error=False,
        affected_components=affected_components,
    )
