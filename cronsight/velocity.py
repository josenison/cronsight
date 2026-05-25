"""Velocity module: tracks run-rate changes between two reports."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


class VelocityError(Exception):
    """Raised when velocity computation fails."""


@dataclass
class VelocityDelta:
    command: str
    old_runs: int
    new_runs: int
    old_success_rate: float
    new_success_rate: float

    @property
    def run_delta(self) -> int:
        return self.new_runs - self.old_runs

    @property
    def rate_delta(self) -> float:
        return round(self.new_success_rate - self.old_success_rate, 4)

    @property
    def accelerating(self) -> bool:
        """True when run count grew between snapshots."""
        return self.run_delta > 0

    def __str__(self) -> str:
        direction = "+" if self.run_delta >= 0 else ""
        return (
            f"{self.command}: runs {direction}{self.run_delta}, "
            f"rate {self.rate_delta:+.1%}"
        )


@dataclass
class VelocityReport:
    deltas: List[VelocityDelta] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.deltas)

    @property
    def accelerating(self) -> List[VelocityDelta]:
        return [d for d in self.deltas if d.accelerating]

    @property
    def decelerating(self) -> List[VelocityDelta]:
        return [d for d in self.deltas if not d.accelerating]


def _success_rate(summary: JobSummary) -> float:
    total = summary.total_runs
    if total == 0:
        return 0.0
    passed = sum(1 for e in summary.entries if e.exit_code == 0)
    return passed / total


def compute_velocity(
    old: AggregatedReport,
    new: AggregatedReport,
) -> VelocityReport:
    """Compare two reports and return per-job velocity deltas."""
    if old is None or new is None:
        raise VelocityError("Both old and new reports are required.")

    old_map: Dict[str, JobSummary] = {s.command: s for s in old.summaries}
    new_map: Dict[str, JobSummary] = {s.command: s for s in new.summaries}

    deltas: List[VelocityDelta] = []
    for cmd, new_summary in new_map.items():
        old_summary = old_map.get(cmd)
        old_runs = old_summary.total_runs if old_summary else 0
        old_rate = _success_rate(old_summary) if old_summary else 0.0
        deltas.append(
            VelocityDelta(
                command=cmd,
                old_runs=old_runs,
                new_runs=new_summary.total_runs,
                old_success_rate=old_rate,
                new_success_rate=_success_rate(new_summary),
            )
        )

    deltas.sort(key=lambda d: d.command)
    return VelocityReport(deltas=deltas)
