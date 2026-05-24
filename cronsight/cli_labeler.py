"""CLI sub-command: label — print per-job severity labels for a snapshot."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from cronsight.labeler import LabelerError, SeverityRule, label_report
from cronsight.snapshot import SnapshotError, load_snapshot


_DEFAULT_RULES: List[SeverityRule] = [
    SeverityRule(label="critical", max_success_rate=0.0),
    SeverityRule(label="warning", max_success_rate=0.79),
]


def _add_labeler_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "label",
        help="Assign severity labels to jobs in a snapshot.",
    )
    p.add_argument("snapshot", help="Path to a .json snapshot file.")
    p.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    p.add_argument(
        "--default-label",
        default="ok",
        metavar="LABEL",
        help="Label used when no severity rule matches (default: ok).",
    )


def handle_labeler(args: argparse.Namespace) -> int:
    """Entry point for the *label* sub-command.  Returns an exit code."""
    try:
        report = load_snapshot(args.snapshot)
    except (SnapshotError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        labeled = label_report(report, _DEFAULT_RULES, default_label=args.default_label)
    except LabelerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(labeled.labels, indent=2))
    else:
        if not labeled.labels:
            print("No jobs found.")
        else:
            col = max(len(cmd) for cmd in labeled.labels)
            for cmd, lbl in sorted(labeled.labels.items()):
                print(f"{cmd:<{col}}  {lbl}")

    return 0
