"""Merge multiple AggregatedReports into a single unified report."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry


class MergerError(Exception):
    """Raised when merging reports fails."""


@dataclass
class MergeResult:
    """The result of merging two or more AggregatedReports."""

    jobs: Dict[str, JobSummary] = field(default_factory=dict)
    source_count: int = 0

    @property
    def job_count(self) -> int:
        return len(self.jobs)

    @property
    def total_runs(self) -> int:
        return sum(j.total_runs for j in self.jobs.values())


def _merge_summaries(base: JobSummary, other: JobSummary) -> JobSummary:
    """Combine two JobSummary objects for the same command."""
    merged_entries: List[CronEntry] = list(base.entries) + list(other.entries)
    merged_servers = sorted(set(base.servers) | set(other.servers))
    return JobSummary(
        command=base.command,
        entries=merged_entries,
        servers=merged_servers,
    )


def merge_reports(reports: List[AggregatedReport]) -> MergeResult:
    """Merge a list of AggregatedReports into a single MergeResult.

    Args:
        reports: One or more AggregatedReport instances to combine.

    Returns:
        A MergeResult containing all jobs from every report.

    Raises:
        MergerError: If the reports list is empty.
    """
    if not reports:
        raise MergerError("At least one report is required to merge.")

    merged: Dict[str, JobSummary] = {}

    for report in reports:
        for command, summary in report.jobs.items():
            if command in merged:
                merged[command] = _merge_summaries(merged[command], summary)
            else:
                merged[command] = summary

    return MergeResult(jobs=merged, source_count=len(reports))
