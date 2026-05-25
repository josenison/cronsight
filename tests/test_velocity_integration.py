"""Integration tests for velocity: full pipeline from entries to report."""
from __future__ import annotations

from datetime import datetime

from cronsight.parser import CronEntry
from cronsight.aggregator import JobSummary, AggregatedReport
from cronsight.velocity import compute_velocity, VelocityReport


def _e(cmd: str, exit_code: int = 0, hour: int = 10) -> CronEntry:
    return CronEntry(
        timestamp=datetime(2024, 3, 1, hour, 0, 0),
        server="host1",
        command=cmd,
        exit_code=exit_code,
    )


def _report(*pairs) -> AggregatedReport:
    summaries = [
        JobSummary(command=cmd, entries=entries, servers={"host1"})
        for cmd, entries in pairs
    ]
    return AggregatedReport(summaries=summaries)


def test_multiple_jobs_each_get_own_delta():
    old = _report(
        ("job_a", [_e("job_a", 0)] * 2),
        ("job_b", [_e("job_b", 0)] * 4),
    )
    new = _report(
        ("job_a", [_e("job_a", 0)] * 5),
        ("job_b", [_e("job_b", 1)] * 2),
    )
    report = compute_velocity(old, new)
    cmds = {d.command for d in report.deltas}
    assert "job_a" in cmds
    assert "job_b" in cmds


def test_accelerating_jobs_identified():
    old = _report(("fast", [_e("fast", 0)]))
    new = _report(("fast", [_e("fast", 0)] * 10))
    report = compute_velocity(old, new)
    assert len(report.accelerating) == 1
    assert report.accelerating[0].command == "fast"


def test_decelerating_jobs_identified():
    old = _report(("slow", [_e("slow", 0)] * 8))
    new = _report(("slow", [_e("slow", 0)] * 2))
    report = compute_velocity(old, new)
    assert len(report.decelerating) == 1


def test_success_rate_degradation_captured():
    old = _report(("flaky", [_e("flaky", 0)] * 10))
    new = _report(("flaky", [_e("flaky", 0)] * 5 + [_e("flaky", 1)] * 5))
    report = compute_velocity(old, new)
    delta = report.deltas[0]
    assert delta.rate_delta < 0


def test_brand_new_job_has_zero_old_runs():
    old = _report()
    new = _report(("brand_new", [_e("brand_new", 0)] * 3))
    report = compute_velocity(old, new)
    assert report.deltas[0].old_runs == 0
    assert report.deltas[0].new_runs == 3
