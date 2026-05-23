"""Tests for cronsight.tagging."""
import pytest
from datetime import datetime, timezone

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.tagging import (
    TagRule,
    TaggingError,
    TaggedReport,
    tag_report,
    rules_from_dict,
)


def _make_entry(cmd: str, rc: int = 0) -> CronEntry:
    return CronEntry(
        timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        command=cmd,
        return_code=rc,
        server="host1",
    )


def _make_summary(cmd: str, rc: int = 0) -> JobSummary:
    entry = _make_entry(cmd, rc)
    return JobSummary(
        command=cmd,
        entries=[entry],
        servers={"host1"},
    )


@pytest.fixture
def sample_report() -> AggregatedReport:
    jobs = {
        "/usr/bin/backup.sh": _make_summary("/usr/bin/backup.sh"),
        "/usr/bin/cleanup.sh": _make_summary("/usr/bin/cleanup.sh"),
        "/opt/deploy.sh": _make_summary("/opt/deploy.sh"),
    }
    return AggregatedReport(jobs=jobs)


def test_tag_report_assigns_matching_tags(sample_report):
    rules = [TagRule(tag="backup", pattern="backup")]
    result = tag_report(sample_report, rules)
    assert result.tags_for("/usr/bin/backup.sh") == ["backup"]


def test_tag_report_no_match_returns_empty(sample_report):
    rules = [TagRule(tag="backup", pattern="backup")]
    result = tag_report(sample_report, rules)
    assert result.tags_for("/opt/deploy.sh") == []


def test_tag_report_multiple_rules_can_match(sample_report):
    rules = [
        TagRule(tag="usr", pattern="/usr"),
        TagRule(tag="shell", pattern=".sh"),
    ]
    result = tag_report(sample_report, rules)
    tags = result.tags_for("/usr/bin/backup.sh")
    assert "usr" in tags
    assert "shell" in tags


def test_tag_report_raises_on_empty_rules(sample_report):
    with pytest.raises(TaggingError):
        tag_report(sample_report, [])


def test_tagged_report_wraps_original(sample_report):
    rules = [TagRule(tag="deploy", pattern="deploy")]
    result = tag_report(sample_report, rules)
    assert result.report is sample_report


def test_rules_from_dict_parses_correctly():
    raw = [{"tag": "backup", "pattern": "backup.sh"}]
    rules = rules_from_dict(raw)
    assert len(rules) == 1
    assert rules[0].tag == "backup"
    assert rules[0].pattern == "backup.sh"


def test_rules_from_dict_raises_on_missing_tag():
    with pytest.raises(TaggingError):
        rules_from_dict([{"pattern": "backup.sh"}])


def test_rules_from_dict_raises_on_missing_pattern():
    with pytest.raises(TaggingError):
        rules_from_dict([{"tag": "backup"}])


def test_rules_from_dict_raises_on_empty_values():
    with pytest.raises(TaggingError):
        rules_from_dict([{"tag": "", "pattern": "backup"}])
