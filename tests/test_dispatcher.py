"""Tests for cronsight.dispatcher."""
from __future__ import annotations

import pytest
from datetime import datetime

from cronsight.alerting import Alert
from cronsight.dispatcher import (
    DispatchChannel,
    DispatcherError,
    DispatchResult,
    _meets_severity,
    dispatch,
)


def _alert(severity: str) -> Alert:
    return Alert(job="backup", server="host1", severity=severity, reason="test")


# ---------------------------------------------------------------------------
# DispatchChannel
# ---------------------------------------------------------------------------

def test_dispatch_channel_valid():
    ch = DispatchChannel(name="main", kind="stdout", min_severity="warning")
    assert ch.name == "main"


def test_dispatch_channel_invalid_kind_raises():
    with pytest.raises(DispatcherError):
        DispatchChannel(name="x", kind="email", min_severity="warning")


def test_dispatch_channel_invalid_severity_raises():
    with pytest.raises(DispatcherError):
        DispatchChannel(name="x", kind="stdout", min_severity="high")


# ---------------------------------------------------------------------------
# _meets_severity
# ---------------------------------------------------------------------------

def test_meets_severity_exact_match():
    assert _meets_severity(_alert("warning"), "warning") is True


def test_meets_severity_higher_passes():
    assert _meets_severity(_alert("critical"), "warning") is True


def test_meets_severity_lower_fails():
    assert _meets_severity(_alert("info"), "warning") is False


# ---------------------------------------------------------------------------
# DispatchResult
# ---------------------------------------------------------------------------

def test_dispatch_result_str():
    r = DispatchResult(channel="main", alerts_sent=3, skipped=1)
    assert "main" in str(r)
    assert "sent=3" in str(r)
    assert "skipped=1" in str(r)


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------

def test_dispatch_no_channels_raises():
    with pytest.raises(DispatcherError):
        dispatch([_alert("warning")], [])


def test_dispatch_filters_by_severity():
    channels = [DispatchChannel("ch", "stdout", "critical")]
    alerts = [_alert("info"), _alert("warning"), _alert("critical")]
    results = dispatch(alerts, channels)
    assert results[0].alerts_sent == 1
    assert results[0].skipped == 2


def test_dispatch_returns_one_result_per_channel():
    channels = [
        DispatchChannel("a", "stdout", "info"),
        DispatchChannel("b", "json", "critical"),
    ]
    results = dispatch([_alert("warning")], channels)
    assert len(results) == 2


def test_dispatch_info_channel_receives_all():
    channels = [DispatchChannel("all", "text", "info")]
    alerts = [_alert("info"), _alert("warning"), _alert("critical")]
    results = dispatch(alerts, channels)
    assert results[0].alerts_sent == 3
    assert results[0].skipped == 0


def test_dispatch_no_alerts_raises():
    """dispatch() should raise DispatcherError when the alerts list is empty."""
    channels = [DispatchChannel("ch", "stdout", "info")]
    with pytest.raises(DispatcherError):
        dispatch([], channels)
