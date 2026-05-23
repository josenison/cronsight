"""Integration-style tests combining tagging with snapshot round-trip."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.tagging import TagRule, tag_report, rules_from_dict


def _entry(cmd: str, rc: int = 0, server: str = "host1") -> CronEntry:
    return CronEntry(
        timestamp=datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc),
        command=cmd,
        return_code=rc,
        server=server,
    )


def _report(*commands: str) -> AggregatedReport:
    jobs = {
        cmd: JobSummary(command=cmd, entries=[_entry(cmd)], servers={"host1"})
        for cmd in commands
    }
    return AggregatedReport(jobs=jobs)


def test_no_jobs_match_returns_empty_tags():
    report = _report("/opt/app.py")
    rules = [TagRule(tag="backup", pattern="backup")]
    tagged = tag_report(report, rules)
    assert tagged.tags == {}


def test_all_jobs_tagged_when_pattern_universal():
    report = _report("/usr/bin/a.sh", "/usr/bin/b.sh")
    rules = [TagRule(tag="shell", pattern=".sh")]
    tagged = tag_report(report, rules)
    assert len(tagged.tags) == 2
    for tags in tagged.tags.values():
        assert "shell" in tags


def test_rules_from_dict_round_trip():
    raw = [
        {"tag": "db", "pattern": "pg_dump"},
        {"tag": "deploy", "pattern": "deploy.sh"},
    ]
    rules = rules_from_dict(raw)
    assert [(r.tag, r.pattern) for r in rules] == [
        ("db", "pg_dump"),
        ("deploy", "deploy.sh"),
    ]


def test_tag_report_preserves_original_report():
    report = _report("/usr/bin/backup.sh")
    rules = [TagRule(tag="backup", pattern="backup")]
    tagged = tag_report(report, rules)
    assert tagged.report is report
    assert tagged.report.jobs == report.jobs


def test_multiple_tags_on_single_job():
    report = _report("/usr/bin/backup_db.sh")
    rules = [
        TagRule(tag="backup", pattern="backup"),
        TagRule(tag="db", pattern="_db"),
        TagRule(tag="shell", pattern=".sh"),
    ]
    tagged = tag_report(report, rules)
    tags = tagged.tags_for("/usr/bin/backup_db.sh")
    assert set(tags) == {"backup", "db", "shell"}
