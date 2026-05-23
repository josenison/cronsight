"""CLI subcommand for applying retention policies to snapshots."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronsight.retention import RetentionError, RetentionPolicy, apply_retention
from cronsight.snapshot import SnapshotError, load_snapshot, save_snapshot


def _add_retention_subparser(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    parser = subparsers.add_parser(
        "retain",
        help="Apply a retention policy to a saved snapshot",
    )
    parser.add_argument("snapshot", help="Path to the snapshot file to process")
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=None,
        metavar="DAYS",
        help="Remove entries older than DAYS days",
    )
    parser.add_argument(
        "--max-entries",
        type=int,
        default=None,
        metavar="N",
        help="Keep at most N entries per job (newest first)",
    )
    parser.add_argument(
        "--no-keep-failures",
        action="store_true",
        default=False,
        help="Do not preserve failed entries that would otherwise be pruned by age",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be removed without modifying the snapshot",
    )
    parser.set_defaults(func=handle_retention)


def handle_retention(args: argparse.Namespace) -> int:
    """Handle the 'retain' subcommand. Returns an exit code."""
    snapshot_path = Path(args.snapshot)

    try:
        report = load_snapshot(snapshot_path)
    except SnapshotError as exc:
        print(f"error: could not load snapshot: {exc}", file=sys.stderr)
        return 1

    try:
        policy = RetentionPolicy(
            max_age_days=args.max_age_days,
            max_entries_per_job=args.max_entries,
            keep_failures=not args.no_keep_failures,
        )
    except RetentionError as exc:
        print(f"error: invalid retention policy: {exc}", file=sys.stderr)
        return 1

    result = apply_retention(report, policy)

    if args.dry_run:
        print(f"[dry-run] would remove {result.removed_count} entries")
        if result.jobs_affected:
            for cmd in result.jobs_affected:
                print(f"  affected job: {cmd}")
        return 0

    try:
        save_snapshot(report, snapshot_path)
    except SnapshotError as exc:
        print(f"error: could not save snapshot: {exc}", file=sys.stderr)
        return 1

    print(
        f"Retention applied: removed {result.removed_count} entries "
        f"across {len(result.jobs_affected)} job(s)."
    )
    return 0
