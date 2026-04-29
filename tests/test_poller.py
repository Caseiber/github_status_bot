"""Integration tests for poller.py — T033.

fetch_service_status is patched; WebClient is mocked; state file uses tmp_path.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from github_status_bot.github_status import ServiceStatusResponse
from github_status_bot.poller import poll_once

_UP = ServiceStatusResponse(indicator="none", incidents=[], components=[], fetch_error=False)
_MINOR = ServiceStatusResponse(indicator="minor", incidents=[], components=[], fetch_error=False)
_MAJOR = ServiceStatusResponse(indicator="major", incidents=[], components=[], fetch_error=False)
_ERROR = ServiceStatusResponse(indicator="none", incidents=[], components=[], fetch_error=True)


@pytest.fixture()
def state_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "state.json"
    monkeypatch.setenv("STATE_FILE_PATH", str(path))
    return path


@pytest.fixture()
def slack_client() -> MagicMock:
    return MagicMock()


def _patch_fetch(gh_response: ServiceStatusResponse, cl_response: ServiceStatusResponse) -> Any:
    async def _fake(base_url: str) -> ServiceStatusResponse:
        if "github" in base_url:
            return gh_response
        return cl_response

    return patch("github_status_bot.poller.fetch_service_status", side_effect=_fake)


# ---------------------------------------------------------------------------
# No prior state
# ---------------------------------------------------------------------------


def test_no_prior_state_service_up_no_alert(
    state_file: Path, slack_client: MagicMock
) -> None:
    with _patch_fetch(_UP, _UP):
        asyncio.run(poll_once(slack_client, "C_ALERT"))

    slack_client.chat_postMessage.assert_not_called()
    assert json.loads(state_file.read_text()) == {"github": "none", "claude": "none"}


def test_no_prior_state_service_degraded_posts_alert(
    state_file: Path, slack_client: MagicMock
) -> None:
    with _patch_fetch(_MINOR, _UP):
        asyncio.run(poll_once(slack_client, "C_ALERT"))

    slack_client.chat_postMessage.assert_called_once()
    text = slack_client.chat_postMessage.call_args.kwargs["text"]
    assert "*struggling*" in text
    assert json.loads(state_file.read_text())["github"] == "minor"


# ---------------------------------------------------------------------------
# Same indicator — no alert
# ---------------------------------------------------------------------------


def test_same_indicator_no_alert(state_file: Path, slack_client: MagicMock) -> None:
    state_file.write_text(json.dumps({"github": "minor", "claude": "none"}))

    with _patch_fetch(_MINOR, _UP):
        asyncio.run(poll_once(slack_client, "C_ALERT"))

    slack_client.chat_postMessage.assert_not_called()


# ---------------------------------------------------------------------------
# Escalation — minor → major
# ---------------------------------------------------------------------------


def test_escalation_posts_alert(state_file: Path, slack_client: MagicMock) -> None:
    state_file.write_text(json.dumps({"github": "minor", "claude": "none"}))

    with _patch_fetch(_MAJOR, _UP):
        asyncio.run(poll_once(slack_client, "C_ALERT"))

    slack_client.chat_postMessage.assert_called_once()
    text = slack_client.chat_postMessage.call_args.kwargs["text"]
    assert "*down*" in text
    assert json.loads(state_file.read_text())["github"] == "major"


# ---------------------------------------------------------------------------
# Recovery — major → none
# ---------------------------------------------------------------------------


def test_recovery_posts_recovery_alert(state_file: Path, slack_client: MagicMock) -> None:
    state_file.write_text(json.dumps({"github": "major", "claude": "none"}))

    with _patch_fetch(_UP, _UP):
        asyncio.run(poll_once(slack_client, "C_ALERT"))

    slack_client.chat_postMessage.assert_called_once()
    text = slack_client.chat_postMessage.call_args.kwargs["text"]
    assert "back *up*" in text
    assert json.loads(state_file.read_text())["github"] == "none"


# ---------------------------------------------------------------------------
# Fetch error — no alert, state not updated for failed service
# ---------------------------------------------------------------------------


def test_fetch_error_no_alert_state_unchanged(
    state_file: Path, slack_client: MagicMock
) -> None:
    state_file.write_text(json.dumps({"github": "none", "claude": "none"}))

    with _patch_fetch(_ERROR, _UP):
        asyncio.run(poll_once(slack_client, "C_ALERT"))

    slack_client.chat_postMessage.assert_not_called()
    # github state stays "none" (fetch_error means we skip)
    assert json.loads(state_file.read_text())["github"] == "none"


# ---------------------------------------------------------------------------
# Corrupt state file — no crash, treats as no prior state
# ---------------------------------------------------------------------------


def test_corrupt_state_file_no_crash(state_file: Path, slack_client: MagicMock) -> None:
    state_file.write_text("not valid json {{")

    with _patch_fetch(_UP, _UP):
        asyncio.run(poll_once(slack_client, "C_ALERT"))

    slack_client.chat_postMessage.assert_not_called()
    assert state_file.exists()


# ---------------------------------------------------------------------------
# Per-service independence — Claude down, GitHub up
# ---------------------------------------------------------------------------


def test_only_changed_service_posts_alert(
    state_file: Path, slack_client: MagicMock
) -> None:
    state_file.write_text(json.dumps({"github": "none", "claude": "none"}))

    with _patch_fetch(_UP, _MINOR):
        asyncio.run(poll_once(slack_client, "C_ALERT"))

    slack_client.chat_postMessage.assert_called_once()
    text = slack_client.chat_postMessage.call_args.kwargs["text"]
    assert "Claude" in text
    assert "GitHub" not in text


# ---------------------------------------------------------------------------
# Exception paths — fetch raises, Slack post fails, state write fails
# ---------------------------------------------------------------------------


def test_fetch_raises_unexpected_exception_no_crash(
    state_file: Path, slack_client: MagicMock
) -> None:
    with patch(
        "github_status_bot.poller.fetch_service_status",
        side_effect=RuntimeError("boom"),
    ):
        asyncio.run(poll_once(slack_client, "C_ALERT"))

    slack_client.chat_postMessage.assert_not_called()


def test_slack_post_failure_does_not_crash(
    state_file: Path, slack_client: MagicMock
) -> None:
    from slack_sdk.errors import SlackApiError

    slack_client.chat_postMessage.side_effect = SlackApiError(
        "fail", {"error": "channel_not_found"}
    )

    with _patch_fetch(_MINOR, _UP):
        asyncio.run(poll_once(slack_client, "C_ALERT"))

    # State file still written even if post failed
    assert state_file.exists()


def test_state_write_failure_does_not_crash(
    state_file: Path, slack_client: MagicMock
) -> None:
    with _patch_fetch(_UP, _UP), patch(
        "github_status_bot.poller.write_state", side_effect=OSError("disk full")
    ):
        asyncio.run(poll_once(slack_client, "C_ALERT"))

    slack_client.chat_postMessage.assert_not_called()
