"""Integration tests for recurrence analysis end-to-end."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.recurrence import build_recurrence_report

BASE = datetime(2024, 6, 1, 0, 0, 0)


def _e(cmd: str, ts: datetime, server: str = "srv", success: bool = True) -> CronEntry:
    return CronEntry(command=cmd, timestamp=ts, success=success, server=server)


def _report(*pairs) -> AggregatedReport:
    r = AggregatedReport()
    for cmd, entries in pairs:
        s = JobSummary(command=cmd)
        for e in entries:
            s.entries.append(e)
            s.servers.add(e.server)
        r.jobs[cmd] = s
    return r


def test_multiple_jobs_each_get_own_profile():
    r = _report(
        ("alpha.sh", [_e("alpha.sh", BASE + timedelta(hours=i)) for i in range(5)]),
        ("beta.sh", [_e("beta.sh", BASE + timedelta(hours=i * 2)) for i in range(5)]),
    )
    result = build_recurrence_report(r)
    commands = {p.command for p in result.profiles}
    assert "alpha.sh" in commands
    assert "beta.sh" in commands


def test_perfectly_regular_job_not_irregular():
    entries = [_e("tick.sh", BASE + timedelta(minutes=i * 60)) for i in range(10)]
    r = _report(("tick.sh", entries))
    result = build_recurrence_report(r, irregularity_threshold=0.05)
    profile = result.profiles[0]
    assert profile.irregular is False


def test_all_irregular_jobs_counted():
    def noisy(cmd):
        offsets = [0, 1, 500, 501, 100000]
        return [_e(cmd, BASE + timedelta(minutes=o)) for o in offsets]

    r = _report(("j1.sh", noisy("j1.sh")), ("j2.sh", noisy("j2.sh")))
    result = build_recurrence_report(r, irregularity_threshold=0.05)
    assert result.irregular_count == 2


def test_empty_report_returns_empty_profiles():
    r = AggregatedReport()
    result = build_recurrence_report(r)
    assert result.count == 0
    assert result.irregular_count == 0
