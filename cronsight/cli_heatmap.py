"""CLI subcommand: heatmap — show hour-of-day execution heatmap."""

from __future__ import annotations

import argparse
import sys
from typing import List

from cronsight.heatmap import JobHeatmap, build_heatmap
from cronsight.snapshot import SnapshotError, load_snapshot

_BLOCK_CHARS = [" ", "░", "▒", "▓", "█"]


def _add_heatmap_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("heatmap", help="Show hour-of-day execution heatmap")
    p.add_argument("snapshot", help="Path to snapshot file")
    p.add_argument(
        "--job",
        dest="job_filter",
        default=None,
        help="Filter to a specific job command substring",
    )
    p.add_argument(
        "--no-color",
        action="store_true",
        default=False,
        help="Disable colored output",
    )


def _render_row(hm: JobHeatmap, no_color: bool) -> str:
    max_runs = max((b.run_count for b in hm.buckets), default=1) or 1
    cells: List[str] = []
    for b in hm.buckets:
        intensity = int((b.run_count / max_runs) * (len(_BLOCK_CHARS) - 1))
        char = _BLOCK_CHARS[intensity]
        if not no_color and b.run_count > 0 and b.failure_rate > 0.3:
            char = f"\033[31m{char}\033[0m"
        cells.append(char)
    return "".join(cells)


def handle_heatmap(args: argparse.Namespace) -> int:
    try:
        report = load_snapshot(args.snapshot)
    except (SnapshotError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    heatmap = build_heatmap(report)

    if not heatmap.jobs:
        print("No jobs found in snapshot.", file=sys.stderr)
        return 1

    header = "Command" + " " * 30 + "00                   12                   23"
    print(header)
    print("-" * len(header))

    for command, hm in sorted(heatmap.jobs.items()):
        if args.job_filter and args.job_filter not in command:
            continue
        label = command[:36].ljust(37)
        row = _render_row(hm, args.no_color)
        peak = hm.peak_hour
        print(f"{label} {row}  peak={peak:02d}h")

    return 0
