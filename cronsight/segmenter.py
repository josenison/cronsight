"""Segment a report into time-based buckets (hourly, daily, weekly)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Literal

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry

Granularity = Literal["hourly", "daily", "weekly"]


class SegmenterError(Exception):
    """Raised when segmentation fails."""


@dataclass
class Segment:
    label: str
    jobs: Dict[str, JobSummary] = field(default_factory=dict)

    @property
    def job_count(self) -> int:
        return len(self.jobs)

    @property
    def total_runs(self) -> int:
        return sum(len(s.entries) for s in self.jobs.values())

    def __str__(self) -> str:
        return f"Segment({self.label}, jobs={self.job_count}, runs={self.total_runs})"


@dataclass
class SegmentReport:
    granularity: Granularity
    segments: List[Segment] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.segments)


def _bucket_label(ts: datetime, granularity: Granularity) -> str:
    if granularity == "hourly":
        return ts.strftime("%Y-%m-%d %H:00")
    if granularity == "daily":
        return ts.strftime("%Y-%m-%d")
    if granularity == "weekly":
        iso = ts.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    raise SegmenterError(f"Unknown granularity: {granularity}")


def segment_report(
    report: AggregatedReport,
    granularity: Granularity = "daily",
) -> SegmentReport:
    """Split every job's entries into time buckets and return a SegmentReport."""
    if granularity not in ("hourly", "daily", "weekly"):
        raise SegmenterError(f"Invalid granularity: {granularity!r}")

    buckets: Dict[str, Dict[str, List[CronEntry]]] = {}

    for cmd, summary in report.jobs.items():
        for entry in summary.entries:
            if entry.timestamp is None:
                continue
            label = _bucket_label(entry.timestamp, granularity)
            buckets.setdefault(label, {}).setdefault(cmd, []).append(entry)

    segments: List[Segment] = []
    for label in sorted(buckets):
        seg = Segment(label=label)
        for cmd, entries in buckets[label].items():
            original = report.jobs[cmd]
            seg.jobs[cmd] = JobSummary(
                command=cmd,
                entries=entries,
                servers=original.servers,
            )
        segments.append(seg)

    return SegmentReport(granularity=granularity, segments=segments)
