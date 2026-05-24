"""Tests for cronsight.correlator."""
from __future__ import annotations

import pytest
from datetime import datetime

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.correlator import (
    CorrelatorError,
    JobCorrelation,
    correlate_reports,
    _success_rate,
)


def _entry(cmd: str, status: str, ts: str = "2024-01-01T10:00:00") -> CronEntry:
    return CronEntry(timestamp=datetime.fromisoformat(ts), command=cmd, status=status, server="srv")


def _summary(cmd: str, entries: list) -> JobSummary:
    return JobSummary(command=cmd, entries=entries)


def _report(*summaries: JobSummary) -> AggregatedReport:
    return AggregatedReport(jobs={s.command: s for s in summaries})


# --- _success_rate ---

def test_success_rate_all_pass():
    c = JobCorrelation(command="x", servers=["a"], total_runs=4, total_failures=0)
    assert _success_rate(c) == 1.0


def test_success_rate_half():
    c = JobCorrelation(command="x", servers=["a"], total_runs=4, total_failures=2)
    assert _success_rate(c) == 0.5


def test_success_rate_zero_runs():
    c = JobCorrelation(command="x", servers=[], total_runs=0, total_failures=0)
    assert _success_rate(c) == 1.0


# --- correlate_reports ---

def test_correlate_raises_on_empty_input():
    with pytest.raises(CorrelatorError):
        correlate_reports({})


def test_correlate_single_report_single_job():
    s = _summary("backup.sh", [_entry("backup.sh", "success")])
    result = correlate_reports({"server1": _report(s)})
    assert len(result.correlations) == 1
    assert result.correlations[0].command == "backup.sh"
    assert result.correlations[0].total_runs == 1


def test_correlate_merges_same_job_across_reports():
    s1 = _summary("job.sh", [_entry("job.sh", "success"), _entry("job.sh", "success")])
    s2 = _summary("job.sh", [_entry("job.sh", "success")])
    result = correlate_reports({"a": _report(s1), "b": _report(s2)})
    assert len(result.correlations) == 1
    corr = result.correlations[0]
    assert corr.total_runs == 3
    assert set(corr.servers) == {"a", "b"}


def test_correlate_consistent_when_statuses_match():
    s1 = _summary("job.sh", [_entry("job.sh", "success")])
    s2 = _summary("job.sh", [_entry("job.sh", "success")])
    result = correlate_reports({"a": _report(s1), "b": _report(s2)})
    assert result.correlations[0].consistent is True


def test_correlate_inconsistent_when_statuses_differ():
    s1 = _summary("job.sh", [_entry("job.sh", "success")])
    s2 = _summary("job.sh", [_entry("job.sh", "failure")])
    result = correlate_reports({"a": _report(s1), "b": _report(s2)})
    assert result.correlations[0].consistent is False


def test_correlate_inconsistent_jobs_property():
    s1 = _summary("a.sh", [_entry("a.sh", "success")])
    s2 = _summary("b.sh", [_entry("b.sh", "failure")])
    s3 = _summary("b.sh", [_entry("b.sh", "success")])
    result = correlate_reports({"x": _report(s1, s2), "y": _report(s3)})
    inconsistent = result.inconsistent_jobs
    assert len(inconsistent) == 1
    assert inconsistent[0].command == "b.sh"


def test_correlate_results_sorted_by_command():
    s1 = _summary("z.sh", [_entry("z.sh", "success")])
    s2 = _summary("a.sh", [_entry("a.sh", "success")])
    result = correlate_reports({"srv": _report(s1, s2)})
    commands = [c.command for c in result.correlations]
    assert commands == sorted(commands)
