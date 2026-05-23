"""Tests for cronsight.filter."""

from __future__ import annotations

from datetime import datetime

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.filter import FilterCriteria, filter_report, matches


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def summaries() -> list[JobSummary]:
    base = datetime(2024, 1, 15, 8, 0, 0)
    return [
        JobSummary(
            command="/usr/bin/backup.sh",
            server="web-01",
            total_runs=10,
            successful_runs=10,
            failed_runs=0,
            last_run=base,
            first_run=base,
        ),
        JobSummary(
            command="/usr/bin/cleanup.sh",
            server="web-01",
            total_runs=5,
            successful_runs=2,
            failed_runs=3,
            last_run=base,
            first_run=base,
        ),
        JobSummary(
            command="/usr/bin/report.sh",
            server="db-01",
            total_runs=3,
            successful_runs=3,
            failed_runs=0,
            last_run=base,
            first_run=base,
        ),
    ]


@pytest.fixture()
def report(summaries: list[JobSummary]) -> AggregatedReport:
    return AggregatedReport(summaries=summaries)


# ---------------------------------------------------------------------------
# matches()
# ---------------------------------------------------------------------------


def test_matches_no_criteria_returns_true(summaries: list[JobSummary]) -> None:
    criteria = FilterCriteria()
    assert all(matches(s, criteria) for s in summaries)


def test_matches_server_filter(summaries: list[JobSummary]) -> None:
    criteria = FilterCriteria(server="db-01")
    result = [s for s in summaries if matches(s, criteria)]
    assert len(result) == 1
    assert result[0].server == "db-01"


def test_matches_min_runs(summaries: list[JobSummary]) -> None:
    criteria = FilterCriteria(min_runs=6)
    result = [s for s in summaries if matches(s, criteria)]
    assert len(result) == 1
    assert result[0].command == "/usr/bin/backup.sh"


def test_matches_failed_only(summaries: list[JobSummary]) -> None:
    criteria = FilterCriteria(failed_only=True)
    result = [s for s in summaries if matches(s, criteria)]
    assert len(result) == 1
    assert result[0].command == "/usr/bin/cleanup.sh"


def test_matches_command_contains(summaries: list[JobSummary]) -> None:
    criteria = FilterCriteria(command_contains="backup")
    result = [s for s in summaries if matches(s, criteria)]
    assert len(result) == 1


def test_matches_max_success_rate_excludes_perfect(summaries: list[JobSummary]) -> None:
    # Only jobs with success rate <= 0.5 should pass
    criteria = FilterCriteria(max_success_rate=0.5)
    result = [s for s in summaries if matches(s, criteria)]
    assert all(s.failed_runs > 0 for s in result)


# ---------------------------------------------------------------------------
# filter_report()
# ---------------------------------------------------------------------------


def test_filter_report_returns_new_report(report: AggregatedReport) -> None:
    filtered = filter_report(report, FilterCriteria(server="web-01"))
    assert isinstance(filtered, AggregatedReport)
    assert len(filtered.summaries) == 2


def test_filter_report_empty_when_no_match(report: AggregatedReport) -> None:
    filtered = filter_report(report, FilterCriteria(server="nonexistent"))
    assert filtered.summaries == []


def test_filter_report_does_not_mutate_original(report: AggregatedReport) -> None:
    original_count = len(report.summaries)
    filter_report(report, FilterCriteria(failed_only=True))
    assert len(report.summaries) == original_count
