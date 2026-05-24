"""Diff two AggregatedReports and surface added / removed / changed jobs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


@dataclass
class ReportDiff:
    added_jobs: List[str] = field(default_factory=list)
    removed_jobs: List[str] = field(default_factory=list)
    changed_jobs: List[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added_jobs or self.removed_jobs or self.changed_jobs)


def _last_status(summary: JobSummary) -> Optional[str]:
    """Return the exit status string of the most recent entry, or None."""
    if not summary.entries:
        return None
    latest = max(summary.entries, key=lambda e: e.timestamp or "")
    return latest.status


def diff_reports(
    previous: Optional[AggregatedReport],
    current: AggregatedReport,
) -> ReportDiff:
    """Compare two reports and return a ReportDiff describing what changed.

    A job is considered *changed* when its last-known exit status differs
    between the two reports (e.g. a previously failing job started passing).
    """
    if previous is None:
        return ReportDiff()

    prev_keys = set(previous.jobs.keys())
    curr_keys = set(current.jobs.keys())

    added = sorted(curr_keys - prev_keys)
    removed = sorted(prev_keys - curr_keys)
    changed: List[str] = []

    for key in sorted(prev_keys & curr_keys):
        if _last_status(previous.jobs[key]) != _last_status(current.jobs[key]):
            changed.append(key)

    return ReportDiff(added_jobs=added, removed_jobs=removed, changed_jobs=changed)
