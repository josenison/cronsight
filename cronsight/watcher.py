"""Watch mode: periodically re-collect and report changes since last run."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

from cronsight.aggregator import AggregatedReport
from cronsight.diff import ReportDiff, diff_reports


class WatcherError(Exception):
    """Raised when the watcher encounters a fatal error."""


@dataclass
class WatchConfig:
    interval_seconds: int = 60
    max_iterations: Optional[int] = None  # None means run forever

    def __post_init__(self) -> None:
        if self.interval_seconds < 1:
            raise WatcherError("interval_seconds must be >= 1")
        if self.max_iterations is not None and self.max_iterations < 1:
            raise WatcherError("max_iterations must be >= 1 when set")


@dataclass
class WatchIteration:
    index: int
    timestamp: datetime
    report: AggregatedReport
    diff: Optional[ReportDiff]
    changed: bool = field(init=False)

    def __post_init__(self) -> None:
        self.changed = self.diff is not None and self.diff.has_changes


def watch(
    collect: Callable[[], AggregatedReport],
    config: WatchConfig,
    on_iteration: Callable[[WatchIteration], None],
) -> None:
    """Run collect in a loop, calling on_iteration with each result.

    Args:
        collect: Zero-argument callable that returns a fresh AggregatedReport.
        config:  WatchConfig controlling timing and iteration limits.
        on_iteration: Callback invoked after each successful collection.
    """
    previous: Optional[AggregatedReport] = None
    index = 0

    while True:
        report = collect()
        diff = diff_reports(previous, report) if previous is not None else None
        iteration = WatchIteration(
            index=index,
            timestamp=datetime.utcnow(),
            report=report,
            diff=diff,
        )
        on_iteration(iteration)
        previous = report
        index += 1

        if config.max_iterations is not None and index >= config.max_iterations:
            break

        time.sleep(config.interval_seconds)
