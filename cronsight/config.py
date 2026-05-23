"""Load and validate cronsight server configuration from a TOML file."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from cronsight.collector import ServerConfig

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "cronsight" / "servers.toml"


class ConfigError(Exception):
    pass


def _parse_server(raw: dict[str, Any], name: str) -> ServerConfig:
    required = ("host", "user")
    for key in required:
        if key not in raw:
            raise ConfigError(f"Server '{name}' is missing required field '{key}'")
    return ServerConfig(
        host=raw["host"],
        user=raw["user"],
        port=int(raw.get("port", 22)),
        identity_file=raw.get("identity_file"),
        log_path=raw.get("log_path", "/var/log/syslog"),
    )


def load_config(path: Path | str | None = None) -> list[ServerConfig]:
    """Load server definitions from a TOML config file.

    Expected format::

        [servers.web1]
        host = "192.168.1.10"
        user = "admin"
        port = 22
        log_path = "/var/log/syslog"
    """
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    with config_path.open("rb") as fh:
        data = tomllib.load(fh)

    servers_raw = data.get("servers", {})
    if not servers_raw:
        raise ConfigError("No servers defined in config file")

    return [_parse_server(raw, name) for name, raw in servers_raw.items()]
