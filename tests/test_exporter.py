"""Tests for cronsight.exporter."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.exporter import export_csv, export_json


@pytest.fixture()
def sample_report() -> AggregatedReport:
    summaries = [
        JobSummary(
            command="/usr/bin/backup.sh",
            server="web-01",
            total_runs=10,
            successful_runs=9,
            failed_runs=1,
            first_run=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            last_run=datetime(2024, 1, 10, 0, 0, tzinfo=timezone.utc),
        ),
        JobSummary(
            command="/usr/bin/cleanup.sh",
            server="db-01",
            total_runs=5,
            successful_runs=5,
            failed_runs=0,
            first_run=datetime(2024, 1, 2, 0, 0, tzinfo=timezone.utc),
            last_run=datetime(2024, 1, 6, 0, 0, tzinfo=timezone.utc),
        ),
    ]
    return AggregatedReport(
        summaries=summaries,
        servers={"web-01", "db-01"},
        generated_at=datetime(2024, 1, 11, 12, 0, tzinfo=timezone.utc),
    )


def test_export_json_contains_jobs(sample_report):
    result = json.loads(export_json(sample_report))
    assert len(result["jobs"]) == 2


def test_export_json_job_fields(sample_report):
    result = json.loads(export_json(sample_report))
    job = next(j for j in result["jobs"] if j["command"] == "/usr/bin/backup.sh")
    assert job["total_runs"] == 10
    assert job["successful_runs"] == 9
    assert job["failed_runs"] == 1
    assert job["success_rate"] == pytest.approx(0.9)
    assert job["server"] == "web-01"


def test_export_json_includes_servers(sample_report):
    result = json.loads(export_json(sample_report))
    assert set(result["servers"]) == {"web-01", "db-01"}


def test_export_json_timestamps(sample_report):
    result = json.loads(export_json(sample_report))
    job = next(j for j in result["jobs"] if j["command"] == "/usr/bin/backup.sh")
    assert job["first_run"] == "2024-01-01T00:00:00+00:00"
    assert job["last_run"] == "2024-01-10T00:00:00+00:00"


def test_export_csv_has_header(sample_report):
    result = export_csv(sample_report)
    reader = csv.DictReader(io.StringIO(result))
    assert "command" in (reader.fieldnames or [])
    assert "success_rate" in (reader.fieldnames or [])


def test_export_csv_row_count(sample_report):
    result = export_csv(sample_report)
    reader = csv.DictReader(io.StringIO(result))
    rows = list(reader)
    assert len(rows) == 2


def test_export_csv_values(sample_report):
    result = export_csv(sample_report)
    reader = csv.DictReader(io.StringIO(result))
    rows = {r["command"]: r for r in reader}
    assert rows["/usr/bin/cleanup.sh"]["failed_runs"] == "0"
    assert rows["/usr/bin/cleanup.sh"]["success_rate"] == "1.0"


def test_export_json_none_timestamps():
    summary = JobSummary(
        command="/bin/test",
        server="s1",
        total_runs=0,
        successful_runs=0,
        failed_runs=0,
        first_run=None,
        last_run=None,
    )
    report = AggregatedReport(
        summaries=[summary],
        servers={"s1"},
        generated_at=None,
    )
    result = json.loads(export_json(report))
    assert result["jobs"][0]["first_run"] is None
    assert result["jobs"][0]["last_run"] is None
    assert result["generated_at"] is None
