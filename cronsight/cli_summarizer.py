"""CLI sub-command: summarize — print a text summary of a snapshot."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronsight.snapshot import SnapshotError, load_snapshot
from cronsight.summarizer import render_text_summary


def _add_summarizer_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "summarize",
        help="Print a plain-text summary of a saved snapshot.",
    )
    parser.add_argument(
        "snapshot",
        metavar="SNAPSHOT",
        help="Path to the snapshot JSON file.",
    )
    parser.add_argument(
        "--server",
        metavar="SERVER",
        default=None,
        help="Filter output to a specific server.",
    )


def handle_summarizer(args: argparse.Namespace) -> int:
    snapshot_path = Path(args.snapshot)

    try:
        report = load_snapshot(snapshot_path)
    except (SnapshotError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.server:
        filtered_jobs = {
            k: v
            for k, v in report.jobs.items()
            if v.server == args.server
        }
        if not filtered_jobs:
            print(
                f"No jobs found for server '{args.server}'.",
                file=sys.stderr,
            )
            return 1
        from cronsight.aggregator import AggregatedReport
        report = AggregatedReport(jobs=filtered_jobs)

    print(render_text_summary(report))
    return 0
