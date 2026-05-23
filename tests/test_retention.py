"""Tests for cronsight.retention module."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.retention import (
    RetentionError,
    RetentionPolicy,
    RetentionResult,
    apply_retention,
)


def _make_entry(success: bool = True, days_ago: int = 0) -> CronEntry:
    ts = datetime.utcnow() - timedelta(days=days_ago)
    return CronEntry(timestamp=ts, command="/usr/bin/backup", success=success, server="host1")


def _make_summary(entries: list) -> JobSummary:
    return JobSummary(command="/usr/bin/backup", entries=entries)


def _make_report(summaries: list) -> AggregatedReport:
    return AggregatedReport(jobs=summaries)


def test_policy_raises_if_no_criteria():
    with pytest.raises(RetentionError, match="At least one retention criterion"):
        RetentionPolicy()


def test_policy_raises_on_zero_max_age():
    with pytest.raises(RetentionError, match="max_age_days"):
        RetentionPolicy(max_age_days=0)


def test_policy_raises_on_zero_max_entries():
    with pytest.raises(RetentionError, match="max_entries_per_job"):
        RetentionPolicy(max_entries_per_job=0)


def test_retention_result_removed_count():
    result = RetentionResult(original_entry_count=10, retained_entry_count=6)
    assert result.removed_count == 4


def test_apply_max_age_removes_old_entries():
    entries = [
        _make_entry(days_ago=5),
        _make_entry(days_ago=2),
        _make_entry(days_ago=0),
    ]
    report = _make_report([_make_summary(entries)])
    policy = RetentionPolicy(max_age_days=3)

    result = apply_retention(report, policy)

    assert result.retained_entry_count == 2
    assert result.removed_count == 1


def test_apply_max_entries_keeps_newest():
    entries = [_make_entry(days_ago=i) for i in range(5)]
    report = _make_report([_make_summary(entries)])
    policy = RetentionPolicy(max_entries_per_job=3)

    result = apply_retention(report, policy)

    assert result.retained_entry_count == 3
    assert len(report.jobs[0].entries) == 3


def test_keep_failures_preserves_old_failed_entries():
    entries = [
        _make_entry(success=False, days_ago=10),
        _make_entry(success=True, days_ago=10),
        _make_entry(success=True, days_ago=0),
    ]
    report = _make_report([_make_summary(entries)])
    policy = RetentionPolicy(max_age_days=3, keep_failures=True)

    result = apply_retention(report, policy)

    assert result.retained_entry_count == 2


def test_keep_failures_false_removes_all_old():
    entries = [
        _make_entry(success=False, days_ago=10),
        _make_entry(success=True, days_ago=0),
    ]
    report = _make_report([_make_summary(entries)])
    policy = RetentionPolicy(max_age_days=3, keep_failures=False)

    result = apply_retention(report, policy)

    assert result.retained_entry_count == 1


def test_jobs_affected_lists_changed_commands():
    entries = [_make_entry(days_ago=10), _make_entry(days_ago=0)]
    report = _make_report([_make_summary(entries)])
    policy = RetentionPolicy(max_age_days=3, keep_failures=False)

    result = apply_retention(report, policy)

    assert "/usr/bin/backup" in result.jobs_affected


def test_no_entries_removed_when_all_recent():
    entries = [_make_entry(days_ago=0), _make_entry(days_ago=1)]
    report = _make_report([_make_summary(entries)])
    policy = RetentionPolicy(max_age_days=7)

    result = apply_retention(report, policy)

    assert result.removed_count == 0
    assert result.jobs_affected == []
