"""Unit tests for cronsight.cli_mirror."""
from __future__ import annotations
import argparse
from unittest.mock import patch, MagicMock
from cronsight.cli_mirror import _add_mirror_subparser, handle_mirror
from cronsight.snapshot import SnapshotError
from cronsight.mirror import MirrorError


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {"left": "left.json", "right": "right.json", "divergent_only": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_add_mirror_subparser_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    _add_mirror_subparser(sub)
    parsed = parser.parse_args(["mirror", "a.json", "b.json"])
    assert parsed.left == "a.json"
    assert parsed.right == "b.json"
    assert parsed.divergent_only is False


def test_add_mirror_subparser_divergent_only_flag():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    _add_mirror_subparser(sub)
    parsed = parser.parse_args(["mirror", "a.json", "b.json", "--divergent-only"])
    assert parsed.divergent_only is True


def test_handle_mirror_returns_1_on_missing_left_snapshot():
    with patch("cronsight.cli_mirror.load_snapshot", side_effect=FileNotFoundError("nope")):
        assert handle_mirror(_make_args()) == 1


def test_handle_mirror_returns_1_on_snapshot_error_left():
    with patch("cronsight.cli_mirror.load_snapshot", side_effect=SnapshotError("bad")):
        assert handle_mirror(_make_args()) == 1


def test_handle_mirror_returns_1_on_missing_right_snapshot():
    left_report = MagicMock()
    side_effects = [left_report, FileNotFoundError("nope")]
    with patch("cronsight.cli_mirror.load_snapshot", side_effect=side_effects):
        assert handle_mirror(_make_args()) == 1


def test_handle_mirror_returns_1_on_mirror_error():
    left_report = MagicMock()
    right_report = MagicMock()
    with patch("cronsight.cli_mirror.load_snapshot", side_effect=[left_report, right_report]):
        with patch("cronsight.cli_mirror.mirror_reports", side_effect=MirrorError("oops")):
            assert handle_mirror(_make_args()) == 1


def test_handle_mirror_returns_0_on_success(capsys):
    left_report = MagicMock()
    right_report = MagicMock()
    mock_mirror = MagicMock()
    mock_mirror.rows = []
    mock_mirror.divergent_rows = []
    with patch("cronsight.cli_mirror.load_snapshot", side_effect=[left_report, right_report]):
        with patch("cronsight.cli_mirror.mirror_reports", return_value=mock_mirror):
            result = handle_mirror(_make_args())
    assert result == 0
    captured = capsys.readouterr()
    assert "No differences" in captured.out
