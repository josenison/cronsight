"""windower.py — Slice an AggregatedReport into fixed-size rolling time windows."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry


class WindowerError(Exception):
    """Raised when windower parameters are invalid."""


@dataclass
class TimeWindow:
    start: datetime
    end: datetime
    summaries: Dict[str, JobSummary] = field(default_factory=dict)

    @property
    def job_count(self) -> int:
        return len(self.summaries)

    @property
    def total_runs(self) -> int:
        return sum(s.total_runs for s in self.summaries.values())

    def __str__(self) -> str:
        return (
            f"TimeWindow({self.start.strftime('%Y-%m-%d %H:%M')} – "
            f"{self.end.strftime('%Y-%m-%d %H:%M')}, "
            f"jobs={self.job_count}, runs={self.total_runs})"
        )


@dataclass
class WindowReport:
    windows: List[TimeWindow] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.windows)


def _entries_in_range(
    summary: JobSummary, start: datetime, end: datetime
) -> List[CronEntry]:
    return [
        e for e in summary.entries
        if e.timestamp is not None and start <= e.timestamp < end
    ]


def _slice_summary(summary: JobSummary, entries: List[CronEntry]) -> Optional[JobSummary]:
    if not entries:
        return None
    sliced = JobSummary(
        command=summary.command,
        entries=entries,
        servers=list({
            e.server for e in entries if hasattr(e, "server") and e.server
        }) or summary.servers,
    )
    return sliced


def build_windows(
    report: AggregatedReport,
    window_minutes: int = 60,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> WindowReport:
    """Partition *report* into non-overlapping windows of *window_minutes* width."""
    if window_minutes <= 0:
        raise WindowerError("window_minutes must be a positive integer")

    all_entries = [
        e
        for s in report.summaries.values()
        for e in s.entries
        if e.timestamp is not None
    ]
    if not all_entries:
        return WindowReport()

    ts_min = since or min(e.timestamp for e in all_entries)
    ts_max = until or max(e.timestamp for e in all_entries)
    delta = timedelta(minutes=window_minutes)

    windows: List[TimeWindow] = []
    cursor = ts_min
    while cursor <= ts_max:
        win_end = cursor + delta
        win = TimeWindow(start=cursor, end=win_end)
        for cmd, summary in report.summaries.items():
            entries = _entries_in_range(summary, cursor, win_end)
            sliced = _slice_summary(summary, entries)
            if sliced is not None:
                win.summaries[cmd] = sliced
        windows.append(win)
        cursor = win_end

    return WindowReport(windows=windows)
