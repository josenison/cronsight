"""Tests for cronsight.normalizer."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from cronsight.normalizer import (
    NormalizerError,
    normalize_command,
    normalize_report,
)


# ---------------------------------------------------------------------------
# normalize_command
# ---------------------------------------------------------------------------

def test_normalize_command_strips_whitespace():
    assert normalize_command("  backup.sh  ") == "backup.sh"


def test_normalize_command_removes_usr_bin_prefix():
    assert normalize_command("/usr/bin/python3 script.py") == "python3 script.py"


def test_normalize_command_removes_usr_local_bin_prefix():
    assert normalize_command("/usr/local/bin/node app.js") == "node app.js"


def test_normalize_command_removes_bin_prefix():
    assert normalize_command("/bin/bash run.sh") == "bash run.sh"


def test_normalize_command_strips_redirect_dev_null():
    result = normalize_command("backup.sh >> /dev/null")
    assert ">>" not in result
    assert "backup.sh" in result


def test_normalize_command_strips_stderr_redirect():
    result = normalize_command("backup.sh 2>&1")
    assert "2>&1" not in result


def test_normalize_command_collapses_spaces():
    assert normalize_command("cmd   --flag   value") == "cmd --flag value"


def test_normalize_command_lowercases():
    assert normalize_command("MyScript.sh") == "myscript.sh"


def test_normalize_command_empty_string_raises():
    with pytest.raises(NormalizerError):
        normalize_command("")


def test_normalize_command_whitespace_only_raises():
    with pytest.raises(NormalizerError):
        normalize_command("   ")


def test_normalize_command_no_prefix_unchanged():
    assert normalize_command("my_script.py --verbose") == "my_script.py --verbose"


# ---------------------------------------------------------------------------
# normalize_report
# ---------------------------------------------------------------------------

def _make_summary(command: str) -> MagicMock:
    s = MagicMock()
    s.command = command
    s.last_run = datetime(2024, 1, 1, 12, 0, 0)
    return s


def _make_report(*commands: str) -> MagicMock:
    report = MagicMock()
    report.jobs = {cmd: _make_summary(cmd) for cmd in commands}
    return report


def test_normalize_report_returns_one_job_per_summary():
    report = _make_report("/usr/bin/backup.sh", "/bin/cleanup.sh")
    result = normalize_report(report)
    assert result.count == 2


def test_normalize_report_normalized_command_differs_from_original():
    report = _make_report("/usr/bin/backup.sh")
    result = normalize_report(report)
    job = result.jobs[0]
    assert job.normalized_command == "backup.sh"
    assert job.original_command == "/usr/bin/backup.sh"


def test_normalize_report_str_includes_both_forms():
    report = _make_report("/usr/bin/backup.sh")
    result = normalize_report(report)
    text = str(result.jobs[0])
    assert "backup.sh" in text
    assert "/usr/bin/backup.sh" in text


def test_normalize_report_empty_report_returns_empty():
    report = _make_report()
    result = normalize_report(report)
    assert result.count == 0
