"""Event log builder: converts job summaries into a flat chronological event stream."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry


class EventerError(Exception):
    """Raised when event stream construction fails."""


@dataclass
class JobEvent:
    command: str
    server: str
    timestamp: str
    status: str  # "success" | "failure"
    raw_line: str

    def __str__(self) -> str:
        icon = "✓" if self.status == "success" else "✗"
        return f"[{self.timestamp}] {icon} {self.server}: {self.command}"


@dataclass
class EventStream:
    events: List[JobEvent] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.events)

    @property
    def failure_count(self) -> int:
        return sum(1 for e in self.events if e.status == "failure")

    @property
    def success_count(self) -> int:
        return sum(1 for e in self.events if e.status == "success")


def _entry_status(entry: CronEntry) -> str:
    return "failure" if entry.return_code not in (None, 0) else "success"


def build_event_stream(
    report: AggregatedReport,
    since: Optional[str] = None,
    until: Optional[str] = None,
    server: Optional[str] = None,
) -> EventStream:
    """Build a flat chronological event stream from an aggregated report."""
    events: List[JobEvent] = []

    for job_key, summary in report.jobs.items():
        for entry in summary.entries:
            if server and entry.server != server:
                continue
            ts = entry.timestamp or ""
            if since and ts < since:
                continue
            if until and ts > until:
                continue
            events.append(
                JobEvent(
                    command=entry.command,
                    server=entry.server,
                    timestamp=ts,
                    status=_entry_status(entry),
                    raw_line=entry.raw_line,
                )
            )

    events.sort(key=lambda e: e.timestamp)
    return EventStream(events=events)
