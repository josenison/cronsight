"""Tests for cronsight.forecaster."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cronsight.forecaster import (
    ForecastWindow,
    ForecastReport,
    ForecasterError,
    _is_overdue,
    forecast,
)
from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry


NOW = datetime(2024, 6, 1, 12, 0, 0)


def _make_entry(status: str = "success") -> CronEntry:
    return CronEntry(
        timestamp=NOW - timedelta(hours=1),
        server="host1",
        command="/usr/bin/backup",
        status=status,
    )


def _make_summary(command: str = "/usr/bin/backup", last_run: datetime = None) -> JobSummary:
    entry = CronEntry(
        timestamp=last_run or (NOW - timedelta(hours=1)),
        server="host1",
        command=command,
        status="success",
    )
    return JobSummary(command=command, entries=[entry], servers={"host1"})


def _make_report(*summaries: JobSummary) -> AggregatedReport:
    return AggregatedReport(jobs=list(summaries))


# --- ForecastWindow ---

def test_forecast_window_overdue_false_by_default():
    w = ForecastWindow(command="cmd", expression="* * * * *")
    assert w.overdue is False


def test_forecast_window_next_runs_default_empty():
    w = ForecastWindow(command="cmd", expression="* * * * *")
    assert w.next_runs == []


# --- ForecastReport ---

def test_forecast_report_overdue_count_zero_when_none_overdue():
    w1 = ForecastWindow(command="a", expression="* * * * *", overdue=False)
    w2 = ForecastWindow(command="b", expression="* * * * *", overdue=False)
    r = ForecastReport(generated_at=NOW, windows=[w1, w2])
    assert r.overdue_count == 0


def test_forecast_report_overdue_count_reflects_overdue_windows():
    w1 = ForecastWindow(command="a", expression="* * * * *", overdue=True)
    w2 = ForecastWindow(command="b", expression="* * * * *", overdue=False)
    r = ForecastReport(generated_at=NOW, windows=[w1, w2])
    assert r.overdue_count == 1


# --- _is_overdue ---

def test_is_overdue_returns_false_when_last_seen_none():
    assert _is_overdue("* * * * *", None, NOW) is False


def test_is_overdue_returns_false_when_last_seen_after_prev_run():
    # last seen 30 seconds ago; prev_run would be within the last minute
    last_seen = NOW - timedelta(seconds=30)
    # patch prev_run to return 2 minutes ago so last_seen > prev
    with patch("cronsight.forecaster.prev_run", return_value=NOW - timedelta(minutes=2)):
        assert _is_overdue("* * * * *", last_seen, NOW) is False


def test_is_overdue_returns_true_when_last_seen_before_prev_run():
    last_seen = NOW - timedelta(hours=2)
    with patch("cronsight.forecaster.prev_run", return_value=NOW - timedelta(minutes=1)):
        assert _is_overdue("* * * * *", last_seen, NOW) is True


# --- forecast ---

def test_forecast_raises_on_empty_expressions():
    report = _make_report()
    with pytest.raises(ForecasterError, match="expressions"):
        forecast(report, {}, now=NOW)


def test_forecast_raises_on_invalid_horizon():
    report = _make_report()
    with pytest.raises(ForecasterError, match="horizon"):
        forecast(report, {"cmd": "* * * * *"}, horizon=0, now=NOW)


def test_forecast_returns_report_with_correct_window_count():
    summary = _make_summary("/usr/bin/backup")
    report = _make_report(summary)
    expressions = {"/usr/bin/backup": "0 * * * *"}
    result = forecast(report, expressions, horizon=3, now=NOW)
    assert len(result.windows) == 1
    assert len(result.windows[0].next_runs) == 3


def test_forecast_window_next_runs_are_in_future():
    summary = _make_summary("/usr/bin/backup")
    report = _make_report(summary)
    expressions = {"/usr/bin/backup": "0 * * * *"}
    result = forecast(report, expressions, horizon=3, now=NOW)
    for ts in result.windows[0].next_runs:
        assert ts > NOW


def test_forecast_unknown_command_has_no_last_seen():
    report = _make_report()  # empty report
    expressions = {"/usr/bin/cleanup": "0 0 * * *"}
    result = forecast(report, expressions, horizon=2, now=NOW)
    assert result.windows[0].last_seen is None


def test_forecast_overdue_flag_set_correctly():
    last_seen = NOW - timedelta(hours=3)
    summary = _make_summary("/usr/bin/backup", last_run=last_seen)
    report = _make_report(summary)
    expressions = {"/usr/bin/backup": "0 * * * *"}
    with patch("cronsight.forecaster.prev_run", return_value=NOW - timedelta(minutes=30)):
        result = forecast(report, expressions, horizon=1, now=NOW)
    assert result.windows[0].overdue is True


def test_forecast_raises_on_bad_expression():
    report = _make_report()
    expressions = {"cmd": "not_a_cron_expression"}
    with patch(
        "cronsight.forecaster.next_run",
        side_effect=Exception("bad expression"),
    ):
        with pytest.raises(ForecasterError):
            forecast(report, expressions, horizon=1, now=NOW)
