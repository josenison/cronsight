"""CLI sub-command: velocity — compare run-rate between two snapshots."""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronsight.snapshot import load_snapshot, SnapshotError
from cronsight.velocity import VelocityDelta, VelocityReport, VelocityError, compute_velocity


def _add_velocity_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "velocity",
        help="Compare run-rate and success-rate between two snapshots.",
    )
    p.add_argument("old_snapshot", help="Path to the older snapshot file.")
    p.add_argument("new_snapshot", help="Path to the newer snapshot file.")
    p.add_argument(
        "--accelerating-only",
        action="store_true",
        default=False,
        help="Show only jobs whose run count increased.",
    )
    p.add_argument(
        "--decelerating-only",
        action="store_true",
        default=False,
        help="Show only jobs whose run count decreased or stayed the same.",
    )


def _print_report(report: VelocityReport, args: argparse.Namespace) -> None:
    deltas = report.deltas
    if args.accelerating_only:
        deltas = report.accelerating
    elif args.decelerating_only:
        deltas = report.decelerating

    if not deltas:
        print("No velocity data to display.")
        return

    print(f"{'COMMAND':<40} {'RUN Δ':>8} {'RATE Δ':>10}")
    print("-" * 62)
    for d in deltas:
        sign = "+" if d.run_delta >= 0 else ""
        print(f"{d.command:<40} {sign}{d.run_delta:>7} {d.rate_delta:>+10.1%}")


def handle_velocity(args: argparse.Namespace) -> int:
    try:
        old_report = load_snapshot(args.old_snapshot)
    except (SnapshotError, FileNotFoundError) as exc:
        print(f"error: cannot load old snapshot: {exc}", file=sys.stderr)
        return 1

    try:
        new_report = load_snapshot(args.new_snapshot)
    except (SnapshotError, FileNotFoundError) as exc:
        print(f"error: cannot load new snapshot: {exc}", file=sys.stderr)
        return 1

    try:
        report = compute_velocity(old_report, new_report)
    except VelocityError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _print_report(report, args)
    return 0
