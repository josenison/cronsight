"""Integration tests for cadence analysis across multiple jobs and servers."""
from __future__ import annotations

from datetime import datetime, timedelta

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.cadence import analyze_cadence
from cronsight.parser import CronEntry


def _e(ts: datetime, cmd: str, server: str, status: str = "success") -> CronEntry:
    return CronEntry(timestamp=ts, command=cmd, server=server, status=status)


def _report(*summaries: JobSummary) -> AggregatedReport:
    return AggregatedReport(summaries=list(summaries))


def test_multiple_jobs_each_get_own_profile():
    base = datetime(2024, 3, 1, 0, 0)
    s1 = JobSummary(
        command="/usr/bin/alpha", server="host1",
        entries=[_e(base + timedelta(hours=i), "/usr/bin/alpha", "host1") for i in range(5)],
    )
    s2 = JobSummary(
        command="/usr/bin/beta", server="host1",
        entries=[_e(base + timedelta(hours=i * 2), "/usr/bin/beta", "host1") for i in range(5)],
    )
    result = analyze_cadence(_report(s1, s2))
    assert result.count == 2
    commands = {p.command for p in result.profiles}
    assert "/usr/bin/alpha" in commands
    assert "/usr/bin/beta" in commands


def test_regular_job_has_low_stdev():
    base = datetime(2024, 3, 1, 0, 0)
    ts = [base + timedelta(hours=i) for i in range(10)]
    s = JobSummary(
        command="/cron/regular", server="srv",
        entries=[_e(t, "/cron/regular", "srv") for t in ts],
    )
    result = analyze_cadence(_report(s))
    p = result.profiles[0]
    assert p.stdev_interval_seconds is not None
    assert p.stdev_interval_seconds < 1.0
    assert p.is_irregular is False


def test_all_irregular_jobs_counted():
    base = datetime(2024, 3, 1, 0, 0)
    # Two jobs with very uneven spacing
    def _uneven(cmd: str) -> JobSummary:
        ts = [
            base,
            base + timedelta(minutes=2),
            base + timedelta(hours=8),
            base + timedelta(hours=8, minutes=3),
            base + timedelta(hours=16),
        ]
        return JobSummary(
            command=cmd, server="s1",
            entries=[_e(t, cmd, "s1") for t in ts],
        )

    result = analyze_cadence(_report(_uneven("/a"), _uneven("/b")))
    assert result.irregular_count == 2


def test_empty_report_returns_empty_cadence_report():
    result = analyze_cadence(_report())
    assert result.count == 0
    assert result.irregular_count == 0


def test_mean_interval_reflects_actual_spacing():
    base = datetime(2024, 3, 1, 0, 0)
    ts = [base + timedelta(hours=i) for i in range(4)]  # 3 intervals of 3600s
    s = JobSummary(
        command="/cron/hourly", server="srv",
        entries=[_e(t, "/cron/hourly", "srv") for t in ts],
    )
    result = analyze_cadence(_report(s))
    assert result.profiles[0].mean_interval_seconds == 3600.0
