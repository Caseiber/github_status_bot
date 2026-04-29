"""Integration tests — full event → HTTP fetch → verdict → reply pipeline (T019).

All external HTTP is mocked via pytest-httpx. fetch_service_status() is called for
real so the entire call chain is exercised: handler → fetcher → verdict → formatter.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from pytest_httpx import HTTPXMock

from github_status_bot.slack_handler import handle_mention

FIXTURES = Path(__file__).parent / "fixtures"

_GH_BASE = "https://www.githubstatus.com/api/v2"
_GH_STATUS = f"{_GH_BASE}/status.json"
_GH_INCIDENTS = f"{_GH_BASE}/incidents/unresolved.json"
_GH_COMPONENTS = f"{_GH_BASE}/components.json"

_CL_BASE = "https://status.claude.com/api/v2"
_CL_STATUS = f"{_CL_BASE}/status.json"
_CL_INCIDENTS = f"{_CL_BASE}/incidents/unresolved.json"
_CL_COMPONENTS = f"{_CL_BASE}/components.json"


def _load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


def _channel_event() -> dict[str, Any]:
    return _load("slack_mention_channel.json")


def _thread_event() -> dict[str, Any]:
    return _load("slack_mention_thread.json")


def _retry_event() -> dict[str, Any]:
    return _load("slack_mention_retry.json")


def _bare_event() -> dict[str, Any]:
    return _load("slack_mention_bare.json")


def _mock_gh(httpx_mock: HTTPXMock, status: str, incidents: str, components: str) -> None:
    httpx_mock.add_response(url=_GH_STATUS, json=_load(status))
    httpx_mock.add_response(url=_GH_INCIDENTS, json=_load(incidents))
    httpx_mock.add_response(url=_GH_COMPONENTS, json=_load(components))


def _mock_cl(httpx_mock: HTTPXMock, status: str, incidents: str, components: str) -> None:
    httpx_mock.add_response(url=_CL_STATUS, json=_load(status))
    httpx_mock.add_response(url=_CL_INCIDENTS, json=_load(incidents))
    httpx_mock.add_response(url=_CL_COMPONENTS, json=_load(components))


# ---------------------------------------------------------------------------
# Happy path — GitHub up (named service)
# ---------------------------------------------------------------------------


def test_full_pipeline_github_up(httpx_mock: HTTPXMock) -> None:
    _mock_gh(httpx_mock, "status_none.json", "unresolved_empty.json", "components_all_operational.json")

    say = MagicMock()
    handle_mention(_channel_event(), say)

    say.assert_called_once()
    text = say.call_args.kwargs["text"]
    assert "*up*" in text
    assert "GitHub's status page" in text
    assert "*down*" not in text


# ---------------------------------------------------------------------------
# Down — with active incident, duration, and a degraded component
# ---------------------------------------------------------------------------


def test_full_pipeline_github_down_with_component(httpx_mock: HTTPXMock) -> None:
    _mock_gh(httpx_mock, "status_major.json", "unresolved_active.json", "components_partial_outage.json")

    say = MagicMock()
    handle_mention(_channel_event(), say)

    say.assert_called_once()
    text = say.call_args.kwargs["text"]
    assert "*down*" in text
    assert "Affected Area: Git Operations" in text
    assert "Severity: Major Outage" in text
    assert "Time Down:" in text
    assert "GitHub's status page" in text


# ---------------------------------------------------------------------------
# Down — missing started_at; no Time Down line
# ---------------------------------------------------------------------------


def test_full_pipeline_down_missing_started_at(httpx_mock: HTTPXMock) -> None:
    _mock_gh(httpx_mock, "status_minor.json", "unresolved_missing_started_at.json", "components_all_operational.json")

    say = MagicMock()
    handle_mention(_channel_event(), say)

    say.assert_called_once()
    text = say.call_args.kwargs["text"]
    assert "*down*" in text
    assert "Severity: Degraded" in text
    assert "Time Down:" not in text


# ---------------------------------------------------------------------------
# Down — components endpoint fails; reply still sent, no Affected Area line
# ---------------------------------------------------------------------------


def test_full_pipeline_components_failure_reply_sent(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=_GH_STATUS, json=_load("status_major.json"))
    httpx_mock.add_response(url=_GH_INCIDENTS, json=_load("unresolved_active.json"))
    httpx_mock.add_response(url=_GH_COMPONENTS, status_code=500)
    httpx_mock.add_response(url=_GH_COMPONENTS, status_code=500)  # retry

    say = MagicMock()
    handle_mention(_channel_event(), say)

    say.assert_called_once()
    text = say.call_args.kwargs["text"]
    assert "*down*" in text
    assert "Affected Area" not in text
    assert "Severity: Major Outage" in text


# ---------------------------------------------------------------------------
# API unreachable — error reply
# ---------------------------------------------------------------------------


def test_full_pipeline_api_unreachable(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=_GH_STATUS, status_code=500)
    httpx_mock.add_response(url=_GH_STATUS, status_code=500)  # retry
    httpx_mock.add_response(url=_GH_INCIDENTS, json=_load("unresolved_empty.json"))

    say = MagicMock()
    handle_mention(_channel_event(), say)

    say.assert_called_once()
    text = say.call_args.kwargs["text"]
    assert "couldn't check" in text.lower()
    assert "*up*" not in text
    assert "*down*" not in text


# ---------------------------------------------------------------------------
# Thread-aware reply
# ---------------------------------------------------------------------------


def test_full_pipeline_thread_mention_replies_in_thread(httpx_mock: HTTPXMock) -> None:
    _mock_gh(httpx_mock, "status_none.json", "unresolved_empty.json", "components_all_operational.json")

    say = MagicMock()
    handle_mention(_thread_event(), say)

    say.assert_called_once()
    assert say.call_args.kwargs.get("thread_ts") == "1234567890.000100"


# ---------------------------------------------------------------------------
# Idempotency — Slack retry with same event_id posts only once
# ---------------------------------------------------------------------------


def test_full_pipeline_retry_event_suppressed(httpx_mock: HTTPXMock) -> None:
    _mock_gh(httpx_mock, "status_none.json", "unresolved_empty.json", "components_all_operational.json")

    say = MagicMock()
    original = _channel_event()
    retry = _retry_event()

    handle_mention(original, say)
    handle_mention(retry, say)  # same event_id — should be suppressed

    assert say.call_count == 1


# ---------------------------------------------------------------------------
# Two distinct mentions both answered (no rate-limit)
# ---------------------------------------------------------------------------


def test_two_distinct_mentions_both_answered(httpx_mock: HTTPXMock) -> None:
    _mock_gh(httpx_mock, "status_none.json", "unresolved_empty.json", "components_all_operational.json")
    _mock_gh(httpx_mock, "status_none.json", "unresolved_empty.json", "components_all_operational.json")

    say = MagicMock()
    first = _channel_event()
    second = {**_channel_event(), "ts": "1234567890.000200"}

    handle_mention(first, say)
    handle_mention(second, say)

    assert say.call_count == 2


# ---------------------------------------------------------------------------
# Bare mention — compact summary for all services
# ---------------------------------------------------------------------------


def test_full_pipeline_bare_mention_summary(httpx_mock: HTTPXMock) -> None:
    _mock_gh(httpx_mock, "status_none.json", "unresolved_empty.json", "components_all_operational.json")
    _mock_cl(httpx_mock, "status_none.json", "unresolved_empty.json", "components_all_operational.json")

    say = MagicMock()
    handle_mention(_bare_event(), say)

    say.assert_called_once()
    text = say.call_args.kwargs["text"]
    assert "*GitHub*" in text
    assert "*Claude*" in text
    assert "github_status_bot github" in text


# ---------------------------------------------------------------------------
# Claude named service
# ---------------------------------------------------------------------------


def test_full_pipeline_claude_up(httpx_mock: HTTPXMock) -> None:
    _mock_cl(httpx_mock, "status_none.json", "unresolved_empty.json", "components_all_operational.json")

    say = MagicMock()
    event = {**_channel_event(), "event_id": "Ev01CLAUDE01", "text": "<@U99999BOTID> claude"}
    handle_mention(event, say)

    say.assert_called_once()
    text = say.call_args.kwargs["text"]
    assert "*up*" in text
    assert "Claude's status page" in text
    assert "*down*" not in text
