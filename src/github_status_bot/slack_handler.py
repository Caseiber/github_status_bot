"""slack-bolt app_mention handler. Run via: uv run python -m github_status_bot.slack_handler"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

from github_status_bot.formatter import format_reply
from github_status_bot.github_status import fetch_github_status
from github_status_bot.verdict import VerdictResult, compute_verdict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Idempotency cache (T015)
# ---------------------------------------------------------------------------

_SEEN_TTL: float = 60.0
_SEEN_CAPACITY: int = 100
_seen_events: dict[str, float] = {}


def _is_duplicate(event_id: str) -> bool:
    now = time.monotonic()
    expired = [k for k, ts in list(_seen_events.items()) if now - ts > _SEEN_TTL]
    for k in expired:
        del _seen_events[k]
    if event_id in _seen_events:
        return True
    if len(_seen_events) >= _SEEN_CAPACITY:
        oldest = min(_seen_events, key=lambda k: _seen_events[k])
        del _seen_events[oldest]
    _seen_events[event_id] = now
    return False


# ---------------------------------------------------------------------------
# Per-channel rate-limit guard (T016)
# ---------------------------------------------------------------------------

_COOLDOWN_SECONDS: float = 5.0
_channel_cooldown: dict[str, float] = {}


def _is_rate_limited(channel_id: str) -> bool:
    last = _channel_cooldown.get(channel_id)
    return last is not None and time.monotonic() - last < _COOLDOWN_SECONDS


# ---------------------------------------------------------------------------
# Fallback verdict used when an unexpected exception escapes (T013)
# ---------------------------------------------------------------------------

_FETCH_ERROR_VERDICT = VerdictResult(
    is_down=False, indicator="unknown", duration_seconds=None, has_fetch_error=True,
    affected_components=(),
)


# ---------------------------------------------------------------------------
# Handler — plain function; App registration happens in __main__
# ---------------------------------------------------------------------------


def handle_mention(event: dict[str, Any], say: Any) -> None:
    event_id: str = event.get("event_id", "")
    channel: str = event.get("channel", "")
    thread_ts: str | None = event.get("thread_ts")  # T017

    if _is_duplicate(event_id):
        logger.debug("Skipping duplicate event %s", event_id)
        return

    if _is_rate_limited(channel):
        logger.debug("Rate-limited in channel %s", channel)
        return

    try:
        status = asyncio.run(fetch_github_status())
        verdict = compute_verdict(status)
        text = format_reply(verdict)
    except Exception:
        logger.exception("Unexpected error in handle_mention")
        text = format_reply(_FETCH_ERROR_VERDICT)

    kwargs: dict[str, Any] = {"text": text}
    if thread_ts:
        kwargs["thread_ts"] = thread_ts

    say(**kwargs)
    _channel_cooldown[channel] = time.monotonic()


if __name__ == "__main__":  # pragma: no cover
    from dotenv import load_dotenv
    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    _app = App(
        token=os.environ["SLACK_BOT_TOKEN"],
        signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    )
    _app.event("app_mention")(handle_mention)
    SocketModeHandler(_app, os.environ["SLACK_APP_TOKEN"]).start()  # type: ignore[no-untyped-call]
