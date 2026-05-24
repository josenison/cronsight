"""CLI subcommand: detect outlier jobs from a snapshot."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from cronsight.outlier import OutlierError, detect_outliers
from cronsight.snapshot import SnapshotError, load_snapshot


def _add_outlier_subparser(subparsers: Any) -> None:
    p = subparsers.add_parser(
        "outliers",
        help="Detect jobs with abnormal success rates",
    )
    p.add_argument("snapshot", help="Path to snapshot file")
    p.add_argument(
        "--z-threshold",
        type=float,
        default=2.0,
        metavar="Z",
        help="Z-score threshold for flagging outliers (default: 2.0)",
    )
    p.add_argument(
        "--min-runs",
        type=int,
        default=2,
        metavar="N",
        help="Minimum runs required to consider a job (default: 2)",
    )


def handle_outlier(args: argparse.Namespace) -> int:
    try:
        report = load_snapshot(args.snapshot)
    except (SnapshotError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        result = detect_outliers(
            report,
            z_threshold=args.z_threshold,
            min_runs=args.min_runs,
        )
    except OutlierError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not result.has_outliers():
        print("No outliers detected.")
        return 0

    print(f"Outliers detected: {result.count}")
    print(f"{'Command':<40} {'Server':<20} {'Runs':>6} {'Success':>8} {'Z':>7}  Reason")
    print("-" * 90)
    for o in result.outliers:
        print(
            f"{o.command:<40} {o.server:<20} {o.total_runs:>6} "
            f"{o.success_rate:>7.0%} {o.z_score:>7.2f}  {o.reason}"
        )
    return 0
