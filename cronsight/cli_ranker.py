"""CLI sub-command: rank — list jobs sorted by a chosen metric."""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronsight.ranker import RankerError, RankedJob, rank_report
from cronsight.snapshot import load_snapshot, SnapshotError


def _add_ranker_subparser(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "rank",
        help="Rank jobs by failure rate, run count, or last-run recency.",
    )
    p.add_argument("snapshot", help="Path to a cronsight snapshot file.")
    p.add_argument(
        "--by",
        choices=["failure_rate", "run_count", "last_run"],
        default="failure_rate",
        help="Metric to rank by (default: failure_rate).",
    )
    p.add_argument(
        "--asc",
        action="store_true",
        help="Sort ascending instead of descending.",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Show only the top N results.",
    )


def _print_ranked(jobs: List[RankedJob]) -> None:
    header = f"{'#':<4} {'Command':<40} {'Runs':>6} {'Failures':>10}"
    print(header)
    print("-" * len(header))
    for job in jobs:
        failures = f"{job.failure_rate:.0%}"
        print(f"{job.rank:<4} {job.command:<40} {job.total_runs:>6} {failures:>10}")


def handle_ranker(args: argparse.Namespace) -> int:
    try:
        report = load_snapshot(args.snapshot)
    except SnapshotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        ranked = rank_report(
            report,
            by=args.by,
            descending=not args.asc,
            limit=args.limit,
        )
    except RankerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not ranked:
        print("No jobs found.")
        return 0

    _print_ranked(ranked)
    return 0
