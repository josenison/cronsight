"""Summarizer: produce human-readable text summaries of aggregated reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


@dataclass
class SummaryLine:
    job: str
    server: str
    total_runs: int
    success_rate: float
    last_status: str
    last_run: Optional[str]

    def __str__(self) -> str:
        rate = f"{self.success_rate * 100:.0f}%"
        last = self.last_run or "N/A"
        return (
            f"[{self.server}] {self.job} — "
            f"runs: {self.total_runs}, success: {rate}, "
            f"last: {self.last_status} @ {last}"
        )


def _last_status(summary: JobSummary) -> str:
    if not summary.entries:
        return "unknown"
    return "ok" if summary.entries[-1].exit_code == 0 else "fail"


def _success_rate(summary: JobSummary) -> float:
    if not summary.entries:
        return 0.0
    passed = sum(1 for e in summary.entries if e.exit_code == 0)
    return passed / len(summary.entries)


def _format_last_run(summary: JobSummary) -> Optional[str]:
    if summary.last_run is None:
        return None
    return summary.last_run.strftime("%Y-%m-%d %H:%M:%S")


def build_summary_lines(report: AggregatedReport) -> List[SummaryLine]:
    """Convert an AggregatedReport into a list of SummaryLine objects."""
    lines: List[SummaryLine] = []
    for job_key, summary in report.jobs.items():
        lines.append(
            SummaryLine(
                job=summary.command,
                server=summary.server,
                total_runs=summary.total_runs,
                success_rate=_success_rate(summary),
                last_status=_last_status(summary),
                last_run=_format_last_run(summary),
            )
        )
    return lines


def render_text_summary(report: AggregatedReport) -> str:
    """Render a plain-text summary of the report."""
    lines = build_summary_lines(report)
    if not lines:
        return "No jobs found."
    return "\n".join(str(line) for line in lines)
