"""Tests for cronsight.replayer."""

from __future__ import annotations

from datetime import datetime

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.replayer import (
    ReplayerError,
    ReplayReport,
    replay_report,
)


def _entry(ts: datetime, exit_code: int = 0) -> CronEntry:
    return CronEntry(
        timestamp=ts,
        command="/usr/bin/backup",
        exit_code=exit_code,
        raw="",
    )


def _summary(*entries: CronEntry) -> JobSummary:
    return JobSummary(
        command="/usr/bin/backup",
        entries=list(entries),
        servers=["web01"],
    )


def _report(*entries: CronEntry) -> AggregatedReport:
    s = _summary(*entries)
    return AggregatedReport(jobs={"/usr/bin/backup": s})


def test_replay_report_returns_replay_report():
    rpt = _report(_entry(datetime(2024, 1, 1, 6, 0)))
    result = replay_report(rpt)
    assert isinstance(result, ReplayReport)


def test_replay_report_count_matches_jobs():
    rpt = _report(_entry(datetime(2024, 1, 1, 6, 0)))
    result = replay_report(rpt)
    assert result.count == 1


def test_replay_report_event_count():
    rpt = _report(
        _entry(datetime(2024, 1, 1, 6, 0)),
        _entry(datetime(2024, 1, 2, 6, 0)),
    )
    result = replay_report(rpt)
    assert result.timelines[0].event_count == 2


def test_replay_report_failure_count():
    rpt = _report(
        _entry(datetime(2024, 1, 1, 6, 0), exit_code=0),
        _entry(datetime(2024, 1, 2, 6, 0), exit_code=1),
    )
    result = replay_report(rpt)
    assert result.timelines[0].failure_count == 1


def test_replay_report_filters_by_since():
    rpt = _report(
        _entry(datetime(2024, 1, 1, 6, 0)),
        _entry(datetime(2024, 1, 3, 6, 0)),
    )
    result = replay_report(rpt, since=datetime(2024, 1, 2, 0, 0))
    assert result.timelines[0].event_count == 1


def test_replay_report_filters_by_until():
    rpt = _report(
        _entry(datetime(2024, 1, 1, 6, 0)),
        _entry(datetime(2024, 1, 3, 6, 0)),
    )
    result = replay_report(rpt, until=datetime(2024, 1, 2, 0, 0))
    assert result.timelines[0].event_count == 1


def test_replay_report_raises_on_empty_report():
    rpt = AggregatedReport(jobs={})
    with pytest.raises(ReplayerError):
        replay_report(rpt)


def test_replay_event_str_success():
    rpt = _report(_entry(datetime(2024, 6, 15, 12, 30, 0)))
    ev = replay_report(rpt).timelines[0].events[0]
    assert "✓" in str(ev)
    assert "2024-06-15" in str(ev)


def test_replay_event_str_failure():
    rpt = _report(_entry(datetime(2024, 6, 15, 12, 30, 0), exit_code=2))
    ev = replay_report(rpt).timelines[0].events[0]
    assert "✗" in str(ev)
