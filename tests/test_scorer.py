"""Tests for cronsight.scorer."""
from __future__ import annotations

from datetime import datetime

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.scorer import (
    ScoredReport,
    ScorerError,
    _compute_score,
    _has_recent_failure,
    _success_rate,
    score_report,
)


def _entry(cmd: str, exit_code: int, ts: datetime) -> CronEntry:
    return CronEntry(timestamp=ts, command=cmd, exit_code=exit_code, server="srv1")


def _summary(cmd: str, entries) -> JobSummary:
    s = JobSummary(command=cmd, server="srv1")
    s.entries.extend(entries)
    return s


def _report(*summaries: JobSummary) -> AggregatedReport:
    r = AggregatedReport()
    for s in summaries:
        r.jobs[s.command] = s
    return r


t0 = datetime(2024, 1, 1, 0, 0, 0)
t1 = datetime(2024, 1, 1, 1, 0, 0)
t2 = datetime(2024, 1, 1, 2, 0, 0)


def test_success_rate_all_pass():
    s = _summary("job", [_entry("job", 0, t0), _entry("job", 0, t1)])
    assert _success_rate(s) == 1.0


def test_success_rate_mixed():
    s = _summary("job", [_entry("job", 0, t0), _entry("job", 1, t1)])
    assert _success_rate(s) == 0.5


def test_success_rate_no_entries():
    s = _summary("job", [])
    assert _success_rate(s) == 0.0


def test_has_recent_failure_true():
    s = _summary("job", [_entry("job", 0, t0), _entry("job", 1, t2)])
    assert _has_recent_failure(s) is True


def test_has_recent_failure_false():
    s = _summary("job", [_entry("job", 1, t0), _entry("job", 0, t2)])
    assert _has_recent_failure(s) is False


def test_compute_score_perfect():
    score = _compute_score(1.0, False, 10)
    assert score == 90.0


def test_compute_score_recent_failure_reduces_score():
    without = _compute_score(1.0, False, 10)
    with_fail = _compute_score(1.0, True, 10)
    assert with_fail < without


def test_compute_score_clamps_to_zero():
    assert _compute_score(0.0, True, 0) == 0.0


def test_score_report_returns_sorted_ascending():
    good = _summary("good", [_entry("good", 0, t0)] * 10)
    bad = _summary("bad", [_entry("bad", 1, t0)] * 10)
    result = score_report(_report(good, bad))
    assert result.jobs[0].command == "bad"
    assert result.jobs[-1].command == "good"


def test_score_report_lowest_and_highest():
    good = _summary("good", [_entry("good", 0, t0)] * 5)
    bad = _summary("bad", [_entry("bad", 1, t0)] * 5)
    result = score_report(_report(good, bad))
    assert result.lowest_score.command == "bad"
    assert result.highest_score.command == "good"


def test_score_report_empty_report():
    result = score_report(AggregatedReport())
    assert result.jobs == []
    assert result.lowest_score is None
    assert result.highest_score is None
