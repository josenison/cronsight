"""Tests for cronsight.trend module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronsight.trend import JobTrend, TrendPoint, analyze_trends, build_trend


def _make_entry(timestamp: str, exit_code: int, server: str = "host1"):
    entry = MagicMock()
    entry.timestamp = timestamp
    entry.exit_code = exit_code
    entry.server = server
    return entry


def _make_summary(command: str, entries):
    summary = MagicMock()
    summary.command = command
    summary.entries = entries
    return summary


@pytest.fixture
def simple_summary():
    entries = [
        _make_entry("2024-01-01 00:00", 0),
        _make_entry("2024-01-02 00:00", 1),
        _make_entry("2024-01-03 00:00", 0),
    ]
    return _make_summary("/usr/bin/backup.sh", entries)


def test_build_trend_command(simple_summary):
    trend = build_trend(simple_summary)
    assert trend.command == "/usr/bin/backup.sh"


def test_build_trend_point_count(simple_summary):
    trend = build_trend(simple_summary)
    assert trend.total == 3


def test_build_trend_success_count(simple_summary):
    trend = build_trend(simple_summary)
    assert trend.success_count == 2


def test_build_trend_failure_count(simple_summary):
    trend = build_trend(simple_summary)
    assert trend.failure_count == 1


def test_success_rate(simple_summary):
    trend = build_trend(simple_summary)
    assert pytest.approx(trend.success_rate, 0.01) == 2 / 3


def test_success_rate_empty():
    summary = _make_summary("/bin/empty", [])
    trend = build_trend(summary)
    assert trend.success_rate is None


def test_is_degrading_true():
    entries = [
        _make_entry("2024-01-01", 0),
        _make_entry("2024-01-02", 1),
        _make_entry("2024-01-03", 1),
        _make_entry("2024-01-04", 1),
    ]
    trend = build_trend(_make_summary("/bin/job", entries))
    assert trend.is_degrading is True


def test_is_degrading_false(simple_summary):
    trend = build_trend(simple_summary)
    assert trend.is_degrading is False


def test_is_recovering_true():
    entries = [
        _make_entry("2024-01-01", 1),
        _make_entry("2024-01-02", 0),
        _make_entry("2024-01-03", 0),
        _make_entry("2024-01-04", 0),
    ]
    trend = build_trend(_make_summary("/bin/job", entries))
    assert trend.is_recovering is True


def test_is_recovering_false_all_passing():
    entries = [
        _make_entry("2024-01-01", 0),
        _make_entry("2024-01-02", 0),
        _make_entry("2024-01-03", 0),
        _make_entry("2024-01-04", 0),
    ]
    trend = build_trend(_make_summary("/bin/job", entries))
    assert trend.is_recovering is False


def test_analyze_trends_returns_all():
    summaries = [
        _make_summary("/bin/a", [_make_entry("2024-01-01", 0)]),
        _make_summary("/bin/b", [_make_entry("2024-01-01", 1)]),
    ]
    trends = analyze_trends(summaries)
    assert len(trends) == 2
    assert {t.command for t in trends} == {"/bin/a", "/bin/b"}
