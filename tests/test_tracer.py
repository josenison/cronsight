"""Tests for cronsight.tracer."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.tracer import (
    TraceEvent,
    JobTrace,
    TraceReport,
    build_trace,
    TracerError,
)


def _entry(ts: str, failed: bool = False) -> CronEntry:
    e = MagicMock(spec=CronEntry)
    e.timestamp = ts
    e.failed = failed
    e.command = "/usr/bin/backup"
    return e


def _make_summary(command: str, entries_by_server: dict) -> JobSummary:
    s = MagicMock(spec=JobSummary)
    s.command = command
    s.entries_by_server = entries_by_server
    return s


def _make_report(summaries: list) -> AggregatedReport:
    r = MagicMock(spec=AggregatedReport)
    r.jobs = {s.command: s for s in summaries}
    return r


# --- TraceEvent ---

def test_trace_event_str_success():
    e = TraceEvent(server="host1", command="/bin/job", timestamp="2024-01-01 00:00", status="success")
    assert "✓" in str(e)
    assert "host1" in str(e)


def test_trace_event_str_failure():
    e = TraceEvent(server="host1", command="/bin/job", timestamp="2024-01-01 00:00", status="failure")
    assert "✗" in str(e)


# --- JobTrace ---

def test_job_trace_event_count():
    t = JobTrace(command="/bin/job", events=[
        TraceEvent("s1", "/bin/job", "2024-01-01", "success"),
        TraceEvent("s2", "/bin/job", "2024-01-02", "failure"),
    ])
    assert t.event_count == 2


def test_job_trace_failure_count():
    t = JobTrace(command="/bin/job", events=[
        TraceEvent("s1", "/bin/job", "2024-01-01", "success"),
        TraceEvent("s2", "/bin/job", "2024-01-02", "failure"),
    ])
    assert t.failure_count == 1


def test_job_trace_servers_unique():
    t = JobTrace(command="/bin/job", events=[
        TraceEvent("s1", "/bin/job", "2024-01-01", "success"),
        TraceEvent("s1", "/bin/job", "2024-01-02", "failure"),
        TraceEvent("s2", "/bin/job", "2024-01-03", "success"),
    ])
    assert t.servers == ["s1", "s2"]


# --- build_trace ---

def test_build_trace_raises_on_empty_report():
    r = MagicMock(spec=AggregatedReport)
    r.jobs = {}
    with pytest.raises(TracerError):
        build_trace(r)


def test_build_trace_returns_trace_report():
    summary = _make_summary("/usr/bin/backup", {
        "server1": [_entry("2024-01-01 01:00"), _entry("2024-01-01 02:00", failed=True)]
    })
    report = _make_report([summary])
    result = build_trace(report)
    assert isinstance(result, TraceReport)
    assert result.job_count == 1


def test_build_trace_counts_events():
    summary = _make_summary("/usr/bin/backup", {
        "server1": [_entry("2024-01-01 01:00"), _entry("2024-01-01 02:00")]
    })
    report = _make_report([summary])
    result = build_trace(report)
    assert result.traces["/usr/bin/backup"].event_count == 2


def test_build_trace_failure_status():
    summary = _make_summary("/usr/bin/backup", {
        "server1": [_entry("2024-01-01 01:00", failed=True)]
    })
    report = _make_report([summary])
    result = build_trace(report)
    assert result.traces["/usr/bin/backup"].events[0].status == "failure"


def test_build_trace_command_filter_excludes():
    s1 = _make_summary("/usr/bin/backup", {"s1": [_entry("2024-01-01")]})
    s2 = _make_summary("/usr/bin/cleanup", {"s1": [_entry("2024-01-01")]})
    report = _make_report([s1, s2])
    result = build_trace(report, command_filter="backup")
    assert "/usr/bin/backup" in result.traces
    assert "/usr/bin/cleanup" not in result.traces


def test_build_trace_events_sorted_by_timestamp():
    summary = _make_summary("/bin/job", {
        "s1": [_entry("2024-01-03"), _entry("2024-01-01"), _entry("2024-01-02")]
    })
    report = _make_report([summary])
    result = build_trace(report)
    timestamps = [e.timestamp for e in result.traces["/bin/job"].events]
    assert timestamps == sorted(timestamps)


def test_trace_report_total_events():
    s1 = _make_summary("/bin/a", {"s1": [_entry("2024-01-01"), _entry("2024-01-02")]})
    s2 = _make_summary("/bin/b", {"s1": [_entry("2024-01-01")]})
    report = _make_report([s1, s2])
    result = build_trace(report)
    assert result.total_events == 3
