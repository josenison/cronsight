"""ScorerTrend: tracks score changes for jobs across two snapshots."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronsight.aggregator import AggregatedReport
from cronsight.scorer import ScoredReport, score_report


class ScorerTrendError(Exception):
    """Raised when scorer trend analysis fails."""


@dataclass
class ScoreDelta:
    command: str
    old_score: float
    new_score: float
    servers: List[str] = field(default_factory=list)

    @property
    def delta(self) -> float:
        return self.new_score - self.old_score

    @property
    def improved(self) -> bool:
        return self.delta > 0

    @property
    def degraded(self) -> bool:
        return self.delta < 0

    def __str__(self) -> str:
        direction = "+" if self.delta >= 0 else ""
        return f"{self.command}: {self.old_score:.2f} -> {self.new_score:.2f} ({direction}{self.delta:.2f})"


@dataclass
class ScorerTrendReport:
    deltas: List[ScoreDelta] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.deltas)

    @property
    def improved_count(self) -> int:
        return sum(1 for d in self.deltas if d.improved)

    @property
    def degraded_count(self) -> int:
        return sum(1 for d in self.deltas if d.degraded)

    def most_improved(self) -> Optional[ScoreDelta]:
        if not self.deltas:
            return None
        return max(self.deltas, key=lambda d: d.delta)

    def most_degraded(self) -> Optional[ScoreDelta]:
        if not self.deltas:
            return None
        return min(self.deltas, key=lambda d: d.delta)


def build_scorer_trend(
    old_report: AggregatedReport,
    new_report: AggregatedReport,
    only_changed: bool = False,
) -> ScorerTrendReport:
    """Compare job scores between two reports and return a trend report."""
    old_scored: ScoredReport = score_report(old_report)
    new_scored: ScoredReport = score_report(new_report)

    old_map: Dict[str, float] = {j.command: j.score for j in old_scored.jobs}
    new_map: Dict[str, float] = {j.command: j.score for j in new_scored.jobs}
    new_servers: Dict[str, List[str]] = {
        j.command: j.servers for j in new_scored.jobs
    }

    deltas: List[ScoreDelta] = []
    for cmd, new_score in new_map.items():
        old_score = old_map.get(cmd, 0.0)
        delta = ScoreDelta(
            command=cmd,
            old_score=old_score,
            new_score=new_score,
            servers=new_servers.get(cmd, []),
        )
        if only_changed and delta.delta == 0.0:
            continue
        deltas.append(delta)

    deltas.sort(key=lambda d: d.delta)
    return ScorerTrendReport(deltas=deltas)
