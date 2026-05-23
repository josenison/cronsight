"""Tests for cronsight.baseline."""

from __future__ import annotations

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.baseline import (
    BaselineDelta,
    compare_to_baseline,
    format_delta,
)


def _make_summary(cmd: str, total: int, successful: int, server: str = "host1") -> JobSummary:
    entries = [
        CronEntry(
            timestamp="2024-01-01T00:00:00",
            cmd=cmd,
            exit_code=0 if i < successful else 1,
            server=server,
        )
        for i in range(total)
    ]
    return JobSummary(
        cmd=cmd,
        total_runs=total,
        successful_runs=successful,
        servers={server},
        entries=entries,
    )


def _make_report(*summaries: JobSummary) -> AggregatedReport:
    return AggregatedReport(jobs={s.cmd: s for s in summaries})


# --- compare_to_baseline ---

def test_no_changes_returns_empty_delta():
    s = _make_summary("backup.sh", 10, 10)
    report = _make_report(s)
    delta = compare_to_baseline(report, report)
    assert not delta.has_changes


def test_new_job_detected():
    baseline = _make_report(_make_summary("old.sh", 5, 5))
    current = _make_report(_make_summary("old.sh", 5, 5), _make_summary("new.sh", 3, 3))
    delta = compare_to_baseline(baseline, current)
    assert "new.sh" in delta.new_jobs
    assert not delta.removed_jobs


def test_removed_job_detected():
    baseline = _make_report(_make_summary("gone.sh", 5, 5), _make_summary("keep.sh", 5, 5))
    current = _make_report(_make_summary("keep.sh", 5, 5))
    delta = compare_to_baseline(baseline, current)
    assert "gone.sh" in delta.removed_jobs
    assert not delta.new_jobs


def test_degraded_job_detected():
    baseline = _make_report(_make_summary("sync.sh", 10, 10))
    current = _make_report(_make_summary("sync.sh", 10, 5))  # 50% success
    delta = compare_to_baseline(baseline, current)
    assert "sync.sh" in delta.degraded_jobs
    assert not delta.improved_jobs


def test_improved_job_detected():
    baseline = _make_report(_make_summary("sync.sh", 10, 5))
    current = _make_report(_make_summary("sync.sh", 10, 10))
    delta = compare_to_baseline(baseline, current)
    assert "sync.sh" in delta.improved_jobs
    assert not delta.degraded_jobs


def test_small_change_below_threshold_ignored():
    baseline = _make_report(_make_summary("sync.sh", 100, 95))
    current = _make_report(_make_summary("sync.sh", 100, 92))  # 3% drop
    delta = compare_to_baseline(baseline, current, degradation_threshold=0.05)
    assert not delta.degraded_jobs


# --- format_delta ---

def test_format_delta_no_changes():
    delta = BaselineDelta()
    assert "No changes" in format_delta(delta)


def test_format_delta_lists_all_categories():
    delta = BaselineDelta(
        new_jobs=["a.sh"],
        removed_jobs=["b.sh"],
        degraded_jobs=["c.sh"],
        improved_jobs=["d.sh"],
    )
    text = format_delta(delta)
    assert "a.sh" in text
    assert "b.sh" in text
    assert "c.sh" in text
    assert "d.sh" in text
