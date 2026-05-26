"""Tests for cronsight.eventer."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.eventer import EventStream, JobEvent, build_event_stream, _entry_status
from cronsight.parser import CronEntry


def _entry(cmd: str, server: str, ts: str, rc: int = 0) -> CronEntry:
    return CronEntry(
        command=cmd,
        server=server,
        timestamp=ts,
        return_code=rc,
        raw_line=f"{ts} {server} {cmd}",
    )


def _summary(cmd: str, entries: list) -> JobSummary:
    return JobSummary(command=cmd, entries=entries)


def _report(*summaries: JobSummary) -> AggregatedReport:
    return AggregatedReport(jobs={s.command: s for s in summaries})


# --- JobEvent ---

def test_job_event_str_success():
    e = JobEvent(command="backup", server="s1", timestamp="2024-01-01T00:00:00", status="success", raw_line="")
    assert "✓" in str(e)
    assert "backup" in str(e)


def test_job_event_str_failure():
    e = JobEvent(command="backup", server="s1", timestamp="2024-01-01T00:00:00", status="failure", raw_line="")
    assert "✗" in str(e)


# --- _entry_status ---

def test_entry_status_zero_rc_is_success():
    e = _entry("cmd", "s", "2024-01-01T00:00:00", rc=0)
    assert _entry_status(e) == "success"


def test_entry_status_nonzero_rc_is_failure():
    e = _entry("cmd", "s", "2024-01-01T00:00:00", rc=1)
    assert _entry_status(e) == "failure"


def test_entry_status_none_rc_is_success():
    e = _entry("cmd", "s", "2024-01-01T00:00:00", rc=0)
    e = CronEntry(command="cmd", server="s", timestamp="t", return_code=None, raw_line="")
    assert _entry_status(e) == "success"


# --- build_event_stream ---

def test_build_event_stream_returns_all_events():
    r = _report(
        _summary("cmd1", [_entry("cmd1", "s1", "2024-01-01T01:00:00")]),
        _summary("cmd2", [_entry("cmd2", "s2", "2024-01-01T02:00:00")]),
    )
    stream = build_event_stream(r)
    assert stream.count == 2


def test_build_event_stream_sorted_by_timestamp():
    r = _report(
        _summary("cmd", [
            _entry("cmd", "s", "2024-01-01T03:00:00"),
            _entry("cmd", "s", "2024-01-01T01:00:00"),
        ])
    )
    stream = build_event_stream(r)
    assert stream.events[0].timestamp < stream.events[1].timestamp


def test_build_event_stream_server_filter():
    r = _report(
        _summary("cmd", [
            _entry("cmd", "s1", "2024-01-01T01:00:00"),
            _entry("cmd", "s2", "2024-01-01T02:00:00"),
        ])
    )
    stream = build_event_stream(r, server="s1")
    assert stream.count == 1
    assert stream.events[0].server == "s1"


def test_build_event_stream_since_filter():
    r = _report(
        _summary("cmd", [
            _entry("cmd", "s", "2024-01-01T00:00:00"),
            _entry("cmd", "s", "2024-01-02T00:00:00"),
        ])
    )
    stream = build_event_stream(r, since="2024-01-02T00:00:00")
    assert stream.count == 1


def test_build_event_stream_until_filter():
    r = _report(
        _summary("cmd", [
            _entry("cmd", "s", "2024-01-01T00:00:00"),
            _entry("cmd", "s", "2024-01-03T00:00:00"),
        ])
    )
    stream = build_event_stream(r, until="2024-01-02T00:00:00")
    assert stream.count == 1


def test_event_stream_failure_count():
    r = _report(
        _summary("cmd", [
            _entry("cmd", "s", "2024-01-01T01:00:00", rc=0),
            _entry("cmd", "s", "2024-01-01T02:00:00", rc=1),
            _entry("cmd", "s", "2024-01-01T03:00:00", rc=2),
        ])
    )
    stream = build_event_stream(r)
    assert stream.failure_count == 2
    assert stream.success_count == 1
