"""CLI subcommand: scorer-trend — compare job health scores across two snapshots."""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronsight.scorer_trend import ScoreDelta, ScorerTrendError, build_scorer_trend
from cronsight.snapshot import SnapshotError, load_snapshot


def _add_scorer_trend_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "scorer-trend",
        help="Compare job health scores between two snapshots",
    )
    p.add_argument("old_snapshot", help="Path to the older snapshot file")
    p.add_argument("new_snapshot", help="Path to the newer snapshot file")
    p.add_argument(
        "--only-changed",
        action="store_true",
        default=False,
        help="Only show jobs whose score changed",
    )
    p.add_argument(
        "--degraded-only",
        action="store_true",
        default=False,
        help="Only show jobs that degraded",
    )


def _print_deltas(deltas: List[ScoreDelta]) -> None:
    if not deltas:
        print("No score changes found.")
        return
    width = max(len(d.command) for d in deltas)
    for d in deltas:
        arrow = "\033[32m▲\033[0m" if d.improved else ("\033[31m▼\033[0m" if d.degraded else "=")
        print(f"  {arrow}  {d.command:<{width}}  {d.old_score:6.2f} -> {d.new_score:6.2f}  ({d.delta:+.2f})")


def handle_scorer_trend(args: argparse.Namespace) -> int:
    try:
        old_report = load_snapshot(args.old_snapshot)
    except (SnapshotError, FileNotFoundError) as exc:
        print(f"error: cannot load old snapshot: {exc}", file=sys.stderr)
        return 1

    try:
        new_report = load_snapshot(args.new_snapshot)
    except (SnapshotError, FileNotFoundError) as exc:
        print(f"error: cannot load new snapshot: {exc}", file=sys.stderr)
        return 1

    try:
        trend = build_scorer_trend(
            old_report,
            new_report,
            only_changed=args.only_changed,
        )
    except ScorerTrendError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    deltas = trend.deltas
    if args.degraded_only:
        deltas = [d for d in deltas if d.degraded]

    print(f"Score trend: {trend.improved_count} improved, {trend.degraded_count} degraded ({trend.count} total)")
    _print_deltas(deltas)
    return 0
