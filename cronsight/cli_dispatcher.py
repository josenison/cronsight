"""CLI subcommand for dispatching alerts from a snapshot."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from cronsight.alerting import AlertRule, evaluate_summary
from cronsight.dispatcher import DispatchChannel, DispatcherError, dispatch
from cronsight.snapshot import SnapshotError, load_snapshot


def _add_dispatcher_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("dispatch", help="Dispatch alerts to configured channels")
    p.add_argument("snapshot", help="Path to snapshot file")
    p.add_argument(
        "--channel",
        dest="channels",
        action="append",
        default=[],
        metavar="NAME:KIND:SEVERITY",
        help="Channel spec, e.g. main:stdout:warning",
    )
    p.add_argument("--min-failure-rate", type=float, default=0.5)
    p.add_argument("--consecutive-failures", type=int, default=3)


def _parse_channel(spec: str) -> DispatchChannel:
    parts = spec.split(":")
    if len(parts) != 3:
        raise DispatcherError(f"Invalid channel spec: {spec!r}")
    return DispatchChannel(name=parts[0], kind=parts[1], min_severity=parts[2])


def handle_dispatcher(args: argparse.Namespace) -> int:
    snapshot_path = Path(args.snapshot)
    if not snapshot_path.exists():
        print(f"error: snapshot not found: {snapshot_path}", file=sys.stderr)
        return 1

    try:
        report = load_snapshot(snapshot_path)
    except SnapshotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        channels = [_parse_channel(s) for s in args.channels] if args.channels else [
            DispatchChannel(name="default", kind="stdout", min_severity="warning")
        ]
    except DispatcherError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    rule = AlertRule(
        min_failure_rate=args.min_failure_rate,
        consecutive_failures=args.consecutive_failures,
    )
    alerts = []
    for summary in report.jobs.values():
        alerts.extend(evaluate_summary(summary, rule))

    try:
        results = dispatch(alerts, channels, report)
    except DispatcherError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for r in results:
        print(r)
    return 0
