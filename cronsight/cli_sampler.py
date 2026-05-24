"""cli_sampler.py — CLI subcommand for sampling job execution entries."""

from __future__ import annotations

import argparse
import sys

from cronsight.sampler import SamplerError, sample_report
from cronsight.snapshot import SnapshotError, load_snapshot


def _add_sampler_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "sample",
        help="sample a fixed number of execution entries per job",
    )
    p.add_argument("snapshot", help="path to snapshot file")
    p.add_argument(
        "-n",
        "--size",
        type=int,
        default=10,
        metavar="N",
        help="number of entries to sample per job (default: 10)",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="SEED",
        help="random seed for reproducibility",
    )
    p.set_defaults(func=handle_sampler)


def _print_sample(result, file=sys.stdout) -> None:
    print(
        f"Sampled {result.count} job(s) "
        f"(n={result.sample_size}, seed={result.seed})",
        file=file,
    )
    for job in result.jobs:
        print(f"  {job}", file=file)


def handle_sampler(args: argparse.Namespace) -> int:
    try:
        report = load_snapshot(args.snapshot)
    except FileNotFoundError:
        print(f"error: snapshot not found: {args.snapshot}", file=sys.stderr)
        return 1
    except SnapshotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        result = sample_report(report, n=args.size, seed=args.seed)
    except SamplerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _print_sample(result)
    return 0
