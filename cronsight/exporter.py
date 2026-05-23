"""Export aggregated cron job reports to various formats (JSON, CSV)."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from cronsight.aggregator import AggregatedReport, JobSummary


def _summary_to_dict(summary: JobSummary) -> dict[str, Any]:
    """Convert a JobSummary to a plain dictionary."""
    return {
        "command": summary.command,
        "server": summary.server,
        "total_runs": summary.total_runs,
        "successful_runs": summary.successful_runs,
        "failed_runs": summary.failed_runs,
        "success_rate": round(summary.successful_runs / summary.total_runs, 4)
        if summary.total_runs > 0
        else 0.0,
        "first_run": summary.first_run.isoformat() if summary.first_run else None,
        "last_run": summary.last_run.isoformat() if summary.last_run else None,
    }


def export_json(report: AggregatedReport, indent: int = 2) -> str:
    """Serialize an AggregatedReport to a JSON string."""
    data = {
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "servers": sorted(report.servers),
        "jobs": [_summary_to_dict(s) for s in report.summaries],
    }
    return json.dumps(data, indent=indent)


_CSV_FIELDS = [
    "command",
    "server",
    "total_runs",
    "successful_runs",
    "failed_runs",
    "success_rate",
    "first_run",
    "last_run",
]


def export_csv(report: AggregatedReport) -> str:
    """Serialize an AggregatedReport to a CSV string."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for summary in report.summaries:
        writer.writerow(_summary_to_dict(summary))
    return buf.getvalue()
