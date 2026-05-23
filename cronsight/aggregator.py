"""Aggregates cron job execution results across multiple servers."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from cronsight.collector import CollectionResult
from cronsight.parser import CronEntry, parse_cron_log


@dataclass
class JobSummary:
    """Summary of a single cron job's execution history."""

    command: str
    server: str
    runs: list[CronEntry] = field(default_factory=list)

    @property
    def total_runs(self) -> int:
        return len(self.runs)

    @property
    def last_run(self) -> Optional[datetime]:
        if not self.runs:
            return None
        return max(entry.timestamp for entry in self.runs if entry.timestamp)

    @property
    def first_run(self) -> Optional[datetime]:
        if not self.runs:
            return None
        return min(entry.timestamp for entry in self.runs if entry.timestamp)


@dataclass
class AggregatedReport:
    """Aggregated report across all servers."""

    summaries: list[JobSummary] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total_servers(self) -> int:
        return len({s.server for s in self.summaries})

    @property
    def total_jobs(self) -> int:
        return len(self.summaries)


def aggregate_results(results: list[CollectionResult]) -> AggregatedReport:
    """Parse and aggregate CollectionResults into a unified report."""
    report = AggregatedReport()

    for result in results:
        if not result.success:
            report.errors.append(
                f"{result.server}: {result.error or 'unknown error'}"
            )
            continue

        entries = parse_cron_log(result.output or "")
        jobs: dict[str, JobSummary] = {}

        for entry in entries:
            key = entry.command
            if key not in jobs:
                jobs[key] = JobSummary(command=entry.command, server=result.server)
            jobs[key].runs.append(entry)

        report.summaries.extend(jobs.values())

    return report
