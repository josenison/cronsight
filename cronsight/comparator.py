"""Compare two aggregated reports and produce a structured diff summary."""

from dataclasses import dataclass, field
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


@dataclass
class JobChange:
    command: str
    field: str
    old_value: object
    new_value: object

    def __str__(self) -> str:
        return f"{self.command!r}: {self.field} changed from {self.old_value!r} to {self.new_value!r}"


@dataclass
class ComparisonResult:
    added: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    changed: List[JobChange] = field(default_factory=list)

    @property
    def has_differences(self) -> bool:
        return bool(self.added or self.removed or self.changed)

    def summary_lines(self) -> List[str]:
        lines: List[str] = []
        for cmd in self.added:
            lines.append(f"[+] new job: {cmd!r}")
        for cmd in self.removed:
            lines.append(f"[-] removed job: {cmd!r}")
        for change in self.changed:
            lines.append(f"[~] {change}")
        return lines


def _success_rate(summary: JobSummary) -> float:
    if summary.total_runs == 0:
        return 0.0
    return summary.successes / summary.total_runs


def compare_reports(
    baseline: AggregatedReport,
    current: AggregatedReport,
    rate_threshold: float = 0.05,
) -> ComparisonResult:
    """Compare *current* against *baseline* and return a ComparisonResult.

    A job is considered changed when its success-rate shifts by more than
    *rate_threshold* or its total run count differs.
    """
    result = ComparisonResult()

    baseline_jobs = {s.command: s for s in baseline.jobs}
    current_jobs = {s.command: s for s in current.jobs}

    for cmd in current_jobs:
        if cmd not in baseline_jobs:
            result.added.append(cmd)

    for cmd in baseline_jobs:
        if cmd not in current_jobs:
            result.removed.append(cmd)

    for cmd, cur in current_jobs.items():
        if cmd not in baseline_jobs:
            continue
        base = baseline_jobs[cmd]

        if cur.total_runs != base.total_runs:
            result.changed.append(
                JobChange(cmd, "total_runs", base.total_runs, cur.total_runs)
            )

        base_rate = _success_rate(base)
        cur_rate = _success_rate(cur)
        if abs(cur_rate - base_rate) > rate_threshold:
            result.changed.append(
                JobChange(
                    cmd,
                    "success_rate",
                    round(base_rate, 4),
                    round(cur_rate, 4),
                )
            )

    return result
