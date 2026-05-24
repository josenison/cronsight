"""Digest module: produce a human-readable daily/weekly digest of job activity."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


class DigesterError(Exception):
    """Raised when digest generation fails."""


@dataclass
class DigestEntry:
    command: str
    total_runs: int
    success_count: int
    failure_count: int
    servers: List[str]
    last_run: Optional[datetime]

    @property
    def success_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return self.success_count / self.total_runs

    def __str__(self) -> str:
        rate = f"{self.success_rate * 100:.0f}%"
        last = self.last_run.strftime("%Y-%m-%d %H:%M") if self.last_run else "never"
        return f"{self.command}  runs={self.total_runs}  ok={rate}  last={last}"


@dataclass
class DigestReport:
    period_start: datetime
    period_end: datetime
    entries: List[DigestEntry] = field(default_factory=list)

    @property
    def total_jobs(self) -> int:
        return len(self.entries)

    @property
    def failing_jobs(self) -> List[DigestEntry]:
        return [e for e in self.entries if e.failure_count > 0]


def _window_start(period: str, now: datetime) -> datetime:
    if period == "daily":
        return now - timedelta(days=1)
    if period == "weekly":
        return now - timedelta(weeks=1)
    raise DigesterError(f"Unknown period '{period}'. Use 'daily' or 'weekly'.")


def _summary_to_entry(summary: JobSummary) -> DigestEntry:
    successes = sum(1 for e in summary.entries if e.exit_code == 0)
    failures = len(summary.entries) - successes
    return DigestEntry(
        command=summary.command,
        total_runs=len(summary.entries),
        success_count=successes,
        failure_count=failures,
        servers=list(summary.servers),
        last_run=summary.last_run,
    )


def build_digest(
    report: AggregatedReport,
    period: str = "daily",
    now: Optional[datetime] = None,
) -> DigestReport:
    """Build a DigestReport from an AggregatedReport for the given period."""
    if now is None:
        now = datetime.utcnow()
    start = _window_start(period, now)

    entries: List[DigestEntry] = []
    for summary in report.jobs.values():
        relevant = [
            e for e in summary.entries
            if e.timestamp is not None and start <= e.timestamp <= now
        ]
        if not relevant:
            continue
        filtered = JobSummary(
            command=summary.command,
            entries=relevant,
            servers=summary.servers,
        )
        entries.append(_summary_to_entry(filtered))

    entries.sort(key=lambda e: e.failure_count, reverse=True)
    return DigestReport(period_start=start, period_end=now, entries=entries)
