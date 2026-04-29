"""Unit tests for slack_handler.py — T015 idempotency, T017 threads."""

from __future__ import annotations

import time
from collections.abc import Iterator
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

import github_status_bot.slack_handler as handler
from github_status_bot.github_status import ServiceStatusResponse
from github_status_bot.slack_handler import handle_mention

_UP_RESPONSE = ServiceStatusResponse(
    indicator="none", incidents=[], components=[], fetch_error=False
)

_CHANNEL = "C1"  # single channel used throughout — bot operates in one channel


@pytest.fixture
def say() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_fetch() -> Iterator[AsyncMock]:
    with patch(
        "github_status_bot.slack_handler.fetch_service_status",
        new_callable=AsyncMock,
        return_value=_UP_RESPONSE,
    ) as m:
        yield m


def _event(
    event_id: str = "ev1",
    thread_ts: str | None = None,
    text: str = "<@U1> github",
) -> dict[str, str]:
    e: dict[str, str] = {"event_id": event_id, "channel": _CHANNEL, "text": text}
    if thread_ts is not None:
        e["thread_ts"] = thread_ts
    return e


# ---------------------------------------------------------------------------
# T015 — Idempotency
# ---------------------------------------------------------------------------


def test_duplicate_event_id_posts_only_once(
    mock_fetch: AsyncMock, say: MagicMock
) -> None:
    handle_mention(_event("ev1"), say)
    handle_mention(_event("ev1"), say)
    assert say.call_count == 1


def test_distinct_event_ids_each_post(mock_fetch: AsyncMock, say: MagicMock) -> None:
    handle_mention(_event("ev1"), say)
    handle_mention(_event("ev2"), say)
    assert say.call_count == 2


def test_seen_event_id_expires_after_ttl(
    mock_fetch: AsyncMock, say: MagicMock
) -> None:
    with patch("time.monotonic") as mock_time:
        mock_time.return_value = 0.0
        handle_mention(_event("ev1"), say)
        mock_time.return_value = handler._SEEN_TTL + 1.0
        handle_mention(_event("ev1"), say)
    assert say.call_count == 2


# ---------------------------------------------------------------------------
# T017 — Thread-aware replies
# ---------------------------------------------------------------------------


def test_thread_mention_replies_in_thread(
    mock_fetch: AsyncMock, say: MagicMock
) -> None:
    handle_mention(_event("ev1", thread_ts="123.456"), say)
    say.assert_called_once_with(text=ANY, thread_ts="123.456")


def test_channel_root_mention_has_no_thread_ts(
    mock_fetch: AsyncMock, say: MagicMock
) -> None:
    handle_mention(_event("ev1"), say)
    assert "thread_ts" not in say.call_args.kwargs


# ---------------------------------------------------------------------------
# Cache capacity eviction (line coverage for _is_duplicate eviction path)
# ---------------------------------------------------------------------------


def test_cache_at_capacity_evicts_oldest_and_accepts_new(
    mock_fetch: AsyncMock, say: MagicMock
) -> None:
    # Pre-fill to one below capacity with recent timestamps
    now = time.monotonic()
    for i in range(handler._SEEN_CAPACITY - 1):
        handler._seen_events[f"old{i}"] = now

    with patch("time.monotonic") as mock_time:
        mock_time.return_value = now + 1.0
        handle_mention(_event("ev_fill"), say)  # fills to capacity
        mock_time.return_value = now + 2.0
        handle_mention(_event("ev_over"), say)  # triggers eviction

    assert say.call_count == 2
    assert len(handler._seen_events) == handler._SEEN_CAPACITY


# ---------------------------------------------------------------------------
# Unexpected exception fallback
# ---------------------------------------------------------------------------


def test_unexpected_exception_in_fetch_returns_error_reply(say: MagicMock) -> None:
    with patch(
        "github_status_bot.slack_handler.fetch_service_status",
        new_callable=AsyncMock,
        side_effect=RuntimeError("unexpected boom"),
    ):
        handle_mention(_event("ev_err"), say)

    say.assert_called_once()
    text = say.call_args.kwargs["text"]
    assert "something went wrong" in text.lower()
    assert "*up*" not in text
    assert "*down*" not in text


# ---------------------------------------------------------------------------
# Service routing — bare mention → summary
# ---------------------------------------------------------------------------


def test_bare_mention_calls_fetch_for_each_service(say: MagicMock) -> None:
    with patch(
        "github_status_bot.slack_handler.fetch_service_status",
        new_callable=AsyncMock,
        return_value=_UP_RESPONSE,
    ) as mock:
        handle_mention(_event("ev1", text="<@U1>"), say)

    assert mock.call_count == 2  # once per service (github + claude)
    say.assert_called_once()
    text = say.call_args.kwargs["text"]
    assert "*GitHub*" in text
    assert "*Claude*" in text
    assert "github_status_bot github" in text


def test_named_service_github_calls_fetch_once(mock_fetch: AsyncMock, say: MagicMock) -> None:
    handle_mention(_event("ev1", text="<@U1> github"), say)
    assert mock_fetch.call_count == 1
    text = say.call_args.kwargs["text"]
    assert "GitHub" in text
    assert "*Claude*" not in text


def test_named_service_claude_calls_fetch_once(say: MagicMock) -> None:
    with patch(
        "github_status_bot.slack_handler.fetch_service_status",
        new_callable=AsyncMock,
        return_value=_UP_RESPONSE,
    ) as mock:
        handle_mention(_event("ev1", text="<@U1> claude"), say)

    assert mock.call_count == 1
    text = say.call_args.kwargs["text"]
    assert "Claude" in text
    assert "*GitHub*" not in text


def test_unknown_service_keyword_falls_back_to_summary(say: MagicMock) -> None:
    with patch(
        "github_status_bot.slack_handler.fetch_service_status",
        new_callable=AsyncMock,
        return_value=_UP_RESPONSE,
    ) as mock:
        handle_mention(_event("ev1", text="<@U1> jenkins"), say)

    # Unknown keyword → treated as bare mention → summary for all services
    assert mock.call_count == 2
    text = say.call_args.kwargs["text"]
    assert "*GitHub*" in text
    assert "*Claude*" in text
