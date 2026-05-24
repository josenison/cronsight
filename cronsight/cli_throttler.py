"""CLI subcommand: throttler — detect jobs running too frequently."""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronsight.snapshot import load_snapshot, SnapshotError
from cronsight.throttler import ThrottleViolation, detect_throttle_violations, ThrottlerError


def _add_throttler_subparser(subparsers) -> None:
    p = subparsers.add_parser(
        "throttler",
        help="Detect cron jobs that ran more than N times within a time window.",
    )
    p.add_argument("snapshot", help="Path to snapshot file.")
    p.add_argument(
        "--threshold",
        type=int,
        default=10,
        metavar="N",
        help="Maximum allowed runs within the window (default: 10).",
    )
    p.add_argument(
        "--window",
        type=int,
        default=60,
        metavar="MINUTES",
        help="Sliding window in minutes (default: 60).",
    )
    p.add_argument(
        "--fail-on-violations",
        action="store_true",
        help="Exit with code 1 if any violations are found.",
    )
    p.set_defaults(func=handle_throttler)


def _print_violations(violations: List[ThrottleViolation]) -> None:
    for v in violations:
        print(f"  [THROTTLE] {v}")


def handle_throttler(args: argparse.Namespace) -> int:
    try:
        report = load_snapshot(args.snapshot)
    except SnapshotError as exc:
        print(f"error: could not load snapshot: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(f"error: snapshot not found: {args.snapshot}", file=sys.stderr)
        return 1

    try:
        result = detect_throttle_violations(
            report,
            threshold=args.threshold,
            window_minutes=args.window,
        )
    except ThrottlerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not result.has_violations:
        print("No throttle violations detected.")
        return 0

    print(f"Throttle violations ({result.violation_count}):")
    _print_violations(result.violations)

    if args.fail_on_violations:
        return 1
    return 0
