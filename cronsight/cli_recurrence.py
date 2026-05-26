"""CLI sub-command: recurrence — analyse job run intervals."""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronsight.recurrence import RecurrenceProfile, RecurrenceReport, RecurrenceError, build_recurrence_report
from cronsight.snapshot import SnapshotError, load_snapshot


def _add_recurrence_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("recurrence", help="Analyse job run-interval regularity")
    p.add_argument("snapshot", help="Path to snapshot file")
    p.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        metavar="CV",
        help="Coefficient-of-variation threshold for irregularity (default: 0.5)",
    )
    p.add_argument(
        "--irregular-only",
        action="store_true",
        help="Only show irregular jobs",
    )


def _print_report(report: RecurrenceReport, irregular_only: bool) -> None:
    profiles: List[RecurrenceProfile] = (
        [p for p in report.profiles if p.irregular] if irregular_only else report.profiles
    )
    if not profiles:
        print("No jobs to display.")
        return
    print(f"{'COMMAND':<45} {'RUNS':>6} {'MEDIAN':>10} {'STDEV':>10} {'FLAG':<10}")
    print("-" * 85)
    for p in profiles:
        med = f"{p.median_interval_seconds:.0f}s" if p.median_interval_seconds is not None else "N/A"
        sd = f"{p.stdev_interval_seconds:.0f}s" if p.stdev_interval_seconds is not None else "N/A"
        flag = "IRREGULAR" if p.irregular else ""
        print(f"{p.command:<45} {p.run_count:>6} {med:>10} {sd:>10} {flag:<10}")
    print()
    print(f"Total jobs: {report.count}  Irregular: {report.irregular_count}")


def handle_recurrence(args: argparse.Namespace) -> int:
    try:
        snap = load_snapshot(args.snapshot)
    except FileNotFoundError:
        print(f"error: snapshot not found: {args.snapshot}", file=sys.stderr)
        return 1
    except SnapshotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        report = build_recurrence_report(snap, irregularity_threshold=args.threshold)
    except RecurrenceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _print_report(report, irregular_only=args.irregular_only)
    return 0
