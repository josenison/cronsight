"""Audit trail: detect jobs that have gone silent (no recent runs)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


class AuditorError(Exception):
    """Raised when auditor inputs are invalid."""


@dataclass
class SilentJob:
    command: str
    server: str
    last_run: Optional[datetime]
    hours_since_last_run: Optional[float]

    def __str__(self) -> str:
        if self.hours_since_last_run is None:
            return f"{self.command} on {self.server} — never ran"
        return (
            f"{self.command} on {self.server} — "
            f"silent for {self.hours_since_last_run:.1f}h"
        )


@dataclass
class AuditReport:
    silent_jobs: List[SilentJob] = field(default_factory=list)
    threshold_hours: float = 24.0

    @property
    def count(self) -> int:
        return len(self.silent_jobs)

    @property
    def has_silent_jobs(self) -> bool:
        return bool(self.silent_jobs)


def _hours_since(ts: Optional[datetime], now: datetime) -> Optional[float]:
    if ts is None:
        return None
    delta = now - ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else now - ts
    return delta.total_seconds() / 3600.0


def audit_report(
    report: AggregatedReport,
    threshold_hours: float = 24.0,
    now: Optional[datetime] = None,
) -> AuditReport:
    """Return an AuditReport listing jobs silent longer than *threshold_hours*."""
    if threshold_hours <= 0:
        raise AuditorError("threshold_hours must be positive")

    now = now or datetime.now(tz=timezone.utc)
    silent: List[SilentJob] = []

    for command, summary in report.jobs.items():
        last = summary.last_run
        hours = _hours_since(last, now)
        if hours is None or hours >= threshold_hours:
            silent.append(
                SilentJob(
                    command=command,
                    server=summary.servers[0] if summary.servers else "unknown",
                    last_run=last,
                    hours_since_last_run=hours,
                )
            )

    silent.sort(key=lambda j: (j.hours_since_last_run is None, -(j.hours_since_last_run or 0)))
    return AuditReport(silent_jobs=silent, threshold_hours=threshold_hours)
