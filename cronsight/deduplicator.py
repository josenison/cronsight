"""Deduplicator: detect and remove duplicate cron job entries within a report."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Tuple

from cronsight.aggregator import AggregatedReport, JobSummary


class DeduplicatorError(Exception):
    """Raised when deduplication cannot be performed."""


@dataclass
class DuplicateGroup:
    """A set of job summaries sharing the same command across servers."""

    command: str
    summaries: List[JobSummary] = field(default_factory=list)

    @property
    def server_count(self) -> int:
        return len({s.server for s in self.summaries})

    @property
    def total_runs(self) -> int:
        return sum(s.total_runs for s in self.summaries)

    def __str__(self) -> str:
        return (
            f"DuplicateGroup(command={self.command!r}, "
            f"servers={self.server_count}, total_runs={self.total_runs})"
        )


@dataclass
class DeduplicationResult:
    """Result of a deduplication pass over a report."""

    original_count: int
    deduplicated_report: AggregatedReport
    duplicate_groups: List[DuplicateGroup] = field(default_factory=list)

    @property
    def removed_count(self) -> int:
        return self.original_count - len(self.deduplicated_report.jobs)

    @property
    def has_duplicates(self) -> bool:
        return bool(self.duplicate_groups)


def _group_by_command(
    summaries: List[JobSummary],
) -> Dict[str, List[JobSummary]]:
    groups: Dict[str, List[JobSummary]] = {}
    for summary in summaries:
        groups.setdefault(summary.command, []).append(summary)
    return groups


def _merge_summaries(summaries: List[JobSummary]) -> JobSummary:
    """Merge multiple summaries for the same command into one."""
    if not summaries:
        raise DeduplicatorError("Cannot merge an empty list of summaries.")
    all_entries = [entry for s in summaries for entry in s.entries]
    servers = sorted({s.server for s in summaries})
    merged = JobSummary(
        command=summaries[0].command,
        entries=all_entries,
        server=",".join(servers),
    )
    return merged


def deduplicate_report(
    report: AggregatedReport,
    *,
    merge: bool = False,
) -> DeduplicationResult:
    """Detect duplicate job commands across servers.

    Args:
        report: The aggregated report to inspect.
        merge: If True, merge duplicate entries into a single summary.
               If False, keep the first occurrence and discard the rest.

    Returns:
        A DeduplicationResult with the cleaned report and duplicate groups.
    """
    if not report.jobs:
        raise DeduplicatorError("Report contains no jobs to deduplicate.")

    groups = _group_by_command(report.jobs)
    duplicate_groups: List[DuplicateGroup] = []
    kept: List[JobSummary] = []

    for command, summaries in groups.items():
        if len(summaries) > 1:
            duplicate_groups.append(
                DuplicateGroup(command=command, summaries=summaries)
            )
            kept.append(_merge_summaries(summaries) if merge else summaries[0])
        else:
            kept.append(summaries[0])

    deduped_report = AggregatedReport(jobs=kept)
    return DeduplicationResult(
        original_count=len(report.jobs),
        deduplicated_report=deduped_report,
        duplicate_groups=duplicate_groups,
    )
