"""Inspector: per-job detailed execution timeline and gap detection."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


class InspectorError(Exception):
    """Raised when inspection cannot be performed."""


@dataclass
class ExecutionGap:
    """A detected gap between two consecutive runs."""
    start: datetime
    end: datetime

    @property
    def duration_seconds(self) -> float:
        return (self.end - self.start).total_seconds()

    def __str__(self) -> str:
        fmt = "%Y-%m-%d %H:%M:%S"
        return f"Gap {self.start.strftime(fmt)} -> {self.end.strftime(fmt)} ({self.duration_seconds:.0f}s)"


@dataclass
class JobInspection:
    """Detailed inspection result for a single job."""
    command: str
    servers: List[str]
    total_runs: int
    success_runs: int
    failure_runs: int
    first_run: Optional[datetime]
    last_run: Optional[datetime]
    gaps: List[ExecutionGap] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return self.success_runs / self.total_runs

    @property
    def avg_gap_seconds(self) -> Optional[float]:
        if not self.gaps:
            return None
        return sum(g.duration_seconds for g in self.gaps) / len(self.gaps)


@dataclass
class InspectionReport:
    """Collection of per-job inspections derived from an AggregatedReport."""
    inspections: List[JobInspection] = field(default_factory=list)

    def get(self, command: str) -> Optional[JobInspection]:
        for insp in self.inspections:
            if insp.command == command:
                return insp
        return None


def _detect_gaps(timestamps: List[datetime], threshold_seconds: float) -> List[ExecutionGap]:
    """Return gaps between consecutive timestamps exceeding the threshold."""
    gaps: List[ExecutionGap] = []
    sorted_ts = sorted(timestamps)
    for i in range(1, len(sorted_ts)):
        delta = (sorted_ts[i] - sorted_ts[i - 1]).total_seconds()
        if delta > threshold_seconds:
            gaps.append(ExecutionGap(start=sorted_ts[i - 1], end=sorted_ts[i]))
    return gaps


def inspect_report(
    report: AggregatedReport,
    gap_threshold_seconds: float = 3600.0,
) -> InspectionReport:
    """Build an InspectionReport from an AggregatedReport."""
    if not report.jobs:
        raise InspectorError("Report contains no jobs to inspect.")

    inspections: List[JobInspection] = []
    for summary in report.jobs.values():
        entries = summary.entries
        timestamps = [e.timestamp for e in entries if e.timestamp is not None]
        success_runs = sum(1 for e in entries if e.exit_code == 0)
        failure_runs = len(entries) - success_runs
        gaps = _detect_gaps(timestamps, gap_threshold_seconds) if len(timestamps) >= 2 else []
        inspections.append(
            JobInspection(
                command=summary.command,
                servers=list(summary.servers),
                total_runs=len(entries),
                success_runs=success_runs,
                failure_runs=failure_runs,
                first_run=min(timestamps) if timestamps else None,
                last_run=max(timestamps) if timestamps else None,
                gaps=gaps,
            )
        )
    return InspectionReport(inspections=inspections)
