"""sampler.py — Extract a statistical sample of job execution entries from a report."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


class SamplerError(Exception):
    """Raised when sampling parameters are invalid."""


@dataclass
class SampledJob:
    command: str
    server: str
    sampled_runs: int
    total_runs: int
    success_count: int

    @property
    def success_rate(self) -> float:
        if self.sampled_runs == 0:
            return 0.0
        return self.success_count / self.sampled_runs

    def __str__(self) -> str:
        return (
            f"{self.command} [{self.server}] "
            f"{self.sampled_runs}/{self.total_runs} sampled "
            f"({self.success_rate:.0%} ok)"
        )


@dataclass
class SampleReport:
    jobs: List[SampledJob] = field(default_factory=list)
    sample_size: int = 0
    seed: Optional[int] = None

    @property
    def count(self) -> int:
        return len(self.jobs)


def _sample_summary(
    summary: JobSummary,
    n: int,
    rng: random.Random,
) -> SampledJob:
    entries = list(summary.entries)
    sampled = rng.sample(entries, min(n, len(entries)))
    success_count = sum(1 for e in sampled if e.exit_code == 0)
    return SampledJob(
        command=summary.command,
        server=summary.server,
        sampled_runs=len(sampled),
        total_runs=summary.total_runs,
        success_count=success_count,
    )


def sample_report(
    report: AggregatedReport,
    n: int,
    seed: Optional[int] = None,
) -> SampleReport:
    """Return a SampleReport with up to *n* entries sampled per job."""
    if n <= 0:
        raise SamplerError("sample size n must be a positive integer")

    rng = random.Random(seed)
    jobs = [
        _sample_summary(summary, n, rng)
        for summary in report.summaries
    ]
    return SampleReport(jobs=jobs, sample_size=n, seed=seed)
