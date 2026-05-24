"""Heatmap: build hour-of-day execution frequency maps per job."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from cronsight.aggregator import AggregatedReport, JobSummary


class HeatmapError(Exception):
    """Raised when heatmap generation fails."""


@dataclass
class HourBucket:
    hour: int  # 0-23
    run_count: int = 0
    failure_count: int = 0

    @property
    def success_count(self) -> int:
        return self.run_count - self.failure_count

    @property
    def failure_rate(self) -> float:
        if self.run_count == 0:
            return 0.0
        return self.failure_count / self.run_count


@dataclass
class JobHeatmap:
    command: str
    buckets: List[HourBucket] = field(default_factory=lambda: [HourBucket(h) for h in range(24)])

    def bucket(self, hour: int) -> HourBucket:
        if not 0 <= hour <= 23:
            raise HeatmapError(f"Invalid hour: {hour}")
        return self.buckets[hour]

    @property
    def peak_hour(self) -> int:
        return max(range(24), key=lambda h: self.buckets[h].run_count)


@dataclass
class HeatmapReport:
    jobs: Dict[str, JobHeatmap] = field(default_factory=dict)

    def get(self, command: str) -> JobHeatmap:
        return self.jobs[command]


def build_heatmap(report: AggregatedReport) -> HeatmapReport:
    """Build an hour-of-day heatmap from an aggregated report."""
    heatmap = HeatmapReport()
    for command, summary in report.jobs.items():
        job_heatmap = JobHeatmap(command=command)
        for entry in summary.entries:
            if entry.timestamp is None:
                continue
            hour = entry.timestamp.hour
            bucket = job_heatmap.bucket(hour)
            bucket.run_count += 1
            if not entry.success:
                bucket.failure_count += 1
        heatmap.jobs[command] = job_heatmap
    return heatmap
