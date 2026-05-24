"""Tests for cronsight.heatmap."""

from __future__ import annotations

from datetime import datetime

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.heatmap import (
    HeatmapError,
    HeatmapReport,
    JobHeatmap,
    HourBucket,
    build_heatmap,
)
from cronsight.parser import CronEntry


def _entry(hour: int, success: bool = True) -> CronEntry:
    return CronEntry(
        timestamp=datetime(2024, 1, 15, hour, 0, 0),
        server="srv1",
        command="/usr/bin/backup",
        success=success,
    )


def _make_summary(entries) -> JobSummary:
    return JobSummary(command="/usr/bin/backup", entries=entries)


@pytest.fixture
def report():
    entries = [
        _entry(2),
        _entry(2),
        _entry(14, success=False),
        _entry(14),
        _entry(3),
    ]
    summary = _make_summary(entries)
    return AggregatedReport(jobs={"/usr/bin/backup": summary})


def test_build_heatmap_returns_heatmap_report(report):
    result = build_heatmap(report)
    assert isinstance(result, HeatmapReport)


def test_build_heatmap_contains_job(report):
    result = build_heatmap(report)
    assert "/usr/bin/backup" in result.jobs


def test_bucket_run_count_correct(report):
    result = build_heatmap(report)
    hm = result.get("/usr/bin/backup")
    assert hm.bucket(2).run_count == 2
    assert hm.bucket(14).run_count == 2
    assert hm.bucket(3).run_count == 1


def test_bucket_failure_count_correct(report):
    result = build_heatmap(report)
    hm = result.get("/usr/bin/backup")
    assert hm.bucket(14).failure_count == 1
    assert hm.bucket(2).failure_count == 0


def test_bucket_failure_rate(report):
    result = build_heatmap(report)
    hm = result.get("/usr/bin/backup")
    assert hm.bucket(14).failure_rate == pytest.approx(0.5)
    assert hm.bucket(2).failure_rate == pytest.approx(0.0)


def test_zero_run_bucket_failure_rate_is_zero(report):
    result = build_heatmap(report)
    hm = result.get("/usr/bin/backup")
    assert hm.bucket(0).failure_rate == 0.0


def test_peak_hour_is_most_frequent(report):
    result = build_heatmap(report)
    hm = result.get("/usr/bin/backup")
    assert hm.peak_hour in (2, 14)


def test_bucket_invalid_hour_raises(report):
    result = build_heatmap(report)
    hm = result.get("/usr/bin/backup")
    with pytest.raises(HeatmapError):
        hm.bucket(24)


def test_entries_without_timestamp_are_skipped():
    entry = CronEntry(timestamp=None, server="srv1", command="/bin/job", success=True)
    summary = JobSummary(command="/bin/job", entries=[entry])
    report = AggregatedReport(jobs={"/bin/job": summary})
    result = build_heatmap(report)
    hm = result.get("/bin/job")
    assert all(b.run_count == 0 for b in hm.buckets)


def test_hour_bucket_success_count():
    b = HourBucket(hour=5, run_count=10, failure_count=3)
    assert b.success_count == 7
