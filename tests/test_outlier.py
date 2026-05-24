"""Tests for cronsight.outlier."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.outlier import OutlierError, OutlierJob, detect_outliers


def _entry(success: bool, cmd: str = "backup.sh") -> CronEntry:
    return CronEntry(
        timestamp=datetime(2024, 1, 1, 6, 0),
        command=cmd,
        success=success,
    )


def _summary(entries, servers=("srv1",)) -> JobSummary:
    s = JobSummary()
    s.entries.extend(entries)
    s.servers.extend(servers)
    return s


def _report(jobs: dict) -> AggregatedReport:
    r = AggregatedReport()
    r.jobs.update(jobs)
    return r


# --- detect_outliers ---

def test_detect_outliers_returns_empty_when_fewer_than_two_eligible():
    report = _report({"job.sh": _summary([_entry(True), _entry(False)])})
    result = detect_outliers(report, min_runs=2)
    assert not result.has_outliers()


def test_detect_outliers_flags_low_success_rate():
    jobs = {
        "good1.sh": _summary([_entry(True)] * 10),
        "good2.sh": _summary([_entry(True)] * 10),
        "good3.sh": _summary([_entry(True)] * 10),
        "bad.sh": _summary([_entry(False)] * 10),
    }
    result = detect_outliers(_report(jobs), z_threshold=1.5, min_runs=2)
    assert result.has_outliers()
    commands = [o.command for o in result.outliers]
    assert "bad.sh" in commands


def test_detect_outliers_reason_low_for_negative_z():
    jobs = {
        "good1.sh": _summary([_entry(True)] * 10),
        "good2.sh": _summary([_entry(True)] * 10),
        "good3.sh": _summary([_entry(True)] * 10),
        "bad.sh": _summary([_entry(False)] * 10),
    }
    result = detect_outliers(_report(jobs), z_threshold=1.5, min_runs=2)
    bad = next(o for o in result.outliers if o.command == "bad.sh")
    assert bad.reason == "low success rate"
    assert bad.z_score < 0


def test_detect_outliers_skips_jobs_below_min_runs():
    jobs = {
        "good1.sh": _summary([_entry(True)] * 10),
        "good2.sh": _summary([_entry(True)] * 10),
        "rare.sh": _summary([_entry(False)]),  # only 1 run
    }
    result = detect_outliers(_report(jobs), z_threshold=1.0, min_runs=2)
    commands = [o.command for o in result.outliers]
    assert "rare.sh" not in commands


def test_detect_outliers_raises_on_invalid_z_threshold():
    report = _report({"a.sh": _summary([_entry(True)])})
    with pytest.raises(OutlierError, match="z_threshold"):
        detect_outliers(report, z_threshold=0)


def test_detect_outliers_raises_on_invalid_min_runs():
    report = _report({"a.sh": _summary([_entry(True)])})
    with pytest.raises(OutlierError, match="min_runs"):
        detect_outliers(report, min_runs=0)


def test_outlier_job_str_contains_command():
    o = OutlierJob(
        command="myjob.sh",
        server="host1",
        total_runs=5,
        success_rate=0.4,
        z_score=-2.1,
        reason="low success rate",
    )
    assert "myjob.sh" in str(o)
    assert "host1" in str(o)


def test_outlier_report_count_matches_outliers():
    jobs = {
        "good1.sh": _summary([_entry(True)] * 10),
        "good2.sh": _summary([_entry(True)] * 10),
        "good3.sh": _summary([_entry(True)] * 10),
        "bad.sh": _summary([_entry(False)] * 10),
    }
    result = detect_outliers(_report(jobs), z_threshold=1.5, min_runs=2)
    assert result.count == len(result.outliers)
