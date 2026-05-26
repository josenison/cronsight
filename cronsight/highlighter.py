"""Highlight jobs that match specific patterns or conditions for quick visual triage."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


class HighlighterError(Exception):
    pass


@dataclass
class HighlightRule:
    pattern: str
    label: str
    color: str = "yellow"

    def __post_init__(self) -> None:
        if not self.pattern:
            raise HighlighterError("pattern must not be empty")
        if not self.label:
            raise HighlighterError("label must not be empty")
        valid_colors = {"red", "green", "yellow", "blue", "magenta", "cyan"}
        if self.color not in valid_colors:
            raise HighlighterError(f"color must be one of {sorted(valid_colors)}")
        try:
            re.compile(self.pattern)
        except re.error as exc:
            raise HighlighterError(f"invalid regex pattern: {exc}") from exc


@dataclass
class HighlightedJob:
    summary: JobSummary
    labels: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        tag_str = ", ".join(self.labels) if self.labels else "—"
        return f"{self.summary.command} [{tag_str}]"

    @property
    def is_highlighted(self) -> bool:
        return len(self.labels) > 0


@dataclass
class HighlightReport:
    jobs: List[HighlightedJob] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.jobs)

    @property
    def highlighted_count(self) -> int:
        return sum(1 for j in self.jobs if j.is_highlighted)


def _labels_for(summary: JobSummary, rules: List[HighlightRule]) -> List[str]:
    matched: List[str] = []
    for rule in rules:
        if re.search(rule.pattern, summary.command):
            matched.append(rule.label)
    return matched


def highlight_report(
    report: AggregatedReport,
    rules: List[HighlightRule],
    highlighted_only: bool = False,
) -> HighlightReport:
    if not rules:
        raise HighlighterError("at least one HighlightRule is required")

    results: List[HighlightedJob] = []
    for summary in report.jobs.values():
        labels = _labels_for(summary, rules)
        job = HighlightedJob(summary=summary, labels=labels)
        if highlighted_only and not job.is_highlighted:
            continue
        results.append(job)

    results.sort(key=lambda j: j.summary.command)
    return HighlightReport(jobs=results)
