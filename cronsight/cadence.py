"""Cadence analysis: detect jobs that run irregularly or have drifted from expected intervals."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from statistics import mean, stdev
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


class CadenceError(Exception):
    pass


@dataclass
class CadenceProfile:
    command: str
    server: str
    run_count: int
    mean_interval_seconds: Optional[float]
    stdev_interval_seconds: Optional[float]
    max_interval_seconds: Optional[float]
    is_irregular: bool

    def __str__(self) -> str:
        if self.mean_interval_seconds is None:
            return f"{self.command} [{self.server}] — insufficient data"
        mean_min = self.mean_interval_seconds / 60
        flag = " [IRREGULAR]" if self.is_irregular else ""
        return f"{self.command} [{self.server}] mean={mean_min:.1f}m{flag}"


@dataclass
class CadenceReport:
    profiles: List[CadenceProfile] = field(default_factory=list)

    @property
    def irregular_count(self) -> int:
        return sum(1 for p in self.profiles if p.is_irregular)

    @property
    def count(self) -> int:
        return len(self.profiles)


def _intervals(timestamps: List[datetime]) -> List[float]:
    """Return sorted list of interval durations in seconds between consecutive runs."""
    sorted_ts = sorted(timestamps)
    return [
        (sorted_ts[i + 1] - sorted_ts[i]).total_seconds()
        for i in range(len(sorted_ts) - 1)
    ]


def _is_irregular(intervals: List[float], threshold: float) -> bool:
    """A job is irregular if its stdev exceeds `threshold` fraction of the mean."""
    if len(intervals) < 2:
        return False
    m = mean(intervals)
    if m == 0:
        return False
    s = stdev(intervals)
    return (s / m) > threshold


def analyze_cadence(
    report: AggregatedReport,
    irregularity_threshold: float = 0.5,
) -> CadenceReport:
    """Analyze the cadence of each job in the report."""
    if not 0 < irregularity_threshold <= 10:
        raise CadenceError("irregularity_threshold must be a positive number")

    profiles: List[CadenceProfile] = []
    for summary in report.summaries:
        timestamps = [
            e.timestamp for e in summary.entries if e.timestamp is not None
        ]
        ivs = _intervals(timestamps)
        m_iv = mean(ivs) if ivs else None
        s_iv = stdev(ivs) if len(ivs) >= 2 else None
        max_iv = max(ivs) if ivs else None
        irregular = _is_irregular(ivs, irregularity_threshold)
        profiles.append(
            CadenceProfile(
                command=summary.command,
                server=summary.server,
                run_count=summary.total_runs,
                mean_interval_seconds=m_iv,
                stdev_interval_seconds=s_iv,
                max_interval_seconds=max_iv,
                is_irregular=irregular,
            )
        )
    return CadenceReport(profiles=profiles)
