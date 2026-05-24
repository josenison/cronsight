"""CLI sub-command: score — rank jobs by reliability score."""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronsight.scorer import ScoredJob, ScoredReport, score_report
from cronsight.snapshot import SnapshotError, load_snapshot


def _add_scorer_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("score", help="Rank jobs by reliability score")
    p.add_argument("snapshot", help="Path to snapshot file")
    p.add_argument(
        "--top",
        type=int,
        default=None,
        metavar="N",
        help="Show only the N lowest-scoring jobs",
    )
    p.add_argument(
        "--min-score",
        type=float,
        default=None,
        metavar="S",
        help="Exclude jobs with score >= S",
    )


def _print_scored(jobs: List[ScoredJob]) -> None:
    header = f"{'COMMAND':<40} {'SERVER':<16} {'SCORE':>6}  {'SUCCESS':>8}  {'RUNS':>5}  RECENT_FAIL"
    print(header)
    print("-" * len(header))
    for j in jobs:
        flag = "YES" if j.has_recent_failure else "no"
        print(
            f"{j.command:<40} {j.server:<16} {j.score:>6.1f}"
            f"  {j.success_rate * 100:>7.1f}%  {j.total_runs:>5}  {flag}"
        )


def handle_scorer(args: argparse.Namespace) -> int:
    try:
        report = load_snapshot(args.snapshot)
    except (SnapshotError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    scored: ScoredReport = score_report(report)
    jobs = scored.jobs

    if args.min_score is not None:
        jobs = [j for j in jobs if j.score < args.min_score]

    if args.top is not None:
        jobs = jobs[: args.top]

    if not jobs:
        print("No jobs match the given criteria.")
        return 0

    _print_scored(jobs)
    return 0
