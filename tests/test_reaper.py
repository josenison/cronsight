"""Unit tests for cronsight.reaper."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.reaper import DeadJob, ReaperError, ReaperReport, reap


def _entry(success: bool = True) -> CronEntry:
    return CronEntry(timestamp=datetime(2024, 1, 10, 6, 0, 0), command="backup.sh", success=success, server="host1")


def _summary(last_run: datetime | None, total: int = 3, failed: int = 0) -> JobSummary:
    entries = [
        CronEntry(timestamp=last_run or datetime(2024, 1, 1), command="backup.sh", success=True, server="host1")
    ] if last_run else []
    s = JobSummary(entries=entries)
    s._servers = {"host1"}
    return s


def _report(last_run: datetime | None = None) -> AggregatedReport:
    summary = _summary(last_run)
    r = AggregatedReport()
    r.jobs["backup.sh"] = summary
    return r


NOW = datetime(2024, 1, 10, 12, 0, 0)


def test_reap_raises_on_non_positive_interval():
    r = _report()
    with pytest.raises(ReaperError):
        reap(r, expected_interval_hours=0, now=NOW)


def test_reap_raises_on_negative_interval():
    r = _report()
    with pytest.raises(ReaperError):
        reap(r, expected_interval_hours=-1, now=NOW)


def test_reap_raises_on_invalid_pattern():
    r = _report(last_run=NOW - timedelta(hours=1))
    with pytest.raises(ReaperError):
        reap(r, expected_interval_hours=24, pattern="[invalid", now=NOW)


def test_no_dead_jobs_when_recently_run():
    last = NOW - timedelta(hours=1)
    r = _report(last_run=last)
    result = reap(r, expected_interval_hours=24, now=NOW)
    assert result.count == 0
    assert not result.has_dead_jobs


def test_dead_job_detected_when_overdue():
    last = NOW - timedelta(hours=30)
    r = _report(last_run=last)
    result = reap(r, expected_interval_hours=24, now=NOW)
    assert result.count == 1
    assert result.has_dead_jobs


def test_dead_job_has_correct_hours_overdue():
    last = NOW - timedelta(hours=30)
    r = _report(last_run=last)
    result = reap(r, expected_interval_hours=24, now=NOW)
    job = result.dead_jobs[0]
    assert abs(job.hours_overdue - 6.0) < 0.01


def test_never_run_job_is_dead():
    r = _report(last_run=None)
    result = reap(r, expected_interval_hours=24, now=NOW)
    assert result.count == 1
    assert result.dead_jobs[0].hours_overdue == float("inf")


def test_pattern_filters_jobs():
    r = _report(last_run=NOW - timedelta(hours=30))
    result = reap(r, expected_interval_hours=24, pattern="^other", now=NOW)
    assert result.count == 0


def test_dead_job_str_contains_command():
    last = NOW - timedelta(hours=30)
    r = _report(last_run=last)
    result = reap(r, expected_interval_hours=24, now=NOW)
    assert "backup.sh" in str(result.dead_jobs[0])


def test_dead_jobs_sorted_by_overdue_descending():
    r = AggregatedReport()
    for cmd, hours_ago in [("a.sh", 50), ("b.sh", 100), ("c.sh", 30)]:
        s = JobSummary(entries=[
            CronEntry(timestamp=NOW - timedelta(hours=hours_ago), command=cmd, success=True, server="h1")
        ])
        r.jobs[cmd] = s
    result = reap(r, expected_interval_hours=24, now=NOW)
    overdues = [j.hours_overdue for j in result.dead_jobs]
    assert overdues == sorted(overdues, reverse=True)
