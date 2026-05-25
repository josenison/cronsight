"""Tests for cronsight.patcher."""

from __future__ import annotations

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry
from cronsight.patcher import CommandPatch, PatchReport, PatcherError, detect_patches


def _make_entry(status: str = "success") -> CronEntry:
    return CronEntry(timestamp="2024-01-01T10:00:00", command="job", status=status, raw="")


def _make_summary(command: str, server: str = "host1") -> JobSummary:
    return JobSummary(command=command, server=server, entries=[_make_entry()])


def _make_report(*summaries: JobSummary) -> AggregatedReport:
    return AggregatedReport(jobs=list(summaries))


# ---------------------------------------------------------------------------
# CommandPatch
# ---------------------------------------------------------------------------

def test_command_patch_str_includes_old_and_new():
    patch = CommandPatch(
        job_key="host1::backup",
        old_command="backup --fast",
        new_command="backup --slow",
        server="host1",
    )
    s = str(patch)
    assert "backup --fast" in s
    assert "backup --slow" in s
    assert "host1" in s


# ---------------------------------------------------------------------------
# PatchReport
# ---------------------------------------------------------------------------

def test_patch_report_empty_has_no_patches():
    r = PatchReport()
    assert r.count == 0
    assert not r.has_patches


def test_patch_report_count_reflects_patches():
    p = CommandPatch("k", "old", "new", "srv")
    r = PatchReport(patches=[p, p])
    assert r.count == 2
    assert r.has_patches


# ---------------------------------------------------------------------------
# detect_patches
# ---------------------------------------------------------------------------

def test_detect_patches_no_changes_returns_empty():
    s = _make_summary("backup --fast")
    old = _make_report(s)
    new = _make_report(s)
    result = detect_patches(old, new)
    assert not result.has_patches


def test_detect_patches_finds_changed_command():
    old = _make_report(_make_summary("backup --fast"))
    new = _make_report(_make_summary("backup --slow"))
    result = detect_patches(old, new)
    assert result.count == 1
    assert result.patches[0].old_command == "backup --fast"
    assert result.patches[0].new_command == "backup --slow"


def test_detect_patches_new_job_not_flagged():
    old = _make_report(_make_summary("backup --fast"))
    new = _make_report(_make_summary("backup --fast"), _make_summary("cleanup"))
    result = detect_patches(old, new)
    assert not result.has_patches


def test_detect_patches_server_filter_limits_scope():
    old = _make_report(
        _make_summary("backup --fast", server="host1"),
        _make_summary("backup --fast", server="host2"),
    )
    new = _make_report(
        _make_summary("backup --slow", server="host1"),
        _make_summary("backup --slow", server="host2"),
    )
    result = detect_patches(old, new, server="host1")
    assert result.count == 1
    assert result.patches[0].server == "host1"


def test_detect_patches_raises_on_none_old():
    new = _make_report(_make_summary("backup"))
    with pytest.raises(PatcherError):
        detect_patches(None, new)  # type: ignore


def test_detect_patches_raises_on_none_new():
    old = _make_report(_make_summary("backup"))
    with pytest.raises(PatcherError):
        detect_patches(old, None)  # type: ignore
