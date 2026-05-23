"""Trend analysis for cron job execution history."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronsight.aggregator import JobSummary


@dataclass
class TrendPoint:
    """A single data point in a job's execution trend."""

    timestamp: str
    success: bool
    server: str


@dataclass
class JobTrend:
    """Trend data for a single job command."""

    command: str
    points: List[TrendPoint] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.points)

    @property
    def success_count(self) -> int:
        return sum(1 for p in self.points if p.success)

    @property
    def failure_count(self) -> int:
        return self.total - self.success_count

    @property
    def success_rate(self) -> Optional[float]:
        if self.total == 0:
            return None
        return self.success_count / self.total

    @property
    def is_degrading(self) -> bool:
        """Return True if the last 3 runs are all failures."""
        recent = self.points[-3:]
        return len(recent) >= 3 and all(not p.success for p in recent)

    @property
    def is_recovering(self) -> bool:
        """Return True if the last 3 runs are all successes after prior failures."""
        if self.total < 4:
            return False
        recent = self.points[-3:]
        prior = self.points[-4]
        return all(p.success for p in recent) and not prior.success


def build_trend(summary: JobSummary) -> JobTrend:
    """Build a JobTrend from a JobSummary's execution entries."""
    trend = JobTrend(command=summary.command)
    for entry in sorted(summary.entries, key=lambda e: e.timestamp or ""):
        trend.points.append(
            TrendPoint(
                timestamp=entry.timestamp or "",
                success=entry.exit_code == 0,
                server=entry.server or "",
            )
        )
    return trend


def analyze_trends(summaries: List[JobSummary]) -> List[JobTrend]:
    """Return a list of JobTrend objects for each job summary."""
    return [build_trend(s) for s in summaries]
