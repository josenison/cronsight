"""Tests for cronsight.cli_heatmap."""

from __future__ import annotations

import argparse
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.cli_heatmap import _add_heatmap_subparser, handle_heatmap
from cronsight.parser import CronEntry


def _make_args(**kwargs):
    defaults = {"snapshot": "snap.json", "job_filter": None, "no_color": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _make_report(hour: int = 10):
    entry = CronEntry(
        timestamp=datetime(2024, 1, 1, hour, 0, 0),
        server="srv1",
        command="/bin/job",
        success=True,
    )
    summary = JobSummary(command="/bin/job", entries=[entry])
    return AggregatedReport(jobs={"/bin/job": summary})


def test_add_heatmap_subparser_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    _add_heatmap_subparser(sub)
    args = parser.parse_args(["heatmap", "snap.json"])
    assert args.command == "heatmap"


def test_handle_heatmap_returns_1_on_missing_snapshot():
    args = _make_args(snapshot="nonexistent.json")
    with patch("cronsight.cli_heatmap.load_snapshot", side_effect=FileNotFoundError("not found")):
        result = handle_heatmap(args)
    assert result == 1


def test_handle_heatmap_returns_1_on_snapshot_error():
    from cronsight.snapshot import SnapshotError
    args = _make_args()
    with patch("cronsight.cli_heatmap.load_snapshot", side_effect=SnapshotError("bad")):
        result = handle_heatmap(args)
    assert result == 1


def test_handle_heatmap_returns_0_on_success(capsys):
    args = _make_args()
    report = _make_report()
    with patch("cronsight.cli_heatmap.load_snapshot", return_value=report):
        result = handle_heatmap(args)
    assert result == 0


def test_handle_heatmap_output_contains_job(capsys):
    args = _make_args()
    report = _make_report()
    with patch("cronsight.cli_heatmap.load_snapshot", return_value=report):
        handle_heatmap(args)
    captured = capsys.readouterr()
    assert "/bin/job" in captured.out


def test_handle_heatmap_job_filter_excludes_non_matching(capsys):
    args = _make_args(job_filter="/usr/bin/other")
    report = _make_report()
    with patch("cronsight.cli_heatmap.load_snapshot", return_value=report):
        handle_heatmap(args)
    captured = capsys.readouterr()
    assert "/bin/job" not in captured.out


def test_handle_heatmap_returns_1_on_empty_report():
    args = _make_args()
    report = AggregatedReport(jobs={})
    with patch("cronsight.cli_heatmap.load_snapshot", return_value=report):
        result = handle_heatmap(args)
    assert result == 1
