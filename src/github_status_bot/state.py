"""Persistent indicator state for the Phase 2 poller."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_PATH = "gh_status_state.json"


def _state_path() -> Path:
    return Path(os.environ.get("STATE_FILE_PATH", _DEFAULT_PATH))


def read_state() -> dict[str, str] | None:
    """Return {service_name: indicator} from the state file, or None if missing/corrupt."""
    try:
        data = json.loads(_state_path().read_text())
        if isinstance(data, dict) and all(
            isinstance(k, str) and isinstance(v, str) for k, v in data.items()
        ):
            return data
        logger.warning("State file has unexpected shape; treating as missing")
        return None
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read state file: %s", exc)
        return None


def write_state(state: dict[str, str]) -> None:
    """Atomically write {service_name: indicator} to the state file."""
    path = _state_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state))
    tmp.rename(path)
