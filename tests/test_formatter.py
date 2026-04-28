"""Unit tests for formatter.py."""

from __future__ import annotations

import pytest

from github_status_bot.formatter import _format_duration, format_reply
from github_status_bot.verdict import VerdictResult

_SOURCE = "<https://www.githubstatus.com|GitHub's status page>"


def _verdict(
    is_down: bool = False,
    indicator: str = "none",
    duration_seconds: int | None = None,
    has_fetch_error: bool = False,
    affected_components: tuple[str, ...] = (),
) -> VerdictResult:
    return VerdictResult(
        is_down=is_down,
        indicator=indicator,
        duration_seconds=duration_seconds,
        has_fetch_error=has_fetch_error,
        affected_components=affected_components,
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
    assert result == f"GitHub appears to be *up*... for NOW.\n\nSource: {_SOURCE}"


# ---------------------------------------------------------------------------
# format_reply — down with duration
# ---------------------------------------------------------------------------


def test_format_reply_down_with_duration() -> None:
    result = format_reply(_verdict(is_down=True, indicator="major", duration_seconds=7920))
    assert result == (
        "GitHub is *down* because AI DevOps is a blight on our land.\n"
        "\n"
        "Severity: Major Outage\n"
        "Time Down: ~2h 12m\n"
        "\n"
        f"Source: {_SOURCE}"
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
        "GitHub is *down* because AI DevOps is a blight on our land.\n"
        "\n"
        "Severity: Major Outage\n"
        "\n"
        f"Source: {_SOURCE}"
    )
    assert "None" not in result


def test_format_reply_down_critical_no_duration() -> None:
    result = format_reply(_verdict(is_down=True, indicator="critical"))
    assert "Critical Outage" in result
    assert "*down*" in result


# ---------------------------------------------------------------------------
# format_reply — down with affected components
# ---------------------------------------------------------------------------


def test_format_reply_down_with_single_affected_component() -> None:
    result = format_reply(
        _verdict(
            is_down=True,
            indicator="minor",
            duration_seconds=3600,
            affected_components=("Git Operations",),
        )
    )
    assert "Affected Area: Git Operations" in result
    assert "Affected Areas" not in result
    assert "Severity: Degraded" in result
    assert "Time Down: ~1h" in result
    assert f"Source: {_SOURCE}" in result


def test_format_reply_down_with_multiple_affected_components_uses_bullet_list() -> None:
    result = format_reply(
        _verdict(
            is_down=True,
            indicator="major",
            duration_seconds=3600,
            affected_components=("Git Operations", "API Requests"),
        )
    )
    assert "Affected Areas:" in result
    assert "• Git Operations" in result
    assert "• API Requests" in result
    assert "Affected Area:" not in result
    assert "Severity: Major Outage" in result
    assert f"Source: {_SOURCE}" in result


def test_format_reply_down_no_affected_components_omits_area_line() -> None:
    result = format_reply(_verdict(is_down=True, indicator="major"))
    assert "Affected Area" not in result
    assert "Severity: Major Outage" in result
    assert f"Source: {_SOURCE}" in result


def test_format_reply_source_link_present_when_up() -> None:
    result = format_reply(_verdict(is_down=False))
    assert _SOURCE in result


def test_format_reply_source_link_present_when_down() -> None:
    result = format_reply(_verdict(is_down=True, indicator="minor"))
    assert _SOURCE in result
