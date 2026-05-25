"""Flap detection: identify cron jobs that alternate between success and failure."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry


class FlapperError(Exception):
    """Raised when flap detection cannot be performed."""


@dataclass
class FlapJob:
    command: str
    servers: List[str]
    transitions: int  # number of status changes in execution history
    last_status: str  # "success" or "failure"

    def __str__(self) -> str:
        return (
            f"{self.command} | transitions={self.transitions} "
            f"last={self.last_status} servers={','.join(self.servers)}"
        )


@dataclass
class FlapReport:
    flapping: List[FlapJob] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.flapping)


def _count_transitions(entries: List[CronEntry]) -> int:
    """Count how many times the status flips between consecutive entries."""
    sorted_entries = sorted(entries, key=lambda e: e.timestamp or "")
    transitions = 0
    prev = None
    for entry in sorted_entries:
        status = "success" if entry.exit_code == 0 else "failure"
        if prev is not None and status != prev:
            transitions += 1
        prev = status
    return transitions


def _last_status(entries: List[CronEntry]) -> str:
    if not entries:
        return "unknown"
    sorted_entries = sorted(entries, key=lambda e: e.timestamp or "")
    last = sorted_entries[-1]
    return "success" if last.exit_code == 0 else "failure"


def detect_flapping(
    report: AggregatedReport,
    min_transitions: int = 2,
) -> FlapReport:
    """Return jobs whose execution history shows repeated status changes."""
    if min_transitions < 1:
        raise FlapperError("min_transitions must be at least 1")

    result: List[FlapJob] = []
    for command, summary in report.jobs.items():
        transitions = _count_transitions(summary.entries)
        if transitions >= min_transitions:
            result.append(
                FlapJob(
                    command=command,
                    servers=list(summary.servers),
                    transitions=transitions,
                    last_status=_last_status(summary.entries),
                )
            )

    result.sort(key=lambda j: j.transitions, reverse=True)
    return FlapReport(flapping=result)
