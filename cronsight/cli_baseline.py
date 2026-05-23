"""CLI helpers for the 'baseline' sub-command."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronsight.baseline import compare_to_baseline, format_delta
from cronsight.snapshot import load_snapshot, save_snapshot, SnapshotError
from cronsight.runner import run as collect_run
from cronsight.config import load_config, ConfigError


def _add_baseline_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "baseline",
        help="Save or compare against a baseline snapshot.",
    )
    p.add_argument(
        "action",
        choices=["save", "compare"],
        help="'save' writes the current report as baseline; 'compare' diffs against it.",
    )
    p.add_argument(
        "--baseline-path",
        default=".cronsight_baseline.json",
        metavar="PATH",
        help="Path to the baseline snapshot file (default: .cronsight_baseline.json).",
    )
    p.add_argument(
        "--config",
        default="cronsight.toml",
        metavar="FILE",
        help="Config file listing remote servers.",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=0.05,
        metavar="FLOAT",
        help="Success-rate change threshold for degradation/improvement (default: 0.05).",
    )


def handle_baseline(args: argparse.Namespace) -> int:
    """Execute the baseline sub-command.  Returns an exit code."""
    try:
        servers = load_config(args.config)
    except (ConfigError, FileNotFoundError) as exc:
        print(f"[error] Could not load config: {exc}", file=sys.stderr)
        return 1

    report = collect_run(servers)
    baseline_path = Path(args.baseline_path)

    if args.action == "save":
        try:
            save_snapshot(report, baseline_path)
            print(f"Baseline saved to {baseline_path}")
        except SnapshotError as exc:
            print(f"[error] Failed to save baseline: {exc}", file=sys.stderr)
            return 1
        return 0

    # action == "compare"
    try:
        baseline = load_snapshot(baseline_path)
    except (SnapshotError, FileNotFoundError) as exc:
        print(f"[error] Could not load baseline: {exc}", file=sys.stderr)
        return 1

    delta = compare_to_baseline(baseline, report, degradation_threshold=args.threshold)
    print(format_delta(delta))
    return 1 if delta.has_changes else 0
