"""Unit tests for cronsight.escalator."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.escalator import (
    EscalationRule,
    EscalatorError,
    _consecutive_failures,
    escalate_report,
)
from cronsight.parser import CronEntry


def _entry(exit_code: int, ts: str = "2024-01-01T00:00:00") -> CronEntry:
    return CronEntry(
        timestamp=ts,
        command="/usr/bin/backup",
        exit_code=exit_code,
        server="host1",
    )


def _summary(*exit_codes: int) -> JobSummary:
    entries = [
        _entry(code, f"2024-01-01T{i:02d}:00:00")
        for i, code in enumerate(exit_codes)
    ]
    s = JobSummary(command="/usr/bin/backup", entries=entries)
    return s


def _report(**kwargs: JobSummary) -> AggregatedReport:
    r = AggregatedReport()
    for (cmd, srv), summary in [
        (k.split("|"), v) for k, v in kwargs.items()
    ]:
        r.jobs[(cmd, srv)] = summary
    return r


# ---------------------------------------------------------------------------
# EscalationRule validation
# ---------------------------------------------------------------------------

def test_rule_invalid_threshold_raises():
    with pytest.raises(EscalatorError):
        EscalationRule(threshold=0, label="CRIT")


def test_rule_empty_label_raises():
    with pytest.raises(EscalatorError):
        EscalationRule(threshold=2, label="   ")


def test_rule_valid_does_not_raise():
    rule = EscalationRule(threshold=3, label="CRITICAL")
    assert rule.threshold == 3
    assert rule.label == "CRITICAL"


# ---------------------------------------------------------------------------
# _consecutive_failures
# ---------------------------------------------------------------------------

def test_consecutive_failures_all_pass():
    assert _consecutive_failures(_summary(0, 0, 0)) == 0


def test_consecutive_failures_all_fail():
    assert _consecutive_failures(_summary(1, 1, 1)) == 3


def test_consecutive_failures_trailing_only():
    assert _consecutive_failures(_summary(0, 0, 1, 1)) == 2


def test_consecutive_failures_interrupted():
    assert _consecutive_failures(_summary(1, 1, 0, 1)) == 1


# ---------------------------------------------------------------------------
# escalate_report
# ---------------------------------------------------------------------------

def _make_report(exit_codes: list) -> AggregatedReport:
    entries = [
        _entry(code, f"2024-01-01T{i:02d}:00:00")
        for i, code in enumerate(exit_codes)
    ]
    summary = JobSummary(command="/usr/bin/backup", entries=entries)
    r = AggregatedReport()
    r.jobs[("/usr/bin/backup", "host1")] = summary
    return r


def test_escalate_no_rules_raises():
    r = _make_report([1, 1, 1])
    with pytest.raises(EscalatorError):
        escalate_report(r, [])


def test_escalate_below_threshold_not_flagged():
    r = _make_report([1, 1])
    result = escalate_report(r, [EscalationRule(threshold=3, label="CRIT")])
    assert result.count == 0


def test_escalate_at_threshold_flagged():
    r = _make_report([1, 1, 1])
    result = escalate_report(r, [EscalationRule(threshold=3, label="CRIT")])
    assert result.count == 1
    assert result.escalated[0].label == "CRIT"
    assert result.escalated[0].consecutive_failures == 3


def test_escalate_highest_matching_rule_wins():
    r = _make_report([1, 1, 1, 1, 1])
    rules = [
        EscalationRule(threshold=2, label="WARN"),
        EscalationRule(threshold=5, label="CRITICAL"),
    ]
    result = escalate_report(r, rules)
    assert result.escalated[0].label == "CRITICAL"


def test_escalated_job_str_contains_label():
    r = _make_report([1, 1, 1])
    result = escalate_report(r, [EscalationRule(threshold=3, label="CRIT")])
    assert "CRIT" in str(result.escalated[0])
