"""Tests for cronsight.splitter."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.splitter import SplitterError, split_report


def _entry(ts: datetime, status: str = "success") -> CronEntry:
    return CronEntry(timestamp=ts, command="backup.sh", status=status, server="srv1")


def _make_report(*timestamps: datetime) -> AggregatedReport:
    entries = [_entry(ts) for ts in timestamps]
    summary = JobSummary(command="backup.sh", servers=["srv1"], entries=entries)
    report = AggregatedReport(jobs={"backup.sh": summary})
    return report


def _ts(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# split_report – basic
# ---------------------------------------------------------------------------

def test_split_daily_creates_one_window_per_day():
    report = _make_report(_ts(2024, 5, 1), _ts(2024, 5, 2), _ts(2024, 5, 3))
    result = split_report(report, "daily")
    assert result.window_count == 3


def test_split_daily_groups_same_day_entries():
    report = _make_report(
        _ts(2024, 5, 1, 8), _ts(2024, 5, 1, 14), _ts(2024, 5, 2, 9)
    )
    result = split_report(report, "daily")
    assert result.window_count == 2
    first = result.windows[0]
    assert first.total_runs == 2


def test_split_hourly_separates_different_hours():
    report = _make_report(_ts(2024, 5, 1, 8), _ts(2024, 5, 1, 9))
    result = split_report(report, "hourly")
    assert result.window_count == 2


def test_split_hourly_groups_same_hour():
    from datetime import timedelta
    base = _ts(2024, 5, 1, 10)
    t2 = datetime(2024, 5, 1, 10, 30, 0, tzinfo=timezone.utc)
    report = _make_report(base, t2)
    result = split_report(report, "hourly")
    assert result.window_count == 1
    assert result.windows[0].total_runs == 2


def test_split_weekly_groups_same_week():
    # 2024-04-29 is Monday; 2024-05-05 is Sunday of the same week
    report = _make_report(_ts(2024, 4, 29), _ts(2024, 5, 5))
    result = split_report(report, "weekly")
    assert result.window_count == 1


def test_split_weekly_separates_different_weeks():
    report = _make_report(_ts(2024, 4, 29), _ts(2024, 5, 6))
    result = split_report(report, "weekly")
    assert result.window_count == 2


def test_split_windows_sorted_chronologically():
    report = _make_report(_ts(2024, 5, 3), _ts(2024, 5, 1), _ts(2024, 5, 2))
    result = split_report(report, "daily")
    labels = [w.label for w in result.windows]
    assert labels == sorted(labels)


def test_split_invalid_size_raises():
    report = _make_report(_ts(2024, 5, 1))
    with pytest.raises(SplitterError):
        split_report(report, "monthly")  # type: ignore[arg-type]


def test_split_skips_entries_without_timestamp():
    entry_no_ts = CronEntry(timestamp=None, command="backup.sh", status="success", server="srv1")
    summary = JobSummary(command="backup.sh", servers=["srv1"], entries=[entry_no_ts])
    report = AggregatedReport(jobs={"backup.sh": summary})
    result = split_report(report, "daily")
    assert result.window_count == 0


def test_window_job_count_correct():
    report = _make_report(_ts(2024, 5, 1, 8))
    result = split_report(report, "daily")
    assert result.windows[0].job_count == 1
