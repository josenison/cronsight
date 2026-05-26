"""CLI sub-command: split a snapshot into time-based windows."""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronsight.snapshot import load_snapshot, SnapshotError
from cronsight.splitter import SplitterError, SplitReport, split_report, WindowSize


def _add_splitter_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "split",
        help="Split a snapshot into hourly / daily / weekly windows.",
    )
    p.add_argument("snapshot", help="Path to snapshot file.")
    p.add_argument(
        "--window",
        choices=["hourly", "daily", "weekly"],
        default="daily",
        dest="window",
        help="Window size (default: daily).",
    )
    p.add_argument(
        "--min-runs",
        type=int,
        default=0,
        metavar="N",
        help="Only show windows with at least N total runs.",
    )


def _print_split(result: SplitReport, min_runs: int) -> None:
    """Print a formatted table of split windows to stdout.

    Args:
        result:   The SplitReport produced by split_report().
        min_runs: Filter out windows whose total_runs is below this threshold.
    """
    visible = [w for w in result.windows if w.total_runs >= min_runs]
    if not visible:
        print("No windows match the given criteria.")
        return

    print(f"Window size : {result.window_size}")
    print(f"Total windows: {len(visible)}")
    print()
    header = f"{'Window':<22}  {'Jobs':>6}  {'Runs':>8}"
    print(header)
    print("-" * len(header))
    for win in visible:
        print(f"{win.label:<22}  {win.job_count:>6}  {win.total_runs:>8}")


def handle_splitter(args: argparse.Namespace) -> int:
    """Entry point for the 'split' sub-command.

    Loads a snapshot from disk, splits it into time-based windows, and
    prints a summary table.  Returns an exit code suitable for sys.exit().
    """
    try:
        report = load_snapshot(args.snapshot)
    except SnapshotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(f"error: snapshot not found: {args.snapshot}", file=sys.stderr)
        return 1

    window: WindowSize = args.window  # type: ignore[assignment]

    try:
        result = split_report(report, window)
    except SplitterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _print_split(result, min_runs=args.min_runs)
    return 0
