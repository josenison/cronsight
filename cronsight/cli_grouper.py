"""CLI sub-command for grouping and displaying a snapshot by a chosen key."""

from __future__ import annotations

import argparse
import sys
from typing import List

from cronsight.grouper import GrouperError, group_report
from cronsight.snapshot import SnapshotError, load_snapshot


def _add_grouper_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    parser = subparsers.add_parser(
        "group",
        help="Group jobs in a snapshot by server, command, or status.",
    )
    parser.add_argument("snapshot", help="Path to the snapshot JSON file.")
    parser.add_argument(
        "--by",
        dest="key",
        default="server",
        choices=["server", "command", "status"],
        help="Grouping key (default: server).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="List individual job commands within each group.",
    )


def handle_grouper(args: argparse.Namespace) -> int:
    """Execute the 'group' sub-command.

    Returns:
        0 on success, 1 on error.
    """
    try:
        report = load_snapshot(args.snapshot)
    except (SnapshotError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        grouped = group_report(report, args.key)
    except GrouperError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not grouped.groups:
        print("No jobs found in snapshot.")
        return 0

    print(f"Grouped by: {grouped.key}")
    print()

    for name in grouped.group_names():
        group = grouped.groups[name]
        print(f"  [{name}]  jobs={group.job_count}  total_runs={group.total_runs}")
        if args.verbose:
            for summary in group.summaries:
                print(f"    - {summary.command}")

    return 0
