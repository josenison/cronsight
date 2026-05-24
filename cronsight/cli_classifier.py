"""CLI sub-command: classify — group jobs by category using pattern rules."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cronsight.classifier import ClassRule, ClassifierError, classify_report
from cronsight.snapshot import SnapshotError, load_snapshot


def _add_classifier_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    parser = subparsers.add_parser(
        "classify",
        help="Classify jobs into categories using regex rules from a JSON config.",
    )
    parser.add_argument("snapshot", help="Path to a snapshot file.")
    parser.add_argument(
        "--rules",
        required=True,
        metavar="FILE",
        help="JSON file containing a list of {category, pattern} objects.",
    )
    parser.add_argument(
        "--default-category",
        default="uncategorized",
        metavar="LABEL",
        help="Category assigned to jobs that match no rule (default: uncategorized).",
    )


def _load_rules(path: str) -> list[ClassRule]:
    raw = json.loads(Path(path).read_text())
    if not isinstance(raw, list):
        raise ClassifierError("rules file must contain a JSON array")
    rules = []
    for item in raw:
        rules.append(ClassRule(category=item["category"], pattern=item["pattern"]))
    return rules


def handle_classifier(args: argparse.Namespace) -> int:
    try:
        report = load_snapshot(args.snapshot)
    except (SnapshotError, FileNotFoundError) as exc:
        print(f"error: {exc}")
        return 1

    try:
        rules = _load_rules(args.rules)
    except (ClassifierError, KeyError, json.JSONDecodeError, OSError) as exc:
        print(f"error loading rules: {exc}")
        return 1

    try:
        classified = classify_report(report, rules, default_category=args.default_category)
    except ClassifierError as exc:
        print(f"error: {exc}")
        return 1

    for category in classified.categories:
        jobs = classified.jobs_in(category)
        print(f"\n[{category}] ({len(jobs)} job(s))")
        for job in jobs:
            total = job.summary.total_runs
            sr = (
                round(100 * job.summary.successful_runs / total)
                if total
                else 0
            )
            print(f"  {job.summary.command}  runs={total}  success={sr}%")

    return 0
