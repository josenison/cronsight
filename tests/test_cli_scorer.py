"""Tests for cronsight.cli_scorer."""
from __future__ import annotations

import argparse
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.cli_scorer import _add_scorer_subparser, handle_scorer
from cronsight.parser import CronEntry
from cronsight.scorer import ScoredJob, ScoredReport


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {"snapshot": "snap.json", "top": None, "min_score": None}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _make_scored_job(cmd: str, score: float) -> ScoredJob:
    return ScoredJob(
        command=cmd,
        server="srv1",
        score=score,
        total_runs=5,
        success_rate=score / 100.0,
        has_recent_failure=score < 50,
    )


def test_add_scorer_subparser_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    _add_scorer_subparser(sub)
    ns = parser.parse_args(["score", "snap.json"])
    assert ns.snapshot == "snap.json"


def test_handle_scorer_returns_1_on_missing_snapshot():
    with patch("cronsight.cli_scorer.load_snapshot", side_effect=FileNotFoundError("nope")):
        assert handle_scorer(_make_args()) == 1


def test_handle_scorer_returns_0_on_success(capsys):
    jobs = [_make_scored_job("backup", 90.0), _make_scored_job("cleanup", 40.0)]
    mock_report = MagicMock(spec=ScoredReport)
    mock_report.jobs = jobs
    with patch("cronsight.cli_scorer.load_snapshot"), \
         patch("cronsight.cli_scorer.score_report", return_value=mock_report):
        rc = handle_scorer(_make_args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "backup" in out
    assert "cleanup" in out


def test_handle_scorer_top_limits_output(capsys):
    jobs = [_make_scored_job(f"job{i}", float(i * 10)) for i in range(5)]
    mock_report = MagicMock(spec=ScoredReport)
    mock_report.jobs = jobs
    with patch("cronsight.cli_scorer.load_snapshot"), \
         patch("cronsight.cli_scorer.score_report", return_value=mock_report):
        rc = handle_scorer(_make_args(top=2))
    assert rc == 0
    out = capsys.readouterr().out
    lines = [l for l in out.splitlines() if "job" in l]
    assert len(lines) == 2


def test_handle_scorer_min_score_filters(capsys):
    jobs = [_make_scored_job("good", 80.0), _make_scored_job("bad", 20.0)]
    mock_report = MagicMock(spec=ScoredReport)
    mock_report.jobs = jobs
    with patch("cronsight.cli_scorer.load_snapshot"), \
         patch("cronsight.cli_scorer.score_report", return_value=mock_report):
        rc = handle_scorer(_make_args(min_score=50.0))
    assert rc == 0
    out = capsys.readouterr().out
    assert "bad" in out
    assert "good" not in out


def test_handle_scorer_no_matching_jobs_prints_message(capsys):
    mock_report = MagicMock(spec=ScoredReport)
    mock_report.jobs = []
    with patch("cronsight.cli_scorer.load_snapshot"), \
         patch("cronsight.cli_scorer.score_report", return_value=mock_report):
        rc = handle_scorer(_make_args())
    assert rc == 0
    assert "No jobs" in capsys.readouterr().out
