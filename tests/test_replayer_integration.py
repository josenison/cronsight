"""Integration tests for replayer: end-to-end timeline reconstruction."""

from __future__ import annotations

from datetime import datetime

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.replayer import replay_report


def _e(ts: datetime, cmd: str, exit_code: int = 0) -> CronEntry:
    return CronEntry(timestamp=ts, command=cmd, exit_code=exit_code, raw="")


def _report(jobs: dict) -> AggregatedReport:
    summaries = {}
    for cmd, entries in jobs.items():
        servers = list({e.command.split()[0] for e in entries} or {"srv"})
        summaries[cmd] = JobSummary(command=cmd, entries=entries, servers=["srv"])
    return AggregatedReport(jobs=summaries)


def test_multiple_jobs_each_get_own_timeline():
    rpt = _report({
        "/bin/alpha": [_e(datetime(2024, 1, 1, 1, 0), "/bin/alpha")],
        "/bin/beta": [_e(datetime(2024, 1, 1, 2, 0), "/bin/beta")],
    })
    result = replay_report(rpt)
    commands = {tl.command for tl in result.timelines}
    assert "/bin/alpha" in commands
    assert "/bin/beta" in commands


def test_events_sorted_by_timestamp():
    rpt = _report({
        "/bin/job": [
            _e(datetime(2024, 3, 1, 10, 0), "/bin/job"),
            _e(datetime(2024, 1, 1, 8, 0), "/bin/job"),
            _e(datetime(2024, 2, 1, 9, 0), "/bin/job"),
        ]
    })
    result = replay_report(rpt)
    timestamps = [ev.timestamp for ev in result.timelines[0].events]
    assert timestamps == sorted(timestamps)


def test_since_and_until_combined():
    rpt = _report({
        "/bin/job": [
            _e(datetime(2024, 1, 1), "/bin/job"),
            _e(datetime(2024, 2, 1), "/bin/job"),
            _e(datetime(2024, 3, 1), "/bin/job"),
        ]
    })
    result = replay_report(
        rpt,
        since=datetime(2024, 1, 15),
        until=datetime(2024, 2, 15),
    )
    assert result.timelines[0].event_count == 1


def test_all_failures_reflected_in_failure_count():
    rpt = _report({
        "/bin/fail": [
            _e(datetime(2024, 1, 1), "/bin/fail", exit_code=1),
            _e(datetime(2024, 1, 2), "/bin/fail", exit_code=2),
            _e(datetime(2024, 1, 3), "/bin/fail", exit_code=0),
        ]
    })
    result = replay_report(rpt)
    assert result.timelines[0].failure_count == 2
