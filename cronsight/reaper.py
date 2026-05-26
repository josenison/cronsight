"""Reaper: detect and report jobs that have not run within their expected window."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


class ReaperError(Exception):
    """Raised when reaper configuration or execution fails."""


@dataclass
class DeadJob:
    command: str
    server: str
    last_run: Optional[datetime]
    expected_interval_hours: float
    hours_overdue: float

    def __str__(self) -> str:
        last = self.last_run.isoformat() if self.last_run else "never"
        return (
            f"{self.command} on {self.server} | last_run={last} | "
            f"overdue={self.hours_overdue:.1f}h"
        )


@dataclass
class ReaperReport:
    dead_jobs: List[DeadJob] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.dead_jobs)

    @property
    def has_dead_jobs(self) -> bool:
        return self.count > 0


def _hours_since(dt: Optional[datetime], now: datetime) -> Optional[float]:
    if dt is None:
        return None
    delta = now - dt
    return delta.total_seconds() / 3600.0


def reap(
    report: AggregatedReport,
    expected_interval_hours: float,
    pattern: Optional[str] = None,
    now: Optional[datetime] = None,
) -> ReaperReport:
    """Find jobs that have not run within *expected_interval_hours*."""
    if expected_interval_hours <= 0:
        raise ReaperError("expected_interval_hours must be positive")

    compiled = None
    if pattern:
        try:
            compiled = re.compile(pattern)
        except re.error as exc:
            raise ReaperError(f"Invalid pattern: {exc}") from exc

    reference = now or datetime.utcnow()
    dead: List[DeadJob] = []

    for command, summary in report.jobs.items():
        if compiled and not compiled.search(command):
            continue
        hours = _hours_since(summary.last_run, reference)
        if hours is None or hours > expected_interval_hours:
            overdue = (
                hours - expected_interval_hours if hours is not None else float("inf")
            )
            server = next(iter(summary.servers), "unknown")
            dead.append(
                DeadJob(
                    command=command,
                    server=server,
                    last_run=summary.last_run,
                    expected_interval_hours=expected_interval_hours,
                    hours_overdue=overdue,
                )
            )

    dead.sort(key=lambda j: j.hours_overdue, reverse=True)
    return ReaperReport(dead_jobs=dead)
