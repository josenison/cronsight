"""Mirror module: compare job execution patterns across two snapshots side-by-side."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from cronsight.aggregator import AggregatedReport, JobSummary


class MirrorError(Exception):
    pass


@dataclass
class MirrorRow:
    command: str
    left_runs: int
    right_runs: int
    left_success_rate: Optional[float]  # 0.0 – 1.0 or None
    right_success_rate: Optional[float]
    only_in_left: bool = False
    only_in_right: bool = False

    def __str__(self) -> str:
        def _fmt(rate: Optional[float]) -> str:
            return f"{rate * 100:.1f}%" if rate is not None else "n/a"

        side = ""
        if self.only_in_left:
            side = " [left only]"
        elif self.only_in_right:
            side = " [right only]"
        return (
            f"{self.command}{side}: "
            f"runs={self.left_runs}/{self.right_runs} "
            f"success={_fmt(self.left_success_rate)}/{_fmt(self.right_success_rate)}"
        )


@dataclass
class MirrorReport:
    rows: list[MirrorRow] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.rows)

    @property
    def divergent_rows(self) -> list[MirrorRow]:
        """Rows where success rates differ by more than 10 percentage points."""
        result = []
        for r in self.rows:
            if r.only_in_left or r.only_in_right:
                result.append(r)
                continue
            if r.left_success_rate is None or r.right_success_rate is None:
                continue
            if abs(r.left_success_rate - r.right_success_rate) > 0.10:
                result.append(r)
        return result


def _success_rate(summary: JobSummary) -> Optional[float]:
    total = summary.total_runs
    if total == 0:
        return None
    passed = sum(1 for e in summary.entries if e.exit_code == 0)
    return passed / total


def mirror_reports(left: AggregatedReport, right: AggregatedReport) -> MirrorReport:
    """Build a MirrorReport comparing jobs in *left* against *right*."""
    if not isinstance(left, AggregatedReport) or not isinstance(right, AggregatedReport):
        raise MirrorError("Both arguments must be AggregatedReport instances")

    left_map: dict[str, JobSummary] = {s.command: s for s in left.summaries}
    right_map: dict[str, JobSummary] = {s.command: s for s in right.summaries}
    all_commands = sorted(set(left_map) | set(right_map))

    rows: list[MirrorRow] = []
    for cmd in all_commands:
        l_sum = left_map.get(cmd)
        r_sum = right_map.get(cmd)
        rows.append(
            MirrorRow(
                command=cmd,
                left_runs=l_sum.total_runs if l_sum else 0,
                right_runs=r_sum.total_runs if r_sum else 0,
                left_success_rate=_success_rate(l_sum) if l_sum else None,
                right_success_rate=_success_rate(r_sum) if r_sum else None,
                only_in_left=r_sum is None,
                only_in_right=l_sum is None,
            )
        )
    return MirrorReport(rows=rows)
