"""Tag-based labelling for cron job summaries."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


@dataclass
class TaggingError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass
class TagRule:
    """Assign *tag* to any job whose command matches *pattern*."""
    tag: str
    pattern: str  # substring match against JobSummary.command


@dataclass
class TaggedReport:
    """Wraps an AggregatedReport and attaches tags to each job."""
    report: AggregatedReport
    tags: Dict[str, List[str]] = field(default_factory=dict)  # command -> [tag]

    def tags_for(self, command: str) -> List[str]:
        return self.tags.get(command, [])


def _apply_rules(summary: JobSummary, rules: List[TagRule]) -> List[str]:
    """Return list of tags whose pattern appears in *summary.command*."""
    return [
        rule.tag
        for rule in rules
        if rule.pattern in summary.command
    ]


def tag_report(
    report: AggregatedReport,
    rules: List[TagRule],
) -> TaggedReport:
    """Apply *rules* to every job in *report* and return a TaggedReport."""
    if not rules:
        raise TaggingError("At least one TagRule is required")

    tag_map: Dict[str, List[str]] = {}
    for command, summary in report.jobs.items():
        matched = _apply_rules(summary, rules)
        if matched:
            tag_map[command] = matched

    return TaggedReport(report=report, tags=tag_map)


def rules_from_dict(raw: List[Dict[str, str]]) -> List[TagRule]:
    """Parse a list of ``{tag, pattern}`` dicts into TagRule objects."""
    rules: List[TagRule] = []
    for item in raw:
        tag = item.get("tag", "").strip()
        pattern = item.get("pattern", "").strip()
        if not tag or not pattern:
            raise TaggingError(
                f"Each rule must have 'tag' and 'pattern' keys, got: {item!r}"
            )
        rules.append(TagRule(tag=tag, pattern=pattern))
    return rules
