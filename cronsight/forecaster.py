"""Forecast future cron job execution windows based on schedule expressions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from cronsight.scheduler import ScheduleInfo, next_run, prev_run, ScheduleError
from cronsight.aggregator import AggregatedReport, JobSummary


class ForecasterError(Exception):
    """Raised when forecasting cannot be performed."""


@dataclass
class ForecastWindow:
    command: str
    expression: str
    next_runs: List[datetime] = field(default_factory=list)
    last_seen: Optional[datetime] = None
    overdue: bool = False

    def __str__(self) -> str:  # pragma: no cover
        nxt = self.next_runs[0].isoformat() if self.next_runs else "unknown"
        status = " [OVERDUE]" if self.overdue else ""
        return f"{self.command}: next={nxt}{status}"


@dataclass
class ForecastReport:
    generated_at: datetime
    windows: List[ForecastWindow] = field(default_factory=list)

    @property
    def overdue_count(self) -> int:
        return sum(1 for w in self.windows if w.overdue)


def _is_overdue(expression: str, last_seen: Optional[datetime], now: datetime) -> bool:
    """Return True if the job's last known run is before the most recent expected run."""
    if last_seen is None:
        return False
    try:
        previous = prev_run(expression, now)
        return last_seen < previous
    except ScheduleError:
        return False


def forecast(
    report: AggregatedReport,
    expressions: dict[str, str],
    horizon: int = 5,
    now: Optional[datetime] = None,
) -> ForecastReport:
    """Build a ForecastReport for jobs that have known cron expressions.

    Args:
        report: aggregated job data.
        expressions: mapping of command -> cron expression.
        horizon: number of upcoming run times to compute per job.
        now: reference time (defaults to utcnow).
    """
    if horizon < 1:
        raise ForecasterError("horizon must be >= 1")
    if not expressions:
        raise ForecasterError("expressions mapping must not be empty")

    now = now or datetime.utcnow()
    summaries: dict[str, JobSummary] = {s.command: s for s in report.jobs}
    windows: List[ForecastWindow] = []

    for command, expr in expressions.items():
        try:
            runs: List[datetime] = []
            cursor = now
            for _ in range(horizon):
                nxt = next_run(expr, cursor)
                runs.append(nxt)
                cursor = nxt + timedelta(seconds=1)
        except ScheduleError as exc:
            raise ForecasterError(f"invalid expression for '{command}': {exc}") from exc

        summary = summaries.get(command)
        last_seen = summary.last_run if summary else None
        overdue = _is_overdue(expr, last_seen, now)

        windows.append(
            ForecastWindow(
                command=command,
                expression=expr,
                next_runs=runs,
                last_seen=last_seen,
                overdue=overdue,
            )
        )

    return ForecastReport(generated_at=now, windows=windows)
