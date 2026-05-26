"""CLI subcommand: reaper — detect jobs that have not run within their expected window."""

from __future__ import annotations

import argparse
import sys
from typing import List

from cronsight.reaper import ReaperError, reap
from cronsight.snapshot import SnapshotError, load_snapshot


def _add_reaper_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "reaper",
        help="Detect jobs that have not run within their expected window",
    )
    p.add_argument("snapshot", help="Path to snapshot file")
    p.add_argument(
        "--interval",
        type=float,
        required=True,
        metavar="HOURS",
        help="Expected maximum hours between runs",
    )
    p.add_argument(
        "--pattern",
        default=None,
        metavar="REGEX",
        help="Only consider commands matching this regex",
    )
    p.add_argument(
        "--dead-only",
        action="store_true",
        help="Exit with code 1 if any dead jobs are found",
    )


def _print_report(report, file=sys.stdout) -> None:
    if not report.has_dead_jobs:
        print("No dead jobs found.", file=file)
        return
    print(f"Dead jobs ({report.count}):", file=file)
    for job in report.dead_jobs:
        print(f"  {job}", file=file)


def handle_reaper(args: argparse.Namespace) -> int:
    try:
        snapshot = load_snapshot(args.snapshot)
    except FileNotFoundError:
        print(f"Snapshot not found: {args.snapshot}", file=sys.stderr)
        return 1
    except SnapshotError as exc:
        print(f"Snapshot error: {exc}", file=sys.stderr)
        return 1

    try:
        report = reap(
            snapshot,
            expected_interval_hours=args.interval,
            pattern=args.pattern,
        )
    except ReaperError as exc:
        print(f"Reaper error: {exc}", file=sys.stderr)
        return 1

    _print_report(report)

    if args.dead_only and report.has_dead_jobs:
        return 1
    return 0
