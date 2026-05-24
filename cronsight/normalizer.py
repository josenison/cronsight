"""Normalize cron job command strings for consistent comparison and display."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from cronsight.aggregator import AggregatedReport, JobSummary


class NormalizerError(Exception):
    """Raised when normalization cannot be applied."""


@dataclass
class NormalizedJob:
    original_command: str
    normalized_command: str
    summary: JobSummary

    def __str__(self) -> str:
        return f"{self.normalized_command} (was: {self.original_command})"


@dataclass
class NormalizedReport:
    jobs: List[NormalizedJob]

    @property
    def count(self) -> int:
        return len(self.jobs)


_PATH_PREFIX_RE = re.compile(r"^(/usr/local/bin/|/usr/bin/|/bin/|/opt/[^/]+/bin/)")
_MULTI_SPACE_RE = re.compile(r" {2,}")
_REDIRECT_RE = re.compile(r"\s*(>>?|2>&1|&>\s*/dev/null)\s*", re.IGNORECASE)


def normalize_command(command: str) -> str:
    """Return a canonical form of *command* suitable for deduplication.

    Steps applied:
    1. Strip leading/trailing whitespace.
    2. Remove common absolute-path prefixes from the executable.
    3. Strip shell redirections (``>``, ``>>``, ``2>&1``, ``&>/dev/null``).
    4. Collapse consecutive spaces to a single space.
    5. Lower-case the result.
    """
    if not command or not command.strip():
        raise NormalizerError("Command must be a non-empty string.")

    cmd = command.strip()
    cmd = _PATH_PREFIX_RE.sub("", cmd)
    cmd = _REDIRECT_RE.sub(" ", cmd)
    cmd = _MULTI_SPACE_RE.sub(" ", cmd)
    cmd = cmd.strip().lower()
    return cmd


def normalize_report(report: AggregatedReport) -> NormalizedReport:
    """Return a :class:`NormalizedReport` wrapping every job in *report*."""
    jobs: List[NormalizedJob] = []
    for summary in report.jobs.values():
        try:
            norm = normalize_command(summary.command)
        except NormalizerError:
            norm = summary.command
        jobs.append(
            NormalizedJob(
                original_command=summary.command,
                normalized_command=norm,
                summary=summary,
            )
        )
    return NormalizedReport(jobs=jobs)
