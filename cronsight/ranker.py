"""Rank jobs by a given metric (failure rate, run count, last run recency)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal

from cronsight.aggregator import AggregatedReport, JobSummary

RankBy = Literal["failure_rate", "run_count", "last_run"]


class RankerError(ValueError):
    """Raised when ranking parameters are invalid."""


@dataclass
class RankedJob:
    rank: int
    command: str
    servers: List[str]
    total_runs: int
    failure_rate: float  # 0.0 – 1.0
    last_run_ts: float | None  # epoch seconds, None if never ran

    def __str__(self) -> str:  # pragma: no cover
        return (
            f"#{self.rank} {self.command} "
            f"(runs={self.total_runs}, failures={self.failure_rate:.0%})"
        )


def _failure_rate(summary: JobSummary) -> float:
    total = summary.total_runs
    if total == 0:
        return 0.0
    failed = sum(1 for e in summary.entries if not e.success)
    return failed / total


def _last_run_epoch(summary: JobSummary) -> float:
    ts = summary.last_run
    if ts is None:
        return 0.0
    return ts.timestamp()


def rank_report(
    report: AggregatedReport,
    by: RankBy = "failure_rate",
    descending: bool = True,
    limit: int | None = None,
) -> List[RankedJob]:
    """Return jobs from *report* sorted by *by* metric."""
    valid: set[RankBy] = {"failure_rate", "run_count", "last_run"}
    if by not in valid:
        raise RankerError(f"Invalid rank key '{by}'. Choose from {sorted(valid)}.")
    if limit is not None and limit < 1:
        raise RankerError("limit must be a positive integer.")

    key_fn = {
        "failure_rate": _failure_rate,
        "run_count": lambda s: float(s.total_runs),
        "last_run": _last_run_epoch,
    }[by]

    sorted_summaries = sorted(
        report.summaries.values(),
        key=key_fn,
        reverse=descending,
    )

    if limit is not None:
        sorted_summaries = sorted_summaries[:limit]

    return [
        RankedJob(
            rank=idx + 1,
            command=summary.command,
            servers=list(summary.servers),
            total_runs=summary.total_runs,
            failure_rate=_failure_rate(summary),
            last_run_ts=_last_run_epoch(summary) or None,
        )
        for idx, summary in enumerate(sorted_summaries)
    ]
