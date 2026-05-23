"""Baseline management: compare current report against a saved baseline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from cronsight.aggregator import AggregatedReport, JobSummary


class BaselineError(Exception):
    """Raised when baseline operations fail."""


@dataclass
class BaselineDelta:
    """Describes changes between a baseline and a current report."""

    new_jobs: list[str] = field(default_factory=list)
    removed_jobs: list[str] = field(default_factory=list)
    degraded_jobs: list[str] = field(default_factory=list)  # success rate dropped
    improved_jobs: list[str] = field(default_factory=list)  # success rate rose

    @property
    def has_changes(self) -> bool:
        return bool(
            self.new_jobs
            or self.removed_jobs
            or self.degraded_jobs
            or self.improved_jobs
        )


def _success_rate(summary: JobSummary) -> float:
    if summary.total_runs == 0:
        return 0.0
    return summary.successful_runs / summary.total_runs


def compare_to_baseline(
    baseline: AggregatedReport,
    current: AggregatedReport,
    degradation_threshold: float = 0.05,
) -> BaselineDelta:
    """Return a BaselineDelta describing what changed since the baseline.

    Args:
        baseline: Previously saved report used as the reference.
        current: The freshly collected report.
        degradation_threshold: Minimum drop in success rate to count as degraded.
    """
    baseline_keys = set(baseline.jobs.keys())
    current_keys = set(current.jobs.keys())

    delta = BaselineDelta(
        new_jobs=sorted(current_keys - baseline_keys),
        removed_jobs=sorted(baseline_keys - current_keys),
    )

    for key in baseline_keys & current_keys:
        old_rate = _success_rate(baseline.jobs[key])
        new_rate = _success_rate(current.jobs[key])
        diff = new_rate - old_rate
        if diff <= -degradation_threshold:
            delta.degraded_jobs.append(key)
        elif diff >= degradation_threshold:
            delta.improved_jobs.append(key)

    delta.degraded_jobs.sort()
    delta.improved_jobs.sort()
    return delta


def format_delta(delta: BaselineDelta) -> str:
    """Return a human-readable summary of the baseline delta."""
    if not delta.has_changes:
        return "No changes detected against baseline."

    lines: list[str] = []
    if delta.new_jobs:
        lines.append("New jobs: " + ", ".join(delta.new_jobs))
    if delta.removed_jobs:
        lines.append("Removed jobs: " + ", ".join(delta.removed_jobs))
    if delta.degraded_jobs:
        lines.append("Degraded jobs: " + ", ".join(delta.degraded_jobs))
    if delta.improved_jobs:
        lines.append("Improved jobs: " + ", ".join(delta.improved_jobs))
    return "\n".join(lines)
