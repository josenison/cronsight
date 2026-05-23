"""CLI sub-command: tag — annotate jobs in a snapshot with user-defined tags."""
from __future__ import annotations

import json
import sys
from argparse import ArgumentParser, Namespace
from typing import List

from cronsight.snapshot import load_snapshot, SnapshotError
from cronsight.tagging import TagRule, TaggingError, tag_report


def _add_tagging_subparser(subparsers) -> None:  # type: ignore[type-arg]
    p: ArgumentParser = subparsers.add_parser(
        "tag",
        help="Annotate cron jobs from a snapshot with custom tags.",
    )
    p.add_argument("snapshot", help="Path to the snapshot JSON file.")
    p.add_argument(
        "--rules",
        required=True,
        help="JSON file containing a list of {tag, pattern} rule objects.",
    )
    p.add_argument(
        "--output",
        default="-",
        help="Output file path (default: stdout).",
    )


def handle_tagging(args: Namespace) -> int:
    # Load snapshot
    try:
        report = load_snapshot(args.snapshot)
    except SnapshotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    # Load rules
    try:
        with open(args.rules) as fh:
            raw = json.load(fh)
        if not isinstance(raw, list):
            raise TaggingError("Rules file must contain a JSON array.")
        from cronsight.tagging import rules_from_dict
        rules: List[TagRule] = rules_from_dict(raw)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error reading rules: {exc}", file=sys.stderr)
        return 1
    except TaggingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    # Apply tags
    try:
        tagged = tag_report(report, rules)
    except TaggingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    # Serialise output
    output = {
        "jobs": [
            {
                "command": cmd,
                "tags": tagged.tags_for(cmd),
                "servers": sorted(summary.servers),
                "total_runs": summary.total_runs,
            }
            for cmd, summary in tagged.report.jobs.items()
        ]
    }

    text = json.dumps(output, indent=2)
    if args.output == "-":
        print(text)
    else:
        with open(args.output, "w") as fh:
            fh.write(text)

    return 0
