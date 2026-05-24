"""Tests for cronsight.sampler."""

from __future__ import annotations

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.sampler import SamplerError, SampledJob, SampleReport, sample_report


def _entry(cmd: str, exit_code: int = 0, ts: str = "2024-01-01T10:00:00") -> CronEntry:
    return CronEntry(timestamp=ts, command=cmd, exit_code=exit_code, server="srv1")


def _summary(cmd: str, entries) -> JobSummary:
    s = JobSummary(command=cmd, server="srv1")
    for e in entries:
        s.entries.append(e)
    return s


@pytest.fixture
def report():
    entries_a = [_entry("job_a", exit_code=0)] * 8 + [_entry("job_a", exit_code=1)] * 2
    entries_b = [_entry("job_b", exit_code=0)] * 5
    summaries = [
        _summary("job_a", entries_a),
        _summary("job_b", entries_b),
    ]
    r = AggregatedReport()
    r.summaries = summaries
    return r


def test_sample_report_returns_sample_report(report):
    result = sample_report(report, n=5, seed=42)
    assert isinstance(result, SampleReport)


def test_sample_report_count_matches_jobs(report):
    result = sample_report(report, n=5, seed=42)
    assert result.count == 2


def test_sample_report_respects_n(report):
    result = sample_report(report, n=3, seed=0)
    for job in result.jobs:
        assert job.sampled_runs <= 3


def test_sample_report_n_larger_than_entries(report):
    # job_b only has 5 entries; requesting 20 should return all 5
    result = sample_report(report, n=20, seed=0)
    job_b = next(j for j in result.jobs if j.command == "job_b")
    assert job_b.sampled_runs == 5
    assert job_b.total_runs == 5


def test_sample_report_stores_seed(report):
    result = sample_report(report, n=5, seed=99)
    assert result.seed == 99


def test_sample_report_stores_sample_size(report):
    result = sample_report(report, n=7, seed=1)
    assert result.sample_size == 7


def test_sample_report_reproducible_with_seed(report):
    r1 = sample_report(report, n=5, seed=42)
    r2 = sample_report(report, n=5, seed=42)
    for j1, j2 in zip(r1.jobs, r2.jobs):
        assert j1.sampled_runs == j2.sampled_runs
        assert j1.success_count == j2.success_count


def test_sample_report_raises_on_zero_n(report):
    with pytest.raises(SamplerError):
        sample_report(report, n=0)


def test_sample_report_raises_on_negative_n(report):
    with pytest.raises(SamplerError):
        sample_report(report, n=-3)


def test_sampled_job_success_rate(report):
    result = sample_report(report, n=10, seed=42)
    job_a = next(j for j in result.jobs if j.command == "job_a")
    assert 0.0 <= job_a.success_rate <= 1.0


def test_sampled_job_str_contains_command(report):
    result = sample_report(report, n=5, seed=42)
    job_a = next(j for j in result.jobs if j.command == "job_a")
    assert "job_a" in str(job_a)
