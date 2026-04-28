"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Generator

import pytest

import github_status_bot.slack_handler as handler


@pytest.fixture(autouse=True)
def reset_handler_state() -> Generator[None, None, None]:
    handler._seen_events.clear()
    handler._channel_cooldown.clear()
    yield
    handler._seen_events.clear()
    handler._channel_cooldown.clear()
