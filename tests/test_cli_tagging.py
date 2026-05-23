"""Tests for cronsight.cli_tagging."""
import json
import pytest
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.cli_tagging import _add_tagging_subparser, handle_tagging


def _make_entry(cmd: str) -> CronEntry:
    return CronEntry(
        timestamp=datetime(2024, 3, 1, tzinfo=timezone.utc),
        command=cmd,
        return_code=0,
        server="srv1",
    )


def _make_report() -> AggregatedReport:
    jobs = {
        "/usr/bin/backup.sh": JobSummary(
            command="/usr/bin/backup.sh",
            entries=[_make_entry("/usr/bin/backup.sh")],
            servers={"srv1"},
        )
    }
    return AggregatedReport(jobs=jobs)


def _make_args(snapshot: str, rules: str, output: str = "-") -> Namespace:
    return Namespace(snapshot=snapshot, rules=rules, output=output)


def test_add_tagging_subparser_registers_command():
    import argparse
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    _add_tagging_subparser(sub)
    args = parser.parse_args(["tag", "snap.json", "--rules", "rules.json"])
    assert args.command == "tag"


def test_handle_tagging_returns_1_on_missing_snapshot(tmp_path):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps([{"tag": "t", "pattern": "p"}]))
    args = _make_args(str(tmp_path / "missing.json"), str(rules_file))
    assert handle_tagging(args) == 1


def test_handle_tagging_returns_1_on_bad_rules(tmp_path):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text("not json")
    with patch("cronsight.cli_tagging.load_snapshot", return_value=_make_report()):
        args = _make_args("snap.json", str(rules_file))
        assert handle_tagging(args) == 1


def test_handle_tagging_returns_0_and_writes_stdout(tmp_path, capsys):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps([{"tag": "backup", "pattern": "backup"}]))
    with patch("cronsight.cli_tagging.load_snapshot", return_value=_make_report()):
        args = _make_args("snap.json", str(rules_file))
        rc = handle_tagging(args)
    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert any(j["tags"] == ["backup"] for j in data["jobs"])


def test_handle_tagging_writes_to_file(tmp_path):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps([{"tag": "backup", "pattern": "backup"}]))
    out_file = tmp_path / "out.json"
    with patch("cronsight.cli_tagging.load_snapshot", return_value=_make_report()):
        args = _make_args("snap.json", str(rules_file), str(out_file))
        rc = handle_tagging(args)
    assert rc == 0
    data = json.loads(out_file.read_text())
    assert "jobs" in data
