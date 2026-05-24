"""CLI sub-command: forecast upcoming cron job runs."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from cronsight.forecaster import forecast, ForecasterError
from cronsight.snapshot import load_snapshot, SnapshotError


def _add_forecaster_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "forecast",
        help="Forecast upcoming execution windows for monitored cron jobs.",
    )
    p.add_argument("snapshot", help="Path to a cronsight snapshot file.")
    p.add_argument(
        "--expressions",
        required=True,
        help="JSON file mapping command -> cron expression.",
    )
    p.add_argument(
        "--horizon",
        type=int,
        default=5,
        help="Number of upcoming runs to show per job (default: 5).",
    )
    p.add_argument(
        "--overdue-only",
        action="store_true",
        help="Show only jobs that appear overdue.",
    )


def _print_forecast(report, overdue_only: bool) -> None:  # pragma: no cover
    for window in report.windows:
        if overdue_only and not window.overdue:
            continue
        status = " [OVERDUE]" if window.overdue else ""
        last = window.last_seen.isoformat() if window.last_seen else "never"
        print(f"\n{window.command}{status}")
        print(f"  Expression : {window.expression}")
        print(f"  Last seen  : {last}")
        print(f"  Upcoming   :")
        for ts in window.next_runs:
            print(f"    - {ts.isoformat()}")


def handle_forecaster(args: argparse.Namespace) -> int:
    try:
        report = load_snapshot(args.snapshot)
    except SnapshotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(f"error: snapshot not found: {args.snapshot}", file=sys.stderr)
        return 1

    try:
        with open(args.expressions) as fh:
            expressions: dict = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error loading expressions: {exc}", file=sys.stderr)
        return 1

    try:
        forecast_report = forecast(report, expressions, horizon=args.horizon)
    except ForecasterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _print_forecast(forecast_report, overdue_only=args.overdue_only)

    if forecast_report.overdue_count:
        print(f"\n{forecast_report.overdue_count} job(s) appear overdue.", file=sys.stderr)
        return 2
    return 0
