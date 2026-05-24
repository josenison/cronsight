"""Tests for cronsight.grouper."""

from __future__ import annotations

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.grouper import GroupedReport, GrouperError, JobGroup, group_report
from cronsight.parser import CronEntry


def _make_entry(exit_code: int = 0) -> CronEntry:
    return CronEntry(
        timestamp="2024-01-15 08:00:00",
        command="/usr/bin/backup",
        exit_code=exit_code,
        raw="raw line",
    )


def _make_summary(
    command: str = "/usr/bin/backup",
    server: str = "web-01",
    exit_code: int = 0,
) -> JobSummary:
    entry = _make_entry(exit_code=exit_code)
    return JobSummary(
        command=command,
        server=server,
        entries=[entry],
    )


def _make_report(*summaries: JobSummary) -> AggregatedReport:
    report = AggregatedReport()
    for s in summaries:
        report.jobs[f"{s.server}:{s.command}"] = s
    return report


def test_group_by_server_creates_groups():
    report = _make_report(
        _make_summary(server="web-01"),
        _make_summary(server="web-02"),
        _make_summary(command="/usr/bin/sync", server="web-01"),
    )
    grouped = group_report(report, "server")
    assert grouped.key == "server"
    assert set(grouped.groups.keys()) == {"web-01", "web-02"}


def test_group_by_server_counts_jobs_correctly():
    report = _make_report(
        _make_summary(server="web-01"),
        _make_summary(command="/usr/bin/sync", server="web-01"),
        _make_summary(server="db-01"),
    )
    grouped = group_report(report, "server")
    assert grouped.groups["web-01"].job_count == 2
    assert grouped.groups["db-01"].job_count == 1


def test_group_by_command():
    report = _make_report(
        _make_summary(command="/usr/bin/backup", server="web-01"),
        _make_summary(command="/usr/bin/backup", server="web-02"),
        _make_summary(command="/usr/bin/sync", server="web-01"),
    )
    grouped = group_report(report, "command")
    assert set(grouped.groups.keys()) == {"/usr/bin/backup", "/usr/bin/sync"}
    assert grouped.groups["/usr/bin/backup"].job_count == 2


def test_group_by_status_success_and_failure():
    report = _make_report(
        _make_summary(exit_code=0),
        _make_summary(command="/usr/bin/sync", exit_code=1),
    )
    grouped = group_report(report, "status")
    assert "success" in grouped.groups
    assert "failure" in grouped.groups


def test_group_by_invalid_key_raises():
    report = _make_report(_make_summary())
    with pytest.raises(GrouperError, match="Unsupported grouping key"):
        group_report(report, "nonexistent")


def test_group_names_are_sorted():
    report = _make_report(
        _make_summary(server="z-server"),
        _make_summary(command="/sync", server="a-server"),
    )
    grouped = group_report(report, "server")
    assert grouped.group_names() == ["a-server", "z-server"]


def test_total_runs_aggregated_per_group():
    s1 = _make_summary(server="web-01")


def test_empty_report_produces_no_groups():
    """Grouping an empty report should return a GroupedReport with no groups."""
    report = AggregatedReport()
    grouped = group_report(report, "server")
    assert grouped.groups == {}
    assert grouped.group_names() == []
