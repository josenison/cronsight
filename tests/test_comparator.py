"""Tests for cronsight.comparator."""

import pytest
from datetime import datetime

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.comparator import compare_reports, ComparisonResult, JobChange


def _make_entry(cmd: str, success: bool) -> CronEntry:
    return CronEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        command=cmd,
        success=success,
        server="host1",
    )


def _make_summary(cmd: str, runs: int, successes: int) -> JobSummary:
    entries = (
        [_make_entry(cmd, True)] * successes
        + [_make_entry(cmd, False)] * (runs - successes)
    )
    return JobSummary(command=cmd, entries=entries, servers={"host1"})


def _report(*summaries: JobSummary) -> AggregatedReport:
    return AggregatedReport(jobs=list(summaries))


# ---------------------------------------------------------------------------
# added / removed
# ---------------------------------------------------------------------------

def test_new_job_appears_in_added():
    base = _report(_make_summary("/bin/old", 5, 5))
    curr = _report(_make_summary("/bin/old", 5, 5), _make_summary("/bin/new", 3, 3))
    result = compare_reports(base, curr)
    assert "/bin/new" in result.added
    assert result.removed == []


def test_missing_job_appears_in_removed():
    base = _report(_make_summary("/bin/gone", 4, 4), _make_summary("/bin/kept", 2, 2))
    curr = _report(_make_summary("/bin/kept", 2, 2))
    result = compare_reports(base, curr)
    assert "/bin/gone" in result.removed
    assert result.added == []


# ---------------------------------------------------------------------------
# changed
# ---------------------------------------------------------------------------

def test_run_count_change_detected():
    base = _report(_make_summary("/bin/job", 5, 5))
    curr = _report(_make_summary("/bin/job", 10, 10))
    result = compare_reports(base, curr)
    run_changes = [c for c in result.changed if c.field == "total_runs"]
    assert len(run_changes) == 1
    assert run_changes[0].old_value == 5
    assert run_changes[0].new_value == 10


def test_success_rate_drop_detected():
    base = _report(_make_summary("/bin/flaky", 10, 10))  # 100 %
    curr = _report(_make_summary("/bin/flaky", 10, 5))   # 50 %
    result = compare_reports(base, curr)
    rate_changes = [c for c in result.changed if c.field == "success_rate"]
    assert len(rate_changes) == 1
    assert rate_changes[0].new_value < rate_changes[0].old_value


def test_small_rate_change_ignored_below_threshold():
    base = _report(_make_summary("/bin/stable", 100, 99))  # 99 %
    curr = _report(_make_summary("/bin/stable", 100, 98))  # 98 %  delta = 0.01
    result = compare_reports(base, curr, rate_threshold=0.05)
    rate_changes = [c for c in result.changed if c.field == "success_rate"]
    assert rate_changes == []


# ---------------------------------------------------------------------------
# has_differences / summary_lines
# ---------------------------------------------------------------------------

def test_no_differences_returns_false():
    base = _report(_make_summary("/bin/ok", 5, 5))
    curr = _report(_make_summary("/bin/ok", 5, 5))
    result = compare_reports(base, curr)
    assert not result.has_differences


def test_summary_lines_contains_descriptions():
    base = _report(_make_summary("/bin/old", 5, 5))
    curr = _report(_make_summary("/bin/new", 3, 3))
    result = compare_reports(base, curr)
    lines = result.summary_lines()
    assert any("new job" in line for line in lines)
    assert any("removed job" in line for line in lines)


def test_job_change_str():
    change = JobChange("/bin/job", "total_runs", 5, 10)
    assert "total_runs" in str(change)
    assert "/bin/job" in str(change)
