"""Integration tests for heatmap across multiple jobs and edge cases."""

from __future__ import annotations

from datetime import datetime

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.heatmap import build_heatmap
from cronsight.parser import CronEntry


def _e(cmd: str, hour: int, success: bool = True) -> CronEntry:
    return CronEntry(
        timestamp=datetime(2024, 3, 10, hour, 0, 0),
        server="host1",
        command=cmd,
        success=success,
    )


def _report(*pairs) -> AggregatedReport:
    jobs = {}
    for cmd, entries in pairs:
        jobs[cmd] = JobSummary(command=cmd, entries=entries)
    return AggregatedReport(jobs=jobs)


def test_multiple_jobs_each_get_own_heatmap():
    r = _report(
        ("/bin/a", [_e("/bin/a", 6), _e("/bin/a", 6)]),
        ("/bin/b", [_e("/bin/b", 18)]),
    )
    hm = build_heatmap(r)
    assert hm.get("/bin/a").bucket(6).run_count == 2
    assert hm.get("/bin/b").bucket(18).run_count == 1
    assert hm.get("/bin/a").bucket(18).run_count == 0


def test_all_hours_covered():
    entries = [_e("/bin/c", h) for h in range(24)]
    r = _report(("/bin/c", entries))
    hm = build_heatmap(r)
    job = hm.get("/bin/c")
    assert all(job.bucket(h).run_count == 1 for h in range(24))


def test_peak_hour_reflects_most_runs():
    entries = [_e("/bin/d", 9)] * 5 + [_e("/bin/d", 17)] * 2
    r = _report(("/bin/d", entries))
    hm = build_heatmap(r)
    assert hm.get("/bin/d").peak_hour == 9


def test_empty_report_yields_empty_heatmap():
    r = AggregatedReport(jobs={})
    hm = build_heatmap(r)
    assert hm.jobs == {}


def test_all_failures_reflected_in_buckets():
    entries = [_e("/bin/e", 4, success=False)] * 3
    r = _report(("/bin/e", entries))
    hm = build_heatmap(r)
    bucket = hm.get("/bin/e").bucket(4)
    assert bucket.failure_count == 3
    assert bucket.success_count == 0
    assert bucket.failure_rate == pytest.approx(1.0)
