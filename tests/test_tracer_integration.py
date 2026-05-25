"""Integration tests for tracer: build_trace with real-ish data."""
from __future__ import annotations

from unittest.mock import MagicMock

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.tracer import build_trace, TraceReport


def _e(ts: str, failed: bool = False) -> CronEntry:
    e = MagicMock(spec=CronEntry)
    e.timestamp = ts
    e.failed = failed
    e.command = "/bin/job"
    return e


def _report(summaries):
    r = MagicMock(spec=AggregatedReport)
    r.jobs = {s.command: s for s in summaries}
    return r


def _summary(cmd, entries_by_server):
    s = MagicMock(spec=JobSummary)
    s.command = cmd
    s.entries_by_server = entries_by_server
    return s


def test_multiple_servers_merged_into_single_trace():
    s = _summary("/bin/backup", {
        "host-a": [_e("2024-03-01 01:00"), _e("2024-03-01 02:00")],
        "host-b": [_e("2024-03-01 01:30")],
    })
    result = build_trace(_report([s]))
    trace = result.traces["/bin/backup"]
    assert trace.event_count == 3
    assert set(trace.servers) == {"host-a", "host-b"}


def test_all_failures_reflected_in_failure_count():
    s = _summary("/bin/nightly", {
        "host-a": [_e("2024-03-01", failed=True), _e("2024-03-02", failed=True)],
    })
    result = build_trace(_report([s]))
    assert result.traces["/bin/nightly"].failure_count == 2


def test_no_filter_returns_all_jobs():
    jobs = [
        _summary("/bin/alpha", {"s1": [_e("2024-01-01")]}),
        _summary("/bin/beta", {"s1": [_e("2024-01-01")]}),
        _summary("/bin/gamma", {"s1": [_e("2024-01-01")]}),
    ]
    result = build_trace(_report(jobs))
    assert result.job_count == 3


def test_filter_returns_only_matching_job():
    jobs = [
        _summary("/bin/alpha", {"s1": [_e("2024-01-01")]}),
        _summary("/bin/beta", {"s1": [_e("2024-01-01")]}),
    ]
    result = build_trace(_report(jobs), command_filter="alpha")
    assert result.job_count == 1
    assert "/bin/alpha" in result.traces


def test_events_across_servers_sorted_globally():
    s = _summary("/bin/sync", {
        "s1": [_e("2024-01-03"), _e("2024-01-01")],
        "s2": [_e("2024-01-02")],
    })
    result = build_trace(_report([s]))
    timestamps = [ev.timestamp for ev in result.traces["/bin/sync"].events]
    assert timestamps == sorted(timestamps)
