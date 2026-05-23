"""Orchestrates parallel log collection and aggregation across servers."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from cronsight.aggregator import AggregatedReport, aggregate_results
from cronsight.collector import CollectionResult, fetch_cron_log
from cronsight.config import load_config, ServerConfig


DEFAULT_WORKERS = 8


def collect_from_servers(
    servers: list[ServerConfig],
    max_workers: int = DEFAULT_WORKERS,
) -> list[CollectionResult]:
    """Fetch cron logs from all servers in parallel."""
    results: list[CollectionResult] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_server = {
            executor.submit(fetch_cron_log, server): server
            for server in servers
        }
        for future in as_completed(future_to_server):
            try:
                results.append(future.result())
            except Exception as exc:  # noqa: BLE001
                server = future_to_server[future]
                results.append(
                    CollectionResult(
                        server=server.host,
                        success=False,
                        output=None,
                        error=str(exc),
                    )
                )

    return results


def run(
    config_path: str,
    max_workers: int = DEFAULT_WORKERS,
) -> AggregatedReport:
    """Load config, collect logs, and return an aggregated report."""
    servers = load_config(config_path)
    results = collect_from_servers(servers, max_workers=max_workers)
    return aggregate_results(results)
