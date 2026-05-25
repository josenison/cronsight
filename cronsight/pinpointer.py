"""Pinpointer: identify jobs with the highest failure concentration in a specific time window."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry


class PinpointerError(Exception):
    """Raised when pinpointing fails."""


@dataclass
class FailureCluster:
    command: str
    server: str
    failures_in_window: int
    total_in_window: int
    first_failure: Optional[datetime]
    last_failure: Optional[datetime]

    @property
    def failure_rate(self) -> float:
        if self.total_in_window == 0:
            return 0.0
        return self.failures_in_window / self.total_in_window

    def __str__(self) -> str:
        return (
            f"{self.command} [{self.server}] "
            f"{self.failures_in_window}/{self.total_in_window} failures "
            f"({self.failure_rate:.0%})"
        )


@dataclass
class PinpointReport:
    clusters: List[FailureCluster] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.clusters)

    @property
    def top(self) -> Optional[FailureCluster]:
        return self.clusters[0] if self.clusters else None


def _entries_in_window(
    entries: List[CronEntry],
    since: Optional[datetime],
    until: Optional[datetime],
) -> List[CronEntry]:
    result = []
    for e in entries:
        if e.timestamp is None:
            continue
        if since and e.timestamp < since:
            continue
        if until and e.timestamp > until:
            continue
        result.append(e)
    return result


def pinpoint(
    report: AggregatedReport,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    min_failures: int = 1,
) -> PinpointReport:
    if min_failures < 1:
        raise PinpointerError("min_failures must be at least 1")

    clusters: List[FailureCluster] = []

    for command, summary in report.jobs.items():
        windowed = _entries_in_window(summary.entries, since, until)
        if not windowed:
            continue
        failed = [e for e in windowed if not e.success]
        if len(failed) < min_failures:
            continue
        failure_times = sorted(
            (e.timestamp for e in failed if e.timestamp), default=None
        ) if False else sorted(
            e.timestamp for e in failed if e.timestamp
        )
        clusters.append(
            FailureCluster(
                command=command,
                server=summary.servers[0] if summary.servers else "unknown",
                failures_in_window=len(failed),
                total_in_window=len(windowed),
                first_failure=failure_times[0] if failure_times else None,
                last_failure=failure_times[-1] if failure_times else None,
            )
        )

    clusters.sort(key=lambda c: (-c.failures_in_window, -c.failure_rate))
    return PinpointReport(clusters=clusters)
