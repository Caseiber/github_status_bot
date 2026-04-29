"""State-transition logic for the Phase 2 poller."""

from __future__ import annotations

from enum import Enum


class Transition(Enum):
    CHANGED = "changed"
    NO_CHANGE = "no_change"


def compute_transition(current_indicator: str, stored_indicator: str | None) -> Transition:
    """Return CHANGED if the indicator has changed since last alert, NO_CHANGE otherwise.

    On first poll (stored_indicator is None): alert only if the service is already down.
    """
    if stored_indicator is None:
        return Transition.CHANGED if current_indicator != "none" else Transition.NO_CHANGE
    return Transition.CHANGED if current_indicator != stored_indicator else Transition.NO_CHANGE
