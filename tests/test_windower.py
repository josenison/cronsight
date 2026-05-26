"""Tests for cronsight.windower."""
from datetime import datetime, timedelta

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.windower import (
    TimeWindow,
    WindowReport,
    WindowerError,
    build_windows,
)


def _entry(cmd: str, ts: datetime, success: bool = True) -> CronEntry:
    return CronEntry(
        command=cmd,
        timestamp=ts,
        success=success,
        server="srv1",
        raw="",
    )


def _summary(cmd: str, entries) -> JobSummary:
    return JobSummary(command=cmd, entries=entries, servers=["srv1"])


def _report(*summaries: JobSummary) -> AggregatedReport:
    return AggregatedReport(summaries={s.command: s for s in summaries})


BASE = datetime(2024, 6, 1, 12, 0, 0)


def test_build_windows_returns_window_report():
    s = _summary("job1", [_entry("job1", BASE)])
    result = build_windows(_report(s), window_minutes=60)
    assert isinstance(result, WindowReport)


def test_build_windows_empty_report_returns_empty():
    result = build_windows(AggregatedReport(summaries={}), window_minutes=60)
    assert result.count == 0


def test_build_windows_invalid_minutes_raises():
    s = _summary("job1", [_entry("job1", BASE)])
    with pytest.raises(WindowerError):
        build_windows(_report(s), window_minutes=0)


def test_build_windows_negative_minutes_raises():
    s = _summary("job1", [_entry("job1", BASE)])
    with pytest.raises(WindowerError):
        build_windows(_report(s), window_minutes=-30)


def test_single_entry_produces_one_window():
    s = _summary("job1", [_entry("job1", BASE)])
    result = build_windows(_report(s), window_minutes=60)
    assert result.count == 1


def test_entries_spread_across_two_windows():
    e1 = _entry("job1", BASE)
    e2 = _entry("job1", BASE + timedelta(minutes=90))
    s = _summary("job1", [e1, e2])
    result = build_windows(_report(s), window_minutes=60)
    assert result.count == 2


def test_window_total_runs_reflects_entries():
    entries = [_entry("job1", BASE + timedelta(minutes=i * 10)) for i in range(4)]
    s = _summary("job1", entries)
    result = build_windows(_report(s), window_minutes=60)
    total = sum(w.total_runs for w in result.windows)
    assert total == 4


def test_window_job_count():
    s1 = _summary("job1", [_entry("job1", BASE)])
    s2 = _summary("job2", [_entry("job2", BASE + timedelta(minutes=5))])
    result = build_windows(_report(s1, s2), window_minutes=60)
    assert result.windows[0].job_count == 2


def test_since_clips_earlier_entries():
    e_old = _entry("job1", BASE - timedelta(hours=2))
    e_new = _entry("job1", BASE)
    s = _summary("job1", [e_old, e_new])
    result = build_windows(_report(s), window_minutes=60, since=BASE)
    total = sum(w.total_runs for w in result.windows)
    assert total == 1


def test_time_window_str_contains_dates():
    win = TimeWindow(start=BASE, end=BASE + timedelta(hours=1))
    text = str(win)
    assert "2024-06-01" in text
    assert "jobs=0" in text
