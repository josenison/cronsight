"""Assign severity labels to job summaries based on configurable thresholds."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


class LabelerError(Exception):
    """Raised when label configuration is invalid."""


@dataclass
class SeverityRule:
    """Maps a severity label to a maximum success-rate threshold."""

    label: str
    max_success_rate: float  # 0.0 – 1.0; rule fires when rate <= this value

    def __post_init__(self) -> None:
        if not 0.0 <= self.max_success_rate <= 1.0:
            raise LabelerError(
                f"max_success_rate must be in [0, 1], got {self.max_success_rate}"
            )


@dataclass
class LabeledReport:
    """Wraps an AggregatedReport and attaches per-job severity labels."""

    report: AggregatedReport
    labels: Dict[str, str] = field(default_factory=dict)  # command -> label


def _success_rate(summary: JobSummary) -> float:
    if summary.total_runs == 0:
        return 0.0
    return summary.successful_runs / summary.total_runs


def label_for_summary(
    summary: JobSummary,
    rules: List[SeverityRule],
    default_label: str = "ok",
) -> str:
    """Return the first matching severity label for *summary*, or *default_label*."""
    rate = _success_rate(summary)
    # Rules should be ordered from most-severe to least-severe by the caller.
    for rule in rules:
        if rate <= rule.max_success_rate:
            return rule.label
    return default_label


def label_report(
    report: AggregatedReport,
    rules: List[SeverityRule],
    default_label: str = "ok",
) -> LabeledReport:
    """Apply severity labeling to every job in *report*."""
    if not rules:
        raise LabelerError("At least one SeverityRule is required.")

    labels: Dict[str, str] = {}
    for summary in report.jobs:
        labels[summary.command] = label_for_summary(summary, rules, default_label)

    return LabeledReport(report=report, labels=labels)
