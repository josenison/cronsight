"""CLI sub-command: cronsight watch — live monitoring mode."""

from __future__ import annotations

import argparse
import sys
from typing import List

from cronsight.config import ConfigError, load_config
from cronsight.formatter import format_report
from cronsight.runner import collect_from_servers
from cronsight.watcher import WatchConfig, WatchIteration, WatcherError, watch


def _add_watcher_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("watch", help="Continuously monitor cron job changes")
    p.add_argument("--config", required=True, help="Path to server config file")
    p.add_argument(
        "--interval",
        type=int,
        default=60,
        metavar="SECONDS",
        help="Polling interval in seconds (default: 60)",
    )
    p.add_argument(
        "--iterations",
        type=int,
        default=None,
        metavar="N",
        help="Stop after N iterations (default: run forever)",
    )
    p.add_argument(
        "--changes-only",
        action="store_true",
        help="Only print output when changes are detected",
    )


def handle_watcher(args: argparse.Namespace) -> int:
    try:
        servers = load_config(args.config)
    except (ConfigError, FileNotFoundError) as exc:
        print(f"[cronsight] config error: {exc}", file=sys.stderr)
        return 1

    try:
        cfg = WatchConfig(
            interval_seconds=args.interval,
            max_iterations=args.iterations,
        )
    except WatcherError as exc:
        print(f"[cronsight] watch config error: {exc}", file=sys.stderr)
        return 1

    changes_only: bool = getattr(args, "changes_only", False)

    def collect():
        return collect_from_servers(servers)

    def on_iteration(it: WatchIteration) -> None:
        header = f"[{it.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC] iteration #{it.index + 1}"
        if changes_only and not it.changed:
            return
        print(header)
        if it.diff is not None:
            added = ", ".join(it.diff.added_jobs) or "none"
            removed = ", ".join(it.diff.removed_jobs) or "none"
            changed = ", ".join(it.diff.changed_jobs) or "none"
            print(f"  added={added}  removed={removed}  changed={changed}")
        print(format_report(it.report))
        print()

    watch(collect, cfg, on_iteration)
    return 0
