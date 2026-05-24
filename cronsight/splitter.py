"""Split an AggregatedReport into time-based windows (hourly, daily, weekly)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Literal

from cronsight.aggregator import AggregatedReport, JobSummary

WindowSize = Literal["hourly", "daily", "weekly"]

SECONDS = {"hourly": 3600, "daily": 86400, "weekly": 604800}


class SplitterError(Exception):
    """Raised when splitting fails."""


@dataclass
class ReportWindow:
    """A slice of the original report constrained to a time window."""

    label: str  # e.g. "2024-05-01"
    start: datetime
    end: datetime
    jobs: Dict[str, JobSummary] = field(default_factory=dict)

    @property
    def job_count(self) -> int:
        return len(self.jobs)

    @property
    def total_runs(self) -> int:
        return sum(s.total_runs for s in self.jobs.values())


@dataclass
class SplitReport:
    """Collection of time windows derived from a single AggregatedReport."""

    window_size: WindowSize
    windows: List[ReportWindow] = field(default_factory=list)

    @property
    def window_count(self) -> int:
        return len(self.windows)


def _window_label(dt: datetime, size: WindowSize) -> str:
    if size == "hourly":
        return dt.strftime("%Y-%m-%d %H:00")
    if size == "weekly":
        monday = dt - __import__("datetime").timedelta(days=dt.weekday())
        return monday.strftime("week-%Y-%m-%d")
    return dt.strftime("%Y-%m-%d")


def split_report(report: AggregatedReport, size: WindowSize) -> SplitReport:
    """Split *report* into non-overlapping windows of the given *size*."""
    if size not in SECONDS:
        raise SplitterError(f"Unknown window size: {size!r}")

    windows: Dict[str, ReportWindow] = {}

    for job_key, summary in report.jobs.items():
        for entry in summary.entries:
            ts = entry.timestamp
            if ts is None:
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            label = _window_label(ts, size)
            if label not in windows:
                import datetime as _dt
                span = _dt.timedelta(seconds=SECONDS[size])
                # align start to window boundary
                epoch = ts.replace(minute=0, second=0, microsecond=0)
                if size == "daily":
                    epoch = epoch.replace(hour=0)
                elif size == "weekly":
                    epoch = epoch.replace(hour=0) - _dt.timedelta(days=epoch.weekday())
                windows[label] = ReportWindow(label=label, start=epoch, end=epoch + span)

            win = windows[label]
            if job_key not in win.jobs:
                win.jobs[job_key] = JobSummary(
                    command=summary.command,
                    servers=list(summary.servers),
                    entries=[],
                )
            win.jobs[job_key].entries.append(entry)

    sorted_windows = sorted(windows.values(), key=lambda w: w.start)
    return SplitReport(window_size=size, windows=sorted_windows)
