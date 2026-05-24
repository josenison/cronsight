"""Correlate job execution patterns across multiple servers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


class CorrelatorError(Exception):
    """Raised when correlation fails."""


@dataclass
class JobCorrelation:
    """Correlation data for a single job command across servers."""

    command: str
    servers: List[str] = field(default_factory=list)
    total_runs: int = 0
    total_failures: int = 0
    consistent: bool = True  # True if all servers agree on last status

    def __str__(self) -> str:
        rate = _success_rate(self)
        return f"{self.command} | servers={len(self.servers)} runs={self.total_runs} success={rate:.0%}"


@dataclass
class CorrelationReport:
    """Aggregated correlation across all jobs."""

    correlations: List[JobCorrelation] = field(default_factory=list)

    @property
    def inconsistent_jobs(self) -> List[JobCorrelation]:
        return [c for c in self.correlations if not c.consistent]


def _success_rate(corr: JobCorrelation) -> float:
    if corr.total_runs == 0:
        return 1.0
    return (corr.total_runs - corr.total_failures) / corr.total_runs


def _last_status(summary: JobSummary) -> Optional[str]:
    if not summary.entries:
        return None
    return summary.entries[-1].status


def correlate_reports(reports: Dict[str, AggregatedReport]) -> CorrelationReport:
    """Correlate job summaries across multiple named reports (e.g. per-server).

    Args:
        reports: Mapping of label (e.g. server name) to AggregatedReport.

    Returns:
        CorrelationReport grouping jobs by command.
    """
    if not reports:
        raise CorrelatorError("No reports provided for correlation.")

    merged: Dict[str, Dict] = {}

    for label, report in reports.items():
        for summary in report.jobs.values():
            cmd = summary.command
            if cmd not in merged:
                merged[cmd] = {
                    "servers": [],
                    "total_runs": 0,
                    "total_failures": 0,
                    "statuses": [],
                }
            entry = merged[cmd]
            entry["servers"].append(label)
            entry["total_runs"] += summary.total_runs
            entry["total_failures"] += summary.total_runs - sum(
                1 for e in summary.entries if e.status == "success"
            )
            status = _last_status(summary)
            if status:
                entry["statuses"].append(status)

    correlations = []
    for cmd, data in merged.items():
        consistent = len(set(data["statuses"])) <= 1
        correlations.append(
            JobCorrelation(
                command=cmd,
                servers=data["servers"],
                total_runs=data["total_runs"],
                total_failures=data["total_failures"],
                consistent=consistent,
            )
        )

    correlations.sort(key=lambda c: c.command)
    return CorrelationReport(correlations=correlations)
