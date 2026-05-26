"""Tests for cronsight.batcher."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.batcher import (
    BatcherError,
    BatchReport,
    ExecutionBatch,
    build_batch_report,
    _group_entries,
)
from cronsight.parser import CronEntry


def _entry(ts: datetime, status: str = "success", server: str = "host1") -> CronEntry:
    e = CronEntry(command="/usr/bin/backup", status=status, timestamp=ts)
    e.server = server
    return e


def _ts(hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(2024, 1, 15, hour, minute, second, tzinfo=timezone.utc)


def _summary(entries, servers=None) -> JobSummary:
    s = JobSummary(command="/usr/bin/backup")
    s.entries = entries
    s.servers = servers or {e.server for e in entries}
    return s


def _report(summaries: dict) -> AggregatedReport:
    r = AggregatedReport()
    r.jobs = summaries
    return r


# --- ExecutionBatch ---

def test_execution_batch_run_count():
    b = ExecutionBatch(command="cmd", server="s1", entries=[_entry(_ts(1)), _entry(_ts(2))])
    assert b.run_count == 2


def test_execution_batch_has_overlap_true():
    b = ExecutionBatch(command="cmd", server="s1", entries=[_entry(_ts(1)), _entry(_ts(1))])
    assert b.has_overlap is True


def test_execution_batch_has_overlap_false():
    b = ExecutionBatch(command="cmd", server="s1", entries=[_entry(_ts(1))])
    assert b.has_overlap is False


def test_execution_batch_str_contains_overlap():
    b = ExecutionBatch(command="cmd", server="s1", entries=[_entry(_ts(1)), _entry(_ts(2))])
    assert "OVERLAP" in str(b)


def test_execution_batch_earliest_and_latest():
    e1 = _entry(_ts(1, 0))
    e2 = _entry(_ts(1, 0, 30))
    b = ExecutionBatch(command="cmd", server="s1", entries=[e1, e2])
    assert b.earliest == _ts(1, 0)
    assert b.latest == _ts(1, 0, 30)


# --- _group_entries ---

def test_group_entries_empty_returns_empty():
    assert _group_entries([], 60) == []


def test_group_entries_single_returns_one_group():
    result = _group_entries([_entry(_ts(1))], 60)
    assert len(result) == 1


def test_group_entries_within_window_grouped():
    entries = [_entry(_ts(1, 0, 0)), _entry(_ts(1, 0, 30))]
    result = _group_entries(entries, 60)
    assert len(result) == 1
    assert len(result[0]) == 2


def test_group_entries_outside_window_split():
    entries = [_entry(_ts(1, 0)), _entry(_ts(2, 0))]
    result = _group_entries(entries, 60)
    assert len(result) == 2


# --- build_batch_report ---

def test_build_batch_report_no_overlaps_returns_empty():
    e1 = _entry(_ts(1, 0))
    e2 = _entry(_ts(3, 0))
    s = _summary([e1, e2])
    r = _report({"/usr/bin/backup": s})
    result = build_batch_report(r, window_seconds=60)
    assert result.count == 0
    assert result.overlap_count == 0


def test_build_batch_report_detects_overlap():
    e1 = _entry(_ts(1, 0, 0))
    e2 = _entry(_ts(1, 0, 20))
    s = _summary([e1, e2])
    r = _report({"/usr/bin/backup": s})
    result = build_batch_report(r, window_seconds=60)
    assert result.count == 1
    assert result.overlap_count == 1


def test_build_batch_report_raises_on_invalid_window():
    r = _report({})
    with pytest.raises(BatcherError):
        build_batch_report(r, window_seconds=0)


def test_batch_report_overlap_count_property():
    b1 = ExecutionBatch("cmd", "s1", [_entry(_ts(1)), _entry(_ts(1))])
    b2 = ExecutionBatch("cmd2", "s1", [_entry(_ts(2))])
    report = BatchReport(batches=[b1, b2])
    assert report.overlap_count == 1
