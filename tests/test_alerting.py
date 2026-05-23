"""Tests for cronsight.alerting."""

import pytest
from cronsight.alerting import AlertRule, Alert, evaluate_summary, check_report, _consecutive_failures
from cronsight.aggregator import JobSummary, AggregatedReport
from cronsight.parser import CronEntry
from datetime import datetime


def _entry(exit_code: int) -> CronEntry:
    return CronEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        job_name="backup",
        command="/usr/bin/backup.sh",
        exit_code=exit_code,
    )


@pytest.fixture
def passing_summary() -> JobSummary:
    runs = [_entry(0)] * 5
    return JobSummary(job_name="backup", server="web-01", runs=runs, failed_runs=0)


@pytest.fixture
def failing_summary() -> JobSummary:
    runs = [_entry(0)] * 2 + [_entry(1)] * 3
    return JobSummary(job_name="backup", server="web-01", runs=runs, failed_runs=3)


@pytest.fixture
def sample_report(passing_summary, failing_summary) -> AggregatedReport:
    return AggregatedReport(jobs=[passing_summary, failing_summary])


def test_consecutive_failures_all_pass(passing_summary):
    assert _consecutive_failures(passing_summary) == 0


def test_consecutive_failures_trailing(failing_summary):
    assert _consecutive_failures(failing_summary) == 3


def test_consecutive_failures_interleaved():
    runs = [_entry(1), _entry(0), _entry(1)]
    summary = JobSummary(job_name="job", server="s", runs=runs, failed_runs=2)
    assert _consecutive_failures(summary) == 1


def test_evaluate_no_alert_when_healthy(passing_summary):
    rule = AlertRule(min_success_rate=0.8, max_consecutive_failures=2)
    alerts = evaluate_summary(passing_summary, rule)
    assert alerts == []


def test_evaluate_triggers_low_success_rate(failing_summary):
    rule = AlertRule(min_success_rate=0.8)
    alerts = evaluate_summary(failing_summary, rule)
    assert len(alerts) == 1
    assert "success rate" in alerts[0].reason
    assert alerts[0].job_name == "backup"
    assert alerts[0].server == "web-01"


def test_evaluate_triggers_consecutive_failures(failing_summary):
    rule = AlertRule(max_consecutive_failures=1)
    alerts = evaluate_summary(failing_summary, rule)
    assert len(alerts) == 1
    assert "consecutive failures" in alerts[0].reason


def test_evaluate_respects_min_runs(failing_summary):
    rule = AlertRule(min_success_rate=0.5, min_runs=10)
    alerts = evaluate_summary(failing_summary, rule)
    assert alerts == []


def test_evaluate_can_emit_multiple_alerts(failing_summary):
    rule = AlertRule(min_success_rate=0.9, max_consecutive_failures=1)
    alerts = evaluate_summary(failing_summary, rule)
    assert len(alerts) == 2


def test_check_report_aggregates_alerts(sample_report):
    rule = AlertRule(min_success_rate=0.8)
    alerts = check_report(sample_report, rule)
    # only the failing_summary should trigger
    assert len(alerts) == 1
    assert alerts[0].job_name == "backup"


def test_alert_str_representation(failing_summary):
    rule = AlertRule(min_success_rate=0.9)
    alerts = evaluate_summary(failing_summary, rule)
    assert "[ALERT]" in str(alerts[0])
    assert "backup" in str(alerts[0])
