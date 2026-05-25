"""CLI subcommand for tracing cron job execution paths."""
from __future__ import annotations

import argparse
import sys

from cronsight.snapshot import load_snapshot, SnapshotError
from cronsight.tracer import build_trace, TracerError


def _add_tracer_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "trace",
        help="Trace execution events for cron jobs across servers.",
    )
    p.add_argument("snapshot", help="Path to snapshot file.")
    p.add_argument(
        "--command",
        default=None,
        metavar="PATTERN",
        help="Filter traces to commands containing PATTERN.",
    )
    p.add_argument(
        "--failures-only",
        action="store_true",
        help="Show only failure events.",
    )
    p.set_defaults(func=handle_tracer)


def _print_trace_report(report, failures_only: bool) -> None:
    if report.job_count == 0:
        print("No matching jobs found.")
        return

    for cmd, trace in sorted(report.traces.items()):
        print(f"\n{'='*60}")
        print(f"Job : {cmd}")
        print(f"Servers: {', '.join(trace.servers)}")
        print(f"Events : {trace.event_count}  Failures: {trace.failure_count}")
        print("-" * 60)
        for event in trace.events:
            if failures_only and event.status != "failure":
                continue
            print(f"  {event}")


def handle_tracer(args: argparse.Namespace) -> int:
    try:
        report = load_snapshot(args.snapshot)
    except FileNotFoundError:
        print(f"Error: snapshot not found: {args.snapshot}", file=sys.stderr)
        return 1
    except SnapshotError as exc:
        print(f"Error loading snapshot: {exc}", file=sys.stderr)
        return 1

    try:
        trace_report = build_trace(report, command_filter=args.command)
    except TracerError as exc:
        print(f"Trace error: {exc}", file=sys.stderr)
        return 1

    _print_trace_report(trace_report, failures_only=args.failures_only)
    return 0
