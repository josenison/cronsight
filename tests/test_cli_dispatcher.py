"""Tests for cronsight.cli_dispatcher."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from cronsight.cli_dispatcher import (
    _add_dispatcher_subparser,
    _parse_channel,
    handle_dispatcher,
)
from cronsight.dispatcher import DispatcherError


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {
        "snapshot": "/nonexistent/snap.json",
        "channels": [],
        "min_failure_rate": 0.5,
        "consecutive_failures": 3,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_add_dispatcher_subparser_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    _add_dispatcher_subparser(sub)
    args = parser.parse_args(["dispatch", "snap.json"])
    assert args.cmd == "dispatch"


def test_parse_channel_valid():
    ch = _parse_channel("main:stdout:warning")
    assert ch.name == "main"
    assert ch.kind == "stdout"
    assert ch.min_severity == "warning"


def test_parse_channel_invalid_raises():
    with pytest.raises(DispatcherError):
        _parse_channel("bad-spec")


def test_handle_dispatcher_returns_1_on_missing_snapshot():
    args = _make_args(snapshot="/no/such/file.json")
    assert handle_dispatcher(args) == 1


def test_handle_dispatcher_returns_1_on_snapshot_error():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        f.write(b"{invalid json")
        path = f.name
    args = _make_args(snapshot=path)
    assert handle_dispatcher(args) == 1


def test_handle_dispatcher_returns_1_on_bad_channel():
    from cronsight.snapshot import save_snapshot
    from cronsight.aggregator import AggregatedReport

    report = AggregatedReport(jobs={})
    with tempfile.TemporaryDirectory() as d:
        snap = Path(d) / "snap.json"
        save_snapshot(report, snap)
        args = _make_args(snapshot=str(snap), channels=["bad-spec"])
        assert handle_dispatcher(args) == 1


def test_handle_dispatcher_returns_0_on_success():
    from cronsight.snapshot import save_snapshot
    from cronsight.aggregator import AggregatedReport

    report = AggregatedReport(jobs={})
    with tempfile.TemporaryDirectory() as d:
        snap = Path(d) / "snap.json"
        save_snapshot(report, snap)
        args = _make_args(snapshot=str(snap))
        assert handle_dispatcher(args) == 0
