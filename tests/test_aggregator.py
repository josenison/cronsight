"""Tests for cronsight.aggregator module."""

from datetime import datetime
from unittest.mock import patch

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary, aggregate_results
from cronsight.collector import CollectionResult
from cronsight.parser import CronEntry


SAMPLE_LOG = """
CRON[1234]: (root) CMD (/usr/bin/backup.sh)
CRON[1235]: (root) CMD (/usr/bin/backup.sh)
CRON[1236]: (www-data) CMD (/usr/bin/cleanup.sh)
"""


@pytest.fixture
def success_result():
    return CollectionResult(
        server="web-01",
        success=True,
        output=SAMPLE_LOG,
        error=None,
    )


@pytest.fixture
def failed_result():
    return CollectionResult(
        server="db-01",
        success=False,
        output=None,
        error="Connection refused",
    )


def test_aggregate_results_parses_entries(success_result):
    report = aggregate_results([success_result])
    assert report.total_jobs == 2
    commands = {s.command for s in report.summaries}
    assert "/usr/bin/backup.sh" in commands
    assert "/usr/bin/cleanup.sh" in commands


def test_aggregate_results_counts_runs(success_result):
    report = aggregate_results([success_result])
    backup = next(s for s in report.summaries if "backup" in s.command)
    assert backup.total_runs == 2


def test_aggregate_results_records_server(success_result):
    report = aggregate_results([success_result])
    assert all(s.server == "web-01" for s in report.summaries)


def test_aggregate_results_failed_server(failed_result):
    report = aggregate_results([failed_result])
    assert report.total_jobs == 0
    assert len(report.errors) == 1
    assert "db-01" in report.errors[0]
    assert "Connection refused" in report.errors[0]


def test_aggregate_results_mixed(success_result, failed_result):
    report = aggregate_results([success_result, failed_result])
    assert report.total_jobs == 2
    assert len(report.errors) == 1
    assert report.total_servers == 1


def test_aggregate_empty_results():
    report = aggregate_results([])
    assert report.total_jobs == 0
    assert report.errors == []


def test_job_summary_last_run():
    ts1 = datetime(2024, 1, 1, 10, 0)
    ts2 = datetime(2024, 1, 1, 12, 0)
    entries = [
        CronEntry(timestamp=ts1, user="root", command="/bin/job", raw=""),
        CronEntry(timestamp=ts2, user="root", command="/bin/job", raw=""),
    ]
    summary = JobSummary(command="/bin/job", server="srv", runs=entries)
    assert summary.last_run == ts2
    assert summary.first_run == ts1
