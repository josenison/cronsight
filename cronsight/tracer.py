"""Trace execution paths for cron jobs across multiple servers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry


class TracerError(Exception):
    """Raised when tracing fails."""


@dataclass
class TraceEvent:
    """A single execution event in a job trace."""

    server: str
    command: str
    timestamp: str
    status: str  # 'success' | 'failure'
    exit_code: Optional[int] = None

    def __str__(self) -> str:
        mark = "✓" if self.status == "success" else "✗"
        return f"[{mark}] {self.timestamp}  {self.server}  {self.command}"


@dataclass
class JobTrace:
    """Full trace for a single job command."""

    command: str
    events: List[TraceEvent] = field(default_factory=list)

    @property
    def event_count(self) -> int:
        return len(self.events)

    @property
    def failure_count(self) -> int:
        return sum(1 for e in self.events if e.status == "failure")

    @property
    def servers(self) -> List[str]:
        return sorted({e.server for e in self.events})


@dataclass
class TraceReport:
    """Collection of traces for all jobs."""

    traces: Dict[str, JobTrace] = field(default_factory=dict)

    @property
    def job_count(self) -> int:
        return len(self.traces)

    @property
    def total_events(self) -> int:
        return sum(t.event_count for t in self.traces.values())


def _entry_status(entry: CronEntry) -> str:
    return "failure" if entry.failed else "success"


def build_trace(report: AggregatedReport, command_filter: Optional[str] = None) -> TraceReport:
    """Build a TraceReport from an AggregatedReport.

    Args:
        report: Aggregated cron report.
        command_filter: Optional substring to filter commands.

    Returns:
        TraceReport with one JobTrace per matching command.

    Raises:
        TracerError: If report has no jobs.
    """
    if not report.jobs:
        raise TracerError("Report contains no jobs to trace.")

    traces: Dict[str, JobTrace] = {}

    for summary in report.jobs.values():
        cmd = summary.command
        if command_filter and command_filter not in cmd:
            continue

        trace = traces.setdefault(cmd, JobTrace(command=cmd))

        for server, entries in summary.entries_by_server.items():
            for entry in entries:
                event = TraceEvent(
                    server=server,
                    command=cmd,
                    timestamp=entry.timestamp,
                    status=_entry_status(entry),
                )
                trace.events.append(event)

    # Sort events within each trace by timestamp
    for trace in traces.values():
        trace.events.sort(key=lambda e: e.timestamp)

    return TraceReport(traces=traces)
