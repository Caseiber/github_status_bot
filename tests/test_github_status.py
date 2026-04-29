"""Unit tests for github_status.py — all HTTP calls mocked via pytest-httpx."""

from __future__ import annotations

import json
from datetime import UTC
from pathlib import Path

import httpx
from pytest_httpx import HTTPXMock

from github_status_bot.github_status import (
    COMPONENTS_URL,
    INCIDENTS_URL,
    STATUS_URL,
    Component,
    GitHubStatusResponse,
    Incident,
    _parse_components,
    _parse_dt,
    _parse_incidents,
    _parse_status,
    fetch_github_status,
)

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> dict[str, object]:
    result: dict[str, object] = json.loads((FIXTURES / name).read_text())
    return result


# ---------------------------------------------------------------------------
# _parse_dt
# ---------------------------------------------------------------------------


def test_parse_dt_valid_z_suffix() -> None:
    dt = _parse_dt("2026-04-27T12:00:07.236Z")
    assert dt is not None
    assert dt.tzinfo == UTC
    assert dt.year == 2026


def test_parse_dt_none_input() -> None:
    assert _parse_dt(None) is None


def test_parse_dt_non_string() -> None:
    assert _parse_dt(12345) is None


def test_parse_dt_malformed_string() -> None:
    assert _parse_dt("not-a-date") is None


# ---------------------------------------------------------------------------
# _parse_status
# ---------------------------------------------------------------------------


def test_parse_status_valid() -> None:
    assert _parse_status({"status": {"indicator": "major"}}) == "major"


def test_parse_status_missing_key() -> None:
    assert _parse_status({}) == "unknown"


def test_parse_status_non_dict() -> None:
    assert _parse_status(None) == "unknown"


# ---------------------------------------------------------------------------
# _parse_incidents
# ---------------------------------------------------------------------------


def test_parse_incidents_empty_list() -> None:
    assert _parse_incidents({"incidents": []}) == []


def test_parse_incidents_active_with_started_at() -> None:
    data = fixture("unresolved_active.json")
    incidents = _parse_incidents(data)
    assert len(incidents) == 1
    assert incidents[0].started_at is not None
    assert incidents[0].resolved_at is None


def test_parse_incidents_missing_started_at() -> None:
    data = fixture("unresolved_missing_started_at.json")
    incidents = _parse_incidents(data)
    assert len(incidents) == 1
    assert incidents[0].started_at is None
    assert incidents[0].resolved_at is None


def test_parse_incidents_non_list_value() -> None:
    assert _parse_incidents({"incidents": "bad"}) == []


def test_parse_incidents_missing_key() -> None:
    assert _parse_incidents({}) == []


def test_parse_incidents_skips_non_dict_items() -> None:
    assert _parse_incidents({"incidents": ["not-a-dict", 42]}) == []


# ---------------------------------------------------------------------------
# _parse_components
# ---------------------------------------------------------------------------


def test_parse_components_all_operational() -> None:
    data = fixture("components_all_operational.json")
    components = _parse_components(data)
    assert len(components) == 4
    assert all(isinstance(c, Component) for c in components)
    assert all(c.status == "operational" for c in components)


def test_parse_components_partial_outage() -> None:
    data = fixture("components_partial_outage.json")
    components = _parse_components(data)
    assert len(components) == 4
    git_ops = next(c for c in components if c.name == "Git Operations")
    assert git_ops.status == "degraded_performance"


def test_parse_components_empty_list() -> None:
    assert _parse_components({"components": []}) == []


def test_parse_components_missing_key() -> None:
    assert _parse_components({}) == []


def test_parse_components_non_list_value() -> None:
    assert _parse_components({"components": "bad"}) == []


def test_parse_components_skips_nameless_items() -> None:
    data = {"components": [{"id": "x", "name": "", "status": "operational"}]}
    assert _parse_components(data) == []


def test_parse_components_skips_non_dict_items() -> None:
    data = {"components": ["not-a-dict", 42]}
    assert _parse_components(data) == []


# ---------------------------------------------------------------------------
# fetch_github_status — async (HTTP mocked via pytest-httpx)
# ---------------------------------------------------------------------------


async def test_fetch_up_no_incidents(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=STATUS_URL, json=fixture("status_none.json"))
    httpx_mock.add_response(url=INCIDENTS_URL, json=fixture("unresolved_empty.json"))
    httpx_mock.add_response(url=COMPONENTS_URL, json=fixture("components_all_operational.json"))

    result = await fetch_github_status()

    assert isinstance(result, GitHubStatusResponse)
    assert result.indicator == "none"
    assert result.incidents == []
    assert result.fetch_error is False
    assert len(result.components) == 4
    assert all(c.status == "operational" for c in result.components)


async def test_fetch_down_major_with_incident(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=STATUS_URL, json=fixture("status_major.json"))
    httpx_mock.add_response(url=INCIDENTS_URL, json=fixture("unresolved_active.json"))
    httpx_mock.add_response(url=COMPONENTS_URL, json=fixture("components_partial_outage.json"))

    result = await fetch_github_status()

    assert result.indicator == "major"
    assert len(result.incidents) == 1
    assert isinstance(result.incidents[0], Incident)
    assert result.incidents[0].started_at is not None
    assert result.incidents[0].resolved_at is None
    assert result.fetch_error is False
    assert any(c.status == "degraded_performance" for c in result.components)


async def test_fetch_incident_missing_started_at(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=STATUS_URL, json=fixture("status_minor.json"))
    httpx_mock.add_response(
        url=INCIDENTS_URL, json=fixture("unresolved_missing_started_at.json")
    )
    httpx_mock.add_response(url=COMPONENTS_URL, json=fixture("components_all_operational.json"))

    result = await fetch_github_status()

    assert result.fetch_error is False
    assert len(result.incidents) == 1
    assert result.incidents[0].started_at is None


async def test_fetch_components_failure_returns_empty_components(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(url=STATUS_URL, json=fixture("status_none.json"))
    httpx_mock.add_response(url=INCIDENTS_URL, json=fixture("unresolved_empty.json"))
    httpx_mock.add_response(url=COMPONENTS_URL, status_code=500)
    httpx_mock.add_response(url=COMPONENTS_URL, status_code=500)  # retry

    result = await fetch_github_status()

    assert result.fetch_error is False
    assert result.components == []


async def test_fetch_status_500_both_attempts_returns_fetch_error(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(url=STATUS_URL, status_code=500)
    httpx_mock.add_response(url=STATUS_URL, status_code=500)  # retry
    httpx_mock.add_response(url=INCIDENTS_URL, json=fixture("unresolved_empty.json"))

    result = await fetch_github_status()

    assert result.fetch_error is True


async def test_fetch_incidents_timeout_returns_fetch_error(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(url=STATUS_URL, json=fixture("status_none.json"))
    httpx_mock.add_exception(httpx.ReadTimeout("timed out"), url=INCIDENTS_URL)
    httpx_mock.add_exception(httpx.ReadTimeout("timed out"), url=INCIDENTS_URL)  # retry

    result = await fetch_github_status()

    assert result.fetch_error is True


async def test_fetch_retry_succeeds_on_second_attempt(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=STATUS_URL, status_code=500)  # first attempt
    httpx_mock.add_response(url=STATUS_URL, json=fixture("status_none.json"))  # retry
    httpx_mock.add_response(url=INCIDENTS_URL, json=fixture("unresolved_empty.json"))
    httpx_mock.add_response(url=COMPONENTS_URL, json=fixture("components_all_operational.json"))

    result = await fetch_github_status()

    assert result.indicator == "none"
    assert result.fetch_error is False
