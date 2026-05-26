"""Unit tests for cronsight.cli_recurrence."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.cli_recurrence import _add_recurrence_subparser, handle_recurrence
from cronsight.parser import CronEntry
from cronsight.recurrence import RecurrenceReport
from cronsight.snapshot import SnapshotError

BASE = datetime(2024, 3, 1, 8, 0, 0)


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = dict(snapshot="snap.json", threshold=0.5, irregular_only=False)
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _make_report() -> AggregatedReport:
    s = JobSummary(command="job.sh")
    for i in range(4):
        e = CronEntry(command="job.sh", timestamp=BASE + timedelta(hours=i), success=True, server="h1")
        s.entries.append(e)
        s.servers.add("h1")
    r = AggregatedReport()
    r.jobs["job.sh"] = s
    return r


def test_add_recurrence_subparser_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    _add_recurrence_subparser(sub)
    args = parser.parse_args(["recurrence", "snap.json"])
    assert args.snapshot == "snap.json"


def test_add_recurrence_subparser_threshold_flag():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    _add_recurrence_subparser(sub)
    args = parser.parse_args(["recurrence", "snap.json", "--threshold", "0.3"])
    assert args.threshold == pytest.approx(0.3)


def test_add_recurrence_subparser_irregular_only_flag():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    _add_recurrence_subparser(sub)
    args = parser.parse_args(["recurrence", "snap.json", "--irregular-only"])
    assert args.irregular_only is True


def test_handle_recurrence_returns_1_on_missing_snapshot():
    with patch("cronsight.cli_recurrence.load_snapshot", side_effect=FileNotFoundError):
        assert handle_recurrence(_make_args()) == 1


def test_handle_recurrence_returns_1_on_snapshot_error():
    with patch("cronsight.cli_recurrence.load_snapshot", side_effect=SnapshotError("bad")):
        assert handle_recurrence(_make_args()) == 1


def test_handle_recurrence_returns_0_on_success(capsys):
    rep = _make_report()
    with patch("cronsight.cli_recurrence.load_snapshot", return_value=rep):
        result = handle_recurrence(_make_args())
    assert result == 0
    out = capsys.readouterr().out
    assert "job.sh" in out


def test_handle_recurrence_irregular_only_filters(capsys):
    rep = _make_report()
    with patch("cronsight.cli_recurrence.load_snapshot", return_value=rep):
        handle_recurrence(_make_args(irregular_only=True))
    out = capsys.readouterr().out
    # regular job should not appear in irregular-only output
    assert "IRREGULAR" not in out or "job.sh" not in out
