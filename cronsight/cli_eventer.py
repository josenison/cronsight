"""CLI subcommand: eventer — stream job events from a snapshot."""
from __future__ import annotations

import argparse
import sys

from cronsight.eventer import EventStream, build_event_stream
from cronsight.snapshot import SnapshotError, load_snapshot


def _add_eventer_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("eventer", help="Stream job events from a snapshot")
    p.add_argument("snapshot", help="Path to snapshot file")
    p.add_argument("--server", default=None, help="Filter events by server name")
    p.add_argument("--since", default=None, help="Show events at or after this timestamp (ISO)")
    p.add_argument("--until", default=None, help="Show events at or before this timestamp (ISO)")
    p.add_argument("--failures-only", action="store_true", help="Show only failed events")
    p.set_defaults(func=handle_eventer)


def _print_stream(stream: EventStream, failures_only: bool) -> None:
    for event in stream.events:
        if failures_only and event.status != "failure":
            continue
        print(str(event))
    print(f"\n{stream.count} events | {stream.success_count} passed | {stream.failure_count} failed")


def handle_eventer(args: argparse.Namespace) -> int:
    try:
        report = load_snapshot(args.snapshot)
    except FileNotFoundError:
        print(f"error: snapshot not found: {args.snapshot}", file=sys.stderr)
        return 1
    except SnapshotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    stream = build_event_stream(
        report,
        since=args.since,
        until=args.until,
        server=args.server,
    )
    _print_stream(stream, failures_only=args.failures_only)
    return 0
