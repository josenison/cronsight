"""Unit tests for cronsight.recurrence."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.recurrence import (
    RecurrenceError,
    RecurrenceProfile,
    build_recurrence_report,
)


def _entry(cmd: str, ts: datetime, success: bool = True) -> CronEntry:
    return CronEntry(command=cmd, timestamp=ts, success=success, server="host1")


def _summary(cmd: str, entries: List[CronEntry]) -> JobSummary:
    s = JobSummary(command=cmd)
    for e in entries:
        s.entries.append(e)
        s.servers.add(e.server)
    return s


def _report(*summaries: JobSummary) -> AggregatedReport:
    r = AggregatedReport()
    for s in summaries:
        r.jobs[s.command] = s
    return r


BASE = datetime(2024, 1, 1, 6, 0, 0)


def test_build_recurrence_report_returns_report():
    entries = [_entry("backup.sh", BASE + timedelta(hours=i)) for i in range(5)]
    rep = _report(_summary("backup.sh", entries))
    result = build_recurrence_report(rep)
    assert result.count == 1


def test_regular_job_not_flagged():
    entries = [_entry("backup.sh", BASE + timedelta(hours=i)) for i in range(6)]
    rep = _report(_summary("backup.sh", entries))
    result = build_recurrence_report(rep, irregularity_threshold=0.5)
    assert result.profiles[0].irregular is False


def test_irregular_job_flagged():
    # Highly variable intervals
    offsets = [0, 1, 60, 61, 3600]
    entries = [_entry("noisy.sh", BASE + timedelta(minutes=o)) for o in offsets]
    rep = _report(_summary("noisy.sh", entries))
    result = build_recurrence_report(rep, irregularity_threshold=0.1)
    assert result.profiles[0].irregular is True


def test_single_entry_no_intervals():
    entries = [_entry("solo.sh", BASE)]
    rep = _report(_summary("solo.sh", entries))
    result = build_recurrence_report(rep)
    p = result.profiles[0]
    assert p.median_interval_seconds is None
    assert p.stdev_interval_seconds is None
    assert p.irregular is False


def test_two_entries_no_stdev():
    entries = [_entry("pair.sh", BASE), _entry("pair.sh", BASE + timedelta(hours=1))]
    rep = _report(_summary("pair.sh", entries))
    result = build_recurrence_report(rep)
    p = result.profiles[0]
    assert p.median_interval_seconds == pytest.approx(3600.0)
    assert p.stdev_interval_seconds is None


def test_irregular_count():
    offsets_regular = [0, 60, 120, 180, 240]
    offsets_noisy = [0, 1, 600, 601, 36000]
    s1 = _summary("regular.sh", [_entry("regular.sh", BASE + timedelta(minutes=o)) for o in offsets_regular])
    s2 = _summary("noisy.sh", [_entry("noisy.sh", BASE + timedelta(minutes=o)) for o in offsets_noisy])
    rep = _report(s1, s2)
    result = build_recurrence_report(rep, irregularity_threshold=0.1)
    assert result.irregular_count >= 1


def test_negative_threshold_raises():
    rep = _report()
    with pytest.raises(RecurrenceError):
        build_recurrence_report(rep, irregularity_threshold=-0.1)


def test_profile_str_contains_command():
    entries = [_entry("myjob.sh", BASE + timedelta(hours=i)) for i in range(4)]
    rep = _report(_summary("myjob.sh", entries))
    result = build_recurrence_report(rep)
    assert "myjob.sh" in str(result.profiles[0])


def test_servers_populated():
    e1 = CronEntry(command="job.sh", timestamp=BASE, success=True, server="alpha")
    e2 = CronEntry(command="job.sh", timestamp=BASE + timedelta(hours=1), success=True, server="beta")
    s = JobSummary(command="job.sh")
    for e in [e1, e2]:
        s.entries.append(e)
        s.servers.add(e.server)
    rep = _report(s)
    result = build_recurrence_report(rep)
    assert set(result.profiles[0].servers) == {"alpha", "beta"}
