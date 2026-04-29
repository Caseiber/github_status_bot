"""Phase 2 proactive status poller — intended to be run via cron.

Cron example (every 5 minutes):
    */5 * * * * /path/to/.venv/bin/python -m github_status_bot.poller

For each configured service, compares the live indicator against the last-alerted
indicator stored in the state file. Posts a Slack alert only when the indicator
changes (escalation, de-escalation, or recovery). Same indicator = no post.
"""

from __future__ import annotations

import asyncio
import logging
import os

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from github_status_bot.formatter import format_recovery_alert, format_reply
from github_status_bot.github_status import ServiceStatusResponse, fetch_service_status
from github_status_bot.services import SERVICES
from github_status_bot.state import read_state, write_state
from github_status_bot.transition import Transition, compute_transition
from github_status_bot.verdict import compute_verdict

logger = logging.getLogger(__name__)


async def _fetch_all() -> dict[str, ServiceStatusResponse]:
    names = list(SERVICES.keys())
    responses = await asyncio.gather(
        *[fetch_service_status(SERVICES[name].base_url) for name in names],
        return_exceptions=True,
    )
    result: dict[str, ServiceStatusResponse] = {}
    for name, response in zip(names, responses, strict=False):
        if isinstance(response, BaseException):
            logger.exception("Unexpected error fetching %s: %s", name, response)
        else:
            result[name] = response
    return result


async def poll_once(client: WebClient, channel: str) -> None:
    stored = read_state() or {}
    new_state = dict(stored)

    status_responses = await _fetch_all()

    for name, cfg in SERVICES.items():
        response = status_responses.get(name)
        if response is None or response.fetch_error:
            logger.warning("Skipping %s: fetch failed", name)
            continue

        verdict = compute_verdict(response, cfg.ignored_components)
        stored_indicator = stored.get(name)
        transition = compute_transition(verdict.indicator, stored_indicator)

        new_state[name] = verdict.indicator

        if transition == Transition.CHANGED:
            if verdict.indicator == "none":
                text = format_recovery_alert(cfg.display_name, cfg.status_page_url)
            else:
                text = format_reply(verdict, cfg.display_name, cfg.status_page_url)
            try:
                client.chat_postMessage(channel=channel, text=text)
                logger.info(
                    "Alert posted for %s: %r -> %r", name, stored_indicator, verdict.indicator
                )
            except SlackApiError:
                logger.exception("Failed to post alert for %s", name)

    try:
        write_state(new_state)
    except OSError:
        logger.exception("Failed to write state file")


if __name__ == "__main__":  # pragma: no cover
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    _client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    _channel = os.environ["ALERT_CHANNEL_ID"]
    asyncio.run(poll_once(_client, _channel))
