"""Replayer: reconstruct and replay cron job execution timelines from snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry


class ReplayerError(Exception):
    """Raised when replay cannot be performed."""


@dataclass
class ReplayEvent:
    """A single event in a replayed job timeline."""

    timestamp: datetime
    command: str
    server: str
    status: str  # "success" | "failure"

    def __str__(self) -> str:
        icon = "✓" if self.status == "success" else "✗"
        ts = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return f"[{ts}] {icon} {self.server}: {self.command}"


@dataclass
class JobTimeline:
    """Ordered sequence of replay events for a single job command."""

    command: str
    events: List[ReplayEvent] = field(default_factory=list)

    @property
    def event_count(self) -> int:
        return len(self.events)

    @property
    def failure_count(self) -> int:
        return sum(1 for e in self.events if e.status == "failure")


@dataclass
class ReplayReport:
    """Collection of timelines produced by a replay run."""

    timelines: List[JobTimeline] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.timelines)


def _entry_status(entry: CronEntry) -> str:
    return "failure" if entry.exit_code not in (None, 0) else "success"


def _build_timeline(command: str, summary: JobSummary) -> JobTimeline:
    events: List[ReplayEvent] = []
    for entry in sorted(summary.entries, key=lambda e: e.timestamp or datetime.min):
        if entry.timestamp is None:
            continue
        events.append(
            ReplayEvent(
                timestamp=entry.timestamp,
                command=command,
                server=summary.servers[0] if summary.servers else "unknown",
                status=_entry_status(entry),
            )
        )
    return JobTimeline(command=command, events=events)


def replay_report(
    report: AggregatedReport,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> ReplayReport:
    """Build a ReplayReport from an AggregatedReport, optionally filtered by time range."""
    if not report.jobs:
        raise ReplayerError("Report contains no jobs to replay.")

    timelines: List[JobTimeline] = []
    for command, summary in report.jobs.items():
        tl = _build_timeline(command, summary)
        if since is not None or until is not None:
            tl.events = [
                e
                for e in tl.events
                if (since is None or e.timestamp >= since)
                and (until is None or e.timestamp <= until)
            ]
        timelines.append(tl)

    timelines.sort(key=lambda t: t.events[0].timestamp if t.events else datetime.min)
    return ReplayReport(timelines=timelines)
