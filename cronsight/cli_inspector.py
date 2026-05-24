"""CLI subcommand: inspect — show per-job execution timeline and gap analysis."""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronsight.inspector import InspectionReport, inspect_report, InspectorError
from cronsight.snapshot import load_snapshot, SnapshotError


def _add_inspector_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "inspect",
        help="Detailed per-job execution timeline and gap detection.",
    )
    p.add_argument("snapshot", help="Path to snapshot file.")
    p.add_argument(
        "--job",
        metavar="COMMAND",
        default=None,
        help="Inspect a specific job command (substring match).",
    )
    p.add_argument(
        "--gap-threshold",
        type=float,
        default=3600.0,
        metavar="SECONDS",
        help="Minimum gap duration in seconds to report (default: 3600).",
    )
    p.add_argument(
        "--show-gaps",
        action="store_true",
        default=False,
        help="Print individual gap details.",
    )


def _print_inspection(report: InspectionReport, job_filter: str | None, show_gaps: bool) -> None:
    inspections = report.inspections
    if job_filter:
        inspections = [i for i in inspections if job_filter in i.command]
    if not inspections:
        print("No matching jobs found.")
        return
    for insp in inspections:
        rate = f"{insp.success_rate * 100:.1f}%"
        first = insp.first_run.strftime("%Y-%m-%d %H:%M:%S") if insp.first_run else "N/A"
        last = insp.last_run.strftime("%Y-%m-%d %H:%M:%S") if insp.last_run else "N/A"
        avg_gap = f"{insp.avg_gap_seconds:.0f}s" if insp.avg_gap_seconds is not None else "N/A"
        print(f"Job      : {insp.command}")
        print(f"Servers  : {', '.join(insp.servers) or 'N/A'}")
        print(f"Runs     : {insp.total_runs} (ok={insp.success_runs}, fail={insp.failure_runs})")
        print(f"Rate     : {rate}")
        print(f"First    : {first}")
        print(f"Last     : {last}")
        print(f"Gaps     : {len(insp.gaps)} (avg={avg_gap})")
        if show_gaps:
            for gap in insp.gaps:
                print(f"  {gap}")
        print()


def handle_inspector(args: argparse.Namespace) -> int:
    try:
        report = load_snapshot(args.snapshot)
    except (SnapshotError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    try:
        inspection = inspect_report(report, gap_threshold_seconds=args.gap_threshold)
    except InspectorError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    _print_inspection(inspection, job_filter=args.job, show_gaps=args.show_gaps)
    return 0
