"""Tests for cronsight.auditor."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.auditor import AuditorError, SilentJob, audit_report
from cronsight.parser import CronEntry


NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_entry(ts: datetime, exit_code: int = 0) -> CronEntry:
    return CronEntry(timestamp=ts, command="/bin/job", exit_code=exit_code, server="srv1")


def _make_summary(last_run: datetime | None, command: str = "/bin/job") -> JobSummary:
    entries = [_make_entry(last_run)] if last_run else []
    return JobSummary(command=command, entries=entries, servers=["srv1"])


def _make_report(*summaries: JobSummary) -> AggregatedReport:
    return AggregatedReport(jobs={s.command: s for s in summaries})


def test_audit_no_silent_jobs_returns_empty():
    recent = NOW - timedelta(hours=1)
    report = _make_report(_make_summary(recent))
    result = audit_report(report, threshold_hours=24.0, now=NOW)
    assert not result.has_silent_jobs
    assert result.count == 0


def test_audit_detects_silent_job():
    old = NOW - timedelta(hours=30)
    report = _make_report(_make_summary(old))
    result = audit_report(report, threshold_hours=24.0, now=NOW)
    assert result.has_silent_jobs
    assert result.count == 1
    assert result.silent_jobs[0].command == "/bin/job"


def test_audit_detects_never_ran_job():
    report = _make_report(_make_summary(None))
    result = audit_report(report, threshold_hours=24.0, now=NOW)
    assert result.count == 1
    assert result.silent_jobs[0].last_run is None
    assert result.silent_jobs[0].hours_since_last_run is None


def test_audit_mixed_jobs():
    recent = NOW - timedelta(hours=2)
    old = NOW - timedelta(hours=48)
    report = _make_report(
        _make_summary(recent, "/bin/ok"),
        _make_summary(old, "/bin/stale"),
    )
    result = audit_report(report, threshold_hours=24.0, now=NOW)
    assert result.count == 1
    assert result.silent_jobs[0].command == "/bin/stale"


def test_audit_threshold_zero_raises():
    report = _make_report(_make_summary(NOW))
    with pytest.raises(AuditorError):
        audit_report(report, threshold_hours=0, now=NOW)


def test_audit_threshold_negative_raises():
    report = _make_report(_make_summary(NOW))
    with pytest.raises(AuditorError):
        audit_report(report, threshold_hours=-5.0, now=NOW)


def test_silent_job_str_with_hours():
    job = SilentJob(command="/bin/x", server="s1", last_run=None, hours_since_last_run=36.5)
    assert "36.5h" in str(job)
    assert "/bin/x" in str(job)


def test_silent_job_str_never_ran():
    job = SilentJob(command="/bin/x", server="s1", last_run=None, hours_since_last_run=None)
    assert "never ran" in str(job)


def test_audit_report_sorted_most_silent_first():
    old1 = NOW - timedelta(hours=100)
    old2 = NOW - timedelta(hours=50)
    report = _make_report(
        _make_summary(old2, "/bin/b"),
        _make_summary(old1, "/bin/a"),
    )
    result = audit_report(report, threshold_hours=24.0, now=NOW)
    assert result.silent_jobs[0].command == "/bin/a"
