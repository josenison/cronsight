"""CLI sub-command: escalate — surface jobs with sustained failure streaks."""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronsight.escalator import EscalationRule, EscalatorError, escalate_report
from cronsight.snapshot import SnapshotError, load_snapshot


def _add_escalator_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "escalate",
        help="List jobs whose consecutive failure count exceeds a threshold.",
    )
    p.add_argument("snapshot", help="Path to a snapshot JSON file.")
    p.add_argument(
        "--threshold",
        type=int,
        default=3,
        metavar="N",
        help="Consecutive-failure threshold (default: 3).",
    )
    p.add_argument(
        "--label",
        default="CRITICAL",
        metavar="LABEL",
        help="Severity label applied when threshold is met (default: CRITICAL).",
    )


def handle_escalator(args: argparse.Namespace) -> int:
    try:
        report = load_snapshot(args.snapshot)
    except FileNotFoundError:
        print(f"error: snapshot not found: {args.snapshot}", file=sys.stderr)
        return 1
    except SnapshotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        rules: List[EscalationRule] = [
            EscalationRule(threshold=args.threshold, label=args.label)
        ]
        result = escalate_report(report, rules)
    except EscalatorError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not result.escalated:
        print("No escalated jobs found.")
        return 0

    print(f"{'COMMAND':<40} {'SERVER':<20} {'FAILURES':>8}  LABEL")
    print("-" * 78)
    for job in result.escalated:
        print(
            f"{job.command:<40} {job.server:<20} {job.consecutive_failures:>8}  {job.label}"
        )
    return 0
