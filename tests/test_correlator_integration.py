"""Integration tests for correlator across realistic multi-server data."""
from __future__ import annotations

from datetime import datetime

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.correlator import correlate_reports


def _e(cmd: str, status: str, hour: int = 10, server: str = "srv") -> CronEntry:
    ts = datetime(2024, 3, 1, hour, 0, 0)
    return CronEntry(timestamp=ts, command=cmd, status=status, server=server)


def _report(*summaries: JobSummary) -> AggregatedReport:
    return AggregatedReport(jobs={s.command: s for s in summaries})


def test_three_servers_same_job_all_consistent():
    reports = {
        "s1": _report(JobSummary("nightly.sh", [_e("nightly.sh", "success", server="s1")])),
        "s2": _report(JobSummary("nightly.sh", [_e("nightly.sh", "success", server="s2")])),
        "s3": _report(JobSummary("nightly.sh", [_e("nightly.sh", "success", server="s3")])),
    }
    result = correlate_reports(reports)
    assert len(result.correlations) == 1
    assert result.correlations[0].consistent is True
    assert len(result.correlations[0].servers) == 3
    assert result.correlations[0].total_runs == 3


def test_unique_jobs_per_server_all_listed():
    reports = {
        "s1": _report(JobSummary("alpha.sh", [_e("alpha.sh", "success")])),
        "s2": _report(JobSummary("beta.sh", [_e("beta.sh", "success")])),
    }
    result = correlate_reports(reports)
    commands = {c.command for c in result.correlations}
    assert commands == {"alpha.sh", "beta.sh"}


def test_failure_count_reflects_failed_entries():
    entries = [
        _e("job.sh", "success"),
        _e("job.sh", "failure"),
        _e("job.sh", "failure"),
    ]
    reports = {"s1": _report(JobSummary("job.sh", entries))}
    result = correlate_reports(reports)
    corr = result.correlations[0]
    assert corr.total_runs == 3
    assert corr.total_failures == 2


def test_no_inconsistent_jobs_when_all_agree():
    s1 = JobSummary("x.sh", [_e("x.sh", "success")])
    s2 = JobSummary("x.sh", [_e("x.sh", "success")])
    result = correlate_reports({"a": _report(s1), "b": _report(s2)})
    assert result.inconsistent_jobs == []


def test_mixed_jobs_only_shared_job_is_inconsistent():
    shared_ok = JobSummary("shared.sh", [_e("shared.sh", "success")])
    shared_fail = JobSummary("shared.sh", [_e("shared.sh", "failure")])
    only_a = JobSummary("only_a.sh", [_e("only_a.sh", "success")])
    result = correlate_reports(
        {"a": _report(shared_ok, only_a), "b": _report(shared_fail)}
    )
    inconsistent_cmds = {c.command for c in result.inconsistent_jobs}
    assert "shared.sh" in inconsistent_cmds
    assert "only_a.sh" not in inconsistent_cmds
