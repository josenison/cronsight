"""CLI subcommand: correlate job execution across snapshots."""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronsight.correlator import CorrelationReport, CorrelatorError, correlate_reports, _success_rate
from cronsight.snapshot import SnapshotError, load_snapshot


def _add_correlator_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "correlate",
        help="Correlate job execution patterns across multiple snapshot files.",
    )
    p.add_argument(
        "snapshots",
        nargs="+",
        metavar="SNAPSHOT",
        help="Two or more snapshot files to correlate.",
    )
    p.add_argument(
        "--inconsistent-only",
        action="store_true",
        default=False,
        help="Show only jobs with inconsistent status across servers.",
    )
    p.set_defaults(func=handle_correlator)


def _print_report(report: CorrelationReport, inconsistent_only: bool) -> None:
    jobs = report.inconsistent_jobs if inconsistent_only else report.correlations
    if not jobs:
        print("No jobs to display.")
        return
    header = f"{'COMMAND':<45} {'SERVERS':>7} {'RUNS':>6} {'SUCCESS':>8} {'CONSISTENT':>11}"
    print(header)
    print("-" * len(header))
    for corr in jobs:
        rate = _success_rate(corr)
        consistent_label = "yes" if corr.consistent else "NO"
        cmd = corr.command[:44]
        print(
            f"{cmd:<45} {len(corr.servers):>7} {corr.total_runs:>6} {rate:>7.0%} {consistent_label:>11}"
        )


def handle_correlator(args: argparse.Namespace) -> int:
    snapshots: List[str] = args.snapshots
    if len(snapshots) < 2:
        print("error: at least two snapshot files are required.", file=sys.stderr)
        return 1

    reports = {}
    for path in snapshots:
        try:
            report = load_snapshot(path)
        except (SnapshotError, FileNotFoundError) as exc:
            print(f"error: could not load snapshot '{path}': {exc}", file=sys.stderr)
            return 1
        reports[path] = report

    try:
        correlation_report = correlate_reports(reports)
    except CorrelatorError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _print_report(correlation_report, inconsistent_only=args.inconsistent_only)
    return 0
