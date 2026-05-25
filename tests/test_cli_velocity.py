"""Unit tests for cronsight.cli_velocity."""
from __future__ import annotations

import argparse
import pytest
from unittest.mock import patch, MagicMock

from cronsight.cli_velocity import _add_velocity_subparser, handle_velocity
from cronsight.velocity import VelocityReport, VelocityDelta, VelocityError
from cronsight.snapshot import SnapshotError


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {
        "old_snapshot": "old.json",
        "new_snapshot": "new.json",
        "accelerating_only": False,
        "decelerating_only": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_add_velocity_subparser_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    _add_velocity_subparser(sub)
    args = parser.parse_args(["velocity", "old.json", "new.json"])
    assert args.old_snapshot == "old.json"
    assert args.new_snapshot == "new.json"


def test_add_velocity_subparser_accelerating_flag():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    _add_velocity_subparser(sub)
    args = parser.parse_args(["velocity", "a.json", "b.json", "--accelerating-only"])
    assert args.accelerating_only is True


def test_handle_velocity_returns_1_on_missing_old_snapshot():
    args = _make_args()
    with patch("cronsight.cli_velocity.load_snapshot", side_effect=FileNotFoundError("missing")):
        assert handle_velocity(args) == 1


def test_handle_velocity_returns_1_on_missing_new_snapshot():
    args = _make_args()
    old_report = MagicMock()
    with patch(
        "cronsight.cli_velocity.load_snapshot",
        side_effect=[old_report, FileNotFoundError("missing")],
    ):
        assert handle_velocity(args) == 1


def test_handle_velocity_returns_1_on_snapshot_error():
    args = _make_args()
    with patch("cronsight.cli_velocity.load_snapshot", side_effect=SnapshotError("bad")):
        assert handle_velocity(args) == 1


def test_handle_velocity_returns_1_on_velocity_error():
    args = _make_args()
    old_report = MagicMock()
    new_report = MagicMock()
    with patch("cronsight.cli_velocity.load_snapshot", side_effect=[old_report, new_report]):
        with patch("cronsight.cli_velocity.compute_velocity", side_effect=VelocityError("oops")):
            assert handle_velocity(args) == 1


def test_handle_velocity_returns_0_on_success(capsys):
    args = _make_args()
    old_report = MagicMock()
    new_report = MagicMock()
    delta = VelocityDelta("backup", old_runs=2, new_runs=5, old_success_rate=1.0, new_success_rate=0.8)
    report = VelocityReport(deltas=[delta])
    with patch("cronsight.cli_velocity.load_snapshot", side_effect=[old_report, new_report]):
        with patch("cronsight.cli_velocity.compute_velocity", return_value=report):
            result = handle_velocity(args)
    assert result == 0
    captured = capsys.readouterr()
    assert "backup" in captured.out


def test_handle_velocity_empty_report_prints_message(capsys):
    args = _make_args()
    old_report = MagicMock()
    new_report = MagicMock()
    report = VelocityReport(deltas=[])
    with patch("cronsight.cli_velocity.load_snapshot", side_effect=[old_report, new_report]):
        with patch("cronsight.cli_velocity.compute_velocity", return_value=report):
            result = handle_velocity(args)
    assert result == 0
    assert "No velocity" in capsys.readouterr().out
