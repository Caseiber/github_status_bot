"""Unit tests for slack_handler.py — T015 idempotency, T016 rate-limit, T017 threads."""

from __future__ import annotations

from collections.abc import Generator, Iterator
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

import github_status_bot.slack_handler as handler
from github_status_bot.github_status import GitHubStatusResponse
from github_status_bot.slack_handler import handle_mention

_UP_RESPONSE = GitHubStatusResponse(
    indicator="none", incidents=[], components=[], fetch_error=False
)


@pytest.fixture(autouse=True)
def reset_handler_state() -> Generator[None, None, None]:
    handler._seen_events.clear()
    handler._channel_cooldown.clear()
    yield
    handler._seen_events.clear()
    handler._channel_cooldown.clear()


@pytest.fixture
def say() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_fetch() -> Iterator[AsyncMock]:
    with patch(
        "github_status_bot.slack_handler.fetch_github_status",
        new_callable=AsyncMock,
        return_value=_UP_RESPONSE,
    ) as m:
        yield m


def _event(
    event_id: str = "ev1",
    channel: str = "C1",
    thread_ts: str | None = None,
) -> dict[str, str]:
    e: dict[str, str] = {"event_id": event_id, "channel": channel}
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
    handle_mention(_event("ev1", channel="C1"), say)
    handle_mention(_event("ev2", channel="C2"), say)  # different channel avoids rate-limit
    assert say.call_count == 2


def test_seen_event_id_expires_after_ttl(
    mock_fetch: AsyncMock, say: MagicMock
) -> None:
    with patch("time.monotonic") as mock_time:
        mock_time.return_value = 0.0
        handle_mention(_event("ev1", channel="C1"), say)
        mock_time.return_value = handler._SEEN_TTL + 1.0
        handle_mention(_event("ev1", channel="C2"), say)  # different channel, post-TTL
    assert say.call_count == 2


# ---------------------------------------------------------------------------
# T016 — Per-channel rate-limit guard
# ---------------------------------------------------------------------------


def test_second_mention_same_channel_within_cooldown_is_ignored(
    mock_fetch: AsyncMock, say: MagicMock
) -> None:
    handle_mention(_event("ev1", channel="C1"), say)
    handle_mention(_event("ev2", channel="C1"), say)
    assert say.call_count == 1


def test_mentions_in_different_channels_both_answered(
    mock_fetch: AsyncMock, say: MagicMock
) -> None:
    handle_mention(_event("ev1", channel="C1"), say)
    handle_mention(_event("ev2", channel="C2"), say)
    assert say.call_count == 2


def test_mention_after_cooldown_is_answered(
    mock_fetch: AsyncMock, say: MagicMock
) -> None:
    with patch("time.monotonic") as mock_time:
        mock_time.return_value = 0.0
        handle_mention(_event("ev1", channel="C1"), say)
        mock_time.return_value = handler._COOLDOWN_SECONDS + 1.0
        handle_mention(_event("ev2", channel="C1"), say)
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
