"""Escalation engine: promotes alerts to higher severity when a job
has been failing continuously for more than a configurable threshold."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry


class EscalatorError(Exception):
    """Raised when escalation configuration is invalid."""


@dataclass
class EscalationRule:
    """Rule that triggers when consecutive failures exceed *threshold*."""

    threshold: int
    label: str

    def __post_init__(self) -> None:
        if self.threshold < 1:
            raise EscalatorError("threshold must be >= 1")
        if not self.label.strip():
            raise EscalatorError("label must not be empty")


@dataclass
class EscalatedJob:
    command: str
    server: str
    consecutive_failures: int
    label: str

    def __str__(self) -> str:
        return (
            f"[{self.label}] {self.command} on {self.server} "
            f"({self.consecutive_failures} consecutive failures)"
        )


@dataclass
class EscalationReport:
    escalated: List[EscalatedJob] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.escalated)


def _consecutive_failures(summary: JobSummary) -> int:
    """Count trailing failures in chronological order."""
    entries: List[CronEntry] = sorted(
        summary.entries, key=lambda e: e.timestamp or ""
    )
    count = 0
    for entry in reversed(entries):
        if entry.exit_code != 0:
            count += 1
        else:
            break
    return count


def escalate_report(
    report: AggregatedReport,
    rules: List[EscalationRule],
) -> EscalationReport:
    """Evaluate *rules* against every job in *report*."""
    if not rules:
        raise EscalatorError("at least one EscalationRule is required")

    rules_sorted = sorted(rules, key=lambda r: r.threshold, reverse=True)
    result = EscalationReport()

    for key, summary in report.jobs.items():
        command, server = key
        failures = _consecutive_failures(summary)
        for rule in rules_sorted:
            if failures >= rule.threshold:
                result.escalated.append(
                    EscalatedJob(
                        command=command,
                        server=server,
                        consecutive_failures=failures,
                        label=rule.label,
                    )
                )
                break

    return result
