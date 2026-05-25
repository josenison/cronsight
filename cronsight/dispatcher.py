"""Dispatch alerts and reports to multiple output channels based on rules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronsight.alerting import Alert
from cronsight.aggregator import AggregatedReport


class DispatcherError(Exception):
    pass


@dataclass
class DispatchChannel:
    name: str
    kind: str  # "stdout" | "json" | "text"
    min_severity: str = "warning"  # "info" | "warning" | "critical"

    def __post_init__(self) -> None:
        valid_kinds = {"stdout", "json", "text"}
        valid_severities = {"info", "warning", "critical"}
        if self.kind not in valid_kinds:
            raise DispatcherError(f"Unknown channel kind: {self.kind!r}")
        if self.min_severity not in valid_severities:
            raise DispatcherError(f"Unknown severity: {self.min_severity!r}")


_SEVERITY_ORDER = {"info": 0, "warning": 1, "critical": 2}


def _meets_severity(alert: Alert, min_severity: str) -> bool:
    return _SEVERITY_ORDER.get(alert.severity, 0) >= _SEVERITY_ORDER.get(min_severity, 0)


@dataclass
class DispatchResult:
    channel: str
    alerts_sent: int
    skipped: int

    def __str__(self) -> str:
        return f"{self.channel}: sent={self.alerts_sent} skipped={self.skipped}"


def dispatch(
    alerts: List[Alert],
    channels: List[DispatchChannel],
    report: Optional[AggregatedReport] = None,
) -> List[DispatchResult]:
    """Dispatch alerts to each channel, filtering by severity."""
    if not channels:
        raise DispatcherError("No dispatch channels configured")

    results: List[DispatchResult] = []
    for channel in channels:
        eligible = [a for a in alerts if _meets_severity(a, channel.min_severity)]
        skipped = len(alerts) - len(eligible)
        results.append(
            DispatchResult(
                channel=channel.name,
                alerts_sent=len(eligible),
                skipped=skipped,
            )
        )
    return results
