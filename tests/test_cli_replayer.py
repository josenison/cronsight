"""Tests for cronsight.cli_replayer."""

from __future__ import annotations

import argparse
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from cronsight.cli_replayer import _add_replayer_subparser, _parse_dt, handle_replayer
from cronsight.replayer import ReplayerError, ReplayReport


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {"snapshot": "snap.json", "since": None, "until": None, "job": None}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_add_replayer_subparser_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    _add_replayer_subparser(sub)
    args = parser.parse_args(["replay", "snap.json"])
    assert args.command == "replay"


def test_parse_dt_returns_none_for_none():
    assert _parse_dt(None) is None


def test_parse_dt_parses_valid_string():
    dt = _parse_dt("2024-06-01T12:00:00")
    assert dt == datetime(2024, 6, 1, 12, 0, 0)


def test_parse_dt_raises_on_invalid():
    with pytest.raises(ValueError):
        _parse_dt("not-a-date")


def test_handle_replayer_returns_1_on_missing_snapshot():
    args = _make_args(snapshot="missing.json")
    with patch("cronsight.cli_replayer.load_snapshot", side_effect=FileNotFoundError("no file")):
        assert handle_replayer(args) == 1


def test_handle_replayer_returns_1_on_snapshot_error():
    from cronsight.snapshot import SnapshotError
    args = _make_args()
    with patch("cronsight.cli_replayer.load_snapshot", side_effect=SnapshotError("bad")):
        assert handle_replayer(args) == 1


def test_handle_replayer_returns_1_on_replayer_error():
    args = _make_args()
    mock_report = MagicMock()
    with patch("cronsight.cli_replayer.load_snapshot", return_value=mock_report), \
         patch("cronsight.cli_replayer.replay_report", side_effect=ReplayerError("empty")):
        assert handle_replayer(args) == 1


def test_handle_replayer_returns_1_on_bad_since():
    args = _make_args(since="bad-date")
    with patch("cronsight.cli_replayer.load_snapshot", return_value=MagicMock()):
        assert handle_replayer(args) == 1


def test_handle_replayer_returns_0_on_success(capsys):
    args = _make_args()
    mock_report = MagicMock()
    mock_rpt = ReplayReport(timelines=[])
    with patch("cronsight.cli_replayer.load_snapshot", return_value=mock_report), \
         patch("cronsight.cli_replayer.replay_report", return_value=mock_rpt):
        result = handle_replayer(args)
    assert result == 0
