"""Tests for cronsight.ranker."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.ranker import RankerError, RankedJob, rank_report


def _entry(cmd: str, success: bool, ts: datetime | None = None) -> CronEntry:
    return CronEntry(
        command=cmd,
        success=success,
        timestamp=ts or datetime(2024, 1, 1, tzinfo=timezone.utc),
        raw="",
    )


def _summary(cmd: str, entries: list[CronEntry]) -> JobSummary:
    s = JobSummary(command=cmd)
    for e in entries:
        s.entries.append(e)
        s.servers.add("host1")
    return s


@pytest.fixture()
def report() -> AggregatedReport:
    r = AggregatedReport()
    r.summaries["backup"] = _summary(
        "backup",
        [
            _entry("backup", True),
            _entry("backup", False),
            _entry("backup", False),
        ],
    )
    r.summaries["cleanup"] = _summary(
        "cleanup",
        [
            _entry("cleanup", True),
            _entry("cleanup", True),
        ],
    )
    r.summaries["sync"] = _summary(
        "sync",
        [
            _entry("sync", False),
            _entry("sync", False),
            _entry("sync", False),
            _entry("sync", False),
        ],
    )
    return r


def test_rank_by_failure_rate_descending(report):
    ranked = rank_report(report, by="failure_rate", descending=True)
    assert ranked[0].command == "sync"
    assert ranked[0].failure_rate == pytest.approx(1.0)
    assert ranked[-1].command == "cleanup"
    assert ranked[-1].failure_rate == pytest.approx(0.0)


def test_rank_by_run_count_descending(report):
    ranked = rank_report(report, by="run_count", descending=True)
    assert ranked[0].command == "sync"
    assert ranked[0].total_runs == 4


def test_rank_assigns_sequential_ranks(report):
    ranked = rank_report(report, by="run_count")
    assert [r.rank for r in ranked] == list(range(1, len(ranked) + 1))


def test_limit_truncates_results(report):
    ranked = rank_report(report, by="failure_rate", limit=2)
    assert len(ranked) == 2


def test_limit_zero_raises(report):
    with pytest.raises(RankerError):
        rank_report(report, by="run_count", limit=0)


def test_invalid_rank_key_raises(report):
    with pytest.raises(RankerError, match="Invalid rank key"):
        rank_report(report, by="nonexistent")  # type: ignore[arg-type]


def test_ranked_job_includes_servers(report):
    ranked = rank_report(report, by="run_count")
    for rj in ranked:
        assert isinstance(rj.servers, list)
        assert len(rj.servers) > 0


def test_rank_ascending(report):
    ranked = rank_report(report, by="failure_rate", descending=False)
    assert ranked[0].failure_rate == pytest.approx(0.0)
