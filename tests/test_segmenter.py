"""Tests for cronsight.segmenter."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.segmenter import SegmenterError, segment_report


def _entry(cmd: str, ts: datetime, success: bool = True) -> CronEntry:
    return CronEntry(command=cmd, timestamp=ts, success=success, raw="")


def _ts(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, 0, 0, tzinfo=timezone.utc)


def _make_report(*entries: CronEntry) -> AggregatedReport:
    jobs: dict = {}
    for e in entries:
        jobs.setdefault(e.command, []).append(e)
    summaries = {
        cmd: JobSummary(command=cmd, entries=elist, servers={"srv1"})
        for cmd, elist in jobs.items()
    }
    return AggregatedReport(jobs=summaries)


def test_segment_daily_creates_one_segment_per_day():
    report = _make_report(
        _entry("backup", _ts(2024, 1, 1)),
        _entry("backup", _ts(2024, 1, 2)),
        _entry("backup", _ts(2024, 1, 3)),
    )
    result = segment_report(report, granularity="daily")
    assert result.count == 3
    assert result.granularity == "daily"


def test_segment_daily_groups_same_day():
    report = _make_report(
        _entry("cleanup", _ts(2024, 3, 5, 6)),
        _entry("cleanup", _ts(2024, 3, 5, 18)),
        _entry("cleanup", _ts(2024, 3, 6, 9)),
    )
    result = segment_report(report, granularity="daily")
    assert result.count == 2
    march5 = next(s for s in result.segments if s.label == "2024-03-05")
    assert len(march5.jobs["cleanup"].entries) == 2


def test_segment_hourly_creates_one_segment_per_hour():
    report = _make_report(
        _entry("job", _ts(2024, 6, 1, 10)),
        _entry("job", _ts(2024, 6, 1, 11)),
        _entry("job", _ts(2024, 6, 1, 11)),
    )
    result = segment_report(report, granularity="hourly")
    assert result.count == 2
    labels = {s.label for s in result.segments}
    assert "2024-06-01 10:00" in labels
    assert "2024-06-01 11:00" in labels


def test_segment_weekly_groups_same_week():
    report = _make_report(
        _entry("sync", _ts(2024, 1, 8)),   # week 2
        _entry("sync", _ts(2024, 1, 10)),  # week 2
        _entry("sync", _ts(2024, 1, 15)),  # week 3
    )
    result = segment_report(report, granularity="weekly")
    assert result.count == 2


def test_segment_skips_entries_without_timestamp():
    no_ts = CronEntry(command="job", timestamp=None, success=True, raw="")
    report = _make_report(_entry("job", _ts(2024, 1, 1)))
    report.jobs["job"].entries.append(no_ts)
    result = segment_report(report, granularity="daily")
    seg = result.segments[0]
    assert len(seg.jobs["job"].entries) == 1


def test_segment_invalid_granularity_raises():
    report = _make_report(_entry("job", _ts(2024, 1, 1)))
    with pytest.raises(SegmenterError):
        segment_report(report, granularity="monthly")  # type: ignore[arg-type]


def test_segment_total_runs_matches_entry_count():
    report = _make_report(
        _entry("a", _ts(2024, 2, 1)),
        _entry("b", _ts(2024, 2, 1)),
        _entry("a", _ts(2024, 2, 1)),
    )
    result = segment_report(report, granularity="daily")
    assert result.segments[0].total_runs == 3


def test_segment_job_count_per_segment():
    report = _make_report(
        _entry("a", _ts(2024, 5, 1)),
        _entry("b", _ts(2024, 5, 1)),
        _entry("c", _ts(2024, 5, 2)),
    )
    result = segment_report(report, granularity="daily")
    may1 = next(s for s in result.segments if s.label == "2024-05-01")
    assert may1.job_count == 2
