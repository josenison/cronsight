"""Tests for cronsight.pruner."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from cronsight.pruner import PrunerError, PruneResult, prune_snapshots


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_snapshots(directory: Path, names: list[str]) -> list[Path]:
    """Create empty JSON files with a small mtime gap so ordering is stable."""
    paths = []
    for i, name in enumerate(names):
        p = directory / name
        p.write_text("{}")
        # Stagger mtimes by 1 second per file so sorting is deterministic.
        mtime = time.time() - (len(names) - i) * 2
        import os
        os.utime(p, (mtime, mtime))
        paths.append(p)
    return paths


# ---------------------------------------------------------------------------
# PruneResult
# ---------------------------------------------------------------------------

def test_prune_result_counts():
    r = PruneResult(removed=[Path("a"), Path("b")], kept=[Path("c")])
    assert r.removed_count == 2
    assert r.kept_count == 1


# ---------------------------------------------------------------------------
# prune_snapshots — argument validation
# ---------------------------------------------------------------------------

def test_raises_if_no_criteria(tmp_path):
    with pytest.raises(PrunerError, match="At least one"):
        prune_snapshots(tmp_path)


def test_raises_if_directory_missing(tmp_path):
    missing = tmp_path / "no_such_dir"
    with pytest.raises(PrunerError, match="does not exist"):
        prune_snapshots(missing, max_count=5)


# ---------------------------------------------------------------------------
# prune_snapshots — max_count
# ---------------------------------------------------------------------------

def test_max_count_removes_oldest(tmp_path):
    files = _make_snapshots(tmp_path, ["a.json", "b.json", "c.json", "d.json"])
    result = prune_snapshots(tmp_path, max_count=2)
    assert result.removed_count == 2
    assert result.kept_count == 2
    # Oldest two should be gone
    assert not files[0].exists()
    assert not files[1].exists()
    assert files[2].exists()
    assert files[3].exists()


def test_max_count_no_removal_when_under_limit(tmp_path):
    _make_snapshots(tmp_path, ["x.json", "y.json"])
    result = prune_snapshots(tmp_path, max_count=10)
    assert result.removed_count == 0
    assert result.kept_count == 2


# ---------------------------------------------------------------------------
# prune_snapshots — max_age_days
# ---------------------------------------------------------------------------

def test_max_age_removes_old_files(tmp_path):
    import os
    old = tmp_path / "old.json"
    old.write_text("{}")
    ancient_mtime = time.time() - 10 * 86400  # 10 days ago
    os.utime(old, (ancient_mtime, ancient_mtime))

    fresh = tmp_path / "fresh.json"
    fresh.write_text("{}")

    result = prune_snapshots(tmp_path, max_age_days=5)
    assert result.removed_count == 1
    assert not old.exists()
    assert fresh.exists()


# ---------------------------------------------------------------------------
# prune_snapshots — dry_run
# ---------------------------------------------------------------------------

def test_dry_run_does_not_delete(tmp_path):
    files = _make_snapshots(tmp_path, ["a.json", "b.json", "c.json"])
    result = prune_snapshots(tmp_path, max_count=1, dry_run=True)
    assert result.removed_count == 2
    # Files must still exist
    for f in files:
        assert f.exists()
