"""Tests for cronsight.capper."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.capper import CapperError, CappedReport, cap_report


def _entry(cmd: str, success: bool, ts: str) -> CronEntry:
    return CronEntry(command=cmd, success=success, timestamp=ts, server="srv1")


def _summary(cmd: str, entries) -> JobSummary:
    return JobSummary(command=cmd, server="srv1", entries=entries)


def _report(*summaries: JobSummary) -> AggregatedReport:
    report = AggregatedReport()
    for s in summaries:
        report.jobs[(s.command, s.server)] = s
    return report


# ---------------------------------------------------------------------------
# CapperError
# ---------------------------------------------------------------------------

def test_cap_raises_on_zero_max_entries():
    r = _report(_summary("job.sh", []))
    with pytest.raises(CapperError):
        cap_report(r, 0)


def test_cap_raises_on_negative_max_entries():
    r = _report(_summary("job.sh", []))
    with pytest.raises(CapperError):
        cap_report(r, -5)


# ---------------------------------------------------------------------------
# Basic behaviour
# ---------------------------------------------------------------------------

def test_cap_report_returns_capped_report():
    entries = [_entry("job.sh", True, "2024-01-01T10:00:00") for _ in range(5)]
    r = _report(_summary("job.sh", entries))
    result = cap_report(r, 3)
    assert isinstance(result, CappedReport)


def test_cap_report_count_matches_jobs():
    r = _report(
        _summary("a.sh", [_entry("a.sh", True, "2024-01-01T10:00:00")]),
        _summary("b.sh", [_entry("b.sh", False, "2024-01-02T10:00:00")]),
    )
    result = cap_report(r, 10)
    assert result.count == 2


def test_cap_keeps_most_recent_entries():
    entries = [
        _entry("job.sh", True, f"2024-01-0{i}T10:00:00") for i in range(1, 6)
    ]
    r = _report(_summary("job.sh", entries))
    result = cap_report(r, 2)
    capped = result.jobs[0]
    timestamps = [e.timestamp for e in capped.summary.entries]
    assert "2024-01-05T10:00:00" in timestamps
    assert "2024-01-04T10:00:00" in timestamps
    assert len(timestamps) == 2


def test_cap_original_count_recorded():
    entries = [_entry("job.sh", True, f"2024-01-0{i}T10:00:00") for i in range(1, 6)]
    r = _report(_summary("job.sh", entries))
    result = cap_report(r, 3)
    assert result.jobs[0].original_count == 5
    assert result.jobs[0].capped_count == 3


def test_total_dropped_reflects_difference():
    entries = [_entry("job.sh", True, f"2024-01-0{i}T10:00:00") for i in range(1, 6)]
    r = _report(_summary("job.sh", entries))
    result = cap_report(r, 2)
    assert result.total_dropped == 3


def test_cap_does_not_drop_when_under_limit():
    entries = [_entry("job.sh", True, "2024-01-01T10:00:00")]
    r = _report(_summary("job.sh", entries))
    result = cap_report(r, 10)
    assert result.jobs[0].capped_count == 1
    assert result.total_dropped == 0


def test_capped_job_str_contains_command():
    entries = [_entry("job.sh", True, f"2024-01-0{i}T10:00:00") for i in range(1, 4)]
    r = _report(_summary("job.sh", entries))
    result = cap_report(r, 1)
    assert "job.sh" in str(result.jobs[0])
