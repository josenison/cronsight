"""Tests for cronsight.scorer_trend."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.scorer_trend import ScoreDelta, ScorerTrendReport, build_scorer_trend


def _entry(status: str = "success", ts: str = "2024-01-01T10:00:00") -> CronEntry:
    return CronEntry(
        timestamp=datetime.fromisoformat(ts).replace(tzinfo=timezone.utc),
        server="srv1",
        command="/usr/bin/backup",
        status=status,
        raw=f"{ts} srv1 /usr/bin/backup {status}",
    )


def _summary(command: str, entries: List[CronEntry]) -> JobSummary:
    return JobSummary(
        command=command,
        entries=entries,
        servers=list({e.server for e in entries}),
    )


def _report(*summaries: JobSummary) -> AggregatedReport:
    return AggregatedReport(jobs={s.command: s for s in summaries})


# ---------------------------------------------------------------------------
# ScoreDelta
# ---------------------------------------------------------------------------

def test_score_delta_delta_positive():
    d = ScoreDelta(command="cmd", old_score=40.0, new_score=70.0)
    assert d.delta == pytest.approx(30.0)


def test_score_delta_improved_true_when_positive():
    d = ScoreDelta(command="cmd", old_score=50.0, new_score=80.0)
    assert d.improved is True
    assert d.degraded is False


def test_score_delta_degraded_true_when_negative():
    d = ScoreDelta(command="cmd", old_score=80.0, new_score=40.0)
    assert d.degraded is True
    assert d.improved is False


def test_score_delta_str_contains_command():
    d = ScoreDelta(command="/usr/bin/backup", old_score=60.0, new_score=75.0)
    assert "/usr/bin/backup" in str(d)


# ---------------------------------------------------------------------------
# ScorerTrendReport
# ---------------------------------------------------------------------------

def test_trend_report_count():
    deltas = [ScoreDelta("a", 50.0, 80.0), ScoreDelta("b", 80.0, 50.0)]
    report = ScorerTrendReport(deltas=deltas)
    assert report.count == 2


def test_trend_report_improved_count():
    deltas = [ScoreDelta("a", 50.0, 80.0), ScoreDelta("b", 80.0, 50.0)]
    report = ScorerTrendReport(deltas=deltas)
    assert report.improved_count == 1
    assert report.degraded_count == 1


def test_trend_report_most_improved():
    deltas = [ScoreDelta("a", 50.0, 60.0), ScoreDelta("b", 50.0, 90.0)]
    report = ScorerTrendReport(deltas=deltas)
    assert report.most_improved().command == "b"


def test_trend_report_most_degraded():
    deltas = [ScoreDelta("a", 90.0, 30.0), ScoreDelta("b", 90.0, 70.0)]
    report = ScorerTrendReport(deltas=deltas)
    assert report.most_degraded().command == "a"


def test_trend_report_most_improved_empty_returns_none():
    report = ScorerTrendReport(deltas=[])
    assert report.most_improved() is None
    assert report.most_degraded() is None


# ---------------------------------------------------------------------------
# build_scorer_trend
# ---------------------------------------------------------------------------

def test_build_scorer_trend_returns_report():
    s1 = _summary("/usr/bin/backup", [_entry("success")] * 5)
    old = _report(s1)
    s2 = _summary("/usr/bin/backup", [_entry("success")] * 5)
    new = _report(s2)
    result = build_scorer_trend(old, new)
    assert isinstance(result, ScorerTrendReport)


def test_build_scorer_trend_only_changed_excludes_stable():
    entries = [_entry("success")] * 5
    s = _summary("/usr/bin/backup", entries)
    old = _report(s)
    new = _report(_summary("/usr/bin/backup", entries))
    result = build_scorer_trend(old, new, only_changed=True)
    assert all(d.delta != 0.0 for d in result.deltas)


def test_build_scorer_trend_new_job_has_old_score_zero():
    old = _report()  # empty
    s = _summary("/usr/bin/newjob", [_entry("success")] * 3)
    new = _report(s)
    result = build_scorer_trend(old, new)
    assert any(d.command == "/usr/bin/newjob" for d in result.deltas)
    match = next(d for d in result.deltas if d.command == "/usr/bin/newjob")
    assert match.old_score == 0.0


def test_build_scorer_trend_degraded_job_has_negative_delta():
    good_entries = [_entry("success")] * 10
    bad_entries = [_entry("failure")] * 10
    old = _report(_summary("/usr/bin/job", good_entries))
    new = _report(_summary("/usr/bin/job", bad_entries))
    result = build_scorer_trend(old, new)
    match = next(d for d in result.deltas if d.command == "/usr/bin/job")
    assert match.degraded
