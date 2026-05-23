"""Collects cron log data from remote servers via SSH."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Optional

from cronsight.parser import CronEntry, parse_cron_log


@dataclass
class ServerConfig:
    host: str
    user: str
    port: int = 22
    identity_file: Optional[str] = None
    log_path: str = "/var/log/syslog"

    def ssh_args(self) -> list[str]:
        args = ["ssh", "-p", str(self.port), "-o", "StrictHostKeyChecking=no"]
        if self.identity_file:
            args += ["-i", self.identity_file]
        args.append(f"{self.user}@{self.host}")
        return args


@dataclass
class CollectionResult:
    server: str
    entries: list[CronEntry] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


def fetch_cron_log(config: ServerConfig, lines: int = 500) -> CollectionResult:
    """SSH into a server and retrieve the last N lines of the cron log."""
    cmd = config.ssh_args() + [f"tail -n {lines} {config.log_path}"]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return CollectionResult(
                server=config.host,
                error=result.stderr.strip() or "Non-zero exit code",
            )
        entries = parse_cron_log(result.stdout)
        return CollectionResult(server=config.host, entries=entries)
    except subprocess.TimeoutExpired:
        return CollectionResult(server=config.host, error="SSH connection timed out")
    except FileNotFoundError:
        return CollectionResult(server=config.host, error="ssh binary not found")
    except Exception as exc:  # noqa: BLE001
        return CollectionResult(server=config.host, error=str(exc))


def collect_from_servers(configs: list[ServerConfig], lines: int = 500) -> list[CollectionResult]:
    """Collect cron log entries from multiple servers sequentially."""
    return [fetch_cron_log(cfg, lines=lines) for cfg in configs]
