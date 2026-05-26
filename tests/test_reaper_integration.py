"""Integration tests for cronsight.reaper — end-to-end with real aggregated data."""

from __future__ import annotations

from datetime import datetime, timedelta

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.reaper import reap

NOW = datetime(2024, 3, 15, 9, 0, 0)


def _e(cmd: str, ts: datetime, success: bool = True) -> CronEntry:
    return CronEntry(timestamp=ts, command=cmd, success=success, server="srv1")


def _report() -> AggregatedReport:
    r = AggregatedReport()
    # job A: ran 2 hours ago — healthy for 24h window
    r.jobs["job_a.sh"] = JobSummary(entries=[_e("job_a.sh", NOW - timedelta(hours=2))])
    # job B: ran 30 hours ago — overdue for 24h window
    r.jobs["job_b.sh"] = JobSummary(entries=[_e("job_b.sh", NOW - timedelta(hours=30))])
    # job C: never ran
    r.jobs["job_c.sh"] = JobSummary(entries=[])
    return r


def test_healthy_job_not_in_dead_list():
    result = reap(_report(), expected_interval_hours=24, now=NOW)
    commands = [j.command for j in result.dead_jobs]
    assert "job_a.sh" not in commands


def test_overdue_job_in_dead_list():
    result = reap(_report(), expected_interval_hours=24, now=NOW)
    commands = [j.command for j in result.dead_jobs]
    assert "job_b.sh" in commands


def test_never_run_job_in_dead_list():
    result = reap(_report(), expected_interval_hours=24, now=NOW)
    commands = [j.command for j in result.dead_jobs]
    assert "job_c.sh" in commands


def test_total_dead_count():
    result = reap(_report(), expected_interval_hours=24, now=NOW)
    assert result.count == 2


def test_pattern_restricts_to_matching_jobs():
    result = reap(_report(), expected_interval_hours=24, pattern="job_b", now=NOW)
    assert result.count == 1
    assert result.dead_jobs[0].command == "job_b.sh"
