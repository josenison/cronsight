"""Command-line interface for cronsight with optional output filtering."""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from cronsight.config import ConfigError, load_config
from cronsight.filter import FilterCriteria, filter_report
from cronsight.formatter import format_report
from cronsight.runner import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronsight",
        description="Monitor and audit cron job execution history across remote servers.",
    )
    parser.add_argument(
        "config",
        metavar="CONFIG",
        help="Path to the YAML configuration file listing remote servers.",
    )
    parser.add_argument(
        "--server",
        metavar="HOST",
        default=None,
        help="Restrict output to a single server hostname.",
    )
    parser.add_argument(
        "--failed-only",
        action="store_true",
        default=False,
        help="Show only jobs that have at least one failed run.",
    )
    parser.add_argument(
        "--min-runs",
        type=int,
        metavar="N",
        default=None,
        help="Exclude jobs with fewer than N total runs.",
    )
    parser.add_argument(
        "--command",
        metavar="SUBSTR",
        default=None,
        help="Filter jobs whose command contains SUBSTR.",
    )
    parser.add_argument(
        "--max-success-rate",
        type=float,
        metavar="RATE",
        default=None,
        help="Show only jobs with a success rate at or below RATE (0.0–1.0).",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        servers = load_config(args.config)
    except (ConfigError, FileNotFoundError) as exc:
        print(f"cronsight: configuration error: {exc}", file=sys.stderr)
        return 1

    report = run(servers)

    criteria = FilterCriteria(
        server=args.server,
        min_runs=args.min_runs,
        max_success_rate=args.max_success_rate,
        command_contains=args.command,
        failed_only=args.failed_only,
    )
    filtered = filter_report(report, criteria)

    print(format_report(filtered))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
