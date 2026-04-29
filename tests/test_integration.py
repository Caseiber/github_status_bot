"""Integration tests — full event → HTTP fetch → verdict → reply pipeline (T019).

All external HTTP is mocked via pytest-httpx. fetch_github_status() is called for
real so the entire call chain is exercised: handler → fetcher → verdict → formatter.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from pytest_httpx import HTTPXMock

from github_status_bot.github_status import COMPONENTS_URL, INCIDENTS_URL, STATUS_URL
from github_status_bot.slack_handler import handle_mention

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


def _channel_event() -> dict[str, Any]:
    return _load("slack_mention_channel.json")


def _thread_event() -> dict[str, Any]:
    return _load("slack_mention_thread.json")


def _retry_event() -> dict[str, Any]:
    return _load("slack_mention_retry.json")


# ---------------------------------------------------------------------------
# Happy path — GitHub up
# ---------------------------------------------------------------------------


def test_full_pipeline_github_up(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=STATUS_URL, json=_load("status_none.json"))
    httpx_mock.add_response(url=INCIDENTS_URL, json=_load("unresolved_empty.json"))
    httpx_mock.add_response(url=COMPONENTS_URL, json=_load("components_all_operational.json"))

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
    httpx_mock.add_response(url=STATUS_URL, json=_load("status_major.json"))
    httpx_mock.add_response(url=INCIDENTS_URL, json=_load("unresolved_active.json"))
    httpx_mock.add_response(url=COMPONENTS_URL, json=_load("components_partial_outage.json"))

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
    httpx_mock.add_response(url=STATUS_URL, json=_load("status_minor.json"))
    httpx_mock.add_response(
        url=INCIDENTS_URL, json=_load("unresolved_missing_started_at.json")
    )
    httpx_mock.add_response(url=COMPONENTS_URL, json=_load("components_all_operational.json"))

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
    httpx_mock.add_response(url=STATUS_URL, json=_load("status_major.json"))
    httpx_mock.add_response(url=INCIDENTS_URL, json=_load("unresolved_active.json"))
    httpx_mock.add_response(url=COMPONENTS_URL, status_code=500)
    httpx_mock.add_response(url=COMPONENTS_URL, status_code=500)  # retry

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
    httpx_mock.add_response(url=STATUS_URL, status_code=500)
    httpx_mock.add_response(url=STATUS_URL, status_code=500)  # retry
    httpx_mock.add_response(url=INCIDENTS_URL, json=_load("unresolved_empty.json"))

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
    httpx_mock.add_response(url=STATUS_URL, json=_load("status_none.json"))
    httpx_mock.add_response(url=INCIDENTS_URL, json=_load("unresolved_empty.json"))
    httpx_mock.add_response(url=COMPONENTS_URL, json=_load("components_all_operational.json"))

    say = MagicMock()
    handle_mention(_thread_event(), say)

    say.assert_called_once()
    assert say.call_args.kwargs.get("thread_ts") == "1234567890.000100"


# ---------------------------------------------------------------------------
# Idempotency — Slack retry with same event_id posts only once
# ---------------------------------------------------------------------------


def test_full_pipeline_retry_event_suppressed(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=STATUS_URL, json=_load("status_none.json"))
    httpx_mock.add_response(url=INCIDENTS_URL, json=_load("unresolved_empty.json"))
    httpx_mock.add_response(url=COMPONENTS_URL, json=_load("components_all_operational.json"))

    say = MagicMock()
    original = _channel_event()
    retry = _retry_event()

    handle_mention(original, say)
    handle_mention(retry, say)  # same event_id — should be suppressed

    assert say.call_count == 1


# ---------------------------------------------------------------------------
# Rate limit — second mention in same channel within cooldown ignored
# ---------------------------------------------------------------------------


def test_full_pipeline_rate_limit_same_channel(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=STATUS_URL, json=_load("status_none.json"))
    httpx_mock.add_response(url=INCIDENTS_URL, json=_load("unresolved_empty.json"))
    httpx_mock.add_response(url=COMPONENTS_URL, json=_load("components_all_operational.json"))

    say = MagicMock()
    first = _channel_event()
    second = {**_channel_event(), "event_id": "Ev01CHANNEL2"}  # different event, same channel

    handle_mention(first, say)
    handle_mention(second, say)  # same channel, within cooldown

    assert say.call_count == 1
