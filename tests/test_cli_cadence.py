"""Tests for cronsight.cli_cadence."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.cadence import CadenceProfile, CadenceReport
from cronsight.cli_cadence import _add_cadence_subparser, handle_cadence
from cronsight.parser import CronEntry
from cronsight.snapshot import SnapshotError


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = dict(snapshot="snap.json", threshold=0.5, irregular_only=False)
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_add_cadence_subparser_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    _add_cadence_subparser(sub)
    args = parser.parse_args(["cadence", "snap.json"])
    assert args.snapshot == "snap.json"


def test_add_cadence_subparser_threshold_flag():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    _add_cadence_subparser(sub)
    args = parser.parse_args(["cadence", "snap.json", "--threshold", "0.8"])
    assert args.threshold == pytest.approx(0.8)


def test_add_cadence_subparser_irregular_only_flag():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    _add_cadence_subparser(sub)
    args = parser.parse_args(["cadence", "snap.json", "--irregular-only"])
    assert args.irregular_only is True


def test_handle_cadence_returns_1_on_missing_snapshot():
    with patch("cronsight.cli_cadence.load_snapshot", side_effect=FileNotFoundError):
        assert handle_cadence(_make_args()) == 1


def test_handle_cadence_returns_1_on_snapshot_error():
    with patch("cronsight.cli_cadence.load_snapshot", side_effect=SnapshotError("bad")):
        assert handle_cadence(_make_args()) == 1


def test_handle_cadence_returns_0_on_success(capsys):
    base = datetime(2024, 1, 1, 6, 0)
    ts = [base + timedelta(hours=i) for i in range(4)]
    entry = CronEntry(timestamp=ts[0], command="/usr/bin/job", status="success", server="h1")
    summary = JobSummary(command="/usr/bin/job", server="h1", entries=[entry])
    fake_report = AggregatedReport(summaries=[summary])

    with patch("cronsight.cli_cadence.load_snapshot", return_value=fake_report):
        result = handle_cadence(_make_args())
    assert result == 0


def test_handle_cadence_irregular_only_filters_output(capsys):
    profile_ok = CadenceProfile(
        command="/ok", server="h1", run_count=3,
        mean_interval_seconds=3600, stdev_interval_seconds=10,
        max_interval_seconds=3700, is_irregular=False,
    )
    profile_bad = CadenceProfile(
        command="/bad", server="h1", run_count=5,
        mean_interval_seconds=3600, stdev_interval_seconds=5000,
        max_interval_seconds=9000, is_irregular=True,
    )
    fake_cadence = CadenceReport(profiles=[profile_ok, profile_bad])
    fake_agg = AggregatedReport(summaries=[])

    with patch("cronsight.cli_cadence.load_snapshot", return_value=fake_agg), \
         patch("cronsight.cli_cadence.analyze_cadence", return_value=fake_cadence):
        handle_cadence(_make_args(irregular_only=True))

    captured = capsys.readouterr().out
    assert "/bad" in captured
    assert "/ok" not in captured
