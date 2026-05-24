"""Annotator: attach human-readable notes to job summaries in a report."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


class AnnotatorError(Exception):
    """Raised when annotation configuration is invalid."""


@dataclass
class AnnotationRule:
    """Maps a job command substring to a note string."""

    pattern: str
    note: str

    def __post_init__(self) -> None:
        if not self.pattern:
            raise AnnotatorError("pattern must not be empty")
        if not self.note:
            raise AnnotatorError("note must not be empty")


@dataclass
class AnnotatedReport:
    """Wraps an AggregatedReport and attaches per-job notes."""

    report: AggregatedReport
    notes: Dict[str, List[str]] = field(default_factory=dict)

    def get_notes(self, command: str) -> List[str]:
        """Return notes attached to *command*, or an empty list."""
        return self.notes.get(command, [])


def _notes_for(command: str, rules: List[AnnotationRule]) -> List[str]:
    """Return all notes whose pattern appears in *command*."""
    return [r.note for r in rules if r.pattern in command]


def annotate_report(
    report: AggregatedReport,
    rules: List[AnnotationRule],
) -> AnnotatedReport:
    """Apply *rules* to every job in *report* and return an AnnotatedReport."""
    notes: Dict[str, List[str]] = {}
    for command, summary in report.jobs.items():
        matched = _notes_for(command, rules)
        if matched:
            notes[command] = matched
    return AnnotatedReport(report=report, notes=notes)


def rules_from_dict(data: List[Dict[str, str]]) -> List[AnnotationRule]:
    """Build a list of AnnotationRule objects from a list of plain dicts."""
    rules: List[AnnotationRule] = []
    for item in data:
        pattern = item.get("pattern", "")
        note = item.get("note", "")
        rules.append(AnnotationRule(pattern=pattern, note=note))
    return rules
