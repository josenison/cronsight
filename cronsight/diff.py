"""Diff two AggregatedReports to surface new failures and recovered jobs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from cronsight.aggregator import AggregatedReport, JobSummary


@dataclass
class ReportDiff:
    """Result of comparing a baseline snapshot against a current report."""

    new_jobs: List[str] = field(default_factory=list)
    """Jobs present in current but not in baseline."""

    removed_jobs: List[str] = field(default_factory=list)
    """Jobs present in baseline but missing from current."""

    newly_failing: List[str] = field(default_factory=list)
    """Jobs whose last run changed from success to failure."""

    recovered: List[str] = field(default_factory=list)
    """Jobs whose last run changed from failure to success."""

    def has_changes(self) -> bool:
        return bool(self.new_jobs or self.removed_jobs or self.newly_failing or self.recovered)


def _last_status(summary: JobSummary) -> str | None:
    """Return the status of the most recent entry, or None if no entries."""
    if not summary.entries:
        return None
    latest = max(
        (e for e in summary.entries if e.timestamp is not None),
        key=lambda e: e.timestamp,
        default=None,
    )
    return latest.status if latest else None


def diff_reports(baseline: AggregatedReport, current: AggregatedReport) -> ReportDiff:
    """Compare *baseline* against *current* and return a :class:`ReportDiff`.

    Args:
        baseline: Previously saved snapshot report.
        current:  Freshly collected report.

    Returns:
        A :class:`ReportDiff` describing what changed between the two reports.
    """
    baseline_map = {s.job: s for s in baseline.jobs}
    current_map = {s.job: s for s in current.jobs}

    baseline_keys = set(baseline_map)
    current_keys = set(current_map)

    new_jobs = sorted(current_keys - baseline_keys)
    removed_jobs = sorted(baseline_keys - current_keys)

    newly_failing: list[str] = []
    recovered: list[str] = []

    for job in sorted(baseline_keys & current_keys):
        old_status = _last_status(baseline_map[job])
        new_status = _last_status(current_map[job])

        if old_status == "success" and new_status == "failure":
            newly_failing.append(job)
        elif old_status == "failure" and new_status == "success":
            recovered.append(job)

    return ReportDiff(
        new_jobs=new_jobs,
        removed_jobs=removed_jobs,
        newly_failing=newly_failing,
        recovered=recovered,
    )
