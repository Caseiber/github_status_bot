"""Unit tests for verdict.py."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from github_status_bot.github_status import Component, Incident, ServiceStatusResponse
from github_status_bot.verdict import VerdictResult, compute_verdict

_NOW = datetime.now(UTC)

_GITHUB_IGNORED = frozenset({"Pages", "Webhooks", "Codespaces", "Copilot AI Model Providers"})


def _make_response(
    indicator: str = "none",
    incidents: list[Incident] | None = None,
    components: list[Component] | None = None,
    fetch_error: bool = False,
) -> ServiceStatusResponse:
    return ServiceStatusResponse(
        indicator=indicator,
        incidents=incidents or [],
        components=components or [],
        fetch_error=fetch_error,
    )


def _active_incident(started_at: datetime | None = None) -> Incident:
    return Incident(id="i1", started_at=started_at, resolved_at=None)


def _resolved_incident(started_at: datetime | None = None) -> Incident:
    return Incident(id="i2", started_at=started_at, resolved_at=_NOW)


# ---------------------------------------------------------------------------
# Up / no incidents
# ---------------------------------------------------------------------------


def test_all_clear_is_up() -> None:
    result = compute_verdict(_make_response(indicator="none"))
    assert result == VerdictResult(
        is_down=False,
        indicator="none",
        duration_seconds=None,
        has_fetch_error=False,
        affected_components=(),
    )


# ---------------------------------------------------------------------------
# Down via indicator (no incidents list)
# ---------------------------------------------------------------------------


def test_minor_indicator_no_incidents_is_down() -> None:
    result = compute_verdict(_make_response(indicator="minor"))
    assert result.is_down is True
    assert result.duration_seconds is None
    assert result.has_fetch_error is False


def test_major_indicator_no_incidents_is_down() -> None:
    result = compute_verdict(_make_response(indicator="major"))
    assert result.is_down is True
    assert result.duration_seconds is None


def test_critical_indicator_no_incidents_is_down() -> None:
    result = compute_verdict(_make_response(indicator="critical"))
    assert result.is_down is True
    assert result.duration_seconds is None


# ---------------------------------------------------------------------------
# Down via unresolved incident
# ---------------------------------------------------------------------------


def test_none_indicator_active_incident_with_started_at_is_down() -> None:
    started = _NOW - timedelta(minutes=30)
    result = compute_verdict(_make_response(incidents=[_active_incident(started)]))
    assert result.is_down is True
    assert result.duration_seconds is not None
    assert result.duration_seconds >= 1799  # ~30 min minus a few ms


def test_none_indicator_active_incident_missing_started_at_is_down() -> None:
    result = compute_verdict(_make_response(incidents=[_active_incident(started_at=None)]))
    assert result.is_down is True
    assert result.duration_seconds is None


# ---------------------------------------------------------------------------
# Resolved incident → up
# ---------------------------------------------------------------------------


def test_resolved_incident_is_up() -> None:
    result = compute_verdict(_make_response(incidents=[_resolved_incident()]))
    assert result.is_down is False
    assert result.duration_seconds is None


# ---------------------------------------------------------------------------
# fetch_error propagation
# ---------------------------------------------------------------------------


def test_fetch_error_propagated() -> None:
    result = compute_verdict(_make_response(fetch_error=True))
    assert result.has_fetch_error is True
    assert result.is_down is False
    assert result.duration_seconds is None
    assert result.affected_components == ()


# ---------------------------------------------------------------------------
# Multiple incidents — duration from earliest started_at
# ---------------------------------------------------------------------------


def test_multiple_incidents_uses_earliest_started_at() -> None:
    earlier = _NOW - timedelta(hours=2)
    later = _NOW - timedelta(hours=1)
    incidents = [
        _active_incident(started_at=later),
        _active_incident(started_at=earlier),
    ]
    result = compute_verdict(_make_response(indicator="major", incidents=incidents))
    assert result.is_down is True
    assert result.duration_seconds is not None
    assert result.duration_seconds >= 7199  # ~2 hours minus a few ms


def test_multiple_incidents_one_missing_started_at_uses_available() -> None:
    started = _NOW - timedelta(minutes=10)
    incidents = [
        _active_incident(started_at=None),
        _active_incident(started_at=started),
    ]
    result = compute_verdict(_make_response(incidents=incidents))
    assert result.is_down is True
    assert result.duration_seconds is not None
    assert result.duration_seconds >= 599


# ---------------------------------------------------------------------------
# affected_components — derived from non-operational components
# ---------------------------------------------------------------------------


def test_all_operational_components_yields_empty_affected() -> None:
    components = [
        Component(name="Git Operations", status="operational"),
        Component(name="API Requests", status="operational"),
    ]
    result = compute_verdict(_make_response(indicator="none", components=components))
    assert result.affected_components == ()


def test_degraded_component_included_in_affected() -> None:
    components = [
        Component(name="Git Operations", status="degraded_performance"),
        Component(name="API Requests", status="operational"),
    ]
    result = compute_verdict(_make_response(indicator="minor", components=components))
    assert result.affected_components == ("Git Operations",)


def test_partial_outage_component_included_in_affected() -> None:
    components = [Component(name="GitHub Actions", status="partial_outage")]
    result = compute_verdict(_make_response(indicator="minor", components=components))
    assert result.affected_components == ("GitHub Actions",)


def test_major_outage_component_included_in_affected() -> None:
    components = [Component(name="GitHub Packages", status="major_outage")]
    result = compute_verdict(_make_response(indicator="major", components=components))
    assert result.affected_components == ("GitHub Packages",)


def test_multiple_non_operational_components_all_included() -> None:
    components = [
        Component(name="Git Operations", status="degraded_performance"),
        Component(name="API Requests", status="partial_outage"),
        Component(name="GitHub Actions", status="operational"),
    ]
    result = compute_verdict(_make_response(indicator="major", components=components))
    assert result.affected_components == ("Git Operations", "API Requests")


# ---------------------------------------------------------------------------
# affected_components — ignored components never surfaced
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["Pages", "Webhooks", "Codespaces", "Copilot AI Model Providers"],
)
def test_ignored_component_excluded_from_affected(name: str) -> None:
    components = [Component(name=name, status="degraded_performance")]
    result = compute_verdict(
        _make_response(indicator="minor", components=components),
        ignored_components=_GITHUB_IGNORED,
    )
    assert result.affected_components == ()


def test_ignored_component_mixed_with_non_ignored() -> None:
    components = [
        Component(name="Git Operations", status="degraded_performance"),
        Component(name="Pages", status="partial_outage"),
        Component(name="Webhooks", status="major_outage"),
    ]
    result = compute_verdict(
        _make_response(indicator="major", components=components),
        ignored_components=_GITHUB_IGNORED,
    )
    assert result.affected_components == ("Git Operations",)
