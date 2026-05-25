"""Unit tests for cronsight.velocity."""
from __future__ import annotations

import pytest
from datetime import datetime

from cronsight.parser import CronEntry
from cronsight.aggregator import JobSummary, AggregatedReport
from cronsight.velocity import (
    VelocityDelta,
    VelocityReport,
    VelocityError,
    compute_velocity,
    _success_rate,
)


def _entry(cmd: str, exit_code: int = 0) -> CronEntry:
    return CronEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        server="srv1",
        command=cmd,
        exit_code=exit_code,
    )


def _summary(cmd: str, entries: list) -> JobSummary:
    return JobSummary(command=cmd, entries=entries, servers={"srv1"})


def _report(*summaries) -> AggregatedReport:
    return AggregatedReport(summaries=list(summaries))


# --- VelocityDelta ---

def test_run_delta_positive():
    d = VelocityDelta("backup", old_runs=3, new_runs=7, old_success_rate=1.0, new_success_rate=0.9)
    assert d.run_delta == 4


def test_run_delta_negative():
    d = VelocityDelta("backup", old_runs=10, new_runs=4, old_success_rate=1.0, new_success_rate=1.0)
    assert d.run_delta == -6


def test_rate_delta_computed():
    d = VelocityDelta("job", old_runs=5, new_runs=5, old_success_rate=0.8, new_success_rate=0.6)
    assert abs(d.rate_delta - (-0.2)) < 1e-6


def test_accelerating_true_when_run_delta_positive():
    d = VelocityDelta("job", old_runs=2, new_runs=5, old_success_rate=1.0, new_success_rate=1.0)
    assert d.accelerating is True


def test_accelerating_false_when_run_delta_zero():
    d = VelocityDelta("job", old_runs=5, new_runs=5, old_success_rate=1.0, new_success_rate=1.0)
    assert d.accelerating is False


def test_str_contains_command():
    d = VelocityDelta("myjob", old_runs=1, new_runs=3, old_success_rate=1.0, new_success_rate=1.0)
    assert "myjob" in str(d)


# --- _success_rate ---

def test_success_rate_all_pass():
    s = _summary("job", [_entry("job", 0), _entry("job", 0)])
    assert _success_rate(s) == 1.0


def test_success_rate_mixed():
    s = _summary("job", [_entry("job", 0), _entry("job", 1)])
    assert _success_rate(s) == 0.5


def test_success_rate_empty():
    s = _summary("job", [])
    assert _success_rate(s) == 0.0


# --- compute_velocity ---

def test_compute_velocity_returns_report():
    old = _report(_summary("job", [_entry("job", 0)]))
    new = _report(_summary("job", [_entry("job", 0), _entry("job", 0)]))
    result = compute_velocity(old, new)
    assert isinstance(result, VelocityReport)


def test_compute_velocity_run_delta():
    old = _report(_summary("job", [_entry("job", 0)]))
    new = _report(_summary("job", [_entry("job", 0)] * 4))
    result = compute_velocity(old, new)
    assert result.deltas[0].run_delta == 3


def test_compute_velocity_new_job_old_runs_zero():
    old = _report()
    new = _report(_summary("newjob", [_entry("newjob", 0)]))
    result = compute_velocity(old, new)
    assert result.deltas[0].old_runs == 0


def test_compute_velocity_raises_on_none_old():
    new = _report(_summary("job", [_entry("job", 0)]))
    with pytest.raises(VelocityError):
        compute_velocity(None, new)


def test_compute_velocity_raises_on_none_new():
    old = _report(_summary("job", [_entry("job", 0)]))
    with pytest.raises(VelocityError):
        compute_velocity(old, None)


def test_velocity_report_accelerating_filter():
    old = _report(_summary("fast", [_entry("fast", 0)]), _summary("slow", [_entry("slow", 0)] * 5))
    new = _report(_summary("fast", [_entry("fast", 0)] * 3), _summary("slow", [_entry("slow", 0)]))
    result = compute_velocity(old, new)
    assert all(d.accelerating for d in result.accelerating)
    assert not any(d.accelerating for d in result.decelerating)
