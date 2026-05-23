"""Snapshot persistence for cron job reports — save and load report state to/from disk."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from cronsight.aggregator import AggregatedReport, JobSummary
from cronsight.parser import CronEntry


class SnapshotError(Exception):
    """Raised when a snapshot cannot be saved or loaded."""


_SNAPSHOT_VERSION = 1


def _entry_to_dict(entry: CronEntry) -> dict:
    return {
        "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
        "server": entry.server,
        "job": entry.job,
        "status": entry.status,
        "message": entry.message,
    }


def _entry_from_dict(d: dict) -> CronEntry:
    return CronEntry(
        timestamp=datetime.fromisoformat(d["timestamp"]) if d["timestamp"] else None,
        server=d["server"],
        job=d["job"],
        status=d["status"],
        message=d.get("message"),
    )


def _summary_to_dict(summary: JobSummary) -> dict:
    return {
        "job": summary.job,
        "servers": list(summary.servers),
        "entries": [_entry_to_dict(e) for e in summary.entries],
    }


def _summary_from_dict(d: dict) -> JobSummary:
    entries = [_entry_from_dict(e) for e in d["entries"]]
    return JobSummary(job=d["job"], servers=set(d["servers"]), entries=entries)


def save_snapshot(report: AggregatedReport, path: str | Path) -> None:
    """Persist an AggregatedReport to a JSON snapshot file."""
    path = Path(path)
    payload = {
        "version": _SNAPSHOT_VERSION,
        "saved_at": datetime.utcnow().isoformat(),
        "jobs": [_summary_to_dict(s) for s in report.jobs],
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        raise SnapshotError(f"Failed to save snapshot to {path}: {exc}") from exc


def load_snapshot(path: str | Path) -> AggregatedReport:
    """Load an AggregatedReport from a previously saved JSON snapshot file."""
    path = Path(path)
    if not path.exists():
        raise SnapshotError(f"Snapshot file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"Failed to read snapshot from {path}: {exc}") from exc

    version = payload.get("version")
    if version != _SNAPSHOT_VERSION:
        raise SnapshotError(f"Unsupported snapshot version: {version}")

    jobs = [_summary_from_dict(d) for d in payload.get("jobs", [])]
    return AggregatedReport(jobs=jobs)
