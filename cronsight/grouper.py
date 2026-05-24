"""Group job summaries by configurable keys for reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List

from cronsight.aggregator import AggregatedReport, JobSummary


class GrouperError(Exception):
    """Raised when an invalid grouping key is requested."""


_SUPPORTED_KEYS = frozenset({"server", "command", "status"})


def _dominant_status(summary: JobSummary) -> str:
    """Return 'success' if last run succeeded, else 'failure'."""
    if not summary.entries:
        return "unknown"
    return "success" if summary.entries[-1].exit_code == 0 else "failure"


_KEY_FN: Dict[str, Callable[[JobSummary], str]] = {
    "server": lambda s: s.server,
    "command": lambda s: s.command,
    "status": _dominant_status,
}


@dataclass
class JobGroup:
    key: str
    value: str
    summaries: List[JobSummary] = field(default_factory=list)

    @property
    def total_runs(self) -> int:
        return sum(s.total_runs for s in self.summaries)

    @property
    def job_count(self) -> int:
        return len(self.summaries)


@dataclass
class GroupedReport:
    key: str
    groups: Dict[str, JobGroup] = field(default_factory=dict)

    def group_names(self) -> List[str]:
        return sorted(self.groups.keys())


def group_report(report: AggregatedReport, key: str) -> GroupedReport:
    """Group all job summaries in *report* by *key*.

    Args:
        report: The aggregated report to group.
        key: One of 'server', 'command', or 'status'.

    Returns:
        A :class:`GroupedReport` mapping group values to job lists.

    Raises:
        GrouperError: If *key* is not supported.
    """
    if key not in _SUPPORTED_KEYS:
        raise GrouperError(
            f"Unsupported grouping key {key!r}. "
            f"Choose from: {', '.join(sorted(_SUPPORTED_KEYS))}"
        )

    fn = _KEY_FN[key]
    grouped = GroupedReport(key=key)

    for summary in report.jobs.values():
        value = fn(summary)
        if value not in grouped.groups:
            grouped.groups[value] = JobGroup(key=key, value=value)
        grouped.groups[value].summaries.append(summary)

    return grouped
