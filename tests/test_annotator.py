"""Tests for cronsight.annotator."""

from __future__ import annotations

from datetime import datetime
from typing import List

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.annotator import (
    AnnotationRule,
    AnnotatorError,
    annotate_report,
    rules_from_dict,
)
from cronsight.parser import CronEntry


def _make_entry(cmd: str, rc: int = 0) -> CronEntry:
    return CronEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        command=cmd,
        return_code=rc,
        server="srv1",
    )


def _make_summary(cmd: str, rc: int = 0) -> JobSummary:
    return JobSummary(command=cmd, entries=[_make_entry(cmd, rc)], servers={"srv1"})


def _make_report(*commands: str) -> AggregatedReport:
    jobs = {cmd: _make_summary(cmd) for cmd in commands}
    return AggregatedReport(jobs=jobs)


# ---------------------------------------------------------------------------
# AnnotationRule validation
# ---------------------------------------------------------------------------

def test_annotation_rule_empty_pattern_raises():
    with pytest.raises(AnnotatorError):
        AnnotationRule(pattern="", note="some note")


def test_annotation_rule_empty_note_raises():
    with pytest.raises(AnnotatorError):
        AnnotationRule(pattern="backup", note="")


def test_annotation_rule_valid():
    rule = AnnotationRule(pattern="backup", note="nightly backup job")
    assert rule.pattern == "backup"
    assert rule.note == "nightly backup job"


# ---------------------------------------------------------------------------
# annotate_report
# ---------------------------------------------------------------------------

def test_annotate_report_no_rules_returns_empty_notes():
    report = _make_report("/usr/bin/backup.sh")
    result = annotate_report(report, rules=[])
    assert result.notes == {}


def test_annotate_report_matching_rule_attaches_note():
    report = _make_report("/usr/bin/backup.sh")
    rules = [AnnotationRule(pattern="backup", note="nightly backup")]
    result = annotate_report(report, rules)
    assert "/usr/bin/backup.sh" in result.notes
    assert "nightly backup" in result.notes["/usr/bin/backup.sh"]


def test_annotate_report_non_matching_rule_excluded():
    report = _make_report("/usr/bin/cleanup.sh")
    rules = [AnnotationRule(pattern="backup", note="nightly backup")]
    result = annotate_report(report, rules)
    assert result.notes == {}


def test_annotate_report_multiple_rules_multiple_notes():
    report = _make_report("/usr/bin/backup-and-sync.sh")
    rules = [
        AnnotationRule(pattern="backup", note="backup job"),
        AnnotationRule(pattern="sync", note="sync job"),
    ]
    result = annotate_report(report, rules)
    notes = result.notes["/usr/bin/backup-and-sync.sh"]
    assert "backup job" in notes
    assert "sync job" in notes


def test_get_notes_returns_empty_for_unknown_command():
    report = _make_report("/usr/bin/backup.sh")
    result = annotate_report(report, rules=[])
    assert result.get_notes("/nonexistent") == []


def test_annotate_report_preserves_original_report():
    report = _make_report("/usr/bin/backup.sh")
    result = annotate_report(report, rules=[])
    assert result.report is report


# ---------------------------------------------------------------------------
# rules_from_dict
# ---------------------------------------------------------------------------

def test_rules_from_dict_builds_rules():
    data = [{"pattern": "backup", "note": "nightly backup"}]
    rules = rules_from_dict(data)
    assert len(rules) == 1
    assert rules[0].pattern == "backup"
    assert rules[0].note == "nightly backup"


def test_rules_from_dict_empty_list():
    assert rules_from_dict([]) == []
