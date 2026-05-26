"""Suppressor: mute known-noisy jobs from reports based on patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


class SuppressorError(Exception):
    pass


@dataclass
class SuppressRule:
    pattern: str
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.pattern:
            raise SuppressorError("pattern must not be empty")
        try:
            re.compile(self.pattern)
        except re.error as exc:
            raise SuppressorError(f"invalid regex pattern: {exc}") from exc

    def matches(self, command: str) -> bool:
        return bool(re.search(self.pattern, command))


@dataclass
class SuppressedReport:
    jobs: List[JobSummary]
    suppressed: List[JobSummary]
    rules_applied: List[SuppressRule]

    @property
    def suppressed_count(self) -> int:
        return len(self.suppressed)

    @property
    def job_count(self) -> int:
        return len(self.jobs)


def suppress_report(
    report: AggregatedReport,
    rules: List[SuppressRule],
) -> SuppressedReport:
    """Return a SuppressedReport with matching jobs removed."""
    if not rules:
        raise SuppressorError("at least one suppress rule is required")

    kept: List[JobSummary] = []
    suppressed: List[JobSummary] = []

    for summary in report.jobs.values():
        if any(rule.matches(summary.command) for rule in rules):
            suppressed.append(summary)
        else:
            kept.append(summary)

    return SuppressedReport(
        jobs=kept,
        suppressed=suppressed,
        rules_applied=list(rules),
    )
