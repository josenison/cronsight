"""Tests for cronsight.bucketer."""

from datetime import datetime, timezone

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.bucketer import (
    BucketerError,
    BucketReport,
    TimeBucket,
    bucket_report,
    bucket_summary,
)
from cronsight.parser import CronEntry


def _entry(cmd: str, ts: datetime, exit_code: int = 0) -> CronEntry:
    return CronEntry(command=cmd, timestamp=ts, exit_code=exit_code, server="srv1")


def _ts(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def simple_summary() -> JobSummary:
    entries = [
        _entry("backup.sh", _ts(2024, 1, 1, 2)),
        _entry("backup.sh", _ts(2024, 1, 1, 14)),
        _entry("backup.sh", _ts(2024, 1, 2, 2), exit_code=1),
        _entry("backup.sh", _ts(2024, 1, 3, 2)),
    ]
    return JobSummary(command="backup.sh", entries=entries)


def test_time_bucket_total_runs():
    entry = _entry("cmd", _ts(2024, 1, 1))
    bucket = TimeBucket(label="2024-01-01", entries=[entry, entry])
    assert bucket.total_runs == 2


def test_time_bucket_success_rate_all_pass():
    entries = [_entry("cmd", _ts(2024, 1, 1)) for _ in range(4)]
    bucket = TimeBucket(label="x", entries=entries)
    assert bucket.success_rate == 1.0


def test_time_bucket_success_rate_mixed():
    entries = [
        _entry("cmd", _ts(2024, 1, 1), exit_code=0),
        _entry("cmd", _ts(2024, 1, 1), exit_code=1),
    ]
    bucket = TimeBucket(label="x", entries=entries)
    assert bucket.success_rate == 0.5


def test_time_bucket_str_includes_label():
    bucket = TimeBucket(label="2024-01-01")
    assert "2024-01-01" in str(bucket)


def test_bucket_summary_daily_creates_one_bucket_per_day(simple_summary):
    report = bucket_summary(simple_summary, granularity="daily")
    assert report.count == 3


def test_bucket_summary_daily_groups_same_day(simple_summary):
    report = bucket_summary(simple_summary, granularity="daily")
    first_bucket = report.buckets[0]
    assert first_bucket.total_runs == 2


def test_bucket_summary_hourly_separates_hours(simple_summary):
    report = bucket_summary(simple_summary, granularity="hourly")
    assert report.count == 4


def test_bucket_summary_weekly_groups_same_week():
    entries = [
        _entry("cmd", _ts(2024, 1, 1)),
        _entry("cmd", _ts(2024, 1, 3)),
        _entry("cmd", _ts(2024, 1, 8)),
    ]
    summary = JobSummary(command="cmd", entries=entries)
    report = bucket_summary(summary, granularity="weekly")
    assert report.count == 2


def test_bucket_summary_invalid_granularity_raises(simple_summary):
    with pytest.raises(BucketerError):
        bucket_summary(simple_summary, granularity="monthly")  # type: ignore


def test_bucket_summary_skips_entries_without_timestamp():
    entries = [
        CronEntry(command="cmd", timestamp=None, exit_code=0, server="srv"),
        _entry("cmd", _ts(2024, 1, 1)),
    ]
    summary = JobSummary(command="cmd", entries=entries)
    report = bucket_summary(summary, granularity="daily")
    assert report.count == 1


def test_bucket_report_returns_one_per_job():
    s1 = JobSummary(command="a", entries=[_entry("a", _ts(2024, 1, 1))])
    s2 = JobSummary(command="b", entries=[_entry("b", _ts(2024, 1, 2))])
    agg = AggregatedReport(summaries=[s1, s2])
    reports = bucket_report(agg, granularity="daily")
    assert len(reports) == 2
    assert all(isinstance(r, BucketReport) for r in reports)


def test_bucket_report_preserves_command(simple_summary):
    agg = AggregatedReport(summaries=[simple_summary])
    reports = bucket_report(agg)
    assert reports[0].command == "backup.sh"
