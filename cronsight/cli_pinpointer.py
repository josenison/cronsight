"""CLI subcommand: pinpoint — find jobs with concentrated failures in a time window."""
from __future__ import annotations

import argparse
from datetime import datetime
from typing import Optional

from cronsight.pinpointer import PinpointReport, PinpointerError, pinpoint
from cronsight.snapshot import SnapshotError, load_snapshot


def _add_pinpointer_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "pinpoint",
        help="Identify jobs with the highest failure concentration in a time window",
    )
    p.add_argument("snapshot", help="Path to snapshot file")
    p.add_argument("--since", metavar="DATETIME", help="Start of window (ISO 8601)")
    p.add_argument("--until", metavar="DATETIME", help="End of window (ISO 8601)")
    p.add_argument(
        "--min-failures",
        type=int,
        default=1,
        metavar="N",
        help="Minimum failures to include a job (default: 1)",
    )


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid datetime: {value!r}") from exc


def _print_report(report: PinpointReport) -> None:
    if not report.clusters:
        print("No failure clusters found.")
        return
    print(f"{'COMMAND':<40} {'SERVER':<20} {'FAILURES':>8} {'TOTAL':>6} {'RATE':>6}")
    print("-" * 84)
    for c in report.clusters:
        print(
            f"{c.command:<40} {c.server:<20} "
            f"{c.failures_in_window:>8} {c.total_in_window:>6} "
            f"{c.failure_rate:>5.0%}"
        )


def handle_pinpointer(args: argparse.Namespace) -> int:
    try:
        report = load_snapshot(args.snapshot)
    except FileNotFoundError:
        print(f"Snapshot not found: {args.snapshot}")
        return 1
    except SnapshotError as exc:
        print(f"Snapshot error: {exc}")
        return 1

    try:
        since = _parse_dt(getattr(args, "since", None))
        until = _parse_dt(getattr(args, "until", None))
    except argparse.ArgumentTypeError as exc:
        print(str(exc))
        return 1

    try:
        result = pinpoint(report, since=since, until=until, min_failures=args.min_failures)
    except PinpointerError as exc:
        print(f"Pinpointer error: {exc}")
        return 1

    _print_report(result)
    return 0
