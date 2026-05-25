"""Tests for cronsight.cadence."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.cadence import (
    CadenceError,
    CadenceProfile,
    CadenceReport,
    _intervals,
    _is_irregular,
    analyze_cadence,
)
from cronsight.parser import CronEntry


def _entry(ts: datetime, status: str = "success") -> CronEntry:
    return CronEntry(timestamp=ts, command="/usr/bin/backup", status=status, server="host1")


def _make_summary(commands_ts: list[datetime], command: str = "/usr/bin/backup", server: str = "host1") -> JobSummary:
    entries = [_entry(ts) for ts in commands_ts]
    return JobSummary(command=command, server=server, entries=entries)


# --- _intervals ---

def test_intervals_empty_returns_empty():
    assert _intervals([]) == []


def test_intervals_single_returns_empty():
    t = datetime(2024, 1, 1, 12, 0)
    assert _intervals([t]) == []


def test_intervals_two_timestamps():
    t1 = datetime(2024, 1, 1, 12, 0)
    t2 = datetime(2024, 1, 1, 13, 0)
    assert _intervals([t1, t2]) == [3600.0]


def test_intervals_sorted_regardless_of_input_order():
    t1 = datetime(2024, 1, 1, 12, 0)
    t2 = datetime(2024, 1, 1, 13, 0)
    t3 = datetime(2024, 1, 1, 14, 0)
    result = _intervals([t3, t1, t2])
    assert result == [3600.0, 3600.0]


# --- _is_irregular ---

def test_is_irregular_regular_intervals_returns_false():
    ivs = [3600.0, 3600.0, 3600.0, 3600.0]
    assert _is_irregular(ivs, threshold=0.5) is False


def test_is_irregular_high_variance_returns_true():
    ivs = [100.0, 10000.0, 200.0, 9000.0]
    assert _is_irregular(ivs, threshold=0.5) is True


def test_is_irregular_single_interval_returns_false():
    assert _is_irregular([3600.0], threshold=0.5) is False


# --- analyze_cadence ---

def test_analyze_cadence_returns_cadence_report():
    base = datetime(2024, 1, 1, 6, 0)
    ts = [base + timedelta(hours=i) for i in range(5)]
    summary = _make_summary(ts)
    report = AggregatedReport(summaries=[summary])
    result = analyze_cadence(report)
    assert isinstance(result, CadenceReport)
    assert result.count == 1


def test_analyze_cadence_regular_job_not_flagged():
    base = datetime(2024, 1, 1, 6, 0)
    ts = [base + timedelta(hours=i) for i in range(6)]
    summary = _make_summary(ts)
    report = AggregatedReport(summaries=[summary])
    result = analyze_cadence(report)
    assert result.profiles[0].is_irregular is False
    assert result.irregular_count == 0


def test_analyze_cadence_irregular_job_flagged():
    base = datetime(2024, 1, 1, 0, 0)
    ts = [
        base,
        base + timedelta(minutes=1),
        base + timedelta(hours=10),
        base + timedelta(hours=10, minutes=1),
        base + timedelta(hours=20),
    ]
    summary = _make_summary(ts)
    report = AggregatedReport(summaries=[summary])
    result = analyze_cadence(report)
    assert result.profiles[0].is_irregular is True
    assert result.irregular_count == 1


def test_analyze_cadence_insufficient_data_no_mean():
    ts = [datetime(2024, 1, 1, 12, 0)]
    summary = _make_summary(ts)
    report = AggregatedReport(summaries=[summary])
    result = analyze_cadence(report)
    assert result.profiles[0].mean_interval_seconds is None


def test_analyze_cadence_invalid_threshold_raises():
    report = AggregatedReport(summaries=[])
    with pytest.raises(CadenceError):
        analyze_cadence(report, irregularity_threshold=-1.0)


def test_cadence_profile_str_includes_command():
    p = CadenceProfile(
        command="/usr/bin/backup",
        server="host1",
        run_count=5,
        mean_interval_seconds=3600.0,
        stdev_interval_seconds=10.0,
        max_interval_seconds=3700.0,
        is_irregular=False,
    )
    assert "/usr/bin/backup" in str(p)
    assert "host1" in str(p)
