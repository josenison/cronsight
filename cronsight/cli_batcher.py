"""CLI subcommand: batcher — detect overlapping/concurrent cron executions."""
from __future__ import annotations

import argparse
import sys

from cronsight.batcher import BatcherError, build_batch_report
from cronsight.snapshot import SnapshotError, load_snapshot


def _add_batcher_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "batcher",
        help="Detect overlapping or concurrent cron job executions",
    )
    p.add_argument("snapshot", help="Path to snapshot file")
    p.add_argument(
        "--window",
        type=int,
        default=60,
        metavar="SECONDS",
        help="Time window in seconds to consider runs concurrent (default: 60)",
    )
    p.add_argument(
        "--overlaps-only",
        action="store_true",
        help="Only show jobs with overlapping executions",
    )


def _print_report(report, overlaps_only: bool) -> None:
    batches = report.batches
    if overlaps_only:
        batches = [b for b in batches if b.has_overlap]
    if not batches:
        print("No concurrent executions detected.")
        return
    print(f"{'COMMAND':<40} {'SERVER':<20} {'RUNS':>5} {'OVERLAP':>8}")
    print("-" * 78)
    for b in batches:
        overlap = "YES" if b.has_overlap else "no"
        print(f"{b.command:<40} {b.server:<20} {b.run_count:>5} {overlap:>8}")
    print(f"\nTotal batches: {report.count}  Overlapping: {report.overlap_count}")


def handle_batcher(args: argparse.Namespace) -> int:
    try:
        report = load_snapshot(args.snapshot)
    except FileNotFoundError:
        print(f"error: snapshot not found: {args.snapshot}", file=sys.stderr)
        return 1
    except SnapshotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    try:
        batch_report = build_batch_report(report, window_seconds=args.window)
    except BatcherError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    _print_report(batch_report, overlaps_only=args.overlaps_only)
    return 0
