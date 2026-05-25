"""Streak detection: identifies jobs with consecutive pass or fail runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry


class StreakerError(Exception):
    """Raised when streak detection fails."""


@dataclass
class JobStreak:
    command: str
    server: str
    streak_type: str          # "passing" or "failing"
    length: int
    last_run: Optional[str]

    def __str__(self) -> str:
        return (
            f"{self.command} on {self.server}: "
            f"{self.length}-run {self.streak_type} streak"
        )


@dataclass
class StreakerReport:
    streaks: List[JobStreak] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.streaks)

    def passing_streaks(self) -> List[JobStreak]:
        return [s for s in self.streaks if s.streak_type == "passing"]

    def failing_streaks(self) -> List[JobStreak]:
        return [s for s in self.streaks if s.streak_type == "failing"]


def _current_streak(entries: List[CronEntry]) -> tuple[str, int]:
    """Return (streak_type, length) based on the tail of sorted entries."""
    if not entries:
        return ("passing", 0)

    sorted_entries = sorted(entries, key=lambda e: e.timestamp or "")
    streak_type = "passing" if sorted_entries[-1].success else "failing"
    length = 0
    for entry in reversed(sorted_entries):
        if entry.success == (streak_type == "passing"):
            length += 1
        else:
            break
    return streak_type, length


def detect_streaks(
    report: AggregatedReport,
    min_length: int = 2,
) -> StreakerReport:
    """Detect consecutive pass/fail streaks across all jobs.

    Args:
        report: Aggregated cron report.
        min_length: Minimum streak length to include (default 2).

    Returns:
        StreakerReport listing all qualifying streaks.
    """
    if min_length < 1:
        raise StreakerError("min_length must be at least 1")

    result: List[JobStreak] = []

    for key, summary in report.jobs.items():
        streak_type, length = _current_streak(summary.entries)
        if length >= min_length:
            result.append(
                JobStreak(
                    command=summary.command,
                    server=summary.server,
                    streak_type=streak_type,
                    length=length,
                    last_run=summary.last_run,
                )
            )

    result.sort(key=lambda s: s.length, reverse=True)
    return StreakerReport(streaks=result)
