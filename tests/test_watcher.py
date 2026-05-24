"""Tests for cronsight.watcher."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from cronsight.aggregator import AggregatedReport
from cronsight.diff import ReportDiff
from cronsight.watcher import WatchConfig, WatchIteration, WatcherError, watch


# ---------------------------------------------------------------------------
# WatchConfig
# ---------------------------------------------------------------------------

def test_watch_config_defaults():
    cfg = WatchConfig()
    assert cfg.interval_seconds == 60
    assert cfg.max_iterations is None


def test_watch_config_invalid_interval_raises():
    with pytest.raises(WatcherError):
        WatchConfig(interval_seconds=0)


def test_watch_config_invalid_max_iterations_raises():
    with pytest.raises(WatcherError):
        WatchConfig(max_iterations=0)


# ---------------------------------------------------------------------------
# WatchIteration
# ---------------------------------------------------------------------------

def _empty_report() -> AggregatedReport:
    return AggregatedReport(jobs={}, servers=[])


def test_watch_iteration_changed_false_when_no_diff():
    it = WatchIteration(index=0, timestamp=datetime.utcnow(), report=_empty_report(), diff=None)
    assert it.changed is False


def test_watch_iteration_changed_false_when_diff_no_changes():
    diff = ReportDiff(added_jobs=[], removed_jobs=[], changed_jobs=[])
    it = WatchIteration(index=1, timestamp=datetime.utcnow(), report=_empty_report(), diff=diff)
    assert it.changed is False


def test_watch_iteration_changed_true_when_diff_has_changes():
    diff = ReportDiff(added_jobs=["job_a"], removed_jobs=[], changed_jobs=[])
    it = WatchIteration(index=2, timestamp=datetime.utcnow(), report=_empty_report(), diff=diff)
    assert it.changed is True


# ---------------------------------------------------------------------------
# watch()
# ---------------------------------------------------------------------------

def test_watch_calls_collect_n_times():
    cfg = WatchConfig(interval_seconds=1, max_iterations=3)
    collect = MagicMock(return_value=_empty_report())
    iterations = []

    with patch("cronsight.watcher.time.sleep"):
        watch(collect, cfg, iterations.append)

    assert collect.call_count == 3
    assert len(iterations) == 3


def test_watch_first_iteration_has_no_diff():
    cfg = WatchConfig(interval_seconds=1, max_iterations=1)
    collect = MagicMock(return_value=_empty_report())
    iterations = []

    with patch("cronsight.watcher.time.sleep"):
        watch(collect, cfg, iterations.append)

    assert iterations[0].diff is None


def test_watch_subsequent_iterations_have_diff():
    cfg = WatchConfig(interval_seconds=1, max_iterations=2)
    collect = MagicMock(return_value=_empty_report())
    iterations = []

    with patch("cronsight.watcher.time.sleep"):
        watch(collect, cfg, iterations.append)

    assert iterations[1].diff is not None


def test_watch_index_increments():
    cfg = WatchConfig(interval_seconds=1, max_iterations=3)
    collect = MagicMock(return_value=_empty_report())
    iterations = []

    with patch("cronsight.watcher.time.sleep"):
        watch(collect, cfg, iterations.append)

    assert [it.index for it in iterations] == [0, 1, 2]
