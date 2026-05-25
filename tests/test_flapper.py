"""Tests for cronsight.flapper."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.flapper import (
    FlapJob,
    FlapReport,
    FlapperError,
    _count_transitions,
    _last_status,
    detect_flapping,
)
from cronsight.parser import CronEntry


def _entry(exit_code: int, ts: str) -> CronEntry:
    e = MagicMock(spec=CronEntry)
    e.exit_code = exit_code
    e.timestamp = ts
    return e


def _summary(entries, servers=("host1",)) -> JobSummary:
    s = MagicMock(spec=JobSummary)
    s.entries = entries
    s.servers = set(servers)
    return s


def _report(jobs: dict) -> AggregatedReport:
    r = MagicMock(spec=AggregatedReport)
    r.jobs = jobs
    return r


# --- _count_transitions ---

def test_count_transitions_all_passing():
    entries = [_entry(0, "2024-01-01T10:00:00"), _entry(0, "2024-01-01T11:00:00")]
    assert _count_transitions(entries) == 0


def test_count_transitions_alternating():
    entries = [
        _entry(0, "2024-01-01T10:00:00"),
        _entry(1, "2024-01-01T11:00:00"),
        _entry(0, "2024-01-01T12:00:00"),
        _entry(1, "2024-01-01T13:00:00"),
    ]
    assert _count_transitions(entries) == 3


def test_count_transitions_single_entry():
    assert _count_transitions([_entry(0, "2024-01-01T10:00:00")]) == 0


def test_count_transitions_empty():
    assert _count_transitions([]) == 0


# --- _last_status ---

def test_last_status_success():
    entries = [_entry(1, "2024-01-01T10:00:00"), _entry(0, "2024-01-01T11:00:00")]
    assert _last_status(entries) == "success"


def test_last_status_failure():
    entries = [_entry(0, "2024-01-01T10:00:00"), _entry(1, "2024-01-01T11:00:00")]
    assert _last_status(entries) == "failure"


def test_last_status_empty():
    assert _last_status([]) == "unknown"


# --- detect_flapping ---

def test_detect_flapping_returns_flap_report():
    r = _report({})
    result = detect_flapping(r)
    assert isinstance(result, FlapReport)
    assert result.count == 0


def test_detect_flapping_detects_flapping_job():
    entries = [
        _entry(0, "2024-01-01T10:00:00"),
        _entry(1, "2024-01-01T11:00:00"),
        _entry(0, "2024-01-01T12:00:00"),
    ]
    r = _report({"backup.sh": _summary(entries)})
    result = detect_flapping(r, min_transitions=2)
    assert result.count == 1
    assert result.flapping[0].command == "backup.sh"
    assert result.flapping[0].transitions == 2


def test_detect_flapping_excludes_stable_job():
    entries = [_entry(0, "2024-01-01T10:00:00"), _entry(0, "2024-01-01T11:00:00")]
    r = _report({"stable.sh": _summary(entries)})
    result = detect_flapping(r, min_transitions=2)
    assert result.count == 0


def test_detect_flapping_sorted_by_transitions_descending():
    e1 = [_entry(0, f"2024-01-01T{h:02d}:00:00") if h % 2 == 0 else _entry(1, f"2024-01-01T{h:02d}:00:00") for h in range(6)]
    e2 = [_entry(0, "2024-01-01T10:00:00"), _entry(1, "2024-01-01T11:00:00"), _entry(0, "2024-01-01T12:00:00")]
    r = _report({"low.sh": _summary(e2), "high.sh": _summary(e1)})
    result = detect_flapping(r, min_transitions=2)
    assert result.flapping[0].transitions >= result.flapping[-1].transitions


def test_detect_flapping_invalid_min_transitions_raises():
    r = _report({})
    with pytest.raises(FlapperError):
        detect_flapping(r, min_transitions=0)


def test_flap_job_str_contains_command():
    job = FlapJob(command="sync.sh", servers=["h1"], transitions=3, last_status="failure")
    assert "sync.sh" in str(job)
    assert "transitions=3" in str(job)
