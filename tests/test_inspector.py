"""Tests for cronsight.inspector."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.inspector import (
    ExecutionGap,
    InspectorError,
    JobInspection,
    _detect_gaps,
    inspect_report,
)
from cronsight.parser import CronEntry


def _ts(hour: int, minute: int = 0) -> datetime:
    return datetime(2024, 1, 15, hour, minute, tzinfo=timezone.utc)


def _entry(exit_code: int = 0, hour: int = 1) -> CronEntry:
    e = MagicMock(spec=CronEntry)
    e.exit_code = exit_code
    e.timestamp = _ts(hour)
    return e


def _summary(command: str, entries) -> JobSummary:
    s = MagicMock(spec=JobSummary)
    s.command = command
    s.entries = entries
    s.servers = {"host1"}
    return s


def _report(*summaries) -> AggregatedReport:
    r = MagicMock(spec=AggregatedReport)
    r.jobs = {s.command: s for s in summaries}
    return r


# --- ExecutionGap ---

def test_execution_gap_duration():
    gap = ExecutionGap(start=_ts(1), end=_ts(3))
    assert gap.duration_seconds == 7200.0


def test_execution_gap_str_contains_times():
    gap = ExecutionGap(start=_ts(1), end=_ts(2))
    text = str(gap)
    assert "2024-01-15 01:00:00" in text
    assert "2024-01-15 02:00:00" in text


# --- _detect_gaps ---

def test_detect_gaps_returns_empty_when_below_threshold():
    timestamps = [_ts(1), _ts(2)]
    gaps = _detect_gaps(timestamps, threshold_seconds=7200.0)
    assert gaps == []


def test_detect_gaps_detects_large_gap():
    timestamps = [_ts(1), _ts(5)]
    gaps = _detect_gaps(timestamps, threshold_seconds=3600.0)
    assert len(gaps) == 1
    assert gaps[0].duration_seconds == 4 * 3600


def test_detect_gaps_single_timestamp_returns_empty():
    assert _detect_gaps([_ts(1)], threshold_seconds=60.0) == []


# --- inspect_report ---

def test_inspect_report_raises_on_empty_report():
    r = MagicMock(spec=AggregatedReport)
    r.jobs = {}
    with pytest.raises(InspectorError):
        inspect_report(r)


def test_inspect_report_returns_one_inspection_per_job():
    r = _report(_summary("backup.sh", [_entry(0, 1), _entry(0, 2)]))
    result = inspect_report(r)
    assert len(result.inspections) == 1


def test_inspect_report_counts_success_and_failures():
    entries = [_entry(0, 1), _entry(1, 2), _entry(0, 3)]
    r = _report(_summary("job.sh", entries))
    result = inspect_report(r)
    insp = result.inspections[0]
    assert insp.success_runs == 2
    assert insp.failure_runs == 1


def test_inspect_report_success_rate():
    entries = [_entry(0, 1), _entry(0, 2), _entry(1, 3), _entry(1, 4)]
    r = _report(_summary("job.sh", entries))
    insp = inspect_report(r).inspections[0]
    assert insp.success_rate == pytest.approx(0.5)


def test_inspect_report_first_and_last_run():
    entries = [_entry(0, 3), _entry(0, 1), _entry(0, 5)]
    r = _report(_summary("job.sh", entries))
    insp = inspect_report(r).inspections[0]
    assert insp.first_run == _ts(1)
    assert insp.last_run == _ts(5)


def test_inspect_report_detects_gaps():
    entries = [_entry(0, 1), _entry(0, 6)]
    r = _report(_summary("job.sh", entries))
    insp = inspect_report(r, gap_threshold_seconds=3600.0).inspections[0]
    assert len(insp.gaps) == 1


def test_inspection_report_get_by_command():
    r = _report(_summary("cleanup.sh", [_entry(0, 1)]))
    report = inspect_report(r)
    assert report.get("cleanup.sh") is not None
    assert report.get("missing.sh") is None
