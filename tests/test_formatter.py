"""Tests for cronsight.formatter."""

from datetime import datetime

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.formatter import (
    format_job_row,
    format_report,
    _format_timestamp,
    _success_rate,
)


@pytest.fixture
def sample_summary() -> JobSummary:
    return JobSummary(
        command="/usr/bin/backup.sh",
        server="web-01",
        total_runs=10,
        failed_runs=2,
        first_run=datetime(2024, 1, 1, 0, 0, 0),
        last_run=datetime(2024, 6, 15, 3, 30, 0),
    )


@pytest.fixture
def sample_report(sample_summary: JobSummary) -> AggregatedReport:
    return AggregatedReport(
        jobs=[sample_summary],
        servers={"web-01"},
    )


def test_format_timestamp_returns_formatted_string():
    dt = datetime(2024, 3, 22, 14, 5, 9)
    assert _format_timestamp(dt) == "2024-03-22 14:05:09"


def test_format_timestamp_returns_na_for_none():
    assert _format_timestamp(None) == "N/A"


def test_success_rate_all_pass(sample_summary: JobSummary):
    sample_summary.failed_runs = 0
    assert _success_rate(sample_summary) == 100.0


def test_success_rate_partial(sample_summary: JobSummary):
    rate = _success_rate(sample_summary)
    assert rate == pytest.approx(80.0)


def test_success_rate_zero_runs():
    summary = JobSummary(
        command="cmd", server="s", total_runs=0, failed_runs=0,
        first_run=None, last_run=None
    )
    assert _success_rate(summary) == 0.0


def test_format_job_row_contains_command(sample_summary: JobSummary):
    row = format_job_row(sample_summary, use_color=False)
    assert "/usr/bin/backup.sh" in row


def test_format_job_row_contains_server(sample_summary: JobSummary):
    row = format_job_row(sample_summary, use_color=False)
    assert "web-01" in row


def test_format_job_row_contains_success_rate(sample_summary: JobSummary):
    row = format_job_row(sample_summary, use_color=False)
    assert "80.0%" in row


def test_format_report_contains_header(sample_report: AggregatedReport):
    output = format_report(sample_report, use_color=False)
    assert "CronSight" in output


def test_format_report_contains_job_command(sample_report: AggregatedReport):
    output = format_report(sample_report, use_color=False)
    assert "/usr/bin/backup.sh" in output


def test_format_report_empty_jobs():
    report = AggregatedReport(jobs=[], servers=set())
    output = format_report(report, use_color=False)
    assert "No jobs found" in output


def test_format_report_footer_counts(sample_report: AggregatedReport):
    output = format_report(sample_report, use_color=False)
    assert "1 job(s)" in output
    assert "1 server(s)" in output
    assert "10 total run(s)" in output
