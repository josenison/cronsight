"""Patch detection: identify jobs whose command has changed between two reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronsight.aggregator import AggregatedReport, JobSummary


class PatcherError(Exception):
    """Raised when patch detection cannot be performed."""


@dataclass
class CommandPatch:
    """Represents a detected change in a job's command string."""

    job_key: str
    old_command: str
    new_command: str
    server: str

    def __str__(self) -> str:
        return f"[{self.server}] {self.job_key}: '{self.old_command}' -> '{self.new_command}'"


@dataclass
class PatchReport:
    """Collection of detected command patches across two reports."""

    patches: List[CommandPatch] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.patches)

    @property
    def has_patches(self) -> bool:
        return bool(self.patches)


def _job_index(report: AggregatedReport) -> Dict[str, JobSummary]:
    """Build a mapping of (server, command) -> JobSummary."""
    index: Dict[str, JobSummary] = {}
    for summary in report.jobs:
        key = f"{summary.server}::{summary.command}"
        index[key] = summary
    return index


def _normalize(cmd: str) -> str:
    return cmd.strip()


def detect_patches(
    old_report: AggregatedReport,
    new_report: AggregatedReport,
    server: Optional[str] = None,
) -> PatchReport:
    """Compare two reports and return jobs whose commands appear to have changed.

    A "patch" is detected when a job key (server + base command prefix) exists in
    both reports but the full command string differs.
    """
    if old_report is None or new_report is None:
        raise PatcherError("Both old and new reports are required.")

    def _prefix(cmd: str) -> str:
        return _normalize(cmd).split()[0] if cmd.strip() else ""

    # Index old report by (server, command-prefix)
    old_index: Dict[str, JobSummary] = {}
    for s in old_report.jobs:
        if server and s.server != server:
            continue
        key = f"{s.server}::{_prefix(s.command)}"
        old_index[key] = s

    patches: List[CommandPatch] = []
    for s in new_report.jobs:
        if server and s.server != server:
            continue
        key = f"{s.server}::{_prefix(s.command)}"
        if key in old_index:
            old_cmd = _normalize(old_index[key].command)
            new_cmd = _normalize(s.command)
            if old_cmd != new_cmd:
                patches.append(
                    CommandPatch(
                        job_key=key,
                        old_command=old_cmd,
                        new_command=new_cmd,
                        server=s.server,
                    )
                )

    return PatchReport(patches=patches)
