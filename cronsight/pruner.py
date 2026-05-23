"""Pruner: remove old snapshot files based on retention policy."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List


class PrunerError(Exception):
    """Raised when pruning fails."""


@dataclass
class PruneResult:
    removed: List[Path] = field(default_factory=list)
    kept: List[Path] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def removed_count(self) -> int:
        return len(self.removed)

    @property
    def kept_count(self) -> int:
        return len(self.kept)


def _snapshot_mtime(path: Path) -> datetime:
    """Return the modification time of a file as an aware UTC datetime."""
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _collect_snapshots(directory: Path) -> List[Path]:
    """Return all .json snapshot files in *directory*, sorted oldest-first."""
    if not directory.is_dir():
        raise PrunerError(f"Snapshot directory does not exist: {directory}")
    files = sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime)
    return files


def prune_snapshots(
    directory: Path,
    *,
    max_age_days: int | None = None,
    max_count: int | None = None,
    dry_run: bool = False,
) -> PruneResult:
    """Remove snapshot files that exceed *max_age_days* and/or *max_count*.

    Parameters
    ----------
    directory:    Path to the snapshots folder.
    max_age_days: Delete files older than this many days.  ``None`` skips age check.
    max_count:    Keep only the most-recent N files.  ``None`` skips count check.
    dry_run:      When *True* files are identified but not deleted.
    """
    if max_age_days is None and max_count is None:
        raise PrunerError("At least one of max_age_days or max_count must be set.")

    result = PruneResult()
    snapshots = _collect_snapshots(directory)
    to_remove: set[Path] = set()

    if max_age_days is not None:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=max_age_days)
        for path in snapshots:
            if _snapshot_mtime(path) < cutoff:
                to_remove.add(path)

    if max_count is not None and len(snapshots) > max_count:
        oldest = snapshots[: len(snapshots) - max_count]
        to_remove.update(oldest)

    for path in snapshots:
        if path in to_remove:
            if not dry_run:
                try:
                    path.unlink()
                except OSError as exc:
                    result.errors.append(f"Failed to remove {path}: {exc}")
                    continue
            result.removed.append(path)
        else:
            result.kept.append(path)

    return result
