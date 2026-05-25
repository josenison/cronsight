"""Tests for the escalate CLI sub-command."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cronsight.cli_escalator import _add_escalator_subparser, handle_escalator
from cronsight.escalator import EscalatedJob, EscalationReport


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {"snapshot": "snap.json", "threshold": 3, "label": "CRITICAL"}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_add_escalator_subparser_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    _add_escalator_subparser(sub)
    args = parser.parse_args(["escalate", "snap.json"])
    assert args.snapshot == "snap.json"
    assert args.threshold == 3
    assert args.label == "CRITICAL"


def test_handle_escalator_returns_1_on_missing_snapshot():
    args = _make_args(snapshot="/nonexistent/snap.json")
    with patch("cronsight.cli_escalator.load_snapshot", side_effect=FileNotFoundError):
        assert handle_escalator(args) == 1


def test_handle_escalator_returns_1_on_snapshot_error():
    from cronsight.snapshot import SnapshotError
    args = _make_args()
    with patch("cronsight.cli_escalator.load_snapshot", side_effect=SnapshotError("bad")):
        assert handle_escalator(args) == 1


def test_handle_escalator_returns_0_when_no_escalations(capsys):
    empty_report = MagicMock()
    with patch("cronsight.cli_escalator.load_snapshot", return_value=empty_report):
        with patch(
            "cronsight.cli_escalator.escalate_report",
            return_value=EscalationReport(escalated=[]),
        ):
            args = _make_args()
            rc = handle_escalator(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "No escalated jobs" in captured.out


def test_handle_escalator_returns_0_and_prints_jobs(capsys):
    job = EscalatedJob(
        command="/usr/bin/backup",
        server="host1",
        consecutive_failures=5,
        label="CRITICAL",
    )
    escalation = EscalationReport(escalated=[job])
    mock_report = MagicMock()
    with patch("cronsight.cli_escalator.load_snapshot", return_value=mock_report):
        with patch("cronsight.cli_escalator.escalate_report", return_value=escalation):
            args = _make_args()
            rc = handle_escalator(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "backup" in captured.out
    assert "CRITICAL" in captured.out
