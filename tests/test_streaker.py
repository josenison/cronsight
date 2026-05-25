"""Tests for cronsight.streaker."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.streaker import (
    JobStreak,
    StreakerError,
    StreakerReport,
    detect_streaks,
    _current_streak,
)


def _entry(success: bool, ts: str = "2024-01-15T10:00:00") -> CronEntry:
    return CronEntry(timestamp=ts, command="backup.sh", success=success)


def _summary(
    command: str,
    server: str,
    entries: List[CronEntry],
) -> JobSummary:
    s = JobSummary(command=command, server=server)
    s.entries.extend(entries)
    return s


def _report(summaries: List[JobSummary]) -> AggregatedReport:
    r = AggregatedReport()
    for s in summaries:
        r.jobs[f"{s.server}:{s.command}"] = s
    return r


# ---------------------------------------------------------------------------
# _current_streak
# ---------------------------------------------------------------------------

def test_current_streak_all_passing():
    entries = [_entry(True, f"2024-01-15T1{i}:00:00") for i in range(3)]
    streak_type, length = _current_streak(entries)
    assert streak_type == "passing"
    assert length == 3


def test_current_streak_all_failing():
    entries = [_entry(False, f"2024-01-15T1{i}:00:00") for i in range(4)]
    streak_type, length = _current_streak(entries)
    assert streak_type == "failing"
    assert length == 4


def test_current_streak_mixed_counts_tail():
    entries = [
        _entry(True, "2024-01-15T10:00:00"),
        _entry(False, "2024-01-15T11:00:00"),
        _entry(False, "2024-01-15T12:00:00"),
    ]
    streak_type, length = _current_streak(entries)
    assert streak_type == "failing"
    assert length == 2


def test_current_streak_empty_returns_passing_zero():
    streak_type, length = _current_streak([])
    assert streak_type == "passing"
    assert length == 0


# ---------------------------------------------------------------------------
# detect_streaks
# ---------------------------------------------------------------------------

def test_detect_streaks_returns_streaker_report():
    entries = [_entry(True, f"2024-01-15T1{i}:00:00") for i in range(3)]
    s = _summary("backup.sh", "srv1", entries)
    r = _report([s])
    result = detect_streaks(r, min_length=2)
    assert isinstance(result, StreakerReport)


def test_detect_streaks_includes_qualifying_streak():
    entries = [_entry(False, f"2024-01-15T1{i}:00:00") for i in range(3)]
    s = _summary("cleanup.sh", "srv1", entries)
    r = _report([s])
    result = detect_streaks(r, min_length=2)
    assert result.count == 1
    assert result.streaks[0].streak_type == "failing"
    assert result.streaks[0].length == 3


def test_detect_streaks_excludes_short_streaks():
    entries = [_entry(True, "2024-01-15T10:00:00")]
    s = _summary("short.sh", "srv1", entries)
    r = _report([s])
    result = detect_streaks(r, min_length=2)
    assert result.count == 0


def test_detect_streaks_sorted_by_length_descending():
    e3 = [_entry(True, f"2024-01-15T1{i}:00:00") for i in range(3)]
    e5 = [_entry(True, f"2024-01-15T1{i}:00:00") for i in range(5)]
    s1 = _summary("a.sh", "srv1", e3)
    s2 = _summary("b.sh", "srv1", e5)
    r = _report([s1, s2])
    result = detect_streaks(r, min_length=2)
    assert result.streaks[0].length >= result.streaks[1].length


def test_detect_streaks_raises_on_invalid_min_length():
    r = _report([])
    with pytest.raises(StreakerError):
        detect_streaks(r, min_length=0)


def test_streaker_report_passing_failing_partition():
    ep = [_entry(True, f"2024-01-15T1{i}:00:00") for i in range(2)]
    ef = [_entry(False, f"2024-01-15T1{i}:00:00") for i in range(2)]
    sp = _summary("pass.sh", "srv1", ep)
    sf = _summary("fail.sh", "srv2", ef)
    r = _report([sp, sf])
    result = detect_streaks(r, min_length=2)
    assert len(result.passing_streaks()) == 1
    assert len(result.failing_streaks()) == 1


def test_job_streak_str_contains_command_and_type():
    streak = JobStreak(
        command="nightly.sh",
        server="srv1",
        streak_type="failing",
        length=4,
        last_run="2024-01-15T10:00:00",
    )
    s = str(streak)
    assert "nightly.sh" in s
    assert "failing" in s
    assert "4" in s
