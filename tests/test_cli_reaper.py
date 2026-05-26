"""Unit tests for cronsight.cli_reaper."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cronsight.cli_reaper import _add_reaper_subparser, handle_reaper
from cronsight.reaper import ReaperReport, DeadJob
from cronsight.snapshot import SnapshotError


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {
        "snapshot": "snap.json",
        "interval": 24.0,
        "pattern": None,
        "dead_only": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_add_reaper_subparser_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    _add_reaper_subparser(sub)
    args = parser.parse_args(["reaper", "snap.json", "--interval", "12"])
    assert args.interval == 12.0


def test_handle_reaper_returns_1_on_missing_snapshot():
    args = _make_args(snapshot="missing.json")
    with patch("cronsight.cli_reaper.load_snapshot", side_effect=FileNotFoundError):
        assert handle_reaper(args) == 1


def test_handle_reaper_returns_1_on_snapshot_error():
    args = _make_args()
    with patch("cronsight.cli_reaper.load_snapshot", side_effect=SnapshotError("bad")):
        assert handle_reaper(args) == 1


def test_handle_reaper_returns_0_when_no_dead_jobs():
    args = _make_args()
    mock_report = ReaperReport(dead_jobs=[])
    with patch("cronsight.cli_reaper.load_snapshot", return_value=MagicMock()), \
         patch("cronsight.cli_reaper.reap", return_value=mock_report):
        assert handle_reaper(args) == 0


def test_handle_reaper_returns_0_with_dead_jobs_and_no_flag():
    args = _make_args(dead_only=False)
    dead = DeadJob(command="x.sh", server="h1", last_run=None,
                   expected_interval_hours=24, hours_overdue=float("inf"))
    mock_report = ReaperReport(dead_jobs=[dead])
    with patch("cronsight.cli_reaper.load_snapshot", return_value=MagicMock()), \
         patch("cronsight.cli_reaper.reap", return_value=mock_report):
        assert handle_reaper(args) == 0


def test_handle_reaper_returns_1_with_dead_only_flag():
    args = _make_args(dead_only=True)
    dead = DeadJob(command="x.sh", server="h1", last_run=None,
                   expected_interval_hours=24, hours_overdue=float("inf"))
    mock_report = ReaperReport(dead_jobs=[dead])
    with patch("cronsight.cli_reaper.load_snapshot", return_value=MagicMock()), \
         patch("cronsight.cli_reaper.reap", return_value=mock_report):
        assert handle_reaper(args) == 1
