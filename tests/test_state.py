"""Unit tests for state.py — T028."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import github_status_bot.state as state_mod


@pytest.fixture(autouse=True)
def tmp_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "state.json"
    monkeypatch.setenv("STATE_FILE_PATH", str(path))
    return path


def test_read_state_missing_file_returns_none() -> None:
    assert state_mod.read_state() is None


def test_read_state_valid_file_returns_dict(tmp_state: Path) -> None:
    tmp_state.write_text(json.dumps({"github": "none", "claude": "minor"}))
    assert state_mod.read_state() == {"github": "none", "claude": "minor"}


def test_read_state_corrupt_json_returns_none(tmp_state: Path) -> None:
    tmp_state.write_text("not json {{{")
    assert state_mod.read_state() is None


def test_read_state_wrong_shape_array_returns_none(tmp_state: Path) -> None:
    tmp_state.write_text(json.dumps(["github", "none"]))
    assert state_mod.read_state() is None


def test_read_state_wrong_shape_nested_dict_returns_none(tmp_state: Path) -> None:
    tmp_state.write_text(json.dumps({"github": {"indicator": "none"}}))
    assert state_mod.read_state() is None


def test_write_then_read_roundtrips() -> None:
    data = {"github": "major", "claude": "none"}
    state_mod.write_state(data)
    assert state_mod.read_state() == data


def test_write_is_atomic(tmp_state: Path) -> None:
    state_mod.write_state({"github": "none"})
    assert tmp_state.exists()
    assert not tmp_state.with_suffix(".tmp").exists()


def test_write_empty_dict_roundtrips() -> None:
    state_mod.write_state({})
    assert state_mod.read_state() == {}
