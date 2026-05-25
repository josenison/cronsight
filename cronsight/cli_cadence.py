"""CLI subcommand: cadence — analyse job execution cadence from a snapshot."""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronsight.cadence import CadenceProfile, CadenceReport, CadenceError, analyze_cadence
from cronsight.snapshot import SnapshotError, load_snapshot


def _add_cadence_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("cadence", help="Analyse job execution cadence")
    p.add_argument("snapshot", help="Path to snapshot file")
    p.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Irregularity threshold (stdev/mean ratio, default 0.5)",
    )
    p.add_argument(
        "--irregular-only",
        action="store_true",
        help="Only show irregular jobs",
    )


def _print_report(report: CadenceReport, irregular_only: bool) -> None:
    profiles = [p for p in report.profiles if p.is_irregular] if irregular_only else report.profiles
    if not profiles:
        print("No cadence data to display.")
        return
    print(f"{'COMMAND':<40} {'SERVER':<20} {'RUNS':>5} {'MEAN(m)':>8} {'STDEV(m)':>9} {'FLAG':<10}")
    print("-" * 96)
    for p in profiles:
        mean_m = f"{p.mean_interval_seconds / 60:.1f}" if p.mean_interval_seconds is not None else "N/A"
        stdev_m = f"{p.stdev_interval_seconds / 60:.1f}" if p.stdev_interval_seconds is not None else "N/A"
        flag = "IRREGULAR" if p.is_irregular else ""
        print(f"{p.command:<40} {p.server:<20} {p.run_count:>5} {mean_m:>8} {stdev_m:>9} {flag:<10}")
    print()
    print(f"Total jobs: {report.count}  Irregular: {report.irregular_count}")


def handle_cadence(args: argparse.Namespace) -> int:
    try:
        report = load_snapshot(args.snapshot)
    except FileNotFoundError:
        print(f"error: snapshot not found: {args.snapshot}", file=sys.stderr)
        return 1
    except SnapshotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        cadence_report = analyze_cadence(report, irregularity_threshold=args.threshold)
    except CadenceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _print_report(cadence_report, irregular_only=args.irregular_only)
    return 0
