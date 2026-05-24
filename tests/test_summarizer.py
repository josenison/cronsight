"""Tests for cronsight.summarizer."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.summarizer import (
    SummaryLine,
    build_summary_lines,
    render_text_summary,
)


def _entry(exit_code: int, ts: datetime | None = None) -> CronEntry:
    return CronEntry(
        timestamp=ts or datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
        command="/usr/bin/backup",
        exit_code=exit_code,
    )


def _summary(entries, server="web-01") -> JobSummary:
    last = max((e.timestamp for e in entries), default=None) if entries else None
    first = min((e.timestamp for e in entries), default=None) if entries else None
    return JobSummary(
        command="/usr/bin/backup",
        server=server,
        entries=entries,
        total_runs=len(entries),
        last_run=last,
        first_run=first,
    )


@pytest.fixture
def sample_report():
    s1 = _summary([_entry(0), _entry(0), _entry(1)], server="web-01")
    s2 = _summary([_entry(1), _entry(1)], server="db-01")
    return AggregatedReport(
        jobs={
            "web-01::/usr/bin/backup": s1,
            "db-01::/usr/bin/backup": s2,
        }
    )


def test_build_summary_lines_returns_one_per_job(sample_report):
    lines = build_summary_lines(sample_report)
    assert len(lines) == 2


def test_build_summary_line_fields(sample_report):
    lines = build_summary_lines(sample_report)
    web_line = next(l for l in lines if l.server == "web-01")
    assert web_line.job == "/usr/bin/backup"
    assert web_line.total_runs == 3


def test_success_rate_calculated_correctly(sample_report):
    lines = build_summary_lines(sample_report)
    web_line = next(l for l in lines if l.server == "web-01")
    assert abs(web_line.success_rate - 2 / 3) < 1e-6


def test_last_status_reflects_final_entry(sample_report):
    lines = build_summary_lines(sample_report)
    web_line = next(l for l in lines if l.server == "web-01")
    assert web_line.last_status == "fail"


def test_all_passing_last_status_ok():
    s = _summary([_entry(0), _entry(0)])
    report = AggregatedReport(jobs={"web-01::/usr/bin/backup": s})
    lines = build_summary_lines(report)
    assert lines[0].last_status == "ok"


def test_render_text_summary_contains_server(sample_report):
    text = render_text_summary(sample_report)
    assert "web-01" in text
    assert "db-01" in text


def test_render_text_summary_empty_report():
    empty = AggregatedReport(jobs={})
    text = render_text_summary(empty)
    assert text == "No jobs found."


def test_summary_line_str_format():
    line = SummaryLine(
        job="/usr/bin/backup",
        server="web-01",
        total_runs=5,
        success_rate=0.8,
        last_status="ok",
        last_run="2024-06-01 12:00:00",
    )
    s = str(line)
    assert "web-01" in s
    assert "80%" in s
    assert "runs: 5" in s
