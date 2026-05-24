"""Tests for cronsight.merger."""

from __future__ import annotations

from datetime import datetime

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.merger import MergerError, MergeResult, merge_reports
from cronsight.parser import CronEntry


def _entry(cmd: str, status: str = "success", server: str = "host1") -> CronEntry:
    return CronEntry(
        timestamp=datetime(2024, 1, 10, 6, 0, 0),
        command=cmd,
        status=status,
        server=server,
    )


def _summary(cmd: str, entries, servers=None) -> JobSummary:
    return JobSummary(
        command=cmd,
        entries=entries,
        servers=servers or ["host1"],
    )


def _report(*summaries: JobSummary) -> AggregatedReport:
    return AggregatedReport(jobs={s.command: s for s in summaries})


# ---------------------------------------------------------------------------
# MergeResult properties
# ---------------------------------------------------------------------------

def test_merge_result_job_count():
    result = MergeResult(jobs={"cmd": _summary("cmd", [_entry("cmd")])})
    assert result.job_count == 1


def test_merge_result_total_runs():
    entries = [_entry("cmd"), _entry("cmd")]
    result = MergeResult(jobs={"cmd": _summary("cmd", entries)})
    assert result.total_runs == 2


# ---------------------------------------------------------------------------
# merge_reports
# ---------------------------------------------------------------------------

def test_merge_reports_raises_on_empty_list():
    with pytest.raises(MergerError):
        merge_reports([])


def test_merge_single_report_returns_same_jobs():
    s = _summary("backup.sh", [_entry("backup.sh")])
    report = _report(s)
    result = merge_reports([report])
    assert "backup.sh" in result.jobs
    assert result.source_count == 1


def test_merge_two_reports_combines_distinct_jobs():
    r1 = _report(_summary("job_a", [_entry("job_a")]))
    r2 = _report(_summary("job_b", [_entry("job_b", server="host2")]))
    result = merge_reports([r1, r2])
    assert "job_a" in result.jobs
    assert "job_b" in result.jobs
    assert result.source_count == 2


def test_merge_overlapping_jobs_combines_entries():
    e1 = _entry("sync.sh", server="host1")
    e2 = _entry("sync.sh", server="host2")
    r1 = _report(_summary("sync.sh", [e1], servers=["host1"]))
    r2 = _report(_summary("sync.sh", [e2], servers=["host2"]))
    result = merge_reports([r1, r2])
    merged = result.jobs["sync.sh"]
    assert len(merged.entries) == 2


def test_merge_overlapping_jobs_merges_servers():
    r1 = _report(_summary("sync.sh", [_entry("sync.sh")], servers=["alpha"]))
    r2 = _report(_summary("sync.sh", [_entry("sync.sh", server="beta")], servers=["beta"]))
    result = merge_reports([r1, r2])
    assert set(result.jobs["sync.sh"].servers) == {"alpha", "beta"}


def test_merge_three_reports_source_count():
    r = _report(_summary("x", [_entry("x")]))
    result = merge_reports([r, r, r])
    assert result.source_count == 3
