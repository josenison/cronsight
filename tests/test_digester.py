"""Tests for cronsight.digester."""
from datetime import datetime, timedelta

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.digester import (
    DigestEntry,
    DigestReport,
    DigesterError,
    build_digest,
)

_NOW = datetime(2024, 6, 15, 12, 0, 0)


def _entry(cmd: str, exit_code: int, hours_ago: float) -> CronEntry:
    return CronEntry(
        command=cmd,
        exit_code=exit_code,
        timestamp=_NOW - timedelta(hours=hours_ago),
        server="host1",
    )


def _make_report(*summaries: JobSummary) -> AggregatedReport:
    return AggregatedReport(jobs={s.command: s for s in summaries})


def _summary(cmd: str, entries):
    servers = {e.server for e in entries}
    return JobSummary(command=cmd, entries=entries, servers=servers)


# --- DigestEntry ---

def test_digest_entry_success_rate_all_pass():
    e = DigestEntry("backup.sh", 4, 4, 0, ["h1"], _NOW)
    assert e.success_rate == 1.0


def test_digest_entry_success_rate_mixed():
    e = DigestEntry("backup.sh", 4, 2, 2, ["h1"], _NOW)
    assert e.success_rate == 0.5


def test_digest_entry_success_rate_zero_runs():
    e = DigestEntry("backup.sh", 0, 0, 0, [], None)
    assert e.success_rate == 0.0


def test_digest_entry_str_contains_command():
    e = DigestEntry("cleanup.sh", 3, 3, 0, ["h1"], _NOW)
    assert "cleanup.sh" in str(e)


def test_digest_entry_str_never_when_no_last_run():
    e = DigestEntry("cleanup.sh", 0, 0, 0, [], None)
    assert "never" in str(e)


# --- build_digest ---

def test_build_digest_daily_includes_recent_entries():
    s = _summary("job.sh", [_entry("job.sh", 0, 2), _entry("job.sh", 0, 25)])
    report = _make_report(s)
    digest = build_digest(report, period="daily", now=_NOW)
    assert digest.total_jobs == 1
    assert digest.entries[0].total_runs == 1  # only within 24h


def test_build_digest_weekly_includes_older_entries():
    s = _summary("job.sh", [_entry("job.sh", 0, 2), _entry("job.sh", 0, 100)])
    report = _make_report(s)
    digest = build_digest(report, period="weekly", now=_NOW)
    assert digest.entries[0].total_runs == 2


def test_build_digest_excludes_jobs_with_no_matching_entries():
    s = _summary("old.sh", [_entry("old.sh", 0, 200)])
    report = _make_report(s)
    digest = build_digest(report, period="daily", now=_NOW)
    assert digest.total_jobs == 0


def test_build_digest_sorted_by_failure_count_descending():
    s1 = _summary("good.sh", [_entry("good.sh", 0, 1)])
    s2 = _summary("bad.sh", [_entry("bad.sh", 1, 1), _entry("bad.sh", 1, 2)])
    report = _make_report(s1, s2)
    digest = build_digest(report, period="daily", now=_NOW)
    assert digest.entries[0].command == "bad.sh"


def test_build_digest_failing_jobs_property():
    s1 = _summary("ok.sh", [_entry("ok.sh", 0, 1)])
    s2 = _summary("fail.sh", [_entry("fail.sh", 1, 1)])
    report = _make_report(s1, s2)
    digest = build_digest(report, period="daily", now=_NOW)
    assert len(digest.failing_jobs) == 1
    assert digest.failing_jobs[0].command == "fail.sh"


def test_build_digest_invalid_period_raises():
    report = _make_report()
    with pytest.raises(DigesterError, match="Unknown period"):
        build_digest(report, period="monthly", now=_NOW)


def test_build_digest_period_bounds():
    report = _make_report()
    digest = build_digest(report, period="daily", now=_NOW)
    assert digest.period_end == _NOW
    assert digest.period_start == _NOW - __import__("datetime").timedelta(days=1)
