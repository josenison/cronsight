"""Detect outlier jobs based on statistical deviation from expected run frequency."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


class OutlierError(Exception):
    """Raised when outlier detection cannot be performed."""


@dataclass
class OutlierJob:
    command: str
    server: str
    total_runs: int
    success_rate: float
    z_score: float
    reason: str

    def __str__(self) -> str:
        return (
            f"{self.command} @ {self.server} "
            f"(runs={self.total_runs}, success={self.success_rate:.0%}, z={self.z_score:.2f})"
        )


@dataclass
class OutlierReport:
    outliers: List[OutlierJob] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.outliers)

    def has_outliers(self) -> bool:
        return bool(self.outliers)


def _success_rate(summary: JobSummary) -> float:
    if summary.total_runs == 0:
        return 0.0
    failures = sum(1 for e in summary.entries if not e.success)
    return 1.0 - failures / summary.total_runs


def _mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stddev(values: List[float], mean: float) -> float:
    if len(values) < 2:
        return 0.0
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return variance ** 0.5


def detect_outliers(
    report: AggregatedReport,
    z_threshold: float = 2.0,
    min_runs: int = 2,
) -> OutlierReport:
    """Return jobs whose success rate deviates significantly from the group mean."""
    if z_threshold <= 0:
        raise OutlierError("z_threshold must be positive")
    if min_runs < 1:
        raise OutlierError("min_runs must be at least 1")

    eligible = [
        (cmd, summary)
        for cmd, summary in report.jobs.items()
        if summary.total_runs >= min_runs
    ]

    if len(eligible) < 2:
        return OutlierReport()

    rates = [_success_rate(s) for _, s in eligible]
    mean = _mean(rates)
    std = _stddev(rates, mean)

    outliers: List[OutlierJob] = []
    for (cmd, summary), rate in zip(eligible, rates):
        z = (rate - mean) / std if std > 0 else 0.0
        if abs(z) >= z_threshold:
            reason = "low success rate" if z < 0 else "unusually high success rate"
            outliers.append(
                OutlierJob(
                    command=cmd,
                    server=summary.servers[0] if summary.servers else "unknown",
                    total_runs=summary.total_runs,
                    success_rate=rate,
                    z_score=z,
                    reason=reason,
                )
            )

    outliers.sort(key=lambda o: o.z_score)
    return OutlierReport(outliers=outliers)
