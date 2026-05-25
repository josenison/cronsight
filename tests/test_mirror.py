"""Unit tests for cronsight.mirror."""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from cronsight.mirror import MirrorRow, MirrorReport, mirror_reports, MirrorError
from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from datetime import datetime


def _entry(cmd: str, exit_code: int = 0) -> CronEntry:
    return CronEntry(
        timestamp=datetime(2024, 1, 1, 10, 0, 0),
        server="srv1",
        command=cmd,
        exit_code=exit_code,
    )


def _summary(cmd: str, entries: list[CronEntry]) -> JobSummary:
    s = JobSummary(command=cmd)
    s.entries = entries
    return s


def _report(*summaries: JobSummary) -> AggregatedReport:
    r = AggregatedReport()
    r.summaries = list(summaries)
    return r


def test_mirror_row_str_both_sides():
    row = MirrorRow(command="backup.sh", left_runs=10, right_runs=8,
                    left_success_rate=1.0, right_success_rate=0.75)
    text = str(row)
    assert "backup.sh" in text
    assert "100.0%" in text
    assert "75.0%" in text


def test_mirror_row_str_only_in_left():
    row = MirrorRow(command="old.sh", left_runs=5, right_runs=0,
                    left_success_rate=1.0, right_success_rate=None,
                    only_in_left=True)
    assert "[left only]" in str(row)


def test_mirror_row_str_only_in_right():
    row = MirrorRow(command="new.sh", left_runs=0, right_runs=3,
                    left_success_rate=None, right_success_rate=1.0,
                    only_in_right=True)
    assert "[right only]" in str(row)


def test_mirror_report_count():
    report = MirrorReport(rows=[MagicMock(), MagicMock()])
    assert report.count == 2


def test_mirror_report_divergent_rows_threshold():
    rows = [
        MirrorRow("a.sh", 10, 10, 1.0, 0.8),   # diff = 0.20 → divergent
        MirrorRow("b.sh", 10, 10, 1.0, 0.95),  # diff = 0.05 → ok
        MirrorRow("c.sh", 5, 0, 1.0, None, only_in_left=True),  # divergent
    ]
    report = MirrorReport(rows=rows)
    divergent = report.divergent_rows
    assert len(divergent) == 2
    assert rows[0] in divergent
    assert rows[2] in divergent


def test_mirror_reports_all_shared():
    left = _report(_summary("job.sh", [_entry("job.sh", 0), _entry("job.sh", 0)]))
    right = _report(_summary("job.sh", [_entry("job.sh", 1)]))
    result = mirror_reports(left, right)
    assert result.count == 1
    row = result.rows[0]
    assert row.command == "job.sh"
    assert row.left_runs == 2
    assert row.right_runs == 1
    assert row.left_success_rate == 1.0
    assert row.right_success_rate == 0.0


def test_mirror_reports_only_in_left():
    left = _report(_summary("old.sh", [_entry("old.sh")]))
    right = _report()
    result = mirror_reports(left, right)
    assert result.count == 1
    assert result.rows[0].only_in_left is True


def test_mirror_reports_only_in_right():
    left = _report()
    right = _report(_summary("new.sh", [_entry("new.sh")]))
    result = mirror_reports(left, right)
    assert result.count == 1
    assert result.rows[0].only_in_right is True


def test_mirror_reports_raises_on_invalid_input():
    with pytest.raises(MirrorError):
        mirror_reports("not a report", MagicMock())  # type: ignore


def test_mirror_reports_empty_both():
    result = mirror_reports(_report(), _report())
    assert result.count == 0
