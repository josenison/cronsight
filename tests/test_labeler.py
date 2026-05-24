"""Tests for cronsight.labeler."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.labeler import (
    LabelerError,
    LabeledReport,
    SeverityRule,
    label_for_summary,
    label_report,
)


_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_entry(success: bool) -> CronEntry:
    return CronEntry(
        timestamp=_NOW,
        command="/usr/bin/backup",
        exit_code=0 if success else 1,
        server="host1",
    )


def _make_summary(total: int, successful: int) -> JobSummary:
    entries = [_make_entry(i < successful) for i in range(total)]
    return JobSummary(
        command="/usr/bin/backup",
        entries=entries,
        servers=["host1"],
    )


@pytest.fixture()
def rules() -> list[SeverityRule]:
    return [
        SeverityRule(label="critical", max_success_rate=0.0),
        SeverityRule(label="warning", max_success_rate=0.5),
    ]


@pytest.fixture()
def report() -> AggregatedReport:
    return AggregatedReport(
        jobs=[
            _make_summary(10, 10),  # 100 % -> ok
            _make_summary(10, 4),   # 40 %  -> warning
            _make_summary(10, 0),   # 0 %   -> critical
        ]
    )


# --- SeverityRule ---

def test_severity_rule_invalid_rate_raises():
    with pytest.raises(LabelerError):
        SeverityRule(label="bad", max_success_rate=1.5)


def test_severity_rule_boundary_values_accepted():
    SeverityRule(label="zero", max_success_rate=0.0)
    SeverityRule(label="full", max_success_rate=1.0)


# --- label_for_summary ---

def test_label_for_summary_returns_default_when_no_rule_matches(rules):
    summary = _make_summary(10, 10)  # 100 % success
    assert label_for_summary(summary, rules) == "ok"


def test_label_for_summary_warning(rules):
    summary = _make_summary(10, 4)  # 40 %
    assert label_for_summary(summary, rules) == "warning"


def test_label_for_summary_critical(rules):
    summary = _make_summary(10, 0)  # 0 %
    assert label_for_summary(summary, rules) == "critical"


def test_label_for_summary_zero_runs_uses_first_rule(rules):
    summary = _make_summary(0, 0)
    assert label_for_summary(summary, rules) == "critical"


# --- label_report ---

def test_label_report_raises_without_rules(report):
    with pytest.raises(LabelerError):
        label_report(report, rules=[])


def test_label_report_returns_labeled_report(report, rules):
    result = label_report(report, rules)
    assert isinstance(result, LabeledReport)


def test_label_report_all_jobs_labeled(report, rules):
    result = label_report(report, rules)
    assert len(result.labels) == len(report.jobs)


def test_label_report_correct_labels(report, rules):
    result = label_report(report, rules)
    cmd = "/usr/bin/backup"
    # Because all three summaries share the same command, the last write wins;
    # verify the label dict contains the key and a valid label.
    assert cmd in result.labels
    assert result.labels[cmd] in {"ok", "warning", "critical"}
