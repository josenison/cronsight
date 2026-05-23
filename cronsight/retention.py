"""Retention policy engine for managing cron job execution history."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from cronsight.aggregator import JobSummary, AggregatedReport


class RetentionError(Exception):
    """Raised when a retention policy cannot be applied."""


@dataclass
class RetentionPolicy:
    """Defines rules for how long job execution history is retained."""

    max_age_days: Optional[int] = None
    max_entries_per_job: Optional[int] = None
    keep_failures: bool = True

    def __post_init__(self) -> None:
        if self.max_age_days is not None and self.max_age_days <= 0:
            raise RetentionError("max_age_days must be a positive integer")
        if self.max_entries_per_job is not None and self.max_entries_per_job <= 0:
            raise RetentionError("max_entries_per_job must be a positive integer")
        if self.max_age_days is None and self.max_entries_per_job is None:
            raise RetentionError("At least one retention criterion must be specified")


@dataclass
class RetentionResult:
    """Result of applying a retention policy to a report."""

    original_entry_count: int
    retained_entry_count: int
    jobs_affected: List[str] = field(default_factory=list)

    @property
    def removed_count(self) -> int:
        return self.original_entry_count - self.retained_entry_count


def apply_retention(report: AggregatedReport, policy: RetentionPolicy) -> RetentionResult:
    """Apply a retention policy to all job summaries in a report.

    Modifies each JobSummary's entries in-place and returns a RetentionResult.
    """
    cutoff: Optional[datetime] = None
    if policy.max_age_days is not None:
        cutoff = datetime.utcnow() - timedelta(days=policy.max_age_days)

    total_original = 0
    total_retained = 0
    jobs_affected: List[str] = []

    for summary in report.jobs:
        original = list(summary.entries)
        total_original += len(original)

        retained = original

        if cutoff is not None:
            retained = [
                e for e in retained
                if (e.timestamp is None or e.timestamp >= cutoff)
                or (policy.keep_failures and not e.success)
            ]

        if policy.max_entries_per_job is not None:
            retained = retained[-policy.max_entries_per_job:]

        total_retained += len(retained)
        if len(retained) < len(original):
            jobs_affected.append(summary.command)
            summary.entries = retained

    return RetentionResult(
        original_entry_count=total_original,
        retained_entry_count=total_retained,
        jobs_affected=jobs_affected,
    )
