"""Tests for cronsight.scheduler."""

from datetime import datetime, timedelta

import pytest

from cronsight.scheduler import (
    ScheduleError,
    ScheduleInfo,
    next_run,
    prev_run,
    schedule_info,
)

# Fixed reference point for deterministic tests
NOW = datetime(2024, 6, 15, 12, 0, 0)  # Saturday 12:00 UTC


# ---------------------------------------------------------------------------
# next_run
# ---------------------------------------------------------------------------

def test_next_run_returns_future_datetime():
    result = next_run("* * * * *", base=NOW)
    assert result > NOW


def test_next_run_every_minute():
    result = next_run("* * * * *", base=NOW)
    assert result == datetime(2024, 6, 15, 12, 1, 0)


def test_next_run_hourly():
    result = next_run("0 * * * *", base=NOW)
    assert result == datetime(2024, 6, 15, 13, 0, 0)


def test_next_run_invalid_expression_raises():
    with pytest.raises(ScheduleError):
        next_run("not a cron", base=NOW)


# ---------------------------------------------------------------------------
# prev_run
# ---------------------------------------------------------------------------

def test_prev_run_returns_past_datetime():
    result = prev_run("* * * * *", base=NOW)
    assert result < NOW


def test_prev_run_hourly():
    result = prev_run("0 * * * *", base=NOW)
    assert result == datetime(2024, 6, 15, 12, 0, 0)


def test_prev_run_invalid_expression_raises():
    with pytest.raises(ScheduleError):
        prev_run("60 * * * *", base=NOW)


# ---------------------------------------------------------------------------
# schedule_info
# ---------------------------------------------------------------------------

def test_schedule_info_returns_schedule_info_instance():
    info = schedule_info("0 * * * *", now=NOW)
    assert isinstance(info, ScheduleInfo)


def test_schedule_info_next_run_is_future():
    info = schedule_info("0 * * * *", now=NOW)
    assert info.next_run > NOW


def test_schedule_info_not_overdue_when_last_run_recent():
    last = datetime(2024, 6, 15, 12, 0, 0)  # exactly on the hour
    info = schedule_info("0 * * * *", last_run=last, now=NOW)
    assert not info.is_overdue


def test_schedule_info_overdue_when_last_run_missed():
    # Job should have run at 11:00; last_run was at 10:00
    last = datetime(2024, 6, 15, 10, 0, 0)
    info = schedule_info("0 * * * *", last_run=last, now=NOW)
    assert info.is_overdue
    assert info.overdue_by is not None
    assert info.overdue_by > timedelta(0)


def test_schedule_info_overdue_by_is_none_without_last_run():
    info = schedule_info("0 * * * *", now=NOW)
    assert info.overdue_by is None
    assert not info.is_overdue


def test_schedule_info_invalid_expression_raises():
    with pytest.raises(ScheduleError):
        schedule_info("@reboot", now=NOW)
