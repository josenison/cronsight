"""Tests for cronsight.cli_retention module."""

import argparse
from unittest.mock import MagicMock, patch

import pytest

from cronsight.cli_retention import _add_retention_subparser, handle_retention
from cronsight.retention import RetentionResult
from cronsight.snapshot import SnapshotError


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {
        "snapshot": "/tmp/snap.json",
        "max_age_days": None,
        "max_entries": 10,
        "no_keep_failures": False,
        "dry_run": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_add_retention_subparser_registers_command():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    _add_retention_subparser(subparsers)
    args = parser.parse_args(["retain", "snap.json", "--max-entries", "5"])
    assert args.max_entries == 5


def test_handle_retention_returns_1_on_load_error():
    with patch("cronsight.cli_retention.load_snapshot", side_effect=SnapshotError("bad")):
        result = handle_retention(_make_args())
    assert result == 1


def test_handle_retention_returns_1_on_invalid_policy():
    mock_report = MagicMock()
    with patch("cronsight.cli_retention.load_snapshot", return_value=mock_report):
        args = _make_args(max_age_days=None, max_entries=None)
        result = handle_retention(args)
    assert result == 1


def test_handle_retention_dry_run_does_not_save(capsys):
    mock_report = MagicMock()
    retention_result = RetentionResult(
        original_entry_count=5, retained_entry_count=3, jobs_affected=["/bin/job"]
    )
    with patch("cronsight.cli_retention.load_snapshot", return_value=mock_report), \
         patch("cronsight.cli_retention.apply_retention", return_value=retention_result), \
         patch("cronsight.cli_retention.save_snapshot") as mock_save:
        result = handle_retention(_make_args(dry_run=True))

    assert result == 0
    mock_save.assert_not_called()
    captured = capsys.readouterr()
    assert "dry-run" in captured.out
    assert "2" in captured.out


def test_handle_retention_saves_on_success(capsys):
    mock_report = MagicMock()
    retention_result = RetentionResult(
        original_entry_count=4, retained_entry_count=4, jobs_affected=[]
    )
    with patch("cronsight.cli_retention.load_snapshot", return_value=mock_report), \
         patch("cronsight.cli_retention.apply_retention", return_value=retention_result), \
         patch("cronsight.cli_retention.save_snapshot") as mock_save:
        result = handle_retention(_make_args())

    assert result == 0
    mock_save.assert_called_once()


def test_handle_retention_returns_1_on_save_error():
    mock_report = MagicMock()
    retention_result = RetentionResult(
        original_entry_count=3, retained_entry_count=2, jobs_affected=[]
    )
    with patch("cronsight.cli_retention.load_snapshot", return_value=mock_report), \
         patch("cronsight.cli_retention.apply_retention", return_value=retention_result), \
         patch("cronsight.cli_retention.save_snapshot", side_effect=SnapshotError("disk full")):
        result = handle_retention(_make_args())

    assert result == 1
