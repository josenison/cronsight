"""Cap (limit) the number of entries per job in a report, keeping the most recent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from cronsight.aggregator import AggregatedReport, JobSummary


class CapperError(Exception):
    """Raised when capper configuration is invalid."""


@dataclass
class CappedJob:
    command: str
    server: str
    original_count: int
    capped_count: int
    summary: JobSummary

    def __str__(self) -> str:
        return (
            f"{self.command} on {self.server}: "
            f"{self.capped_count}/{self.original_count} entries kept"
        )


@dataclass
class CappedReport:
    jobs: List[CappedJob] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.jobs)

    @property
    def total_dropped(self) -> int:
        return sum(j.original_count - j.capped_count for j in self.jobs)


def cap_report(report: AggregatedReport, max_entries: int) -> CappedReport:
    """Return a new report where each job retains at most *max_entries* recent entries."""
    if max_entries < 1:
        raise CapperError(f"max_entries must be >= 1, got {max_entries}")

    capped_jobs: List[CappedJob] = []

    for key, summary in report.jobs.items():
        original_entries = summary.entries
        original_count = len(original_entries)

        sorted_entries = sorted(
            original_entries,
            key=lambda e: e.timestamp or "",
            reverse=True,
        )
        kept = sorted_entries[:max_entries]

        new_summary = JobSummary(
            command=summary.command,
            server=summary.server,
            entries=kept,
        )

        capped_jobs.append(
            CappedJob(
                command=summary.command,
                server=summary.server,
                original_count=original_count,
                capped_count=len(kept),
                summary=new_summary,
            )
        )

    return CappedReport(jobs=capped_jobs)
