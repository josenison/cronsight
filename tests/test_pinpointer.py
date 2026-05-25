"""Tests for cronsight.pinpointer."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.pinpointer import FailureCluster, PinpointReport, PinpointerError, pinpoint


def _entry(success: bool, hour: int = 10) -> CronEntry:
    return CronEntry(
        timestamp=datetime(2024, 6, 1, hour, 0, 0, tzinfo=timezone.utc),
        server="srv1",
        command="/usr/bin/job.sh",
        success=success,
    )


def _summary(entries):
    s = JobSummary(command="/usr/bin/job.sh")
    s.entries = entries
    s.servers = ["srv1"]
    return s


def _report(summary):
    r = AggregatedReport()
    r.jobs["/usr/bin/job.sh"] = summary
    return r


# --- FailureCluster ---

def test_failure_cluster_rate_all_fail():
    c = FailureCluster(
        command="job", server="s", failures_in_window=3, total_in_window=3,
        first_failure=None, last_failure=None,
    )
    assert c.failure_rate == 1.0


def test_failure_cluster_rate_half():
    c = FailureCluster(
        command="job", server="s", failures_in_window=2, total_in_window=4,
        first_failure=None, last_failure=None,
    )
    assert c.failure_rate == 0.5


def test_failure_cluster_rate_zero_total():
    c = FailureCluster(
        command="job", server="s", failures_in_window=0, total_in_window=0,
        first_failure=None, last_failure=None,
    )
    assert c.failure_rate == 0.0


def test_failure_cluster_str_contains_command():
    c = FailureCluster(
        command="/usr/bin/job.sh", server="srv1",
        failures_in_window=2, total_in_window=5,
        first_failure=None, last_failure=None,
    )
    assert "/usr/bin/job.sh" in str(c)
    assert "srv1" in str(c)


# --- pinpoint ---

def test_pinpoint_returns_empty_when_no_failures():
    entries = [_entry(True), _entry(True)]
    r = _report(_summary(entries))
    result = pinpoint(r)
    assert result.count == 0
    assert result.top is None


def test_pinpoint_detects_failures():
    entries = [_entry(False), _entry(False), _entry(True)]
    r = _report(_summary(entries))
    result = pinpoint(r, min_failures=1)
    assert result.count == 1
    assert result.top is not None
    assert result.top.failures_in_window == 2


def test_pinpoint_respects_min_failures():
    entries = [_entry(False), _entry(True)]
    r = _report(_summary(entries))
    result = pinpoint(r, min_failures=2)
    assert result.count == 0


def test_pinpoint_raises_on_invalid_min_failures():
    r = AggregatedReport()
    with pytest.raises(PinpointerError):
        pinpoint(r, min_failures=0)


def test_pinpoint_since_filters_old_entries():
    old = CronEntry(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        server="srv1", command="/usr/bin/job.sh", success=False,
    )
    recent = CronEntry(
        timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc),
        server="srv1", command="/usr/bin/job.sh", success=False,
    )
    r = _report(_summary([old, recent]))
    cutoff = datetime(2024, 3, 1, tzinfo=timezone.utc)
    result = pinpoint(r, since=cutoff, min_failures=1)
    assert result.count == 1
    assert result.top.failures_in_window == 1


def test_pinpoint_until_filters_future_entries():
    early = CronEntry(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        server="srv1", command="/usr/bin/job.sh", success=False,
    )
    late = CronEntry(
        timestamp=datetime(2024, 12, 1, tzinfo=timezone.utc),
        server="srv1", command="/usr/bin/job.sh", success=False,
    )
    r = _report(_summary([early, late]))
    cutoff = datetime(2024, 6, 1, tzinfo=timezone.utc)
    result = pinpoint(r, until=cutoff, min_failures=1)
    assert result.top.failures_in_window == 1


def test_pinpoint_report_top_is_highest_failure_count():
    s1 = JobSummary(command="/usr/bin/a.sh")
    s1.entries = [_entry(False), _entry(False), _entry(False)]
    s1.servers = ["srv1"]
    s2 = JobSummary(command="/usr/bin/b.sh")
    s2.entries = [_entry(False)]
    s2.servers = ["srv1"]
    r = AggregatedReport()
    r.jobs["/usr/bin/a.sh"] = s1
    r.jobs["/usr/bin/b.sh"] = s2
    result = pinpoint(r, min_failures=1)
    assert result.top.command == "/usr/bin/a.sh"
