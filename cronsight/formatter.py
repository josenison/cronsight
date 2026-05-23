"""Terminal output formatting for CronSight dashboard."""

from datetime import datetime
from typing import List

from cronsight.aggregator import AggregatedReport, JobSummary

COLOR_RESET = "\033[0m"
COLOR_GREEN = "\033[32m"
COLOR_RED = "\033[31m"
COLOR_YELLOW = "\033[33m"
COLOR_CYAN = "\033[36m"
COLOR_BOLD = "\033[1m"
COLOR_DIM = "\033[2m"


def _colorize(text: str, color: str, use_color: bool = True) -> str:
    if not use_color:
        return text
    return f"{color}{text}{COLOR_RESET}"


def _format_timestamp(dt: datetime | None) -> str:
    if dt is None:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _success_rate(summary: JobSummary) -> float:
    if summary.total_runs == 0:
        return 0.0
    return (summary.total_runs - summary.failed_runs) / summary.total_runs * 100


def format_job_row(summary: JobSummary, use_color: bool = True) -> str:
    rate = _success_rate(summary)
    if rate == 100.0:
        rate_str = _colorize(f"{rate:5.1f}%", COLOR_GREEN, use_color)
    elif rate >= 80.0:
        rate_str = _colorize(f"{rate:5.1f}%", COLOR_YELLOW, use_color)
    else:
        rate_str = _colorize(f"{rate:5.1f}%", COLOR_RED, use_color)

    cmd = summary.command[:40].ljust(40)
    server = summary.server.ljust(20)
    last = _format_timestamp(summary.last_run)
    runs = str(summary.total_runs).rjust(5)

    return f"  {_colorize(cmd, COLOR_CYAN, use_color)}  {_colorize(server, COLOR_DIM, use_color)}  {last}  {runs}  {rate_str}"


def format_report(report: AggregatedReport, use_color: bool = True) -> str:
    lines: List[str] = []

    header = _colorize("CronSight — Job Execution Report", COLOR_BOLD, use_color)
    lines.append("")
    lines.append(f"  {header}")
    lines.append("  " + "-" * 78)

    col_headers = (
        f"  {'COMMAND':<40}  {'SERVER':<20}  {'LAST RUN':<19}  {'RUNS':>5}  {'SUCCESS%':>7}"
    )
    lines.append(_colorize(col_headers, COLOR_BOLD, use_color))
    lines.append("  " + "-" * 78)

    if not report.jobs:
        lines.append(_colorize("  No jobs found.", COLOR_YELLOW, use_color))
    else:
        for summary in sorted(report.jobs, key=lambda j: j.command):
            lines.append(format_job_row(summary, use_color=use_color))

    lines.append("  " + "-" * 78)
    total_jobs = len(report.jobs)
    total_runs = sum(j.total_runs for j in report.jobs)
    footer = f"  {total_jobs} job(s) across {len(report.servers)} server(s) — {total_runs} total run(s)"
    lines.append(_colorize(footer, COLOR_DIM, use_color))
    lines.append("")

    return "\n".join(lines)
