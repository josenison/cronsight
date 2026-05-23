"""Tests for cronsight.writer."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.writer import WriterError, write_report


@pytest.fixture()
def simple_report() -> AggregatedReport:
    return AggregatedReport(
        summaries=[
            JobSummary(
                command="/bin/task",
                server="host-1",
                total_runs=3,
                successful_runs=3,
                failed_runs=0,
                first_run=datetime(2024, 3, 1, tzinfo=timezone.utc),
                last_run=datetime(2024, 3, 3, tzinfo=timezone.utc),
            )
        ],
        servers={"host-1"},
        generated_at=datetime(2024, 3, 4, tzinfo=timezone.utc),
    )


def test_write_json_to_stdout(capsys, simple_report):
    write_report(simple_report, fmt="json")
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert len(data["jobs"]) == 1
    assert data["jobs"][0]["command"] == "/bin/task"


def test_write_csv_to_stdout(capsys, simple_report):
    write_report(simple_report, fmt="csv")
    captured = capsys.readouterr()
    assert "command" in captured.out
    assert "/bin/task" in captured.out


def test_write_json_to_file(tmp_path, simple_report):
    out_file = tmp_path / "report.json"
    write_report(simple_report, fmt="json", output_path=str(out_file))
    data = json.loads(out_file.read_text())
    assert data["jobs"][0]["server"] == "host-1"


def test_write_csv_to_file(tmp_path, simple_report):
    out_file = tmp_path / "report.csv"
    write_report(simple_report, fmt="csv", output_path=str(out_file))
    content = out_file.read_text()
    assert "/bin/task" in content


def test_write_creates_parent_dirs(tmp_path, simple_report):
    out_file = tmp_path / "nested" / "deep" / "report.json"
    write_report(simple_report, fmt="json", output_path=str(out_file))
    assert out_file.exists()


def test_write_invalid_format_raises(simple_report):
    with pytest.raises(WriterError, match="Unknown export format"):
        write_report(simple_report, fmt="xml")  # type: ignore[arg-type]


def test_write_unwritable_path_raises(simple_report):
    with pytest.raises(WriterError, match="Could not write"):
        write_report(simple_report, fmt="json", output_path="/no_permission_dir/out.json")
