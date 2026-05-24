"""Tests for cronsight.cli_watcher."""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from cronsight.cli_watcher import _add_watcher_subparser, handle_watcher
from cronsight.config import ConfigError


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = dict(
        config="servers.toml",
        interval=60,
        iterations=2,
        changes_only=False,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_add_watcher_subparser_registers_command():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    _add_watcher_subparser(subparsers)
    args = parser.parse_args(["watch", "--config", "x.toml"])
    assert args.config == "x.toml"


def test_handle_watcher_returns_1_on_config_error():
    with patch("cronsight.cli_watcher.load_config", side_effect=ConfigError("bad")):
        assert handle_watcher(_make_args()) == 1


def test_handle_watcher_returns_1_on_missing_file():
    with patch("cronsight.cli_watcher.load_config", side_effect=FileNotFoundError):
        assert handle_watcher(_make_args()) == 1


def test_handle_watcher_returns_1_on_invalid_interval():
    with patch("cronsight.cli_watcher.load_config", return_value=[]):
        assert handle_watcher(_make_args(interval=0)) == 1


def test_handle_watcher_runs_and_returns_0(capsys):
    fake_report = MagicMock()
    fake_report.jobs = {}
    fake_report.servers = []

    with patch("cronsight.cli_watcher.load_config", return_value=[]), \
         patch("cronsight.cli_watcher.collect_from_servers", return_value=fake_report), \
         patch("cronsight.cli_watcher.format_report", return_value="REPORT"), \
         patch("cronsight.watcher.time.sleep"):
        result = handle_watcher(_make_args(iterations=2))

    assert result == 0
    captured = capsys.readouterr()
    assert "REPORT" in captured.out


def test_handle_watcher_changes_only_suppresses_unchanged(capsys):
    fake_report = MagicMock()
    fake_report.jobs = {}
    fake_report.servers = []

    with patch("cronsight.cli_watcher.load_config", return_value=[]), \
         patch("cronsight.cli_watcher.collect_from_servers", return_value=fake_report), \
         patch("cronsight.cli_watcher.format_report", return_value="REPORT"), \
         patch("cronsight.watcher.time.sleep"):
        result = handle_watcher(_make_args(iterations=2, changes_only=True))

    assert result == 0
    # First iteration has no diff → suppressed; second has diff with no changes → suppressed
    captured = capsys.readouterr()
    assert "REPORT" not in captured.out
