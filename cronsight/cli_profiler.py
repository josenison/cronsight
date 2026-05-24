"""CLI sub-command: profile — show execution duration statistics."""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronsight.profiler import DurationProfile, ProfileReport, ProfilerError, build_profile
from cronsight.snapshot import SnapshotError, load_snapshot


def _add_profiler_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("profile", help="Show execution duration statistics for cron jobs")
    p.add_argument("snapshot", help="Path to snapshot file")
    p.add_argument(
        "--sort",
        choices=["mean", "max", "count"],
        default="mean",
        help="Sort profiles by this metric (default: mean)",
    )
    p.add_argument("--top", type=int, default=0, help="Show only top N jobs (0 = all)")


def _sort_key(profile: DurationProfile, metric: str) -> float:
    if metric == "max":
        return profile.max_seconds or 0.0
    if metric == "count":
        return float(profile.count)
    return profile.mean_seconds or 0.0


def _print_profiles(profiles: List[DurationProfile]) -> None:
    header = f"{'COMMAND':<40} {'SERVER':<20} {'COUNT':>5} {'MEAN':>8} {'MEDIAN':>8} {'MAX':>8} {'STDDEV':>8}"
    print(header)
    print("-" * len(header))
    for p in profiles:
        mean_s = f"{p.mean_seconds:.1f}s" if p.mean_seconds is not None else "N/A"
        med_s = f"{p.median_seconds:.1f}s" if p.median_seconds is not None else "N/A"
        max_s = f"{p.max_seconds:.1f}s" if p.max_seconds is not None else "N/A"
        std_s = f"{p.stddev_seconds:.1f}s" if p.stddev_seconds is not None else "N/A"
        print(f"{p.command:<40} {p.server:<20} {p.count:>5} {mean_s:>8} {med_s:>8} {max_s:>8} {std_s:>8}")


def handle_profiler(args: argparse.Namespace) -> int:
    try:
        report = load_snapshot(args.snapshot)
    except (SnapshotError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        profile_report: ProfileReport = build_profile(report)
    except ProfilerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    profiles = sorted(
        profile_report.profiles,
        key=lambda p: _sort_key(p, args.sort),
        reverse=True,
    )
    if args.top > 0:
        profiles = profiles[: args.top]

    _print_profiles(profiles)

    slowest = profile_report.slowest
    if slowest and slowest.mean_seconds is not None:
        print(f"\nSlowest job (by mean): {slowest}")

    return 0
