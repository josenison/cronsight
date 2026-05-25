"""Groups cron job executions into time buckets (hourly, daily, weekly)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Literal

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry

BucketGranularity = Literal["hourly", "daily", "weekly"]


class BucketerError(Exception):
    pass


@dataclass
class TimeBucket:
    label: str
    entries: List[CronEntry] = field(default_factory=list)

    @property
    def total_runs(self) -> int:
        return len(self.entries)

    @property
    def success_count(self) -> int:
        return sum(1 for e in self.entries if e.exit_code == 0)

    @property
    def failure_count(self) -> int:
        return self.total_runs - self.success_count

    @property
    def success_rate(self) -> float:
        if self.total_runs == 0:
            return 1.0
        return self.success_count / self.total_runs

    def __str__(self) -> str:
        return (
            f"{self.label}: {self.total_runs} runs, "
            f"{self.success_count} ok, {self.failure_count} failed"
        )


@dataclass
class BucketReport:
    command: str
    granularity: BucketGranularity
    buckets: List[TimeBucket] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.buckets)


def _bucket_key(ts: datetime, granularity: BucketGranularity) -> str:
    if granularity == "hourly":
        return ts.strftime("%Y-%m-%d %H:00")
    if granularity == "daily":
        return ts.strftime("%Y-%m-%d")
    if granularity == "weekly":
        year, week, _ = ts.isocalendar()
        return f"{year}-W{week:02d}"
    raise BucketerError(f"Unknown granularity: {granularity}")


def bucket_summary(
    summary: JobSummary,
    granularity: BucketGranularity = "daily",
) -> BucketReport:
    if granularity not in ("hourly", "daily", "weekly"):
        raise BucketerError(f"Invalid granularity: {granularity!r}")

    buckets: Dict[str, TimeBucket] = {}
    for entry in summary.entries:
        if entry.timestamp is None:
            continue
        key = _bucket_key(entry.timestamp, granularity)
        if key not in buckets:
            buckets[key] = TimeBucket(label=key)
        buckets[key].entries.append(entry)

    sorted_buckets = [buckets[k] for k in sorted(buckets)]
    return BucketReport(
        command=summary.command,
        granularity=granularity,
        buckets=sorted_buckets,
    )


def bucket_report(
    report: AggregatedReport,
    granularity: BucketGranularity = "daily",
) -> List[BucketReport]:
    return [bucket_summary(s, granularity) for s in report.summaries]
