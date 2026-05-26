"""Tests for cronsight.highlighter."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.highlighter import (
    HighlighterError,
    HighlightRule,
    HighlightedJob,
    highlight_report,
)


def _entry(cmd: str, success: bool = True) -> CronEntry:
    return CronEntry(
        timestamp=datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc),
        command=cmd,
        success=success,
        server="srv1",
    )


def _make_summary(cmd: str, entries=None) -> JobSummary:
    if entries is None:
        entries = [_entry(cmd)]
    return JobSummary(command=cmd, entries=entries)


@pytest.fixture
def report() -> AggregatedReport:
    jobs = {
        "backup.sh": _make_summary("backup.sh"),
        "/usr/bin/cleanup": _make_summary("/usr/bin/cleanup"),
        "rotate_logs": _make_summary("rotate_logs"),
    }
    return AggregatedReport(jobs=jobs)


def test_highlight_rule_empty_pattern_raises():
    with pytest.raises(HighlighterError, match="pattern"):
        HighlightRule(pattern="", label="critical")


def test_highlight_rule_empty_label_raises():
    with pytest.raises(HighlighterError, match="label"):
        HighlightRule(pattern="backup", label="")


def test_highlight_rule_invalid_color_raises():
    with pytest.raises(HighlighterError, match="color"):
        HighlightRule(pattern="backup", label="x", color="purple")


def test_highlight_rule_invalid_regex_raises():
    with pytest.raises(HighlighterError, match="invalid regex"):
        HighlightRule(pattern="[unclosed", label="bad")


def test_highlight_report_no_rules_raises(report):
    with pytest.raises(HighlighterError, match="at least one"):
        highlight_report(report, rules=[])


def test_highlight_report_returns_all_jobs_by_default(report):
    rules = [HighlightRule(pattern="backup", label="important")]
    result = highlight_report(report, rules)
    assert result.count == 3


def test_highlight_report_matches_pattern(report):
    rules = [HighlightRule(pattern="backup", label="important")]
    result = highlight_report(report, rules)
    highlighted = [j for j in result.jobs if j.is_highlighted]
    assert len(highlighted) == 1
    assert highlighted[0].summary.command == "backup.sh"
    assert "important" in highlighted[0].labels


def test_highlight_report_highlighted_only_flag(report):
    rules = [HighlightRule(pattern="rotate", label="log-related")]
    result = highlight_report(report, rules, highlighted_only=True)
    assert result.count == 1
    assert result.jobs[0].summary.command == "rotate_logs"


def test_highlight_report_multiple_rules_accumulate_labels(report):
    rules = [
        HighlightRule(pattern="backup", label="backup"),
        HighlightRule(pattern=r"\.sh$", label="shell-script"),
    ]
    result = highlight_report(report, rules)
    job = next(j for j in result.jobs if j.summary.command == "backup.sh")
    assert "backup" in job.labels
    assert "shell-script" in job.labels


def test_highlighted_count_reflects_matched_jobs(report):
    rules = [HighlightRule(pattern="cleanup|rotate", label="maintenance")]
    result = highlight_report(report, rules)
    assert result.highlighted_count == 2


def test_highlighted_job_str_includes_labels():
    summary = _make_summary("backup.sh")
    job = HighlightedJob(summary=summary, labels=["critical", "backup"])
    assert "backup.sh" in str(job)
    assert "critical" in str(job)
    assert "backup" in str(job)


def test_highlighted_job_str_shows_dash_when_no_labels():
    summary = _make_summary("backup.sh")
    job = HighlightedJob(summary=summary, labels=[])
    assert "—" in str(job)
