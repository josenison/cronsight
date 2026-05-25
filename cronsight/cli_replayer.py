"""CLI sub-command: replay — reconstruct cron job execution timelines."""

from __future__ import annotations

import argparse
from datetime import datetime
from typing import Optional

from cronsight.replayer import ReplayReport, ReplayerError, replay_report
from cronsight.snapshot import SnapshotError, load_snapshot

_TS_FMT = "%Y-%m-%dT%H:%M:%S"


def _add_replayer_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("replay", help="Replay cron job execution timelines")
    p.add_argument("snapshot", help="Path to snapshot file")
    p.add_argument("--since", metavar="DATETIME", help=f"Start time ({_TS_FMT})")
    p.add_argument("--until", metavar="DATETIME", help=f"End time ({_TS_FMT})")
    p.add_argument("--job", metavar="PATTERN", help="Filter by command substring")


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    try:
        return datetime.strptime(value, _TS_FMT)
    except ValueError as exc:
        raise ValueError(f"Invalid datetime '{value}', expected {_TS_FMT}") from exc


def _print_report(rpt: ReplayReport, job_filter: Optional[str]) -> None:
    for tl in rpt.timelines:
        if job_filter and job_filter not in tl.command:
            continue
        print(f"\n=== {tl.command} ({tl.event_count} events, {tl.failure_count} failures) ===")
        for ev in tl.events:
            print(f"  {ev}")


def handle_replayer(args: argparse.Namespace) -> int:
    try:
        since = _parse_dt(getattr(args, "since", None))
        until = _parse_dt(getattr(args, "until", None))
    except ValueError as exc:
        print(f"replay: {exc}")
        return 1

    try:
        report = load_snapshot(args.snapshot)
    except (SnapshotError, FileNotFoundError) as exc:
        print(f"replay: {exc}")
        return 1

    try:
        rpt = replay_report(report, since=since, until=until)
    except ReplayerError as exc:
        print(f"replay: {exc}")
        return 1

    _print_report(rpt, getattr(args, "job", None))
    return 0
