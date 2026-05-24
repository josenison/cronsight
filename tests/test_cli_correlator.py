"""Tests for cronsight.cli_correlator."""
from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from cronsight.cli_correlator import _add_correlator_subparser, handle_correlator
from cronsight.correlator import CorrelationReport, JobCorrelation


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {
        "snapshots": ["a.json", "b.json"],
        "inconsistent_only": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_add_correlator_subparser_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    _add_correlator_subparser(sub)
    args = parser.parse_args(["correlate", "a.json", "b.json"])
    assert args.snapshots == ["a.json", "b.json"]


def test_handle_correlator_returns_1_when_fewer_than_two_snapshots():
    args = _make_args(snapshots=["only_one.json"])
    assert handle_correlator(args) == 1


def test_handle_correlator_returns_1_on_missing_snapshot():
    args = _make_args(snapshots=["missing1.json", "missing2.json"])
    with patch("cronsight.cli_correlator.load_snapshot", side_effect=FileNotFoundError("not found")):
        assert handle_correlator(args) == 1


def test_handle_correlator_returns_0_on_success():
    fake_report = MagicMock()
    fake_report.jobs = {}
    corr_report = CorrelationReport(correlations=[])
    args = _make_args()
    with patch("cronsight.cli_correlator.load_snapshot", return_value=fake_report), \
         patch("cronsight.cli_correlator.correlate_reports", return_value=corr_report):
        result = handle_correlator(args)
    assert result == 0


def test_handle_correlator_inconsistent_only_flag():
    consistent = JobCorrelation(command="a.sh", servers=["x", "y"], total_runs=2, total_failures=0, consistent=True)
    inconsistent = JobCorrelation(command="b.sh", servers=["x", "y"], total_runs=2, total_failures=1, consistent=False)
    corr_report = CorrelationReport(correlations=[consistent, inconsistent])
    fake_report = MagicMock()
    fake_report.jobs = {}
    args = _make_args(inconsistent_only=True)
    with patch("cronsight.cli_correlator.load_snapshot", return_value=fake_report), \
         patch("cronsight.cli_correlator.correlate_reports", return_value=corr_report), \
         patch("builtins.print") as mock_print:
        result = handle_correlator(args)
    assert result == 0
    printed = " ".join(str(c) for c in mock_print.call_args_list)
    assert "b.sh" in printed
    assert "a.sh" not in printed
