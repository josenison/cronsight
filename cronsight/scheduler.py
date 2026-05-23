"""Cron schedule parsing and next-run prediction utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from croniter import croniter


class ScheduleError(Exception):
    """Raised when a cron schedule expression is invalid."""


@dataclass
class ScheduleInfo:
    expression: str
    last_run: Optional[datetime]
    next_run: datetime
    overdue_by: Optional[timedelta]

    @property
    def is_overdue(self) -> bool:
        return self.overdue_by is not None and self.overdue_by.total_seconds() > 0


def _validate_expression(expression: str) -> None:
    """Raise ScheduleError if *expression* is not a valid 5-field cron string."""
    if not croniter.is_valid(expression):
        raise ScheduleError(f"Invalid cron expression: {expression!r}")


def next_run(expression: str, base: Optional[datetime] = None) -> datetime:
    """Return the next scheduled datetime after *base* (defaults to now)."""
    _validate_expression(expression)
    base = base or datetime.utcnow()
    return croniter(expression, base).get_next(datetime)


def prev_run(expression: str, base: Optional[datetime] = None) -> datetime:
    """Return the most recent scheduled datetime before *base* (defaults to now)."""
    _validate_expression(expression)
    base = base or datetime.utcnow()
    return croniter(expression, base).get_prev(datetime)


def schedule_info(
    expression: str,
    last_run: Optional[datetime] = None,
    now: Optional[datetime] = None,
) -> ScheduleInfo:
    """Build a :class:`ScheduleInfo` for *expression* relative to *now*.

    If *last_run* is provided and falls before the most-recently expected
    execution, ``overdue_by`` will reflect how late the job is.
    """
    now = now or datetime.utcnow()
    _validate_expression(expression)

    expected = prev_run(expression, now)
    upcoming = next_run(expression, now)

    overdue: Optional[timedelta] = None
    if last_run is not None and last_run < expected:
        overdue = now - expected

    return ScheduleInfo(
        expression=expression,
        last_run=last_run,
        next_run=upcoming,
        overdue_by=overdue,
    )
