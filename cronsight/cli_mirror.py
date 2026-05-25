"""CLI sub-command: mirror — compare two snapshots side-by-side."""
from __future__ import annotations
import argparse
import sys
from cronsight.snapshot import load_snapshot, SnapshotError
from cronsight.mirror import mirror_reports, MirrorError


def _add_mirror_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "mirror",
        help="Compare job execution patterns across two snapshots",
    )
    p.add_argument("left", help="Path to the left (baseline) snapshot")
    p.add_argument("right", help="Path to the right (current) snapshot")
    p.add_argument(
        "--divergent-only",
        action="store_true",
        default=False,
        help="Show only rows where success rates diverge or jobs are missing",
    )


def _print_report(report, divergent_only: bool) -> None:
    rows = report.divergent_rows if divergent_only else report.rows
    if not rows:
        print("No differences found.")
        return
    for row in rows:
        print(str(row))
    print(f"\n{len(rows)} row(s) shown  |  {len(report.divergent_rows)} divergent")


def handle_mirror(args: argparse.Namespace) -> int:
    try:
        left_report = load_snapshot(args.left)
    except (SnapshotError, FileNotFoundError) as exc:
        print(f"error: cannot load left snapshot: {exc}", file=sys.stderr)
        return 1

    try:
        right_report = load_snapshot(args.right)
    except (SnapshotError, FileNotFoundError) as exc:
        print(f"error: cannot load right snapshot: {exc}", file=sys.stderr)
        return 1

    try:
        mirror = mirror_reports(left_report, right_report)
    except MirrorError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _print_report(mirror, divergent_only=args.divergent_only)
    return 0
