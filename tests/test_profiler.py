"""Tests for cronsight.profiler."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.profiler import (
    DurationProfile,
    ProfileReport,
    ProfilerError,
    _extract_durations,
    build_profile,
)


def _entry(command: str, status: str, ts: float) -> CronEntry:
    e = MagicMock(spec=CronEntry)
    e.command = command
    e.status = status
    e.timestamp = ts
    return e


def _summary(command: str, server: str, entries) -> JobSummary:
    s = MagicMock(spec=JobSummary)
    s.command = command
    s.server = server
    s.entries = entries
    return s


# --- DurationProfile ---

def test_duration_profile_count_empty():
    p = DurationProfile(command="cmd", server="srv")
    assert p.count == 0


def test_duration_profile_mean_none_when_empty():
    p = DurationProfile(command="cmd", server="srv")
    assert p.mean_seconds is None


def test_duration_profile_mean_computed():
    p = DurationProfile(command="cmd", server="srv", durations=[10.0, 20.0, 30.0])
    assert p.mean_seconds == pytest.approx(20.0)


def test_duration_profile_stddev_none_for_single():
    p = DurationProfile(command="cmd", server="srv", durations=[5.0])
    assert p.stddev_seconds is None


def test_duration_profile_str_no_data():
    p = DurationProfile(command="backup", server="host1")
    assert "no data" in str(p)


def test_duration_profile_str_with_data():
    p = DurationProfile(command="backup", server="host1", durations=[60.0, 120.0])
    assert "mean=" in str(p)
    assert "host1" in str(p)


# --- _extract_durations ---

def test_extract_durations_paired_entries():
    entries = [
        _entry("backup", "started", 1000.0),
        _entry("backup", "succeeded", 1060.0),
    ]
    durations = _extract_durations(entries)
    assert durations == pytest.approx([60.0])


def test_extract_durations_ignores_unpaired_end():
    entries = [_entry("backup", "succeeded", 1060.0)]
    assert _extract_durations(entries) == []


def test_extract_durations_multiple_pairs():
    entries = [
        _entry("job", "started", 0.0),
        _entry("job", "succeeded", 10.0),
        _entry("job", "started", 100.0),
        _entry("job", "failed", 115.0),
    ]
    durations = _extract_durations(entries)
    assert len(durations) == 2
    assert durations[0] == pytest.approx(10.0)
    assert durations[1] == pytest.approx(15.0)


# --- build_profile ---

def test_build_profile_raises_on_empty_report():
    report = MagicMock(spec=AggregatedReport)
    report.jobs = {}
    with pytest.raises(ProfilerError):
        build_profile(report)


def test_build_profile_returns_one_profile_per_job():
    entries = [
        _entry("cmd", "started", 0.0),
        _entry("cmd", "succeeded", 5.0),
    ]
    report = MagicMock(spec=AggregatedReport)
    report.jobs = {"cmd": _summary("cmd", "srv", entries)}
    result = build_profile(report)
    assert isinstance(result, ProfileReport)
    assert len(result.profiles) == 1


def test_build_profile_slowest_is_highest_mean():
    e1 = [_entry("fast", "started", 0.0), _entry("fast", "succeeded", 2.0)]
    e2 = [_entry("slow", "started", 0.0), _entry("slow", "succeeded", 30.0)]
    report = MagicMock(spec=AggregatedReport)
    report.jobs = {
        "fast": _summary("fast", "srv", e1),
        "slow": _summary("slow", "srv", e2),
    }
    result = build_profile(report)
    assert result.slowest is not None
    assert result.slowest.command == "slow"
