"""slack-bolt app_mention handler. Run via: uv run python -m github_status_bot.slack_handler"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from slack_bolt import App

from github_status_bot.formatter import format_reply
from github_status_bot.github_status import fetch_github_status
from github_status_bot.verdict import compute_verdict

logger = logging.getLogger(__name__)

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN", ""),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET", ""),
)


@app.event("app_mention")
def handle_mention(event: dict[str, Any], say: Any) -> None:
    thread_ts: str | None = event.get("thread_ts")

    status = asyncio.run(fetch_github_status())
    verdict = compute_verdict(status)
    text = format_reply(verdict)

    kwargs: dict[str, Any] = {"text": text}
    if thread_ts:
        kwargs["thread_ts"] = thread_ts

    say(**kwargs)


if __name__ == "__main__":
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    logging.basicConfig(level=logging.INFO)
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()  # type: ignore[no-untyped-call]
