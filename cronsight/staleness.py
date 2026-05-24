"""Staleness detector: flags jobs that haven't run recently relative to their schedule."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.scheduler import next_run, prev_run, ScheduleError


class StalenessError(Exception):
    """Raised when staleness detection fails."""


@dataclass
class StaleJob:
    command: str
    server: str
    last_run: Optional[datetime]
    expected_after: Optional[datetime]
    staleness_seconds: float

    def __str__(self) -> str:
        last = self.last_run.isoformat() if self.last_run else "never"
        return f"{self.command} on {self.server} (last run: {last}, stale by {self.staleness_seconds:.0f}s)"


@dataclass
class StalenessReport:
    stale_jobs: List[StaleJob] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.stale_jobs)

    @property
    def has_stale(self) -> bool:
        return self.count > 0


def _staleness_seconds(
    summary: JobSummary,
    expression: str,
    now: datetime,
) -> Optional[float]:
    """Return how many seconds overdue the job is, or None if not stale."""
    try:
        expected = prev_run(expression, now)
    except ScheduleError:
        return None

    last = summary.last_run
    if last is None:
        # Never ran — stale since the first expected run
        return (now - expected).total_seconds()

    if last < expected:
        return (expected - last).total_seconds()

    return None


def detect_stale(
    report: AggregatedReport,
    schedules: dict[str, str],
    now: Optional[datetime] = None,
    threshold_seconds: float = 0.0,
) -> StalenessReport:
    """Detect jobs that are overdue based on their cron expression.

    Args:
        report: Aggregated job report.
        schedules: Mapping of command -> cron expression.
        now: Reference time (defaults to UTC now).
        threshold_seconds: Minimum staleness in seconds before flagging.

    Returns:
        StalenessReport containing all stale jobs.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    stale: List[StaleJob] = []

    for command, summary in report.jobs.items():
        expression = schedules.get(command)
        if expression is None:
            continue

        seconds = _staleness_seconds(summary, expression, now)
        if seconds is None or seconds <= threshold_seconds:
            continue

        try:
            expected_after = prev_run(expression, now)
        except ScheduleError:
            expected_after = None

        stale.append(
            StaleJob(
                command=command,
                server=summary.servers[0] if summary.servers else "unknown",
                last_run=summary.last_run,
                expected_after=expected_after,
                staleness_seconds=seconds,
            )
        )

    stale.sort(key=lambda j: j.staleness_seconds, reverse=True)
    return StalenessReport(stale_jobs=stale)
