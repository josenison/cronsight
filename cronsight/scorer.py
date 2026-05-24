"""Job reliability scorer — assigns a numeric reliability score to each job summary."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


class ScorerError(Exception):
    """Raised when scoring configuration is invalid."""


@dataclass
class ScoredJob:
    command: str
    server: str
    score: float  # 0.0 (worst) – 100.0 (perfect)
    total_runs: int
    success_rate: float
    has_recent_failure: bool

    def __str__(self) -> str:
        return f"{self.command}@{self.server}  score={self.score:.1f}"


@dataclass
class ScoredReport:
    jobs: List[ScoredJob] = field(default_factory=list)

    @property
    def lowest_score(self) -> Optional[ScoredJob]:
        return min(self.jobs, key=lambda j: j.score, default=None)

    @property
    def highest_score(self) -> Optional[ScoredJob]:
        return max(self.jobs, key=lambda j: j.score, default=None)


def _success_rate(summary: JobSummary) -> float:
    if summary.total_runs == 0:
        return 0.0
    ok = sum(1 for e in summary.entries if e.exit_code == 0)
    return ok / summary.total_runs


def _has_recent_failure(summary: JobSummary) -> bool:
    """Return True if the most recent entry is a failure."""
    if not summary.entries:
        return False
    latest = max(summary.entries, key=lambda e: e.timestamp)
    return latest.exit_code != 0


def _compute_score(rate: float, has_recent_failure: bool, total_runs: int) -> float:
    """Weighted score: success rate contributes 80 pts, recency penalty 10 pts,
    run-count bonus up to 10 pts."""
    base = rate * 80.0
    recency_penalty = 10.0 if has_recent_failure else 0.0
    run_bonus = min(total_runs / 10.0, 10.0)  # caps at 10 runs
    return max(0.0, base - recency_penalty + run_bonus)


def score_report(report: AggregatedReport) -> ScoredReport:
    """Score every job in *report* and return a ScoredReport."""
    scored: List[ScoredJob] = []
    for summary in report.jobs.values():
        rate = _success_rate(summary)
        recent_fail = _has_recent_failure(summary)
        s = _compute_score(rate, recent_fail, summary.total_runs)
        scored.append(
            ScoredJob(
                command=summary.command,
                server=summary.server,
                score=round(s, 2),
                total_runs=summary.total_runs,
                success_rate=round(rate, 4),
                has_recent_failure=recent_fail,
            )
        )
    scored.sort(key=lambda j: j.score)
    return ScoredReport(jobs=scored)
