"""Batch execution analyzer — groups cron entries into execution batches
based on time proximity and identifies overlapping or concurrent runs."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry


class BatcherError(Exception):
    pass


@dataclass
class ExecutionBatch:
    command: str
    server: str
    entries: List[CronEntry] = field(default_factory=list)

    @property
    def run_count(self) -> int:
        return len(self.entries)

    @property
    def has_overlap(self) -> bool:
        return self.run_count > 1

    @property
    def earliest(self) -> Optional[datetime]:
        ts = [e.timestamp for e in self.entries if e.timestamp]
        return min(ts) if ts else None

    @property
    def latest(self) -> Optional[datetime]:
        ts = [e.timestamp for e in self.entries if e.timestamp]
        return max(ts) if ts else None

    def __str__(self) -> str:
        overlap = " [OVERLAP]" if self.has_overlap else ""
        return f"{self.server}:{self.command} ({self.run_count} runs){overlap}"


@dataclass
class BatchReport:
    batches: List[ExecutionBatch] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.batches)

    @property
    def overlap_count(self) -> int:
        return sum(1 for b in self.batches if b.has_overlap)


def _group_entries(
    entries: List[CronEntry], window_seconds: int
) -> List[List[CronEntry]]:
    """Group entries that fall within window_seconds of each other."""
    if not entries:
        return []
    sorted_entries = sorted(
        [e for e in entries if e.timestamp], key=lambda e: e.timestamp
    )
    if not sorted_entries:
        return []
    groups: List[List[CronEntry]] = [[sorted_entries[0]]]
    for entry in sorted_entries[1:]:
        last = groups[-1][-1]
        delta = (entry.timestamp - last.timestamp).total_seconds()
        if delta <= window_seconds:
            groups[-1].append(entry)
        else:
            groups.append([entry])
    return groups


def build_batch_report(
    report: AggregatedReport, window_seconds: int = 60
) -> BatchReport:
    """Analyze an AggregatedReport for concurrent/overlapping executions."""
    if window_seconds <= 0:
        raise BatcherError("window_seconds must be positive")
    batches: List[ExecutionBatch] = []
    for command, summary in report.jobs.items():
        for server in summary.servers:
            server_entries = [
                e for e in summary.entries if getattr(e, "server", None) == server
            ]
            for group in _group_entries(server_entries, window_seconds):
                if len(group) > 1:
                    batches.append(
                        ExecutionBatch(command=command, server=server, entries=group)
                    )
    return BatchReport(batches=batches)
