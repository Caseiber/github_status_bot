"""slack-bolt app_mention handler. Run via: uv run python -m github_status_bot.slack_handler"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from typing import Any

from github_status_bot.formatter import format_reply
from github_status_bot.github_status import fetch_service_status
from github_status_bot.services import SERVICES
from github_status_bot.verdict import compute_verdict

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
# Service name parsing
# ---------------------------------------------------------------------------

_SERVICE_KEYS = set(SERVICES.keys())

# Matches the first word after the @mention token (e.g. "<@U123> github")
_SERVICE_RE = re.compile(r"<@[^>]+>\s+(\S+)")

_UNEXPECTED_ERROR_REPLY = (
    "Something went wrong while checking service status. Please try again."
)


def _parse_service(text: str) -> str | None:
    """Return the service keyword from the mention text, or None for a bare mention."""
    m = _SERVICE_RE.search(text)
    if m:
        token = m.group(1).lower()
        if token in _SERVICE_KEYS:
            return token
    return None


# ---------------------------------------------------------------------------
# Handler — plain function; App registration happens in __main__
# ---------------------------------------------------------------------------


def handle_mention(event: dict[str, Any], say: Any) -> None:
    event_id: str = event.get("ts", "")  # ts is unique per message and stable on Slack retries
    channel: str = event.get("channel", "")
    thread_ts: str | None = event.get("thread_ts")  # T017

    raw_text: str = event.get("text", "")
    service_key = _parse_service(raw_text)
    logger.info("Received event ts=%s channel=%s service=%r", event_id, channel, service_key)

    if _is_duplicate(event_id):
        logger.info("Suppressed duplicate event ts=%s", event_id)
        return

    try:
        cfg = SERVICES[service_key or "github"]
        status = asyncio.run(fetch_service_status(cfg.base_url))
        verdict = compute_verdict(status, cfg.ignored_components)
        text = format_reply(verdict, cfg.display_name, cfg.status_page_url)
    except Exception:
        logger.exception("Unexpected error in handle_mention")
        text = _UNEXPECTED_ERROR_REPLY

    kwargs: dict[str, Any] = {"text": text}
    if thread_ts:
        kwargs["thread_ts"] = thread_ts

    say(**kwargs)


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
