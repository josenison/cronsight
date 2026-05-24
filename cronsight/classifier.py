"""Classify cron jobs into categories based on command patterns and run behaviour."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import re

from cronsight.aggregator import AggregatedReport, JobSummary


class ClassifierError(Exception):
    """Raised when classification configuration is invalid."""


@dataclass
class ClassRule:
    """A single pattern-based classification rule."""

    category: str
    pattern: str

    def __post_init__(self) -> None:
        if not self.category.strip():
            raise ClassifierError("category must not be empty")
        if not self.pattern.strip():
            raise ClassifierError("pattern must not be empty")
        # Validate regex early.
        try:
            re.compile(self.pattern)
        except re.error as exc:
            raise ClassifierError(f"invalid pattern {self.pattern!r}: {exc}") from exc


@dataclass
class ClassifiedJob:
    """A job summary annotated with a category label."""

    summary: JobSummary
    category: str

    def __str__(self) -> str:
        return f"[{self.category}] {self.summary.command}"


@dataclass
class ClassifiedReport:
    """Collection of classified jobs grouped by category."""

    groups: Dict[str, List[ClassifiedJob]] = field(default_factory=dict)

    @property
    def categories(self) -> List[str]:
        return sorted(self.groups.keys())

    def jobs_in(self, category: str) -> List[ClassifiedJob]:
        return self.groups.get(category, [])


def _match_category(command: str, rules: List[ClassRule]) -> Optional[str]:
    """Return the category of the first matching rule, or None."""
    for rule in rules:
        if re.search(rule.pattern, command):
            return rule.category
    return None


def classify_report(
    report: AggregatedReport,
    rules: List[ClassRule],
    default_category: str = "uncategorized",
) -> ClassifiedReport:
    """Classify every job in *report* using *rules*.

    Jobs that do not match any rule are placed in *default_category*.
    """
    if not rules and default_category == "uncategorized":
        pass  # allowed — everything lands in default

    groups: Dict[str, List[ClassifiedJob]] = {}
    for command, summary in report.jobs.items():
        category = _match_category(command, rules) or default_category
        groups.setdefault(category, []).append(ClassifiedJob(summary=summary, category=category))

    return ClassifiedReport(groups=groups)
