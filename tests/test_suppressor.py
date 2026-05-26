"""Tests for cronsight.suppressor."""

from __future__ import annotations

import pytest
from datetime import datetime

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.suppressor import (
    SuppressRule,
    SuppressorError,
    suppress_report,
)


def _entry(cmd: str, status: str = "success") -> CronEntry:
    return CronEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        server="host1",
        command=cmd,
        status=status,
    )


def _make_summary(cmd: str, *statuses: str) -> JobSummary:
    entries = [_entry(cmd, s) for s in statuses]
    return JobSummary(command=cmd, entries=entries)


def _make_report(*summaries: JobSummary) -> AggregatedReport:
    return AggregatedReport(jobs={s.command: s for s in summaries})


# --- SuppressRule ---

def test_suppress_rule_empty_pattern_raises():
    with pytest.raises(SuppressorError, match="pattern must not be empty"):
        SuppressRule(pattern="")


def test_suppress_rule_invalid_regex_raises():
    with pytest.raises(SuppressorError, match="invalid regex"):
        SuppressRule(pattern="[unclosed")


def test_suppress_rule_matches_substring():
    rule = SuppressRule(pattern="backup")
    assert rule.matches("/usr/bin/backup.sh") is True


def test_suppress_rule_no_match():
    rule = SuppressRule(pattern="backup")
    assert rule.matches("/usr/bin/cleanup.sh") is False


def test_suppress_rule_stores_reason():
    rule = SuppressRule(pattern="noisy", reason="known flaky job")
    assert rule.reason == "known flaky job"


# --- suppress_report ---

def test_suppress_report_no_rules_raises():
    report = _make_report(_make_summary("/bin/job", "success"))
    with pytest.raises(SuppressorError, match="at least one suppress rule"):
        suppress_report(report, [])


def test_suppress_report_removes_matching_job():
    report = _make_report(
        _make_summary("/usr/bin/noisy.sh", "success"),
        _make_summary("/usr/bin/clean.sh", "success"),
    )
    rules = [SuppressRule(pattern="noisy")]
    result = suppress_report(report, rules)
    commands = [j.command for j in result.jobs]
    assert "/usr/bin/noisy.sh" not in commands
    assert "/usr/bin/clean.sh" in commands


def test_suppress_report_suppressed_count():
    report = _make_report(
        _make_summary("/bin/a", "success"),
        _make_summary("/bin/b", "success"),
        _make_summary("/bin/c", "success"),
    )
    rules = [SuppressRule(pattern=r"/bin/[ab]")]
    result = suppress_report(report, rules)
    assert result.suppressed_count == 2
    assert result.job_count == 1


def test_suppress_report_no_matches_keeps_all():
    report = _make_report(
        _make_summary("/bin/x", "success"),
        _make_summary("/bin/y", "failure"),
    )
    rules = [SuppressRule(pattern="zzz")]
    result = suppress_report(report, rules)
    assert result.job_count == 2
    assert result.suppressed_count == 0


def test_suppress_report_rules_applied_stored():
    report = _make_report(_make_summary("/bin/job", "success"))
    rules = [SuppressRule(pattern="job", reason="test")]
    result = suppress_report(report, rules)
    assert result.rules_applied == rules
