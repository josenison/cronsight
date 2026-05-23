"""Tests for cronsight.snapshot — save/load report snapshots."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.snapshot import SnapshotError, load_snapshot, save_snapshot


def _make_entry(job: str, status: str, server: str = "host1") -> CronEntry:
    return CronEntry(
        timestamp=datetime(2024, 5, 1, 12, 0, 0),
        server=server,
        job=job,
        status=status,
        message=None,
    )


@pytest.fixture()
def sample_report() -> AggregatedReport:
    s1 = JobSummary(
        job="/usr/bin/backup.sh",
        servers={"host1"},
        entries=[_make_entry("/usr/bin/backup.sh", "success")],
    )
    s2 = JobSummary(
        job="/usr/bin/cleanup.sh",
        servers={"host2"},
        entries=[
            _make_entry("/usr/bin/cleanup.sh", "success", "host2"),
            _make_entry("/usr/bin/cleanup.sh", "failure", "host2"),
        ],
    )
    return AggregatedReport(jobs=[s1, s2])


def test_save_creates_file(tmp_path, sample_report):
    dest = tmp_path / "snap.json"
    save_snapshot(sample_report, dest)
    assert dest.exists()


def test_save_creates_parent_dirs(tmp_path, sample_report):
    dest = tmp_path / "nested" / "dir" / "snap.json"
    save_snapshot(sample_report, dest)
    assert dest.exists()


def test_save_snapshot_valid_json(tmp_path, sample_report):
    dest = tmp_path / "snap.json"
    save_snapshot(sample_report, dest)
    payload = json.loads(dest.read_text())
    assert payload["version"] == 1
    assert "saved_at" in payload
    assert len(payload["jobs"]) == 2


def test_roundtrip_preserves_job_names(tmp_path, sample_report):
    dest = tmp_path / "snap.json"
    save_snapshot(sample_report, dest)
    loaded = load_snapshot(dest)
    assert [s.job for s in loaded.jobs] == [s.job for s in sample_report.jobs]


def test_roundtrip_preserves_entry_count(tmp_path, sample_report):
    dest = tmp_path / "snap.json"
    save_snapshot(sample_report, dest)
    loaded = load_snapshot(dest)
    for orig, restored in zip(sample_report.jobs, loaded.jobs):
        assert len(restored.entries) == len(orig.entries)


def test_roundtrip_preserves_servers(tmp_path, sample_report):
    dest = tmp_path / "snap.json"
    save_snapshot(sample_report, dest)
    loaded = load_snapshot(dest)
    assert loaded.jobs[1].servers == {"host2"}


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(SnapshotError, match="not found"):
        load_snapshot(tmp_path / "nonexistent.json")


def test_load_invalid_json_raises(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not-json", encoding="utf-8")
    with pytest.raises(SnapshotError, match="Failed to read"):
        load_snapshot(bad)


def test_load_wrong_version_raises(tmp_path):
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps({"version": 99, "jobs": []}), encoding="utf-8")
    with pytest.raises(SnapshotError, match="Unsupported snapshot version"):
        load_snapshot(snap)
