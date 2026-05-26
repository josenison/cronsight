"""Recurrence analysis: detect how often each job is expected to run and flag deviations."""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median, stdev
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


class RecurrenceError(Exception):
    pass


@dataclass
class RecurrenceProfile:
    command: str
    servers: List[str]
    run_count: int
    median_interval_seconds: Optional[float]
    stdev_interval_seconds: Optional[float]
    irregular: bool = False

    def __str__(self) -> str:
        med = f"{self.median_interval_seconds:.0f}s" if self.median_interval_seconds is not None else "N/A"
        sd = f"{self.stdev_interval_seconds:.0f}s" if self.stdev_interval_seconds is not None else "N/A"
        flag = " [IRREGULAR]" if self.irregular else ""
        return f"{self.command}: runs={self.run_count} median={med} stdev={sd}{flag}"


@dataclass
class RecurrenceReport:
    profiles: List[RecurrenceProfile] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.profiles)

    @property
    def irregular_count(self) -> int:
        return sum(1 for p in self.profiles if p.irregular)


def _intervals(summary: JobSummary) -> List[float]:
    timestamps = sorted(
        e.timestamp for e in summary.entries if e.timestamp is not None
    )
    if len(timestamps) < 2:
        return []
    return [
        (timestamps[i + 1] - timestamps[i]).total_seconds()
        for i in range(len(timestamps) - 1)
    ]


def build_recurrence_report(
    report: AggregatedReport,
    irregularity_threshold: float = 0.5,
) -> RecurrenceReport:
    """Build a RecurrenceReport from an AggregatedReport.

    A job is considered irregular when its coefficient of variation
    (stdev / median) exceeds *irregularity_threshold*.
    """
    if irregularity_threshold < 0:
        raise RecurrenceError("irregularity_threshold must be >= 0")

    profiles: List[RecurrenceProfile] = []
    for command, summary in report.jobs.items():
        ivs = _intervals(summary)
        med: Optional[float] = median(ivs) if ivs else None
        sd: Optional[float] = stdev(ivs) if len(ivs) >= 2 else None
        irregular = False
        if med and med > 0 and sd is not None:
            cv = sd / med
            irregular = cv > irregularity_threshold
        profiles.append(
            RecurrenceProfile(
                command=command,
                servers=list(summary.servers),
                run_count=summary.total_runs,
                median_interval_seconds=med,
                stdev_interval_seconds=sd,
                irregular=irregular,
            )
        )
    return RecurrenceReport(profiles=profiles)
