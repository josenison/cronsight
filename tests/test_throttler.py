"""Tests for cronsight.throttler."""
from datetime import datetime, timedelta

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.throttler import (
    ThrottlerError,
    ThrottleViolation,
    ThrottleReport,
    _runs_in_window,
    detect_throttle_violations,
)

_NOW = datetime(2024, 6, 1, 12, 0, 0)


def _entry(minutes_ago: int, success: bool = True) -> CronEntry:
    return CronEntry(
        timestamp=_NOW - timedelta(minutes=minutes_ago),
        command="/usr/bin/backup.sh",
        success=success,
    )


def _summary(entries) -> JobSummary:
    return JobSummary(
        command="/usr/bin/backup.sh",
        server="host1",
        entries=entries,
    )


def _report(summary: JobSummary) -> AggregatedReport:
    key = (summary.server, summary.command)
    return AggregatedReport(jobs={key: summary})


# --- _runs_in_window ---

def test_runs_in_window_counts_recent():
    entries = [_entry(5), _entry(10), _entry(70)]
    s = _summary(entries)
    assert _runs_in_window(s, window_minutes=60, reference=_NOW) == 2


def test_runs_in_window_all_outside_returns_zero():
    entries = [_entry(120), _entry(200)]
    s = _summary(entries)
    assert _runs_in_window(s, window_minutes=60, reference=_NOW) == 0


def test_runs_in_window_all_inside():
    entries = [_entry(1), _entry(2), _entry(3)]
    s = _summary(entries)
    assert _runs_in_window(s, window_minutes=60, reference=_NOW) == 3


def test_runs_in_window_no_entries_returns_zero():
    s = _summary([])
    assert _runs_in_window(s, window_minutes=60, reference=_NOW) == 0


# --- detect_throttle_violations ---

def test_no_violation_when_under_threshold():
    entries = [_entry(5), _entry(10)]
    r = _report(_summary(entries))
    result = detect_throttle_violations(r, threshold=5, window_minutes=60, reference=_NOW)
    assert not result.has_violations
    assert result.violation_count == 0


def test_violation_detected_when_over_threshold():
    entries = [_entry(i) for i in range(1, 8)]  # 7 runs in last 60 min
    r = _report(_summary(entries))
    result = detect_throttle_violations(r, threshold=5, window_minutes=60, reference=_NOW)
    assert result.has_violations
    assert result.violation_count == 1


def test_violation_fields_are_correct():
    entries = [_entry(i) for i in range(1, 8)]
    r = _report(_summary(entries))
    result = detect_throttle_violations(r, threshold=5, window_minutes=60, reference=_NOW)
    v = result.violations[0]
    assert v.command == "/usr/bin/backup.sh"
    assert v.server == "host1"
    assert v.run_count == 7
    assert v.threshold == 5
    assert v.window_minutes == 60


def test_violation_str_contains_key_info():
    v = ThrottleViolation(
        command="/bin/job", server="srv", run_count=10, window_minutes=30, threshold=5
    )
    text = str(v)
    assert "/bin/job" in text
    assert "srv" in text
    assert "10" in text


def test_raises_on_invalid_threshold():
    r = AggregatedReport(jobs={})
    with pytest.raises(ThrottlerError, match="threshold"):
        detect_throttle_violations(r, threshold=0, window_minutes=60)


def test_raises_on_invalid_window():
    r = AggregatedReport(jobs={})
    with pytest.raises(ThrottlerError, match="window_minutes"):
        detect_throttle_violations(r, threshold=3, window_minutes=0)


def test_empty_report_returns_no_violations():
    r = AggregatedReport(jobs={})
    result = detect_throttle_violations(r, threshold=3, window_minutes=60, reference=_NOW)
    assert not result.has_violations
