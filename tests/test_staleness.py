"""Tests for cronsight.staleness."""

from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.staleness import (
    StaleJob,
    StalenessReport,
    StalenessError,
    detect_stale,
    _staleness_seconds,
)


def _make_entry(cmd: str, ts: datetime, status: str = "success") -> CronEntry:
    return CronEntry(timestamp=ts, command=cmd, status=status, server="host1")


def _make_summary(cmd: str, last_run: datetime | None = None) -> JobSummary:
    entries = []
    if last_run:
        entries.append(_make_entry(cmd, last_run))
    return JobSummary(
        command=cmd,
        entries=entries,
        servers=["host1"],
    )


def _make_report(*summaries: JobSummary) -> AggregatedReport:
    return AggregatedReport(jobs={s.command: s for s in summaries})


NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# StaleJob
# ---------------------------------------------------------------------------

def test_stale_job_str_includes_command():
    job = StaleJob(
        command="/usr/bin/backup",
        server="host1",
        last_run=None,
        expected_after=None,
        staleness_seconds=300.0,
    )
    assert "/usr/bin/backup" in str(job)
    assert "host1" in str(job)


def test_stale_job_str_never_when_no_last_run():
    job = StaleJob(
        command="cmd", server="s", last_run=None,
        expected_after=None, staleness_seconds=60.0,
    )
    assert "never" in str(job)


# ---------------------------------------------------------------------------
# StalenessReport
# ---------------------------------------------------------------------------

def test_staleness_report_count_and_has_stale():
    report = StalenessReport()
    assert report.count == 0
    assert not report.has_stale

    job = StaleJob("cmd", "s", None, None, 10.0)
    report.stale_jobs.append(job)
    assert report.count == 1
    assert report.has_stale


# ---------------------------------------------------------------------------
# detect_stale
# ---------------------------------------------------------------------------

def test_detect_stale_no_schedules_returns_empty():
    summary = _make_summary("backup", last_run=NOW - timedelta(hours=2))
    report = _make_report(summary)
    result = detect_stale(report, schedules={}, now=NOW)
    assert result.count == 0


def test_detect_stale_recent_job_not_flagged():
    # Job ran 1 minute ago; schedule is every hour — not stale
    summary = _make_summary("/bin/check", last_run=NOW - timedelta(minutes=1))
    report = _make_report(summary)
    result = detect_stale(report, schedules={"/bin/check": "0 * * * *"}, now=NOW)
    assert result.count == 0


def test_detect_stale_overdue_job_flagged():
    # Job last ran 90 minutes ago; schedule is every hour
    summary = _make_summary("/bin/check", last_run=NOW - timedelta(minutes=90))
    report = _make_report(summary)
    result = detect_stale(report, schedules={"/bin/check": "0 * * * *"}, now=NOW)
    assert result.count == 1
    assert result.stale_jobs[0].command == "/bin/check"


def test_detect_stale_never_ran_flagged():
    summary = _make_summary("/bin/neverran")
    report = _make_report(summary)
    result = detect_stale(report, schedules={"/bin/neverran": "0 * * * *"}, now=NOW)
    assert result.count == 1
    assert result.stale_jobs[0].last_run is None


def test_detect_stale_threshold_filters_minor_staleness():
    summary = _make_summary("/bin/check", last_run=NOW - timedelta(minutes=65))
    report = _make_report(summary)
    # 5 minute staleness but threshold is 600 seconds
    result = detect_stale(
        report,
        schedules={"/bin/check": "0 * * * *"},
        now=NOW,
        threshold_seconds=600.0,
    )
    assert result.count == 0


def test_detect_stale_sorted_by_staleness_descending():
    s1 = _make_summary("/bin/a", last_run=NOW - timedelta(minutes=90))
    s2 = _make_summary("/bin/b", last_run=NOW - timedelta(minutes=200))
    report = _make_report(s1, s2)
    schedules = {"/bin/a": "0 * * * *", "/bin/b": "0 * * * *"}
    result = detect_stale(report, schedules=schedules, now=NOW)
    assert result.count == 2
    assert result.stale_jobs[0].staleness_seconds >= result.stale_jobs[1].staleness_seconds


def test_detect_stale_uses_utc_now_by_default():
    summary = _make_summary("/bin/check", last_run=NOW - timedelta(hours=3))
    report = _make_report(summary)
    # Should not raise even without explicit `now`
    result = detect_stale(report, schedules={"/bin/check": "0 * * * *"})
    assert isinstance(result, StalenessReport)
