"""CLI sub-command: segment — split a snapshot into time buckets."""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronsight.segmenter import Granularity, SegmentReport, SegmenterError, segment_report
from cronsight.snapshot import SnapshotError, load_snapshot

_GRANULARITIES: List[Granularity] = ["hourly", "daily", "weekly"]


def _add_segmenter_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("segment", help="Segment a snapshot into time buckets")
    p.add_argument("snapshot", help="Path to snapshot file")
    p.add_argument(
        "--granularity",
        choices=_GRANULARITIES,
        default="daily",
        help="Bucket size (default: daily)",
    )
    p.add_argument("--top", type=int, default=0, help="Show only the N most recent segments")


def _print_report(report: SegmentReport, top: int) -> None:
    segments = report.segments
    if top > 0:
        segments = segments[-top:]
    print(f"Granularity : {report.granularity}")
    print(f"Segments    : {report.count}")
    print()
    for seg in segments:
        print(f"  [{seg.label}]  jobs={seg.job_count}  runs={seg.total_runs}")
        for cmd, summary in sorted(seg.jobs.items()):
            runs = len(summary.entries)
            failures = sum(1 for e in summary.entries if not e.success)
            print(f"    {cmd}  runs={runs}  failures={failures}")


def handle_segmenter(args: argparse.Namespace) -> int:
    try:
        report = load_snapshot(args.snapshot)
    except FileNotFoundError:
        print(f"error: snapshot not found: {args.snapshot}", file=sys.stderr)
        return 1
    except SnapshotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        seg_report = segment_report(report, granularity=args.granularity)
    except SegmenterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _print_report(seg_report, top=args.top)
    return 0
