"""Notifier module — formats and outputs alerts produced by the alerting engine."""

import json
import sys
from typing import List, TextIO
from cronsight.alerting import Alert


SUPPORTED_FORMATS = ("text", "json")


class NotifierError(Exception):
    """Raised when the notifier encounters an invalid configuration."""


def _alerts_to_dicts(alerts: List[Alert]) -> List[dict]:
    return [
        {
            "job_name": a.job_name,
            "server": a.server,
            "reason": a.reason,
            "success_rate": round(a.success_rate, 4),
            "total_runs": a.total_runs,
        }
        for a in alerts
    ]


def notify_text(alerts: List[Alert], stream: TextIO = sys.stderr) -> None:
    """Write human-readable alert lines to *stream*."""
    if not alerts:
        stream.write("cronsight: no alerts triggered.\n")
        return
    for alert in alerts:
        stream.write(str(alert) + "\n")


def notify_json(alerts: List[Alert], stream: TextIO = sys.stdout) -> None:
    """Write alerts as a JSON array to *stream*."""
    payload = {
        "alert_count": len(alerts),
        "alerts": _alerts_to_dicts(alerts),
    }
    json.dump(payload, stream, indent=2)
    stream.write("\n")


def notify(alerts: List[Alert], fmt: str = "text", stream: TextIO = sys.stderr) -> None:
    """Dispatch alerts using the requested format.

    Args:
        alerts: List of Alert objects to emit.
        fmt:    Output format — ``"text"`` or ``"json"``.
        stream: Destination stream (defaults to stderr).

    Raises:
        NotifierError: If *fmt* is not a supported format.
    """
    if fmt not in SUPPORTED_FORMATS:
        raise NotifierError(
            f"Unsupported notification format: {fmt!r}. "
            f"Choose one of {SUPPORTED_FORMATS}."
        )
    if fmt == "text":
        notify_text(alerts, stream)
    elif fmt == "json":
        notify_json(alerts, stream)
