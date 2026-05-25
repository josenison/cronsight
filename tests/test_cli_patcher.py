"""Tests for cronsight.cli_patcher."""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from cronsight.cli_patcher import _add_patcher_subparser, handle_patcher
from cronsight.patcher import PatchReport, CommandPatch


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {
        "old_snapshot": "old.json",
        "new_snapshot": "new.json",
        "server": None,
        "quiet": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_add_patcher_subparser_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    _add_patcher_subparser(sub)
    args = parser.parse_args(["patch", "old.json", "new.json"])
    assert args.cmd == "patch"


def test_handle_patcher_returns_1_on_missing_old_snapshot():
    args = _make_args(old_snapshot="/no/such/file.json")
    with patch("cronsight.cli_patcher.load_snapshot", side_effect=FileNotFoundError("gone")):
        assert handle_patcher(args) == 1


def test_handle_patcher_returns_1_on_missing_new_snapshot():
    args = _make_args()
    fake_report = MagicMock()

    def _load(path):
        if path == args.old_snapshot:
            return fake_report
        raise FileNotFoundError("gone")

    with patch("cronsight.cli_patcher.load_snapshot", side_effect=_load):
        assert handle_patcher(args) == 1


def test_handle_patcher_returns_0_when_no_patches(capsys):
    args = _make_args()
    empty = PatchReport(patches=[])
    with patch("cronsight.cli_patcher.load_snapshot", return_value=MagicMock()), \
         patch("cronsight.cli_patcher.detect_patches", return_value=empty):
        rc = handle_patcher(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "No command patches" in out


def test_handle_patcher_returns_1_when_patches_found(capsys):
    args = _make_args()
    patch_obj = CommandPatch("k", "old cmd", "new cmd", "host1")
    report = PatchReport(patches=[patch_obj])
    with patch("cronsight.cli_patcher.load_snapshot", return_value=MagicMock()), \
         patch("cronsight.cli_patcher.detect_patches", return_value=report):
        rc = handle_patcher(args)
    assert rc == 1
    out = capsys.readouterr().out
    assert "1 patch" in out


def test_handle_patcher_quiet_suppresses_output(capsys):
    args = _make_args(quiet=True)
    empty = PatchReport(patches=[])
    with patch("cronsight.cli_patcher.load_snapshot", return_value=MagicMock()), \
         patch("cronsight.cli_patcher.detect_patches", return_value=empty):
        handle_patcher(args)
    out = capsys.readouterr().out
    assert out == ""
