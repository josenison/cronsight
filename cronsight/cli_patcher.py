"""CLI subcommand: detect command patches between two snapshots."""

from __future__ import annotations

import argparse
from typing import Optional

from cronsight.patcher import PatcherError, detect_patches
from cronsight.snapshot import SnapshotError, load_snapshot


def _add_patcher_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "patch",
        help="Detect jobs whose commands changed between two snapshots.",
    )
    p.add_argument("old_snapshot", help="Path to the older snapshot file.")
    p.add_argument("new_snapshot", help="Path to the newer snapshot file.")
    p.add_argument(
        "--server",
        default=None,
        metavar="HOST",
        help="Limit detection to a specific server.",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output; exit code 1 if patches found.",
    )


def handle_patcher(args: argparse.Namespace) -> int:
    try:
        old_report = load_snapshot(args.old_snapshot)
    except (SnapshotError, FileNotFoundError) as exc:
        print(f"error: cannot load old snapshot: {exc}")
        return 1

    try:
        new_report = load_snapshot(args.new_snapshot)
    except (SnapshotError, FileNotFoundError) as exc:
        print(f"error: cannot load new snapshot: {exc}")
        return 1

    try:
        report = detect_patches(
            old_report,
            new_report,
            server=getattr(args, "server", None),
        )
    except PatcherError as exc:
        print(f"error: {exc}")
        return 1

    if not report.has_patches:
        if not getattr(args, "quiet", False):
            print("No command patches detected.")
        return 0

    if not getattr(args, "quiet", False):
        print(f"Detected {report.count} patch(es):")
        for patch in report.patches:
            print(f"  {patch}")

    return 1
