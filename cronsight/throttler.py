"""Rate-limiting and throttle detection for cron job execution history."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


class ThrottlerError(Exception):
    """Raised when throttle detection configuration is invalid."""


@dataclass
class ThrottleViolation:
    command: str
    server: str
    run_count: int
    window_minutes: int
    threshold: int

    def __str__(self) -> str:
        return (
            f"{self.command} on {self.server}: "
            f"{self.run_count} runs in {self.window_minutes}m "
            f"(threshold={self.threshold})"
        )


@dataclass
class ThrottleReport:
    violations: List[ThrottleViolation] = field(default_factory=list)

    @property
    def has_violations(self) -> bool:
        return len(self.violations) > 0

    @property
    def violation_count(self) -> int:
        return len(self.violations)


def _runs_in_window(
    summary: JobSummary, window_minutes: int, reference: Optional[datetime] = None
) -> int:
    """Count executions within the trailing window."""
    if reference is None:
        reference = datetime.utcnow()
    cutoff = reference - timedelta(minutes=window_minutes)
    return sum(
        1 for entry in summary.entries if entry.timestamp and entry.timestamp >= cutoff
    )


def detect_throttle_violations(
    report: AggregatedReport,
    threshold: int,
    window_minutes: int,
    reference: Optional[datetime] = None,
) -> ThrottleReport:
    """Return a ThrottleReport listing jobs that exceeded *threshold* runs
    within *window_minutes* minutes."""
    if threshold < 1:
        raise ThrottlerError("threshold must be >= 1")
    if window_minutes < 1:
        raise ThrottlerError("window_minutes must be >= 1")

    violations: List[ThrottleViolation] = []
    for summary in report.jobs.values():
        count = _runs_in_window(summary, window_minutes, reference)
        if count > threshold:
            violations.append(
                ThrottleViolation(
                    command=summary.command,
                    server=summary.server,
                    run_count=count,
                    window_minutes=window_minutes,
                    threshold=threshold,
                )
            )
    return ThrottleReport(violations=violations)
