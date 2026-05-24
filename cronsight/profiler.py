"""Execution duration profiling for cron jobs."""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, median, stdev
from typing import Dict, List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry


class ProfilerError(Exception):
    """Raised when profiling cannot be completed."""


@dataclass
class DurationProfile:
    command: str
    server: str
    durations: List[float] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.durations)

    @property
    def mean_seconds(self) -> Optional[float]:
        return mean(self.durations) if self.durations else None

    @property
    def median_seconds(self) -> Optional[float]:
        return median(self.durations) if self.durations else None

    @property
    def stddev_seconds(self) -> Optional[float]:
        return stdev(self.durations) if len(self.durations) >= 2 else None

    @property
    def max_seconds(self) -> Optional[float]:
        return max(self.durations) if self.durations else None

    @property
    def min_seconds(self) -> Optional[float]:
        return min(self.durations) if self.durations else None

    def __str__(self) -> str:
        if self.mean_seconds is None:
            return f"{self.command} [{self.server}]: no data"
        return (
            f"{self.command} [{self.server}]: "
            f"mean={self.mean_seconds:.1f}s "
            f"median={self.median_seconds:.1f}s "
            f"max={self.max_seconds:.1f}s"
        )


@dataclass
class ProfileReport:
    profiles: List[DurationProfile] = field(default_factory=list)

    @property
    def slowest(self) -> Optional[DurationProfile]:
        eligible = [p for p in self.profiles if p.mean_seconds is not None]
        return max(eligible, key=lambda p: p.mean_seconds, default=None)  # type: ignore[arg-type]


def _extract_durations(entries: List[CronEntry]) -> List[float]:
    """Return elapsed seconds between consecutive START/END pairs."""
    durations: List[float] = []
    pending: Dict[str, float] = {}
    for entry in sorted(entries, key=lambda e: e.timestamp or 0):
        if entry.timestamp is None:
            continue
        key = entry.command
        if entry.status == "started":
            pending[key] = entry.timestamp
        elif entry.status in ("succeeded", "failed") and key in pending:
            elapsed = entry.timestamp - pending.pop(key)
            if elapsed >= 0:
                durations.append(elapsed)
    return durations


def build_profile(report: AggregatedReport) -> ProfileReport:
    """Build a DurationProfile for every job in *report*."""
    if not report.jobs:
        raise ProfilerError("report contains no jobs")
    profiles: List[DurationProfile] = []
    for summary in report.jobs.values():
        durations = _extract_durations(summary.entries)
        profile = DurationProfile(
            command=summary.command,
            server=summary.server,
            durations=durations,
        )
        profiles.append(profile)
    return ProfileReport(profiles=profiles)
