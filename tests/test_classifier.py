"""Tests for cronsight.classifier."""

from __future__ import annotations

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.classifier import (
    ClassifiedReport,
    ClassifierError,
    ClassRule,
    classify_report,
)
from cronsight.parser import CronEntry
from datetime import datetime


def _make_summary(command: str, total: int = 4, success: int = 4) -> JobSummary:
    ts = datetime(2024, 1, 1, 6, 0, 0)
    entries = [
        CronEntry(timestamp=ts, command=command, server="srv", success=(i < success))
        for i in range(total)
    ]
    return JobSummary(command=command, entries=entries)


@pytest.fixture()
def report() -> AggregatedReport:
    jobs = {
        "/usr/bin/backup.sh": _make_summary("/usr/bin/backup.sh"),
        "/usr/bin/cleanup.sh": _make_summary("/usr/bin/cleanup.sh"),
        "/opt/app/deploy.sh": _make_summary("/opt/app/deploy.sh"),
    }
    return AggregatedReport(jobs=jobs)


# --- ClassRule validation ---

def test_class_rule_empty_category_raises():
    with pytest.raises(ClassifierError, match="category"):
        ClassRule(category="", pattern=".*")


def test_class_rule_empty_pattern_raises():
    with pytest.raises(ClassifierError, match="pattern"):
        ClassRule(category="backup", pattern="")


def test_class_rule_invalid_regex_raises():
    with pytest.raises(ClassifierError, match="invalid pattern"):
        ClassRule(category="bad", pattern="[unclosed")


# --- classify_report ---

def test_classify_report_groups_by_pattern(report: AggregatedReport):
    rules = [
        ClassRule(category="backup", pattern=r"backup"),
        ClassRule(category="cleanup", pattern=r"cleanup"),
    ]
    result = classify_report(report, rules)
    assert "backup" in result.categories
    assert "cleanup" in result.categories


def test_classify_report_unmatched_goes_to_default(report: AggregatedReport):
    rules = [ClassRule(category="backup", pattern=r"backup")]
    result = classify_report(report, rules, default_category="other")
    assert "other" in result.categories
    commands = [j.summary.command for j in result.jobs_in("other")]
    assert "/usr/bin/cleanup.sh" in commands
    assert "/opt/app/deploy.sh" in commands


def test_classify_report_no_rules_all_default(report: AggregatedReport):
    result = classify_report(report, [], default_category="misc")
    assert result.categories == ["misc"]
    assert len(result.jobs_in("misc")) == 3


def test_classify_report_jobs_in_unknown_category_returns_empty(report: AggregatedReport):
    result = classify_report(report, [])
    assert result.jobs_in("nonexistent") == []


def test_classified_job_str_contains_category(report: AggregatedReport):
    rules = [ClassRule(category="deploy", pattern=r"deploy")]
    result = classify_report(report, rules)
    job = result.jobs_in("deploy")[0]
    assert "deploy" in str(job)
    assert "/opt/app/deploy.sh" in str(job)


def test_classify_report_first_matching_rule_wins(report: AggregatedReport):
    rules = [
        ClassRule(category="scripts", pattern=r"\.sh$"),
        ClassRule(category="backup", pattern=r"backup"),
    ]
    result = classify_report(report, rules)
    # All .sh files should land in 'scripts', not 'backup'
    assert len(result.jobs_in("scripts")) == 3
    assert result.jobs_in("backup") == []
