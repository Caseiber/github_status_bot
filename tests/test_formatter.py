"""Unit tests for formatter.py."""

from __future__ import annotations

import pytest

from github_status_bot.formatter import _format_duration, format_reply
from github_status_bot.verdict import VerdictResult


def _verdict(
    is_down: bool = False,
    indicator: str = "none",
    duration_seconds: int | None = None,
    has_fetch_error: bool = False,
) -> VerdictResult:
    return VerdictResult(
        is_down=is_down,
        indicator=indicator,
        duration_seconds=duration_seconds,
        has_fetch_error=has_fetch_error,
    )


# ---------------------------------------------------------------------------
# _format_duration
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (0, "less than a minute"),
        (59, "less than a minute"),
        (60, "~1m"),
        (90, "~1m"),
        (3599, "~59m"),
        (3600, "~1h"),
        (5400, "~1h 30m"),  # 90 minutes
        (9000, "~2h 30m"),  # 150 minutes
    ],
)
def test_format_duration(seconds: int, expected: str) -> None:
    assert _format_duration(seconds) == expected


# ---------------------------------------------------------------------------
# format_reply — fetch error
# ---------------------------------------------------------------------------


def test_format_reply_fetch_error() -> None:
    result = format_reply(_verdict(has_fetch_error=True))
    assert result == (
        "Couldn't check GitHub's status right now — the status API didn't respond. "
        "Try again in a moment."
    )
    assert "up" not in result
    assert "down" not in result


# ---------------------------------------------------------------------------
# format_reply — up
# ---------------------------------------------------------------------------


def test_format_reply_up() -> None:
    result = format_reply(_verdict(is_down=False, indicator="none"))
    assert result == (
        "GitHub appears to be *up*... for NOW. "
        "Source: GitHub's official status page (all systems operational)."
    )


# ---------------------------------------------------------------------------
# format_reply — down with duration
# ---------------------------------------------------------------------------


def test_format_reply_down_with_duration() -> None:
    result = format_reply(_verdict(is_down=True, indicator="major", duration_seconds=7920))
    assert result == (
        "GitHub is *down* because AI DevOps is a blight on our land. "
        "Source: GitHub's official status page (indicator: major, ~2h 12m)."
    )


def test_format_reply_down_with_short_duration() -> None:
    result = format_reply(_verdict(is_down=True, indicator="minor", duration_seconds=45))
    assert "less than a minute" in result
    assert "*down*" in result


# ---------------------------------------------------------------------------
# format_reply — down without duration
# ---------------------------------------------------------------------------


def test_format_reply_down_no_duration() -> None:
    result = format_reply(_verdict(is_down=True, indicator="major", duration_seconds=None))
    assert result == (
        "GitHub is *down* because AI DevOps is a blight on our land. "
        "Source: GitHub's official status page (indicator: major)."
    )
    assert "None" not in result


def test_format_reply_down_critical_no_duration() -> None:
    result = format_reply(_verdict(is_down=True, indicator="critical"))
    assert "indicator: critical" in result
    assert "*down*" in result
