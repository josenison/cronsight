"""Tests for cronsight.cli_tracer."""
from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from cronsight.cli_tracer import _add_tracer_subparser, handle_tracer
from cronsight.snapshot import SnapshotError
from cronsight.tracer import TracerError, TraceReport


def _make_args(**kwargs):
    defaults = {
        "snapshot": "snap.json",
        "command": None,
        "failures_only": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_add_tracer_subparser_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    _add_tracer_subparser(sub)
    args = parser.parse_args(["trace", "snap.json"])
    assert args.snapshot == "snap.json"


def test_handle_tracer_returns_1_on_missing_snapshot():
    args = _make_args(snapshot="missing.json")
    with patch("cronsight.cli_tracer.load_snapshot", side_effect=FileNotFoundError):
        assert handle_tracer(args) == 1


def test_handle_tracer_returns_1_on_snapshot_error():
    args = _make_args()
    with patch("cronsight.cli_tracer.load_snapshot", side_effect=SnapshotError("bad")):
        assert handle_tracer(args) == 1


def test_handle_tracer_returns_1_on_tracer_error():
    args = _make_args()
    mock_report = MagicMock()
    with patch("cronsight.cli_tracer.load_snapshot", return_value=mock_report), \
         patch("cronsight.cli_tracer.build_trace", side_effect=TracerError("empty")):
        assert handle_tracer(args) == 1


def test_handle_tracer_returns_0_on_success(capsys):
    args = _make_args()
    mock_report = MagicMock()
    empty_trace = TraceReport(traces={})
    with patch("cronsight.cli_tracer.load_snapshot", return_value=mock_report), \
         patch("cronsight.cli_tracer.build_trace", return_value=empty_trace):
        result = handle_tracer(args)
    assert result == 0
    captured = capsys.readouterr()
    assert "No matching" in captured.out


def test_handle_tracer_passes_command_filter():
    args = _make_args(command="backup")
    mock_report = MagicMock()
    empty_trace = TraceReport(traces={})
    with patch("cronsight.cli_tracer.load_snapshot", return_value=mock_report) as _load, \
         patch("cronsight.cli_tracer.build_trace", return_value=empty_trace) as mock_build:
        handle_tracer(args)
    mock_build.assert_called_once_with(mock_report, command_filter="backup")
