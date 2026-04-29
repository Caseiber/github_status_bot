"""Unit tests for transition.py — T029/T030."""

from __future__ import annotations

import pytest

from github_status_bot.transition import Transition, compute_transition


@pytest.mark.parametrize(
    "current, stored, expected",
    [
        # First poll (no stored state)
        ("none", None, Transition.NO_CHANGE),   # first poll, service up — no alert
        ("minor", None, Transition.CHANGED),    # first poll, already degraded
        ("major", None, Transition.CHANGED),    # first poll, already down
        ("critical", None, Transition.CHANGED), # first poll, already critical
        # Same indicator persists — never alert
        ("none", "none", Transition.NO_CHANGE),
        ("minor", "minor", Transition.NO_CHANGE),
        ("major", "major", Transition.NO_CHANGE),
        ("critical", "critical", Transition.NO_CHANGE),
        # Transitions between levels
        ("minor", "none", Transition.CHANGED),    # went degraded
        ("major", "none", Transition.CHANGED),    # went down
        ("major", "minor", Transition.CHANGED),   # escalated
        ("critical", "major", Transition.CHANGED),# escalated further
        ("minor", "major", Transition.CHANGED),   # de-escalated
        ("none", "minor", Transition.CHANGED),    # recovered from degraded
        ("none", "major", Transition.CHANGED),    # recovered from down
    ],
)
def test_compute_transition(
    current: str, stored: str | None, expected: Transition
) -> None:
    assert compute_transition(current, stored) == expected
