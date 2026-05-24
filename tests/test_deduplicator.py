"""Tests for cronsight.deduplicator."""

from __future__ import annotations

import pytest
from datetime import datetime

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.deduplicator import (
    DeduplicatorError,
    DuplicateGroup,
    deduplicate_report,
)


def _entry(cmd: str, ok: bool = True) -> CronEntry:
    return CronEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        command=cmd,
        success=ok,
        server="srv1",
    )


def _summary(cmd: str, server: str = "srv1", ok: bool = True) -> JobSummary:
    return JobSummary(
        command=cmd,
        entries=[_entry(cmd, ok)],
        server=server,
    )


# ---------------------------------------------------------------------------
# DuplicateGroup
# ---------------------------------------------------------------------------

def test_duplicate_group_server_count():
    s1 = _summary("/bin/backup", server="srv1")
    s2 = _summary("/bin/backup", server="srv2")
    group = DuplicateGroup(command="/bin/backup", summaries=[s1, s2])
    assert group.server_count == 2


def test_duplicate_group_total_runs():
    s1 = _summary("/bin/backup", server="srv1")
    s2 = _summary("/bin/backup", server="srv2")
    group = DuplicateGroup(command="/bin/backup", summaries=[s1, s2])
    assert group.total_runs == 2


def test_duplicate_group_str_contains_command():
    group = DuplicateGroup(command="/bin/job", summaries=[])
    assert "/bin/job" in str(group)


# ---------------------------------------------------------------------------
# deduplicate_report — error cases
# ---------------------------------------------------------------------------

def test_raises_on_empty_report():
    empty = AggregatedReport(jobs=[])
    with pytest.raises(DeduplicatorError):
        deduplicate_report(empty)


# ---------------------------------------------------------------------------
# deduplicate_report — no duplicates
# ---------------------------------------------------------------------------

def test_no_duplicates_returns_same_count():
    report = AggregatedReport(jobs=[
        _summary("/bin/job_a", server="srv1"),
        _summary("/bin/job_b", server="srv1"),
    ])
    result = deduplicate_report(report)
    assert result.removed_count == 0
    assert not result.has_duplicates
    assert len(result.deduplicated_report.jobs) == 2


# ---------------------------------------------------------------------------
# deduplicate_report — with duplicates, keep-first mode
# ---------------------------------------------------------------------------

def test_duplicate_command_detected():
    report = AggregatedReport(jobs=[
        _summary("/bin/backup", server="srv1"),
        _summary("/bin/backup", server="srv2"),
    ])
    result = deduplicate_report(report)
    assert result.has_duplicates
    assert len(result.duplicate_groups) == 1
    assert result.duplicate_groups[0].command == "/bin/backup"


def test_keep_first_removes_duplicate():
    report = AggregatedReport(jobs=[
        _summary("/bin/backup", server="srv1"),
        _summary("/bin/backup", server="srv2"),
        _summary("/bin/cleanup", server="srv1"),
    ])
    result = deduplicate_report(report, merge=False)
    assert result.removed_count == 1
    assert len(result.deduplicated_report.jobs) == 2


# ---------------------------------------------------------------------------
# deduplicate_report — merge mode
# ---------------------------------------------------------------------------

def test_merge_combines_entries():
    s1 = _summary("/bin/backup", server="srv1")
    s2 = _summary("/bin/backup", server="srv2")
    report = AggregatedReport(jobs=[s1, s2])
    result = deduplicate_report(report, merge=True)
    merged = result.deduplicated_report.jobs[0]
    assert len(merged.entries) == 2


def test_merge_combines_server_names():
    s1 = _summary("/bin/backup", server="alpha")
    s2 = _summary("/bin/backup", server="beta")
    report = AggregatedReport(jobs=[s1, s2])
    result = deduplicate_report(report, merge=True)
    merged_server = result.deduplicated_report.jobs[0].server
    assert "alpha" in merged_server
    assert "beta" in merged_server


def test_original_count_preserved():
    report = AggregatedReport(jobs=[
        _summary("/bin/a", server="s1"),
        _summary("/bin/a", server="s2"),
        _summary("/bin/b", server="s1"),
    ])
    result = deduplicate_report(report)
    assert result.original_count == 3
