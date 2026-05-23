"""Alerting module for cronsight — detects jobs with poor health and emits alerts."""

from dataclasses import dataclass, field
from typing import List, Optional
from cronsight.aggregator import JobSummary, AggregatedReport


@dataclass
class AlertRule:
    min_success_rate: Optional[float] = None  # 0.0 – 1.0
    max_consecutive_failures: Optional[int] = None
    min_runs: int = 1  # ignore jobs with fewer runs than this


@dataclass
class Alert:
    job_name: str
    server: str
    reason: str
    success_rate: float
    total_runs: int

    def __str__(self) -> str:
        return (
            f"[ALERT] {self.job_name} on {self.server}: {self.reason} "
            f"(success_rate={self.success_rate:.0%}, runs={self.total_runs})"
        )


def _consecutive_failures(summary: JobSummary) -> int:
    """Return the number of trailing failures in the run history."""
    count = 0
    for entry in reversed(summary.runs):
        if entry.exit_code != 0:
            count += 1
        else:
            break
    return count


def evaluate_summary(summary: JobSummary, rule: AlertRule) -> List[Alert]:
    """Evaluate a single JobSummary against an AlertRule and return any alerts."""
    alerts: List[Alert] = []

    if summary.total_runs < rule.min_runs:
        return alerts

    rate = summary.total_runs and (summary.total_runs - summary.failed_runs) / summary.total_runs

    if rule.min_success_rate is not None and rate < rule.min_success_rate:
        alerts.append(Alert(
            job_name=summary.job_name,
            server=summary.server,
            reason=f"success rate {rate:.0%} below threshold {rule.min_success_rate:.0%}",
            success_rate=rate,
            total_runs=summary.total_runs,
        ))

    if rule.max_consecutive_failures is not None:
        consec = _consecutive_failures(summary)
        if consec > rule.max_consecutive_failures:
            alerts.append(Alert(
                job_name=summary.job_name,
                server=summary.server,
                reason=f"{consec} consecutive failures (max allowed: {rule.max_consecutive_failures})",
                success_rate=rate,
                total_runs=summary.total_runs,
            ))

    return alerts


def check_report(report: AggregatedReport, rule: AlertRule) -> List[Alert]:
    """Evaluate all job summaries in a report and return a flat list of alerts."""
    alerts: List[Alert] = []
    for summary in report.jobs:
        alerts.extend(evaluate_summary(summary, rule))
    return alerts
