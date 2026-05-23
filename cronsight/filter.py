"""Filtering utilities for cron job summaries and aggregated reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from cronsight.aggregator import AggregatedReport, JobSummary


@dataclass
class FilterCriteria:
    """Criteria used to filter job summaries from a report."""

    server: Optional[str] = None
    min_runs: Optional[int] = None
    max_success_rate: Optional[float] = None  # 0.0 – 1.0; filter jobs *below* this
    command_contains: Optional[str] = None
    failed_only: bool = False


def _success_rate(summary: JobSummary) -> float:
    """Return the success rate for a summary as a value between 0.0 and 1.0."""
    if summary.total_runs == 0:
        return 0.0
    return summary.successful_runs / summary.total_runs


def matches(summary: JobSummary, criteria: FilterCriteria) -> bool:
    """Return True when *summary* satisfies every condition in *criteria*."""
    if criteria.server and summary.server != criteria.server:
        return False
    if criteria.min_runs is not None and summary.total_runs < criteria.min_runs:
        return False
    if criteria.command_contains and criteria.command_contains not in summary.command:
        return False
    if criteria.failed_only and summary.failed_runs == 0:
        return False
    if criteria.max_success_rate is not None:
        if _success_rate(summary) > criteria.max_success_rate:
            return False
    return True


def filter_report(
    report: AggregatedReport, criteria: FilterCriteria
) -> AggregatedReport:
    """Return a new :class:`AggregatedReport` containing only matching summaries."""
    filtered = [
        summary for summary in report.summaries if matches(summary, criteria)
    ]
    return AggregatedReport(summaries=filtered)
