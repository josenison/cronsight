"""CLI sub-command: cronsight audit — report jobs that have gone silent."""
from __future__ import annotations

import argparse
import sys
from datetime import timezone

from cronsight.auditor import AuditorError, audit_report
from cronsight.snapshot import SnapshotError, load_snapshot


def _add_auditor_subparser(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser("audit", help="List jobs that have gone silent")
    p.add_argument("snapshot", help="Path to snapshot file")
    p.add_argument(
        "--threshold",
        type=float,
        default=24.0,
        metavar="HOURS",
        help="Hours of silence before a job is flagged (default: 24)",
    )
    p.add_argument(
        "--fail-on-silent",
        action="store_true",
        help="Exit with code 2 when silent jobs are found",
    )


def handle_auditor(args: argparse.Namespace) -> int:
    try:
        report = load_snapshot(args.snapshot)
    except FileNotFoundError:
        print(f"error: snapshot not found: {args.snapshot}", file=sys.stderr)
        return 1
    except SnapshotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        audit = audit_report(report, threshold_hours=args.threshold)
    except AuditorError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not audit.has_silent_jobs:
        print(f"All jobs ran within the last {audit.threshold_hours:.1f}h — no silent jobs.")
        return 0

    print(f"Silent jobs (threshold: {audit.threshold_hours:.1f}h):")
    for job in audit.silent_jobs:
        print(f"  {job}")

    return 2 if args.fail_on_silent else 0
